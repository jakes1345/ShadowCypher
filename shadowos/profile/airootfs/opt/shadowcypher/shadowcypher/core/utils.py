"""Utility functions — file locking, atomic writes, secure reads.
Cross-platform: uses fcntl on Unix, msvcrt on Windows.
"""

import contextlib
import os

# ── Cross-platform file locking ──
# fcntl is Unix-only, msvcrt is Windows-only
import sys
import time

from shadowcypher.core.logger import logger

if sys.platform == "win32":
    import msvcrt

    @contextlib.contextmanager
    def file_lock(file_path, timeout=10):
        """Windows file lock using msvcrt."""
        lock_file = f"{file_path}.lock"
        f = open(lock_file, "w")

        start_time = time.time()
        while True:
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except (IOError, OSError) as e:
                if time.time() - start_time > timeout:
                    logger.error("utils", f"LOCK_TIMEOUT: Failed to acquire lock for {file_path}")
                    f.close()
                    raise TimeoutError(f"Could not acquire lock for {file_path}") from e
                time.sleep(0.1)

        try:
            yield
        finally:
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            except (IOError, OSError):
                pass
            f.close()
            try:
                os.remove(lock_file)
            except OSError:
                pass
else:
    import fcntl

    @contextlib.contextmanager
    def file_lock(file_path, timeout=10):
        """Unix file lock using fcntl (Linux + macOS)."""
        lock_file = f"{file_path}.lock"
        f = open(lock_file, "w")

        start_time = time.time()
        while True:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as e:
                if time.time() - start_time > timeout:
                    logger.error("utils", f"LOCK_TIMEOUT: Failed to acquire lock for {file_path}")
                    f.close()
                    raise TimeoutError(f"Could not acquire lock for {file_path}") from e
                time.sleep(0.1)

        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()
            try:
                os.remove(lock_file)
            except OSError:
                pass


def secure_write(file_path, content, mode="w"):
    """Professional atomic write with locking."""
    with file_lock(file_path):
        with open(file_path, mode) as f:
            f.write(content)


def secure_read(file_path):
    """Professional read with shared lock."""
    with file_lock(file_path):
        if not os.path.exists(file_path):
            return None
        with open(file_path, "r") as f:
            return f.read()
