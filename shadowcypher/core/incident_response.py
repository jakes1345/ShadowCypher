"""
Incident Response Engine — Automated threat remediation and response.
Executes response workflows based on incident severity and type.
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading

from shadowcypher.core.logger import logger


class IncidentSeverity(str, Enum):
    """Incident severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ResponseAction(str, Enum):
    """Available response actions."""
    ALERT = "alert"  # Send notification
    ISOLATE = "isolate"  # Isolate device
    BLOCK = "block"  # Block IP/port
    PATCH = "patch"  # Suggest/apply patch
    QUARANTINE = "quarantine"  # Quarantine files
    LOG = "log"  # Log incident
    ESCALATE = "escalate"  # Escalate to admin


@dataclass
class IncidentRule:
    """Rule for automated incident response."""
    id: str
    name: str
    description: Optional[str]
    condition: str  # keyword match or pattern
    severity_threshold: str  # critical, high, medium, low
    actions: List[str]  # List of ResponseAction
    enabled: bool = True
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class IncidentResponse:
    """Record of an automated response."""
    id: str
    incident_id: str
    rule_id: str
    actions_executed: List[str]
    status: str  # success, partial, failed
    result: Optional[str]
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class IncidentResponseEngine:
    """Manages incident detection and automated responses."""

    def __init__(self):
        self.rules: Dict[str, IncidentRule] = {}
        self.responses: Dict[str, IncidentResponse] = {}
        self.handlers: Dict[str, List[Callable]] = {}
        self.lock = threading.Lock()
        self._load_rules()
        self._setup_default_rules()

    def create_rule(
        self,
        name: str,
        condition: str,
        severity_threshold: str,
        actions: List[str],
        description: Optional[str] = None,
    ) -> str:
        """Create a new incident response rule."""
        import uuid
        rule_id = f"rule-{uuid.uuid4().hex[:8]}"

        rule = IncidentRule(
            id=rule_id,
            name=name,
            description=description,
            condition=condition,
            severity_threshold=severity_threshold,
            actions=actions,
        )

        with self.lock:
            self.rules[rule_id] = rule

        self._save_rules()
        logger.info("incident_response", f"Rule {rule_id} created: {name}")
        return rule_id

    def list_rules(self, enabled_only: bool = False) -> List[IncidentRule]:
        """List all incident response rules."""
        with self.lock:
            rules = list(self.rules.values())

        if enabled_only:
            rules = [r for r in rules if r.enabled]

        return sorted(rules, key=lambda r: r.created_at, reverse=True)

    def get_rule(self, rule_id: str) -> Optional[IncidentRule]:
        """Get a rule by ID."""
        with self.lock:
            return self.rules.get(rule_id)

    def update_rule(self, rule_id: str, **updates) -> bool:
        """Update a rule."""
        with self.lock:
            if rule_id not in self.rules:
                return False
            rule = self.rules[rule_id]
            for key, value in updates.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)

        self._save_rules()
        logger.info("incident_response", f"Rule {rule_id} updated")
        return True

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule."""
        with self.lock:
            if rule_id not in self.rules:
                return False
            del self.rules[rule_id]

        self._save_rules()
        logger.info("incident_response", f"Rule {rule_id} deleted")
        return True

    def process_incident(
        self,
        incident_id: str,
        incident_type: str,
        severity: str,
        details: Dict,
    ) -> Optional[str]:
        """Process an incident and apply matching response rules."""
        try:
            matched_rules = []

            with self.lock:
                for rule in self.rules.values():
                    if not rule.enabled:
                        continue

                    # Check severity
                    severity_order = ["critical", "high", "medium", "low", "info"]
                    if severity_order.index(severity) > severity_order.index(rule.severity_threshold):
                        continue

                    # Check condition match
                    if self._matches_condition(rule.condition, incident_type, details):
                        matched_rules.append(rule)

            # Execute matching rules
            responses = []
            for rule in matched_rules:
                response = self._execute_rule(incident_id, rule, details)
                responses.append(response)

            if responses:
                response_id = responses[0].id
                logger.info(
                    "incident_response",
                    f"Incident {incident_id}: {len(responses)} rules triggered",
                )
                return response_id

            return None

        except Exception as e:
            logger.error("incident_response", f"Failed to process incident: {e}")
            return None

    def _execute_rule(
        self, incident_id: str, rule: IncidentRule, details: Dict
    ) -> IncidentResponse:
        """Execute a single incident response rule."""
        import uuid
        response_id = f"response-{uuid.uuid4().hex[:8]}"

        executed_actions = []
        failed_actions = []

        for action in rule.actions:
            try:
                self._execute_action(action, details)
                executed_actions.append(action)
                logger.info("incident_response", f"Action '{action}' executed for {rule.id}")
            except Exception as e:
                failed_actions.append(action)
                logger.error("incident_response", f"Action '{action}' failed: {e}")

        status = "success" if not failed_actions else ("partial" if executed_actions else "failed")
        result = {
            "executed": executed_actions,
            "failed": failed_actions,
        }

        response = IncidentResponse(
            id=response_id,
            incident_id=incident_id,
            rule_id=rule.id,
            actions_executed=executed_actions,
            status=status,
            result=json.dumps(result),
        )

        with self.lock:
            self.responses[response_id] = response

        return response

    def _execute_action(self, action: str, details: Dict):
        """Execute a single response action."""
        from shadowcypher.core.action_executor import get_action_executor

        executor = get_action_executor()

        if action == ResponseAction.ALERT:
            self._action_alert(details)
        elif action == ResponseAction.LOG:
            self._action_log(details)
        elif action == ResponseAction.ESCALATE:
            self._action_escalate(details)
        elif action == ResponseAction.ISOLATE:
            device_ip = details.get("device_ip")
            if device_ip:
                executor.isolate_device(device_ip, reason=details.get("title", "Threat detected"))
            self._action_isolate(details)
        elif action == ResponseAction.BLOCK:
            source_ip = details.get("source_ip")
            if source_ip:
                executor.block_ip(source_ip, reason=details.get("title", "Threat detected"))
            self._action_block(details)
        elif action == ResponseAction.QUARANTINE:
            file_path = details.get("file_path")
            if file_path:
                executor.quarantine_file(file_path, reason=details.get("title", "Threat detected"))
            self._action_quarantine(details)
        elif action == ResponseAction.PATCH:
            package = details.get("package")
            executor.patch_system(package)
            self._action_patch(details)

    def _action_alert(self, details: Dict):
        """Send security alert."""
        # Notify subscribed handlers
        for handler in self.handlers.get("alert", []):
            try:
                handler(details)
            except Exception as e:
                logger.error("incident_response", f"Alert handler failed: {e}")

        logger.info("incident_response", f"Alert sent: {details.get('title', 'Unknown')}")

    def _action_log(self, details: Dict):
        """Log incident to file."""
        log_file = os.path.expanduser("~/.shadowcypher/incidents.log")
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            with open(log_file, "a") as f:
                f.write(json.dumps(details) + "\n")
            logger.info("incident_response", "Incident logged")
        except Exception as e:
            logger.error("incident_response", f"Failed to log incident: {e}")

    def _action_escalate(self, details: Dict):
        """Escalate incident to admin."""
        # Notify handlers
        for handler in self.handlers.get("escalate", []):
            try:
                handler(details)
            except Exception as e:
                logger.error("incident_response", f"Escalate handler failed: {e}")

        logger.warning("incident_response", f"Incident escalated: {details.get('title', 'Unknown')}")

    def _action_isolate(self, details: Dict):
        """Isolate affected device by dropping its traffic via iptables."""
        import subprocess
        device_ip = details.get("device_ip") or details.get("source_ip")
        if not device_ip:
            logger.warning("incident_response", "Isolate called with no device_ip")
            return
        logger.warning("incident_response", f"Isolating device: {device_ip}")
        try:
            # Block all inbound + outbound traffic for the device IP
            subprocess.run(["iptables", "-I", "INPUT", "-s", device_ip, "-j", "DROP"], check=True, timeout=10)
            subprocess.run(["iptables", "-I", "OUTPUT", "-d", device_ip, "-j", "DROP"], check=True, timeout=10)
            subprocess.run(["iptables", "-I", "FORWARD", "-s", device_ip, "-j", "DROP"], check=True, timeout=10)
            logger.info("incident_response", f"Device {device_ip} isolated via iptables")
        except Exception as e:
            logger.error("incident_response", f"Isolation failed for {device_ip}: {e}")

    def _action_block(self, details: Dict):
        """Block IP or port via iptables."""
        import subprocess
        source_ip = details.get("source_ip")
        port = details.get("port")
        proto = details.get("proto", "tcp")
        if source_ip:
            logger.warning("incident_response", f"Blocking IP: {source_ip}")
            try:
                subprocess.run(["iptables", "-I", "INPUT", "-s", source_ip, "-j", "DROP"], check=True, timeout=10)
                logger.info("incident_response", f"Blocked IP {source_ip}")
            except Exception as e:
                logger.error("incident_response", f"IP block failed for {source_ip}: {e}")
        if port:
            logger.warning("incident_response", f"Blocking port: {port}/{proto}")
            try:
                subprocess.run(["iptables", "-I", "INPUT", "-p", proto, "--dport", str(port), "-j", "DROP"], check=True, timeout=10)
                logger.info("incident_response", f"Blocked port {port}/{proto}")
            except Exception as e:
                logger.error("incident_response", f"Port block failed for {port}: {e}")

    def _action_quarantine(self, details: Dict):
        """Quarantine suspicious file by moving it to /var/quarantine and locking permissions."""
        import subprocess
        import shutil
        file_path = details.get("file_path")
        if not file_path or not os.path.exists(file_path):
            logger.warning("incident_response", f"Quarantine: file not found: {file_path}")
            return
        q_dir = "/var/quarantine/shadowcypher"
        os.makedirs(q_dir, mode=0o700, exist_ok=True)
        q_dest = os.path.join(q_dir, os.path.basename(file_path) + ".quarantined")
        try:
            shutil.move(file_path, q_dest)
            os.chmod(q_dest, 0o000)  # No one can read/exec
            logger.warning("incident_response", f"Quarantined {file_path} → {q_dest}")
        except Exception as e:
            logger.error("incident_response", f"Quarantine failed for {file_path}: {e}")

    def _action_patch(self, details: Dict):
        """Apply available system patch for a CVE via package manager."""
        import subprocess
        import shutil
        cve_id = details.get("cve_id", "unknown")
        package = details.get("package")  # Optional specific package to update
        logger.info("incident_response", f"Attempting patch for: {cve_id} (package={package})")
        try:
            if shutil.which("pacman"):
                cmd = ["pacman", "-Syu", "--noconfirm"]
                if package:
                    cmd = ["pacman", "-S", "--noconfirm", package]
            elif shutil.which("apt-get"):
                cmd = ["apt-get", "install", "-y", "--only-upgrade", package] if package else ["apt-get", "upgrade", "-y"]
            else:
                logger.warning("incident_response", f"No supported package manager found for patching {cve_id}")
                return
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info("incident_response", f"Patch applied for {cve_id}: {result.stdout[-200:]}")
            else:
                logger.error("incident_response", f"Patch failed for {cve_id}: {result.stderr[-200:]}")
        except Exception as e:
            logger.error("incident_response", f"Patch exception for {cve_id}: {e}")

    def _matches_condition(self, condition: str, incident_type: str, details: Dict) -> bool:
        """Check if incident matches rule condition."""
        # Simple substring match for now
        condition_lower = condition.lower()
        incident_type_lower = incident_type.lower()

        if condition_lower in incident_type_lower:
            return True

        # Check details for keyword matches
        details_str = json.dumps(details).lower()
        if condition_lower in details_str:
            return True

        return False

    def register_handler(self, event_type: str, handler: Callable):
        """Register handler for response events."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    def get_response(self, response_id: str) -> Optional[IncidentResponse]:
        """Get a response record by ID."""
        with self.lock:
            return self.responses.get(response_id)

    def _setup_default_rules(self):
        """Create default incident response rules."""
        defaults = [
            {
                "name": "Critical CVE Response",
                "condition": "cve",
                "severity_threshold": "critical",
                "actions": ["alert", "log", "escalate"],
                "description": "Alert and escalate critical CVEs",
            },
            {
                "name": "Malware Detection",
                "condition": "malware",
                "severity_threshold": "high",
                "actions": ["alert", "log", "quarantine"],
                "description": "Quarantine malware and alert admin",
            },
            {
                "name": "Intrusion Attempt",
                "condition": "intrusion",
                "severity_threshold": "high",
                "actions": ["alert", "block", "log"],
                "description": "Block intrusion attempts and alert",
            },
        ]

        for default in defaults:
            # Check if already exists
            existing = [r for r in self.rules.values() if r.name == default["name"]]
            if not existing:
                self.create_rule(
                    name=default["name"],
                    condition=default["condition"],
                    severity_threshold=default["severity_threshold"],
                    actions=default["actions"],
                    description=default.get("description"),
                )

    def _load_rules(self):
        """Load rules from disk."""
        try:
            config_dir = os.path.expanduser("~/.shadowcypher")
            rules_file = os.path.join(config_dir, "incident_rules.json")

            if os.path.exists(rules_file):
                with open(rules_file) as f:
                    data = json.load(f)
                    for rule_id, rule_data in data.items():
                        rule = IncidentRule(**rule_data)
                        self.rules[rule_id] = rule

                logger.info("incident_response", f"Loaded {len(self.rules)} rules")
        except Exception as e:
            logger.debug("incident_response", f"Failed to load rules: {e}")

    def _save_rules(self):
        """Save rules to disk."""
        try:
            config_dir = os.path.expanduser("~/.shadowcypher")
            os.makedirs(config_dir, exist_ok=True)

            rules_file = os.path.join(config_dir, "incident_rules.json")
            with open(rules_file, "w") as f:
                data = {rid: asdict(r) for rid, r in self.rules.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("incident_response", f"Failed to save rules: {e}")


# Singleton instance
_incident_response_engine = None


def get_incident_response_engine() -> IncidentResponseEngine:
    """Get or create IncidentResponseEngine singleton."""
    global _incident_response_engine
    if _incident_response_engine is None:
        _incident_response_engine = IncidentResponseEngine()
    return _incident_response_engine
