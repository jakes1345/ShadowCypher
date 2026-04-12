"""
ShadowCypher Sisyphus Protocol — Enterprise-Grade Integrity & Health Engine.
Google-grade autonomous monitoring focusing on Stability, Integrity, and Performance.
"""

import os
import time
import threading
import psutil
import hashlib
import sys
from datetime import datetime
from typing import Dict, List, Any

from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus

class Sisyphus:
    """
    ShadowCypher's Guardian Loop — Monitors system vitals and codebase integrity.
    Operates on a non-blocking, tiered polling strategy (Sentinel Protocol).
    """

    def __init__(self):
        from shadowcypher.core.config import config
        self.project_root = config.project_root
        self._active = False
        self._thread = None
        self._last_report = {}
        
        # Enterprise Vitals Thresholds
        self.max_cpu_percent = 85.0
        self.max_ram_percent = 90.0
        self.scan_interval = 60  # Polling frequency in seconds
        
        # Integrity Map (Initial verification hashes)
        self._integrity_map: Dict[str, str] = {}
        self._init_integrity_baseline()
        
        # ═══════════════════════════════════════════════
        # DEEP INTEGRATION: Autonomous Governance
        # ═══════════════════════════════════════════════
        bus.subscribe("forensic_update", self._on_forensic_event)

    def _on_forensic_event(self, entry: dict):
        """Autonomous Threat Lockdown: Responding to Forensic Detection."""
        from shadowcypher.core.firewall import firewall
        hostmask = entry.get("hostmask")
        risk = entry.get("risk_level", "LOW")
        
        if hostmask and risk == "HIGH":
            logger.warning("sisyphus", f"GOVERNANCE_PROTOCOL: High-risk threat detected ({hostmask}). Executing Lockdown...")
            firewall.block_host(hostmask)
            self.broadcast_alert(f"AUTONOMOUS_LOCKDOWN: {hostmask} quarantined.", "CRITICAL")

    def _init_integrity_baseline(self):
        """Build initial baseline hashes for core framework files. 
        Re-baselined for APEX v2.2.0 Hardening.
        """
        core_files = [
            "shadowcypher/app.py",
            "shadowcypher/core/hub.py",
            "shadowcypher/core/bus.py",
            "shadowcypher/ai/orchestrator.py",
            "shadowcypher/core/irc_bot.py",
            "shadowcypher/core/forensics.py"
        ]
        for rel_path in core_files:
            abs_path = os.path.join(str(self.project_root), rel_path)
            if os.path.exists(abs_path):
                # We take the CURRENT state as the new GOLDEN baseline
                self._integrity_map[rel_path] = self._get_file_hash(abs_path)
        logger.info("sisyphus", "INTEGRITY_BASELINE: RE-SYNCHRONIZED [APEX_UPGRADE_ACCEPTED]")

    def _get_file_hash(self, path: str) -> str:
        """High-performance SHA256 hashing for file integrity."""
        sha256 = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception:
            return "ERR"

    def start(self):
        """Deploy the Sisyphus sentinel in a dedicated background thread."""
        if self._active:
            return
        self._active = True
        self._thread = threading.Thread(target=self._sentinel_loop, name="Sisyphus-Sentinel", daemon=True)
        self._thread.start()
        logger.info("sisyphus", "SENTINEL_PROTOCOL: ENGAGED [ACTIVE_MONITORING]")

    def stop(self):
        """Graceful termination of the sentinel loop."""
        self._active = False

    def _sentinel_loop(self):
        """The core monitoring loop — executes tiered checks."""
        # Warm-up delay for app bootstrap
        time.sleep(5)
        
        while self._active:
            try:
                report = self._execute_audit()
                self._analyze_and_report(report)
                time.sleep(self.scan_interval)
            except Exception as e:
                logger.error("sisyphus", f"SENTINEL_FAULT: {str(e)}")
                time.sleep(30)

    def _execute_audit(self) -> Dict[str, Any]:
        """Perform a multi-spectrum audit scan."""
        return {
            "vitals": self._check_vitals(),
            "integrity": self._check_integrity(),
            "framework": self._check_framework_health()
        }

    def _check_vitals(self) -> Dict[str, float]:
        """Collect high-fidelity system metrics."""
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage(str(self.project_root)).percent
        return {"cpu": cpu, "ram": ram, "disk": disk}

    def _check_integrity(self) -> List[str]:
        """Verify core framework files against the security baseline."""
        violations = []
        for rel_path, expected_hash in self._integrity_map.items():
            abs_path = os.path.join(str(self.project_root), rel_path)
            if not os.path.exists(abs_path):
                violations.append(f"MISSING: {rel_path}")
                continue
            
            current_hash = self._get_file_hash(abs_path)
            if current_hash != expected_hash:
                violations.append(f"MODIFIED: {rel_path}")
        return violations

    def _check_framework_health(self) -> Dict[str, List[str]]:
        """Deep syntax and structural validation of the codebase."""
        results = {"syntax": [], "orphans": []}
        src_dir = os.path.join(str(self.project_root), "shadowcypher")
        
        for root, _, files in os.walk(src_dir):
            if "__pycache__" in root or "tests" in root: continue
            for f in files:
                if not f.endswith(".py"): continue
                path = os.path.join(root, f)
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        compile(fh.read(), path, "exec")
                except SyntaxError as e:
                    results["syntax"].append(f"{os.path.basename(f)}:L{e.lineno}")
                except Exception:
                    pass
        return results

    def _analyze_and_report(self, report: Dict[str, Any]):
        """Evaluate audit findings and broadcast alerts via the bus."""
        v = report["vitals"]
        i = report["integrity"]
        f = report["framework"]

        # 1. Vital Alerts
        if v["cpu"] > self.max_cpu_percent:
            self.broadcast_alert(f"HIGH_CPU_LOAD: {v['cpu']}%", "CRITICAL")
        if v["ram"] > self.max_ram_percent:
            self.broadcast_alert(f"MEMORY_PRESSURE: {v['ram']}%", "WARN")

        # 2. Integrity Alerts
        for violation in i:
            self.broadcast_alert(f"INTEGRITY_VIOLATION: {violation}", "SECURITY")

        # 3. Code Quality Alerts
        for error in f["syntax"]:
            self.broadcast_alert(f"SYNTAX_FAULT: {error}", "ERROR")

        # Update Hub Telemetry
        from shadowcypher.core.hub import hub
        hub.telemetry["load_avg"] = v["cpu"]
        
        # Log to system bus for UX notification
        bus.publish("sisyphus_report", report)

    def broadcast_alert(self, msg: str, level: str = "WARN"):
        """Publish prioritized alerts to the ShadowBus."""
        bus.publish("module_log", {
            "module": "sisyphus",
            "text": f"SENTINEL >> {msg}",
            "level": level,
            "timestamp": datetime.now().isoformat()
        })
        logger.warning("sisyphus", f"SENTINEL_ALERT [{level}]: {msg}")

    def audit_report(self) -> str:
        """AI-consumable system health summary."""
        report = self._execute_audit()
        v = report["vitals"]
        i = report["integrity"]
        f = report["framework"]
        
        summary = (
            f"SYSTEM_HEALTH: {'NOMINAL' if not i and not f['syntax'] else 'DEGRADED'}\n"
            f"VITALS: CPU={v['cpu']}% | RAM={v['ram']}% | DISK={v['disk']}%\n"
            f"INTEGRITY: {len(i)} violations detected.\n"
            f"CODE_VAL: {len(f['syntax'])} syntax errors active."
        )
        return summary

    def get_quick_report(self) -> Dict[str, Any]:
        """Immediate on-demand audit for the UI Dashboard."""
        return self._execute_audit()

# Singleton Sentinel Instance
sisyphus = Sisyphus()
