"""
ShadowCypher Test Suite — CryptoManager DRM
Tests Fernet key generation, unlock flow, lockout-after-failures,
lockout expiry, and the require_unlock decorator.

Uses yield fixtures so the config patch stays active through the entire test,
and mocks time.sleep so lockout tests run in milliseconds.
"""

import os
import stat
import time
import pytest
from unittest.mock import patch


@pytest.fixture
def mgr(tmp_path):
    """CryptoManager with config.project_root isolated to tmp_path."""
    with patch("shadowcypher.core.crypto.config") as mock_cfg:
        mock_cfg.project_root = str(tmp_path)
        from shadowcypher.core.crypto import CryptoManager
        m = CryptoManager()
        m._failed_attempts = 0
        yield m, tmp_path


class TestKeyGeneration:

    def test_generate_creates_key_file(self, mgr):
        m, tmp_path = mgr
        m.generate_license_key()
        key_file = os.path.join(str(tmp_path), ".session-secret")
        assert os.path.exists(key_file)

    def test_generated_key_is_valid_fernet(self, mgr):
        from cryptography.fernet import Fernet
        m, _ = mgr
        key = m.generate_license_key()
        Fernet(key.encode())  # Must not raise

    def test_generate_sets_unlocked(self, mgr):
        m, _ = mgr
        m.generate_license_key()
        assert m.is_unlocked is True

    def test_generate_sets_fernet(self, mgr):
        from cryptography.fernet import Fernet
        m, _ = mgr
        m.generate_license_key()
        assert m.fernet is not None

    def test_key_file_permissions(self, mgr):
        m, tmp_path = mgr
        m.generate_license_key()
        key_file = os.path.join(str(tmp_path), ".session-secret")
        mode = stat.S_IMODE(os.stat(key_file).st_mode)
        assert mode == 0o600, f"Expected 0o600, got 0o{mode:o}"


class TestUnlock:

    def test_valid_fernet_key_unlocks(self, mgr):
        from cryptography.fernet import Fernet
        m, _ = mgr
        with patch("shadowcypher.core.crypto.time") as mock_time:
            mock_time.time.return_value = time.time()
            mock_time.sleep = lambda _: None
            key = Fernet.generate_key().decode()
            assert m.unlock_system(key) is True
        assert m.is_unlocked is True

    def test_garbage_key_fails(self, mgr):
        m, _ = mgr
        with patch("shadowcypher.core.crypto.time") as mock_time:
            mock_time.time.return_value = time.time()
            mock_time.sleep = lambda _: None
            result = m.unlock_system("definitely-not-a-fernet-key")
        assert result is False
        assert m.is_unlocked is False

    def test_failed_attempts_increment(self, mgr):
        m, _ = mgr
        with patch("shadowcypher.core.crypto.time") as mock_time:
            mock_time.time.return_value = time.time()
            mock_time.sleep = lambda _: None
            m.unlock_system("bad1")
            assert m._failed_attempts == 1
            m.unlock_system("bad2")
            assert m._failed_attempts == 2

    def test_success_resets_failed_attempts(self, mgr):
        from cryptography.fernet import Fernet
        m, _ = mgr
        with patch("shadowcypher.core.crypto.time") as mock_time:
            mock_time.time.return_value = time.time()
            mock_time.sleep = lambda _: None
            m.unlock_system("bad")
            assert m._failed_attempts == 1
            key = Fernet.generate_key().decode()
            m.unlock_system(key)
            assert m._failed_attempts == 0


class TestLockout:

    def _fast_failures(self, m, tmp_path, n=5):
        """Trigger n unlock failures without real sleep delays."""
        lockout_path = os.path.join(str(tmp_path), ".drm-lockout")
        with patch("shadowcypher.core.crypto.time") as mock_time:
            mock_time.time.return_value = time.time()
            mock_time.sleep = lambda _: None
            for _ in range(n):
                m.unlock_system("bad_key")
        return lockout_path

    def test_five_failures_create_lockout_file(self, mgr):
        m, tmp_path = mgr
        lockout_path = self._fast_failures(m, tmp_path, 5)
        assert os.path.exists(lockout_path)

    def test_fresh_lockout_blocks_unlock(self, mgr):
        from cryptography.fernet import Fernet
        m, tmp_path = mgr
        lockout_path = os.path.join(str(tmp_path), ".drm-lockout")
        with open(lockout_path, "w") as f:
            f.write(str(time.time()))
        key = Fernet.generate_key().decode()
        with patch("shadowcypher.core.crypto.time") as mock_time:
            mock_time.time.return_value = time.time()
            mock_time.sleep = lambda _: None
            result = m.unlock_system(key)
        assert result is False

    def test_expired_lockout_cleared_and_allows_unlock(self, mgr):
        from cryptography.fernet import Fernet
        m, tmp_path = mgr
        lockout_path = os.path.join(str(tmp_path), ".drm-lockout")
        with open(lockout_path, "w") as f:
            f.write(str(time.time() - 7200))  # 2 hours ago
        key = Fernet.generate_key().decode()
        with patch("shadowcypher.core.crypto.time") as mock_time:
            mock_time.time.return_value = time.time()
            mock_time.sleep = lambda _: None
            result = m.unlock_system(key)
        assert result is True
        assert not os.path.exists(lockout_path)

    def test_corrupt_lockout_file_cleared(self, mgr):
        from cryptography.fernet import Fernet
        m, tmp_path = mgr
        lockout_path = os.path.join(str(tmp_path), ".drm-lockout")
        with open(lockout_path, "w") as f:
            f.write("not a timestamp")
        key = Fernet.generate_key().decode()
        with patch("shadowcypher.core.crypto.time") as mock_time:
            mock_time.time.return_value = time.time()
            mock_time.sleep = lambda _: None
            result = m.unlock_system(key)
        assert result is True


class TestRequireUnlockDecorator:

    def test_locked_returns_access_denied(self, mgr):
        m, _ = mgr
        assert m.is_unlocked is False

        @m.require_unlock
        def protected():
            return "secret_data"

        result = protected()
        assert "ACCESS DENIED" in result or "DRM_LOCK" in result

    def test_unlocked_calls_through(self, mgr):
        from cryptography.fernet import Fernet
        m, _ = mgr
        with patch("shadowcypher.core.crypto.time") as mock_time:
            mock_time.time.return_value = time.time()
            mock_time.sleep = lambda _: None
            m.unlock_system(Fernet.generate_key().decode())

        @m.require_unlock
        def protected():
            return "secret_data"

        assert protected() == "secret_data"

    def test_decorator_passes_args_through(self, mgr):
        from cryptography.fernet import Fernet
        m, _ = mgr
        with patch("shadowcypher.core.crypto.time") as mock_time:
            mock_time.time.return_value = time.time()
            mock_time.sleep = lambda _: None
            m.unlock_system(Fernet.generate_key().decode())

        @m.require_unlock
        def add(a, b):
            return a + b

        assert add(3, 4) == 7
