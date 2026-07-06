#!/usr/bin/env python3
"""
ShadowCypher Centralized Audit Daemon

Real-time event collection, normalization, and analysis from multiple sources.
Provides centralized audit logging for enterprise security operations.
"""

import asyncio
import json
import logging
import os
import signal
import socket
import sys
import time
import threading
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor
import queue


class EventSource(Enum):
    """Supported event sources."""
    AUDITD = "auditd"
    SYSLOG = "syslog"
    APPLICATION = "application"
    KERNEL = "kernel"
    GUARDIAN_VAULT = "guardian_vault"
    AUTH_SERVICE = "auth_service"


class EventAction(Enum):
    """Standard event actions."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    VAULT_ACCESS = "vault_access"
    ENCRYPTION_KEY_OPERATION = "encryption_key_operation"
    CONFIGURATION_CHANGE = "configuration_change"
    PRIVILEGE_ESCALATION = "privilege_escalation"


class EventSeverity(Enum):
    """Event severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


@dataclass
class AuditEvent:
    """Normalized audit event structure."""
    event_id: str
    timestamp: str
    source_type: str
    source_name: str
    user_id: str
    action: str
    result_status: str
    category: str
    severity: str
    resource_type: Optional[str] = None
    resource_identifier: Optional[str] = None
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict())


class CircuitBreaker:
    """Circuit breaker for handling failures in external integrations."""

    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        self.lock = threading.Lock()

    def call(self, func: Callable, *args, **kwargs) -> Tuple[bool, Any]:
        """Execute function with circuit breaker protection."""
        with self.lock:
            if self.state == "open":
                if time.time() - self.last_failure_time > self.reset_timeout:
                    self.state = "half-open"
                    self.failure_count = 0
                else:
                    return False, "Circuit breaker open"

            try:
                result = func(*args, **kwargs)
                if self.state == "half-open":
                    self.state = "closed"
                    self.failure_count = 0
                return True, result
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
                return False, str(e)

    def is_open(self) -> bool:
        """Check if circuit is open."""
        with self.lock:
            if self.state == "open":
                if time.time() - self.last_failure_time > self.reset_timeout:
                    return False
                return True
            return False


class LogSource(ABC):
    """Abstract base class for log sources."""

    def __init__(self, name: str, source_type: EventSource):
        self.name = name
        self.source_type = source_type
        self.logger = logging.getLogger(f"source.{name}")

    @abstractmethod
    def read_logs(self) -> List[Dict[str, Any]]:
        """Read logs from source."""
        pass

    @abstractmethod
    def normalize(self, raw_log: Dict[str, Any]) -> Optional[AuditEvent]:
        """Normalize raw log to audit event."""
        pass


class SyslogSource(LogSource):
    """Syslog event source."""

    def __init__(self, host: str = "localhost", port: int = 514):
        super().__init__("syslog", EventSource.SYSLOG)
        self.host = host
        self.port = port
        self.socket = None
        self._connect()

    def _connect(self):
        """Establish syslog socket connection."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.host, self.port))
            self.socket.settimeout(5.0)
            self.logger.info(f"Connected to syslog on {self.host}:{self.port}")
        except Exception as e:
            self.logger.error(f"Failed to connect to syslog: {e}")

    def read_logs(self) -> List[Dict[str, Any]]:
        """Read logs from syslog socket."""
        logs = []
        try:
            while True:
                data, addr = self.socket.recvfrom(4096)
                logs.append({
                    "raw": data.decode('utf-8', errors='ignore'),
                    "source_ip": addr[0],
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
        except socket.timeout:
            pass
        except Exception as e:
            self.logger.error(f"Error reading syslog: {e}")
        return logs

    def normalize(self, raw_log: Dict[str, Any]) -> Optional[AuditEvent]:
        """Normalize syslog entry."""
        try:
            message = raw_log.get("raw", "")
            parts = message.split(": ", 1)

            return AuditEvent(
                event_id=str(uuid.uuid4()),
                timestamp=raw_log.get("timestamp", datetime.utcnow().isoformat() + "Z"),
                source_type=self.source_type.value,
                source_name=self.name,
                user_id=raw_log.get("user", "unknown"),
                action="system_event",
                result_status="success",
                category="system_administration",
                severity="informational",
                metadata={"syslog_message": message}
            )
        except Exception as e:
            self.logger.error(f"Failed to normalize syslog: {e}")
            return None


class ApplicationLogSource(LogSource):
    """Application event source."""

    def __init__(self, log_file: str):
        super().__init__("application", EventSource.APPLICATION)
        self.log_file = Path(log_file)
        self.last_position = 0

    def read_logs(self) -> List[Dict[str, Any]]:
        """Read new entries from application log file."""
        logs = []
        try:
            if not self.log_file.exists():
                return logs

            with open(self.log_file, 'r') as f:
                f.seek(self.last_position)
                for line in f:
                    logs.append({"raw": line.strip()})
                self.last_position = f.tell()
        except Exception as e:
            self.logger.error(f"Error reading application log: {e}")
        return logs

    def normalize(self, raw_log: Dict[str, Any]) -> Optional[AuditEvent]:
        """Normalize application log entry."""
        try:
            message = raw_log.get("raw", "")

            return AuditEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().isoformat() + "Z",
                source_type=self.source_type.value,
                source_name=self.name,
                user_id="application",
                action="application_event",
                result_status="success",
                category="application",
                severity="informational",
                metadata={"message": message}
            )
        except Exception as e:
            self.logger.error(f"Failed to normalize application log: {e}")
            return None


class EventCorrelationEngine:
    """Correlates related events for incident investigation."""

    def __init__(self, correlation_window: int = 300):
        self.correlation_window = correlation_window  # seconds
        self.event_chains: Dict[str, List[AuditEvent]] = defaultdict(list)
        self.logger = logging.getLogger("correlation")

    def correlate(self, event: AuditEvent) -> Optional[str]:
        """Find or create correlation ID for event."""
        try:
            # Simple correlation by user and time window
            correlation_key = f"{event.user_id}:{event.action}"

            # Check existing chains
            for chain_id, events in self.event_chains.items():
                if events and events[-1].user_id == event.user_id:
                    event_time = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
                    last_time = datetime.fromisoformat(events[-1].timestamp.replace('Z', '+00:00'))

                    if (event_time - last_time).total_seconds() < self.correlation_window:
                        return chain_id

            # Create new correlation chain
            correlation_id = str(uuid.uuid4())
            self.event_chains[correlation_id] = [event]
            return correlation_id
        except Exception as e:
            self.logger.error(f"Correlation error: {e}")
            return None

    def get_chain(self, correlation_id: str) -> List[AuditEvent]:
        """Retrieve event chain."""
        return self.event_chains.get(correlation_id, [])


class AlertRule:
    """Alert rule for triggering notifications on events."""

    def __init__(self, rule_id: str, name: str, conditions: List[Callable],
                 severity: EventSeverity, actions: List[str]):
        self.rule_id = rule_id
        self.name = name
        self.conditions = conditions
        self.severity = severity
        self.actions = actions
        self.enabled = True
        self.logger = logging.getLogger(f"rule.{rule_id}")

    def evaluate(self, event: AuditEvent) -> bool:
        """Evaluate if event matches rule."""
        if not self.enabled:
            return False

        try:
            return all(condition(event) for condition in self.conditions)
        except Exception as e:
            self.logger.error(f"Rule evaluation error: {e}")
            return False


class AuditDaemon:
    """Centralized audit daemon for log collection and analysis."""

    def __init__(self, config_file: Optional[str] = None):
        self.config = self._load_config(config_file)
        self.logger = self._setup_logging()
        self.sources: List[LogSource] = []
        self.alert_rules: List[AlertRule] = []
        self.correlation_engine = EventCorrelationEngine()
        self.event_queue: queue.Queue = queue.Queue(maxsize=10000)
        self.external_integrations: Dict[str, CircuitBreaker] = {}
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._setup_signal_handlers()
        self._initialize_sources()
        self._initialize_rules()

    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """Load daemon configuration."""
        if config_file and Path(config_file).exists():
            with open(config_file, 'r') as f:
                return json.load(f)

        return {
            "log_level": os.getenv("AUDIT_LOG_LEVEL", "INFO"),
            "event_queue_size": 10000,
            "correlation_window": 300,
            "retention_days": 90,
            "enable_syslog": True,
            "syslog_port": 514,
            "enable_vault_audit": True
        }

    def _setup_logging(self) -> logging.Logger:
        """Configure logging."""
        log_level = getattr(logging, self.config.get("log_level", "INFO"))
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger("audit-daemon")

    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers."""
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.shutdown()
        sys.exit(0)

    def _initialize_sources(self):
        """Initialize log sources."""
        try:
            if self.config.get("enable_syslog"):
                port = self.config.get("syslog_port", 514)
                self.sources.append(SyslogSource(port=port))

            if self.config.get("enable_vault_audit"):
                vault_log = os.getenv("VAULT_AUDIT_LOG", "/var/log/guardian/vault.log")
                self.sources.append(ApplicationLogSource(vault_log))

            self.logger.info(f"Initialized {len(self.sources)} log sources")
        except Exception as e:
            self.logger.error(f"Error initializing sources: {e}")

    def _initialize_rules(self):
        """Initialize alert rules."""
        try:
            # Privilege escalation alert
            escalation_rule = AlertRule(
                rule_id="rule:privilege_escalation",
                name="Privilege Escalation Detected",
                conditions=[
                    lambda e: e.action == "privilege_escalation",
                    lambda e: e.result_status == "success"
                ],
                severity=EventSeverity.CRITICAL,
                actions=["alert", "notification"]
            )
            self.alert_rules.append(escalation_rule)

            # Vault access alert
            vault_access_rule = AlertRule(
                rule_id="rule:vault_access",
                name="Guardian Vault Accessed",
                conditions=[
                    lambda e: e.action == "vault_access"
                ],
                severity=EventSeverity.HIGH,
                actions=["log", "alert"]
            )
            self.alert_rules.append(vault_access_rule)

            self.logger.info(f"Initialized {len(self.alert_rules)} alert rules")
        except Exception as e:
            self.logger.error(f"Error initializing rules: {e}")

    def add_source(self, source: LogSource):
        """Register a new log source."""
        self.sources.append(source)
        self.logger.info(f"Registered source: {source.name}")

    def add_rule(self, rule: AlertRule):
        """Register a new alert rule."""
        self.alert_rules.append(rule)
        self.logger.info(f"Registered rule: {rule.rule_id}")

    async def collect_events(self):
        """Asynchronously collect events from sources."""
        while self.running:
            try:
                for source in self.sources:
                    try:
                        raw_logs = source.read_logs()
                        for raw_log in raw_logs:
                            event = source.normalize(raw_log)
                            if event:
                                # Add correlation
                                event.correlation_id = self.correlation_engine.correlate(event)
                                self.event_queue.put_nowait(event)
                    except queue.Full:
                        self.logger.warning(f"Event queue full, dropping events from {source.name}")
                    except Exception as e:
                        self.logger.error(f"Error collecting from {source.name}: {e}")

                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"Unexpected error in event collection: {e}")

    def process_events(self):
        """Process queued events."""
        while self.running:
            try:
                event = self.event_queue.get(timeout=1)

                # Evaluate alert rules
                matched_rules = [rule for rule in self.alert_rules if rule.evaluate(event)]

                if matched_rules:
                    self._handle_alerts(event, matched_rules)

                # Export to external systems
                self._export_event(event)

                self.logger.debug(f"Processed event: {event.event_id}")
            except queue.Empty:
                pass
            except Exception as e:
                self.logger.error(f"Error processing event: {e}")

    def _handle_alerts(self, event: AuditEvent, matched_rules: List[AlertRule]):
        """Handle triggered alerts."""
        for rule in matched_rules:
            self.logger.warning(f"ALERT [{rule.rule_id}] {rule.name}: {event.event_id}")

            for action in rule.actions:
                if action == "log":
                    self.logger.info(f"Alert logged: {rule.name}")
                elif action == "notification":
                    self._send_notification(rule, event)
                elif action == "escalate":
                    self._escalate_incident(rule, event)

    def _send_notification(self, rule: AlertRule, event: AuditEvent):
        """Send alert notification."""
        try:
            notification = {
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "severity": rule.severity.value,
                "event_id": event.event_id,
                "timestamp": event.timestamp,
                "user": event.user_id,
                "action": event.action
            }
            self.logger.info(f"Notification: {json.dumps(notification)}")
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")

    def _escalate_incident(self, rule: AlertRule, event: AuditEvent):
        """Escalate incident for manual review."""
        self.logger.warning(f"ESCALATION: {rule.name} - Event {event.event_id}")

    def _export_event(self, event: AuditEvent):
        """Export event to external systems."""
        try:
            # Splunk integration
            if not self.external_integrations.get("splunk"):
                self.external_integrations["splunk"] = CircuitBreaker()

            # Format: Splunk HEC JSON
            splunk_event = {
                "event": event.to_dict(),
                "source": event.source_name,
                "sourcetype": f"shadowcypher:{event.source_type}",
                "host": socket.gethostname()
            }

            # Would send to Splunk here via HTTP Event Collector
            # self.external_integrations["splunk"].call(self._send_to_splunk, splunk_event)

        except Exception as e:
            self.logger.error(f"Error exporting event: {e}")

    def get_forensic_query(self, query_params: Dict[str, Any]) -> List[AuditEvent]:
        """Execute forensic query on event chain."""
        try:
            correlation_id = query_params.get("correlation_id")
            if correlation_id:
                return self.correlation_engine.get_chain(correlation_id)
            return []
        except Exception as e:
            self.logger.error(f"Forensic query error: {e}")
            return []

    def start(self):
        """Start the audit daemon."""
        self.running = True
        self.logger.info("Starting ShadowCypher Audit Daemon")

        # Start event processing thread
        process_thread = threading.Thread(target=self.process_events, daemon=True)
        process_thread.start()

        # Start event collection
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.collect_events())
        except KeyboardInterrupt:
            self.logger.info("Audit daemon interrupted")
        finally:
            self.shutdown()

    def shutdown(self):
        """Gracefully shutdown daemon."""
        self.logger.info("Shutting down audit daemon...")
        self.running = False

        try:
            # Drain remaining events
            while not self.event_queue.empty():
                event = self.event_queue.get_nowait()
                self._export_event(event)
        except queue.Empty:
            pass

        self.executor.shutdown(wait=True)
        self.logger.info("Audit daemon shutdown complete")


def main():
    """Entry point for audit daemon."""
    daemon = AuditDaemon(config_file=os.getenv("AUDIT_CONFIG"))
    daemon.start()


if __name__ == "__main__":
    main()
