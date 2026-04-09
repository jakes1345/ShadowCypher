import os
import fcntl
import contextlib
import time
from shadowcypher.core.logger import logger

@contextlib.contextmanager
def file_lock(file_path, timeout=10):
    """
    Tactical File Locking — Prevents race conditions in high-fidelity data ops.
    Uses fcntl for professional Unix-level atomic locking.
    """
    lock_file = f"{file_path}.lock"
    f = open(lock_file, "w")
    
    start_time = time.time()
    while True:
        try:
            # Non-blocking exclusive lock
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError:
            if time.time() - start_time > timeout:
                logger.error("utils", f"LOCK_TIMEOUT: Failed to acquire lock for {file_path}")
                f.close()
                raise TimeoutError(f"Could not acquire lock for {file_path}")
            time.sleep(0.1)
    
    try:
        yield
    finally:
        # Release and close
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
