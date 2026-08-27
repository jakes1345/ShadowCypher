"""
SecureWipe — NIST SP 800-88 Rev.1 compliant file/directory erasure.

Wipe levels:
  QUICK   — 1-pass cryptographically random overwrite (adequate for modern flash/SSD)
  CLEAR   — 3-pass DoD 5220.22-M (zeros → ones → random), suitable for HDD clear
  PURGE   — 7-pass overwrite then cryptographic erasure (encrypt → discard key)
  CRYPTO  — Cryptographic erasure only: encrypt with random key, discard key, unlink

For SSDs/flash, NIST 800-88 recommends CRYPTO (cryptographic erasure) over
multi-pass, since wear-leveling makes multi-pass rewrites unreliable.
"""

import os
import secrets
import stat
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from shadowcypher.core.bus import bus
from shadowcypher.core.logger import logger


class WipeLevel(Enum):
    QUICK = "quick"     # 1-pass random
    CLEAR = "clear"     # 3-pass (DoD 5220.22-M baseline)
    PURGE = "purge"     # 7-pass + crypto erasure
    CRYPTO = "crypto"   # Cryptographic erasure only (SSD-safe)


_PASS_PATTERNS = {
    WipeLevel.QUICK: [None],              # None = random
    WipeLevel.CLEAR: [0x00, 0xFF, None],  # zeros, ones, random
    WipeLevel.PURGE: [0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, None],  # 7-pass
    WipeLevel.CRYPTO: [],                 # handled separately
}


@dataclass
class WipeResult:
    path: str
    success: bool
    bytes_wiped: int = 0
    passes: int = 0
    error: str = ""
    renamed_before_unlink: bool = False


class SecureWipe:
    """NIST 800-88 compliant secure erasure engine."""

    CHUNK = 65536  # 64 KB write chunks

    def wipe_file(
        self,
        path: str,
        level: WipeLevel = WipeLevel.CLEAR,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> WipeResult:
        """
        Securely erase a single file.
        Returns WipeResult with success status and bytes processed.
        """
        path = os.path.abspath(path)
        result = WipeResult(path=path, success=False)

        if not os.path.isfile(path):
            result.error = "not a regular file"
            return result

        try:
            # Make file writable if read-only
            try:
                os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            except OSError:
                pass

            size = os.path.getsize(path)
            result.bytes_wiped = size

            if level == WipeLevel.CRYPTO:
                self._crypto_erase(path, size, progress_cb)
                result.passes = 1
            else:
                patterns = _PASS_PATTERNS[level]
                for i, pattern in enumerate(patterns, 1):
                    label = "RANDOM" if pattern is None else f"0x{pattern:02X}"
                    if progress_cb:
                        progress_cb(f"  Pass {i}/{len(patterns)}: {label} ({self._human(size)})")
                    self._overwrite_pass(path, size, pattern)
                    result.passes = i

                # Final: crypto erasure on top of multi-pass
                if level == WipeLevel.PURGE:
                    if progress_cb:
                        progress_cb("  Pass final: CRYPTO_ERASURE")
                    self._crypto_erase(path, size, None)
                    result.passes += 1

            # Rename to random name before unlink (prevents filename forensics)
            renamed = self._rename_before_unlink(path)
            result.renamed_before_unlink = renamed is not None
            target = renamed if renamed else path

            os.remove(target)
            result.success = True

            bus.publish("module_log", {
                "module": "secure_wipe",
                "text": f"WIPED: {os.path.basename(path)} [{level.value.upper()} | {result.passes} pass | {self._human(size)}]",
                "level": "SUCCESS",
            })

        except Exception as exc:
            result.error = str(exc)
            logger.error("secure_wipe", f"WIPE_ERROR: {path} — {exc}")

        return result

    def wipe_directory(
        self,
        path: str,
        level: WipeLevel = WipeLevel.CLEAR,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> list[WipeResult]:
        """Recursively wipe all files in a directory, then remove empty dirs."""
        path = os.path.abspath(path)
        results = []

        if not os.path.isdir(path):
            results.append(WipeResult(path=path, success=False, error="not a directory"))
            return results

        # Collect all files depth-first (files before dirs)
        all_files = []
        for root, _dirs, files in os.walk(path, topdown=False):
            for fname in files:
                all_files.append(os.path.join(root, fname))

        for fpath in all_files:
            if progress_cb:
                progress_cb(f"ERASING: {os.path.relpath(fpath, path)}")
            r = self.wipe_file(fpath, level, progress_cb)
            results.append(r)

        # Remove empty directories (bottom-up)
        for root, _dirs, _files in os.walk(path, topdown=False):
            try:
                os.rmdir(root)
            except OSError:
                pass  # Not empty yet — leave it

        return results

    def wipe_free_space(
        self,
        mount_point: str,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> WipeResult:
        """
        Overwrite free space on a filesystem by filling it with random data,
        then delete the temporary file. Best-effort — doesn't guarantee
        every deleted block is overwritten on journaled / CoW filesystems.
        """
        tmp = os.path.join(mount_point, f".shadow_wipe_{secrets.token_hex(8)}")
        result = WipeResult(path=mount_point, success=False)

        try:
            if progress_cb:
                progress_cb(f"FREE_SPACE_WIPE: filling {mount_point} …")

            written = 0
            with open(tmp, "wb") as f:
                while True:
                    chunk = secrets.token_bytes(self.CHUNK)
                    try:
                        f.write(chunk)
                        f.flush()
                        written += len(chunk)
                    except OSError:
                        break  # Disk full — that's the goal

            os.remove(tmp)
            result.bytes_wiped = written
            result.success = True
            if progress_cb:
                progress_cb(f"FREE_SPACE_WIPE: {self._human(written)} overwritten + removed")

        except Exception as exc:
            result.error = str(exc)
            try:
                os.remove(tmp)
            except OSError:
                pass

        return result

    # ── Internal ──────────────────────────────────────────────

    def _overwrite_pass(self, path: str, size: int, pattern: Optional[int]):
        """Single overwrite pass. pattern=None means cryptographically random."""
        with open(path, "r+b") as f:
            remaining = size
            while remaining > 0:
                chunk_size = min(self.CHUNK, remaining)
                if pattern is None:
                    data = secrets.token_bytes(chunk_size)
                else:
                    data = bytes([pattern]) * chunk_size
                f.write(data)
                remaining -= chunk_size
            f.flush()
            os.fsync(f.fileno())

    def _crypto_erase(self, path: str, size: int, progress_cb):
        """
        NIST 800-88 cryptographic erasure:
        1. Generate a random AES-256 key.
        2. Encrypt the file content in place.
        3. Discard the key — content is cryptographically unrecoverable.
        """
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            key = secrets.token_bytes(32)
            nonce = secrets.token_bytes(12)
            aesgcm = AESGCM(key)

            with open(path, "r+b") as f:
                plaintext = f.read()
                ct = aesgcm.encrypt(nonce, plaintext, None)
                f.seek(0)
                f.write(ct[:size])  # Truncate to original size
                f.truncate(size)
                f.flush()
                os.fsync(f.fileno())

            # Key is discarded here — no reference kept
            del key
        except ImportError:
            # Fallback: final random pass
            self._overwrite_pass(path, size, None)

    def _rename_before_unlink(self, path: str) -> Optional[str]:
        """Rename to random filename in same dir to obscure original name."""
        try:
            parent = os.path.dirname(path)
            random_name = f".{secrets.token_hex(16)}"
            new_path = os.path.join(parent, random_name)
            os.rename(path, new_path)
            return new_path
        except OSError:
            return None

    @staticmethod
    def _human(nbytes: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if nbytes < 1024:
                return f"{nbytes:.1f} {unit}"
            nbytes /= 1024
        return f"{nbytes:.1f} TB"


# ── Singleton ──────────────────────────────────────────────
secure_wipe = SecureWipe()
