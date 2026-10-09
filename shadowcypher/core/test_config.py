"""
ShadowCypher Test Suite — Configuration Engine
Tests the Pydantic config system: defaults, JSON loading, nested access, env overrides.
"""

import json
import os
from unittest.mock import patch

import pytest


class TestConfig:
    """Test the enterprise configuration engine."""

    @pytest.fixture
    def fresh_config(self, tmp_path):
        """Create a clean config instance."""
        with patch.dict(os.environ, {}, clear=False):
            from shadowcypher.core.config import Config
            cfg = Config()
            cfg.project_root = tmp_path
            return cfg

    def test_default_values(self, fresh_config):
        assert fresh_config.app_name == "ShadowCypher Apex"
        assert fresh_config.ai.temperature == 0.3
        assert fresh_config.ai.max_tokens == 4096
        assert fresh_config.tools.nmap == "nmap"

    def test_nested_get(self, fresh_config):
        assert fresh_config.get("ai", "temperature") == 0.3
        assert fresh_config.get("tools", "nmap") == "nmap"
        assert fresh_config.get("nonexistent", "key", default="fallback") == "fallback"

    def test_nested_set_and_persist(self, fresh_config, tmp_path):
        fresh_config.project_root = tmp_path
        fresh_config.set("ai", "temperature", 0.9)
        assert fresh_config.ai.temperature == 0.9

        # Verify JSON was persisted
        config_path = tmp_path / "config.json"
        assert config_path.exists()
        data = json.loads(config_path.read_text())
        assert data["ai"]["temperature"] == 0.9

    def test_load_from_json(self, fresh_config, tmp_path):
        config_data = {
            "ai": {"temperature": 0.5, "model": "custom-model"},
            "identity": {"handle": "operator-x"},
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config_data))

        fresh_config.load_from_json(config_path)
        assert fresh_config.ai.temperature == 0.5
        assert fresh_config.ai.model == "custom-model"
        assert fresh_config.identity.handle == "operator-x"

    def test_stealth_defaults(self, fresh_config):
        assert fresh_config.stealth.proxy_url == ""
        assert fresh_config.stealth.enforce_privacy is False

    def test_irc_defaults(self, fresh_config):
        assert fresh_config.irc.port == 6697
        assert fresh_config.irc.use_ssl is True

    def test_tool_path_resolution_system(self, fresh_config):
        # Should return "nmap" (the default) since it's in PATH on most systems
        path = fresh_config.get_tool_path("nmap")
        assert path is not None
        assert len(path) > 0
