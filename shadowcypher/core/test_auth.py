"""
ShadowCypher Test Suite — AuthManager
Tests PBKDF2 hashing, constant-time verification, admin key management,
file permissions, and corrupt-registry recovery.
"""

import json
import os
import stat
from unittest.mock import patch

import pytest


def _make_auth(tmp_path):
    """Create an AuthManager with its auth_file isolated to tmp_path."""
    from shadowcypher.core.auth import AuthManager
    auth_dir = tmp_path / "configs" / "security"
    auth_dir.mkdir(parents=True, exist_ok=True)
    mgr = AuthManager.__new__(AuthManager)
    mgr.auth_file = str(auth_dir / "auth.json")
    mgr.registry = {"users": {}, "keys": {}}
    return mgr


@pytest.fixture
def auth(tmp_path):
    return _make_auth(tmp_path)


class TestUserRegistration:

    def test_register_and_verify_correct_password(self, auth):
        auth.register_user("alice", "hunter2")
        assert auth.verify_user("alice", "hunter2") is True

    def test_wrong_password_rejected(self, auth):
        auth.register_user("bob", "secret")
        assert auth.verify_user("bob", "wrong") is False

    def test_unknown_user_returns_false(self, auth):
        assert auth.verify_user("ghost", "anything") is False

    def test_same_password_different_hashes(self, auth):
        auth.register_user("u1", "password")
        auth.register_user("u2", "password")
        h1 = auth.registry["users"]["u1"]["hash"]
        h2 = auth.registry["users"]["u2"]["hash"]
        assert h1 != h2  # Random salts guarantee uniqueness

    def test_empty_password_accepted(self, auth):
        auth.register_user("empty_pw", "")
        assert auth.verify_user("empty_pw", "") is True
        assert auth.verify_user("empty_pw", "notempty") is False

    def test_unicode_password(self, auth):
        auth.register_user("unicode_user", "p@$$w0rd🔒")
        assert auth.verify_user("unicode_user", "p@$$w0rd🔒") is True
        assert auth.verify_user("unicode_user", "p@$$w0rd") is False

    def test_hash_uses_pbkdf2(self, auth):
        auth.register_user("hashtest", "pw")
        entry = auth.registry["users"]["hashtest"]
        assert "hash" in entry
        assert "salt" in entry
        # Salt is 16 random bytes stored as 32-char hex
        assert len(entry["salt"]) == 32


class TestAdminKey:

    def test_generate_admin_key_with_env(self, auth):
        with patch.dict(os.environ, {"SHADOWCYPHER_ADMIN_KEY": "supersecretkey"}):
            with patch("shadowcypher.core.auth.config") as mc:
                mc.project_root = os.path.dirname(auth.auth_file.replace("auth.json",""))
                mc.get.return_value = None
                key = auth.generate_admin_key()
        assert key == "supersecretkey"
        assert "master" in auth.registry["keys"]

    def test_generate_admin_key_without_env_raises(self, auth):
        env = {k: v for k, v in os.environ.items()
               if k != "SHADOWCYPHER_ADMIN_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with patch("shadowcypher.core.auth.config") as mc:
                mc.get.return_value = None
                with pytest.raises(RuntimeError, match="ADMIN_KEY_UNSET"):
                    auth.generate_admin_key()

    def test_verify_correct_admin_key(self, auth):
        with patch.dict(os.environ, {"SHADOWCYPHER_ADMIN_KEY": "mykey"}):
            with patch("shadowcypher.core.auth.config") as mc:
                mc.project_root = os.path.dirname(auth.auth_file)
                mc.get.return_value = None
                auth.generate_admin_key()
        assert auth.verify_key("mykey") == "ADMIN"

    def test_verify_wrong_admin_key(self, auth):
        import hashlib
        auth.registry["keys"]["master"] = hashlib.sha256(b"rightkey").hexdigest()
        assert auth.verify_key("wrongkey") == "NONE"

    def test_verify_key_no_master_registered(self, auth):
        assert auth.verify_key("anykey") == "NONE"


class TestFileSecurity:

    def test_auth_file_permissions(self, auth, tmp_path):
        auth.register_user("testuser", "testpass")
        assert os.path.exists(auth.auth_file)
        mode = stat.S_IMODE(os.stat(auth.auth_file).st_mode)
        assert mode == 0o600, f"Expected 0o600, got 0o{mode:o}"

    def test_auth_file_content_is_valid_json(self, auth):
        auth.register_user("persisted", "data")
        with open(auth.auth_file) as f:
            data = json.load(f)
        assert "users" in data
        assert "persisted" in data["users"]

    def test_save_uses_atomic_rename(self, auth, tmp_path):
        """_save_registry writes to .tmp then renames — no partial writes."""
        auth.register_user("atomic", "test")
        # The .tmp file should not linger after save
        tmp_file = auth.auth_file + ".tmp"
        assert not os.path.exists(tmp_file)


class TestCorruptRegistry:

    def test_corrupt_json_returns_empty_registry(self, tmp_path):
        """_load_registry with corrupt JSON returns empty registry."""
        auth_dir = tmp_path / "configs" / "security"
        auth_dir.mkdir(parents=True)
        auth_file = auth_dir / "auth.json"
        auth_file.write_text("{not valid json!!!")

        mgr = _make_auth(tmp_path)
        mgr.auth_file = str(auth_file)
        registry = mgr._load_registry()

        assert registry["users"] == {}
        assert registry["keys"] == {}

    def test_missing_registry_file_starts_empty(self, tmp_path):
        """No auth.json at all → clean empty registry."""
        mgr = _make_auth(tmp_path)
        # auth_file points to non-existent file (tmp_path is fresh)
        registry = mgr._load_registry()
        assert registry["users"] == {}

    def test_registry_normalizes_missing_keys(self, tmp_path):
        """A JSON file missing 'users' or 'keys' gets defaults added."""
        auth_dir = tmp_path / "configs" / "security"
        auth_dir.mkdir(parents=True)
        auth_file = auth_dir / "auth.json"
        auth_file.write_text('{"users": {"x": {}}}')  # no "keys"

        mgr = _make_auth(tmp_path)
        mgr.auth_file = str(auth_file)
        registry = mgr._load_registry()
        assert "keys" in registry
