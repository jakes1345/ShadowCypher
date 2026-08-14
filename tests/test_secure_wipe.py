"""
Tests for SecureWipe module — NIST 800-88 compliant erasure.
All tests use temp files — no actual vault data is touched.
"""

import os
import tempfile
import pytest

from shadowcypher.modules.secure_wipe import SecureWipe, WipeLevel, WipeResult


@pytest.fixture
def wiper():
    return SecureWipe()


@pytest.fixture
def temp_file():
    """Create a temp file with known content; clean up if still present after test."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".test") as f:
        f.write(b"SHADOW_VAULT_TEST_DATA_1234567890" * 100)
        path = f.name
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def temp_dir():
    """Create a temp directory with a few files."""
    d = tempfile.mkdtemp()
    for i in range(3):
        fpath = os.path.join(d, f"artifact_{i}.dat")
        with open(fpath, "wb") as f:
            f.write(os.urandom(1024 * (i + 1)))
    yield d
    import shutil
    if os.path.exists(d):
        shutil.rmtree(d)


class TestWipeFile:

    def test_quick_wipe_removes_file(self, wiper, temp_file):
        result = wiper.wipe_file(temp_file, WipeLevel.QUICK)
        assert result.success is True
        assert not os.path.exists(temp_file)

    def test_clear_wipe_removes_file(self, wiper, temp_file):
        result = wiper.wipe_file(temp_file, WipeLevel.CLEAR)
        assert result.success is True
        assert not os.path.exists(temp_file)
        assert result.passes == 3

    def test_purge_wipe_removes_file(self, wiper, temp_file):
        result = wiper.wipe_file(temp_file, WipeLevel.PURGE)
        assert result.success is True
        assert not os.path.exists(temp_file)
        assert result.passes >= 7

    def test_crypto_wipe_removes_file(self, wiper, temp_file):
        result = wiper.wipe_file(temp_file, WipeLevel.CRYPTO)
        assert result.success is True
        assert not os.path.exists(temp_file)

    def test_bytes_wiped_reported(self, wiper, temp_file):
        original_size = os.path.getsize(temp_file)
        result = wiper.wipe_file(temp_file, WipeLevel.QUICK)
        assert result.bytes_wiped == original_size

    def test_nonexistent_file_fails_gracefully(self, wiper):
        result = wiper.wipe_file("/tmp/no_such_file_shadowcypher.dat")
        assert result.success is False
        assert result.error != ""

    def test_progress_callback_called(self, wiper, temp_file):
        messages = []
        wiper.wipe_file(temp_file, WipeLevel.CLEAR, progress_cb=messages.append)
        assert len(messages) >= 3  # One per pass

    def test_renamed_before_unlink(self, wiper, temp_file):
        result = wiper.wipe_file(temp_file, WipeLevel.QUICK)
        assert result.renamed_before_unlink is True


class TestWipeDirectory:

    def test_wipes_all_files(self, wiper, temp_dir):
        results = wiper.wipe_directory(temp_dir, WipeLevel.QUICK)
        assert len(results) == 3
        assert all(r.success for r in results)

    def test_directory_removed_after_wipe(self, wiper, temp_dir):
        wiper.wipe_directory(temp_dir, WipeLevel.QUICK)
        assert not os.path.exists(temp_dir)

    def test_nonexistent_dir_fails_gracefully(self, wiper):
        results = wiper.wipe_directory("/tmp/no_such_dir_shadowcypher")
        assert len(results) == 1
        assert results[0].success is False


class TestHelpers:

    def test_human_bytes(self):
        w = SecureWipe()
        assert w._human(512) == "512.0 B"
        assert "KB" in w._human(2048)
        assert "MB" in w._human(2 * 1024 * 1024)

    def test_wipe_level_enum(self):
        assert WipeLevel("quick") == WipeLevel.QUICK
        assert WipeLevel("purge") == WipeLevel.PURGE
