"""
ShadowCypher Test Suite — Database Thread Safety & CRUD Operations
Tests the TacticalDatabase under concurrent access patterns.
"""

import pytest
import threading
import os
import tempfile
from unittest.mock import patch


class TestTacticalDatabase:
    """Test database operations and thread safety."""

    @pytest.fixture(autouse=True)
    def setup_db(self, tmp_path):
        """Create a temporary database for each test."""
        # Patch config.project_root to use temp dir
        with patch("shadowcypher.core.database.config") as mock_config:
            mock_config.project_root = str(tmp_path)
            from shadowcypher.core.database import TacticalDatabase
            self.db = TacticalDatabase()
            yield
            self.db.conn.close()

    def test_register_target_new(self):
        self.db.register_target("192.168.1.1", "test-host", "AA:BB:CC:DD:EE:FF")
        results = self.db.export_target_graph()
        assert len(results) == 1
        assert results[0][1] == "192.168.1.1"
        assert results[0][2] == "test-host"

    def test_register_target_duplicate_updates(self):
        self.db.register_target("10.0.0.1")
        self.db.register_target("10.0.0.1")  # Should update, not duplicate
        results = self.db.export_target_graph()
        assert len(results) == 1

    def test_log_vulnerability(self):
        self.db.log_vulnerability("192.168.1.1", 80, "http", cve_id="CVE-2024-1234", severity="CRITICAL")
        vulns = self.db.export_vulnerabilities("192.168.1.1")
        assert len(vulns) == 1
        assert vulns[0][4] == "CVE-2024-1234"

    def test_log_credential(self):
        self.db.log_credential("10.0.0.5", "ssh", "admin", "password123")
        creds = self.db.export_credentials()
        assert len(creds) == 1
        assert creds[0][3] == "admin"

    def test_concurrent_writes(self):
        """Stress test: 50 threads writing simultaneously."""
        errors = []

        def write_target(i):
            try:
                self.db.register_target(f"10.0.{i // 256}.{i % 256}")
                self.db.log_vulnerability(f"10.0.{i // 256}.{i % 256}", 80 + i, "http")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=write_target, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0, f"Concurrent write errors: {errors}"
        assert self.db.get_target_count() == 50

    def test_get_counts(self):
        self.db.register_target("1.1.1.1")
        self.db.register_target("2.2.2.2")
        self.db.log_vulnerability("1.1.1.1", 443, "https")
        assert self.db.get_target_count() == 2
        assert self.db.get_vuln_count() == 1

    def test_export_empty_tables(self):
        assert self.db.export_target_graph() == []
        assert self.db.export_vulnerabilities() == []
        assert self.db.export_credentials() == []
