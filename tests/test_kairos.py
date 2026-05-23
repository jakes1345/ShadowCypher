"""
ShadowCypher Test Suite — Kairos Intelligence Analyzer
Tests pattern detection for IPs, CVEs, ports, credentials, and vulnerabilities.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
import importlib


class TestKairos:
    @pytest.fixture(autouse=True, scope="class")
    def setup_kairos(self, request):
        """Patch db, bus, and pulse — imported once per class to avoid C-extension re-load crash."""
        mock_db = MagicMock()
        mock_bus = MagicMock()
        mock_pulse = MagicMock()
        mock_pulse.ingest = MagicMock()
        mock_pulse.analyze_spectrum.return_value = {"status": "OK"}

        import shadowcypher.core.kairos as kairos_mod
        import shadowcypher.core.pulse as pulse_mod

        # Inject mocks at module level (safe — modules already cached in sys.modules)
        kairos_mod.db = mock_db
        kairos_mod.bus = mock_bus
        pulse_mod.pulse = mock_pulse

        from shadowcypher.core.kairos import Kairos
        kairos_instance = Kairos()

        # Attach to class so all test methods can access via self
        request.cls.mock_db = mock_db
        request.cls.mock_bus = mock_bus
        request.cls.mock_pulse = mock_pulse
        request.cls.kairos = kairos_instance
        yield

    def test_ip_detection(self):
        self.kairos.analyze("Found host at 192.168.1.100 responding")
        self.mock_db.register_target.assert_called_with("192.168.1.100")

    def test_ignores_localhost(self):
        self.mock_db.register_target.reset_mock()
        self.kairos.analyze("Connecting to 127.0.0.1 on port 80")
        self.mock_db.register_target.assert_not_called()

    def test_ignores_broadcast(self):
        self.mock_db.register_target.reset_mock()
        self.kairos.analyze("Broadcast 255.255.255.255")
        self.mock_db.register_target.assert_not_called()

    def test_cve_detection(self):
        self.kairos.analyze("Vulnerability found: CVE-2024-12345 on target 10.0.0.1")
        # Verify bus was called with CVE event
        calls = str(self.mock_bus.publish.call_args_list)
        assert "CVE-2024-12345" in calls

    def test_cve_dedup(self):
        self.kairos.analyze("Found CVE-2024-99999 on host 10.0.0.1")
        self.mock_bus.publish.reset_mock()
        self.kairos.analyze("Also found CVE-2024-99999 on 10.0.0.2")
        # Second occurrence should NOT re-publish
        cve_calls = [c for c in self.mock_bus.publish.call_args_list
                     if "CVE-2024-99999" in str(c)]
        assert len(cve_calls) == 0

    def test_port_detection(self):
        self.kairos.analyze("22/tcp   open  ssh")
        self.mock_db.log_vulnerability.assert_called()

    def test_vuln_pattern_sql_injection(self):
        self.kairos.analyze("SQL injection vulnerability detected on parameter id at 10.0.0.5")
        self.mock_db.log_vulnerability.assert_called()

    def test_credential_detection(self):
        self.kairos.analyze("password: s3cr3t123 for user admin at 10.0.0.1")
        self.mock_db.log_credential.assert_called()

    def test_empty_line_ignored(self):
        self.mock_db.reset_mock()
        self.kairos.analyze("")
        self.kairos.analyze("   ")
        self.mock_db.register_target.assert_not_called()

    def test_reset_clears_state(self):
        self.kairos.analyze("Found CVE-2024-11111 at 10.0.0.1")
        self.kairos.reset()
        assert len(self.kairos._seen_cves) == 0
        assert len(self.kairos._seen_vulns) == 0
