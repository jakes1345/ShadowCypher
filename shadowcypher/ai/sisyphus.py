"""
ShadowCypher Sisyphus Protocol — Enterprise-Grade Integrity & Health Engine.
Google-grade autonomous monitoring focusing on Stability, Integrity, and Performance.
"""

import hashlib
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, List

import psutil

from shadowcypher.core.bus import bus
from shadowcypher.core.logger import logger


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
            logger.warning("sisyphus", f"High-risk threat: {hostmask} — blocking.")
            firewall.block_host(hostmask)
            self.broadcast_alert(f"Blocked {hostmask} (autonomous lockdown).", "CRITICAL")

    def _init_integrity_baseline(self):
        """Build initial baseline hashes for core framework files.
        Supports static hash persistence to avoid developer false-positives.
        """
        import json
        self.integrity_file = os.path.join(str(self.project_root), "shadowcypher", "core", "integrity.json")

        core_files = [
            "shadowcypher/app.py",
            "shadowcypher/core/hub.py",
            "shadowcypher/core/bus.py",
            "shadowcypher/ai/orchestrator.py",
            "shadowcypher/core/forensics.py"
        ]

        # Load static hashes if they exist
        static_hashes = {}
        if os.path.exists(self.integrity_file):
            try:
                with open(self.integrity_file, "r") as f:
                    static_hashes = json.load(f)
                logger.info("sisyphus", "Loaded integrity baseline from integrity.json.")
            except Exception as e:
                logger.warning("sisyphus", f"Failed to load integrity baseline: {e}")

        new_entries_added = False
        for rel_path in core_files:
            abs_path = os.path.join(str(self.project_root), rel_path)
            if os.path.exists(abs_path):
                if rel_path in static_hashes:
                    self._integrity_map[rel_path] = static_hashes[rel_path]
                else:
                    # Capture current state if not in static map
                    current_hash = self._get_file_hash(abs_path)
                    self._integrity_map[rel_path] = current_hash
                    static_hashes[rel_path] = current_hash
                    new_entries_added = True

        # Persist the baseline if the file is new or new entries were added
        if not os.path.exists(self.integrity_file) or new_entries_added:
            try:
                with open(self.integrity_file, "w") as f:
                    json.dump(static_hashes, f, indent=4)
                logger.info("sisyphus", "INTEGRITY_BASELINE: Created initial static baseline.")
            except Exception:
                pass

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
                self._last_report = report # CACHE THE REPORT
                self._analyze_and_report(report)
                time.sleep(self.scan_interval)
            except Exception as e:
                logger.error("sisyphus", f"Audit loop error: {e}")
                time.sleep(30)

    def _execute_audit(self) -> Dict[str, Any]:
        """Perform a multi-spectrum audit scan."""
        return {
            "vitals": self._check_vitals(),
            "integrity": self._check_integrity(),
            "framework": self._check_framework_health()
        }

    def _check_vitals(self) -> Dict[str, float]:
        """Collect high-fidelity system metrics (Non-blocking)."""
        cpu = psutil.cpu_percent(interval=None) # NON-BLOCKING
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage(str(self.project_root)).percent
        return {"cpu": cpu, "ram": ram, "disk": disk}

    def _check_integrity(self) -> List[str]:
        """Verify core framework files and scan for Quantum-Safe compliance."""
        violations = []
        for rel_path, expected_hash in self._integrity_map.items():
            abs_path = os.path.join(str(self.project_root), rel_path)
            if not os.path.exists(abs_path):
                violations.append(f"MISSING: {rel_path}")
                continue

            current_hash = self._get_file_hash(abs_path)
            if current_hash != expected_hash:
                violations.append(f"MODIFIED: {rel_path}")

        # Year 2026: Quantum-Safe Compliance Scan
        violations.extend(self._check_quantum_readiness())
        return violations

    def _check_quantum_readiness(self) -> List[str]:
        """Scan for legacy cryptographic primitives vulnerable to Shor's algorithm."""
        vulns = []
        # Check if we are still using weak RSA or SHA1 in core modules
        core_dir = os.path.join(str(self.project_root), "shadowcypher", "core")
        for root, _, files in os.walk(core_dir):
            for f in files:
                if f.endswith(".py"):
                    with open(os.path.join(root, f), "r") as fh:
                        content = fh.read()
                        if "RSA.generate(1024)" in content:
                            vulns.append(f"QUANTUM_RISK: Weak RSA (1024) in {f}")
                        if "hashlib.sha1" in content:
                            vulns.append(f"LEGACY_HASH: SHA1 detected in {f}")
        return vulns

    def _check_framework_health(self) -> Dict[str, List[str]]:
        """Differential syntax validation—only audits files that have mutated."""
        results = {"syntax": [], "orphans": []}
        src_dir = os.path.join(str(self.project_root), "shadowcypher")

        if not hasattr(self, "_mtime_cache"):
            self._mtime_cache = {}

        for root, _, files in os.walk(src_dir):
            if "__pycache__" in root or "tests" in root:
                continue
            for f in files:
                if not f.endswith(".py"):
                    continue
                path = os.path.join(root, f)
                try:
                    mtime = os.path.getmtime(path)
                    if self._mtime_cache.get(path) == mtime:
                        continue

                    self._mtime_cache[path] = mtime
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
            self.broadcast_alert(f"Integrity violation: {violation}", "SECURITY")

        # 3. Code Quality Alerts
        for error in f["syntax"]:
            self.broadcast_alert(f"Syntax error: {error}", "ERROR")

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
        logger.warning("sisyphus", f"Alert [{level}]: {msg}")

    def audit_report(self) -> str:
        """AI-consumable system health summary."""
        report = self._execute_audit()
        v = report["vitals"]
        i = report["integrity"]
        f = report["framework"]

        summary = (
            f"System health: {'nominal' if not i and not f['syntax'] else 'degraded'}\n"
            f"Vitals: CPU={v['cpu']}% | RAM={v['ram']}% | Disk={v['disk']}%\n"
            f"Integrity: {len(i)} violation(s) detected.\n"
            f"Syntax: {len(f['syntax'])} error(s) active."
        )
        return summary

    def get_quick_report(self) -> Dict[str, Any]:
        """Immediate access to the LATEST cached audit report."""
        if not self._last_report:
            return self._execute_audit()
        return self._last_report

    @property
    def is_stable(self) -> bool:
        """Instant stability indicator using cached state."""
        if not self._last_report:
            return True
        i = self._last_report.get("integrity", [])
        f = self._last_report.get("framework", {}).get("syntax", [])
        return len(i) == 0 and len(f) == 0

    def generate_baseline(self):
        """Forces a recalculation and persistence of the integrity baseline."""
        logger.info("sisyphus", "Regenerating integrity baseline...")
        new_hashes = {}
        core_files = [
            "shadowcypher/app.py",
            "shadowcypher/core/hub.py",
            "shadowcypher/core/bus.py",
            "shadowcypher/ai/orchestrator.py",
            "shadowcypher/core/forensics.py"
        ]
        for rel_path in core_files:
            abs_path = os.path.join(str(self.project_root), rel_path)
            if os.path.exists(abs_path):
                h = self._get_file_hash(abs_path)
                new_hashes[rel_path] = h
                self._integrity_map[rel_path] = h

        try:
            import json
            with open(self.integrity_file, "w") as f:
                json.dump(new_hashes, f, indent=4)
            logger.info("sisyphus", "Integrity baseline saved.")
        except Exception as e:
            logger.error("sisyphus", f"Failed to save baseline: {e}")

        # Trigger an immediate audit to clear cached 'TAMPERED' status
        self._last_report = self._execute_audit()

# Singleton Sentinel Instance
sisyphus = Sisyphus()
