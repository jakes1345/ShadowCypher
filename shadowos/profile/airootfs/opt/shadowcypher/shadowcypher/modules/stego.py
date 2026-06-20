"""
Steganography + IPFS Dead Drop Module (T4-2).
LSB steganography in PNG images with AES-GCM payload encryption.
"""
import os
import struct
import secrets
from typing import Optional
from shadowcypher.core.logger import logger

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

MAGIC = b"SHDW"
VERSION = b"\x02"


class StegoEngine:
    """LSB image steganography — visually undetectable payload embedding."""

    def hide(self, payload, cover_path: str, output_path: str,
             key: bytes = None, on_output=None) -> str:
        if not HAS_PIL:
            self._emit(on_output, "[STEGO] MISSING: pip install pillow\n")
            return ""
        data = payload.encode() if isinstance(payload, str) else payload
        if key is None:
            key = secrets.token_bytes(32)
            self._emit(on_output, f"[STEGO] Key: {key.hex()} — SAVE THIS\n")
        if HAS_CRYPTO:
            aesgcm = AESGCM(key)
            nonce = secrets.token_bytes(12)
            data = nonce + aesgcm.encrypt(nonce, data, None)
        wire = MAGIC + VERSION + struct.pack(">I", len(data)) + data
        try:
            img = Image.open(cover_path).convert("RGB")
            cap = (img.width * img.height * 3) // 8
            if len(wire) > cap:
                self._emit(on_output, f"[STEGO] CAPACITY: need {len(wire)}B, have {cap}B\n")
                return ""
            pixels = list(img.getdata())
            bits = [int(b) for byte in wire for b in format(byte, "08b")]
            new_px, bi = [], 0
            for r, g, b in pixels:
                if bi < len(bits):
                    r = (r & 0xFE) | bits[bi]
                    bi += 1
                if bi < len(bits):
                    g = (g & 0xFE) | bits[bi]
                    bi += 1
                if bi < len(bits):
                    b = (b & 0xFE) | bits[bi]
                    bi += 1
                new_px.append((r, g, b))
            out = Image.new("RGB", img.size)
            out.putdata(new_px)
            if not output_path.endswith(".png"):
                output_path += ".png"
            out.save(output_path, "PNG")
            os.chmod(output_path, 0o600)
            self._emit(on_output, f"[STEGO] HIDDEN: {output_path}\n")
            return output_path
        except Exception as e:
            self._emit(on_output, f"[STEGO] ERROR: {e}\n")
            return ""

    def reveal(self, stego_path: str, key: bytes = None, on_output=None) -> Optional[bytes]:
        if not HAS_PIL:
            self._emit(on_output, "[STEGO] MISSING: pip install pillow\n")
            return None
        try:
            img = Image.open(stego_path).convert("RGB")
            bits = [c & 1 for px in img.getdata() for c in px]
            header_bytes = bytes(int("".join(str(b) for b in bits[i:i+8]),2) for i in range(0,72,8))
            if header_bytes[:4] != MAGIC:
                self._emit(on_output, "[STEGO] NO_PAYLOAD\n")
                return None
            plen = struct.unpack(">I", header_bytes[5:9])[0]
            raw = bytes(int("".join(str(b) for b in bits[72+i*8:80+i*8]),2) for i in range(plen))
            if key and HAS_CRYPTO:
                aesgcm = AESGCM(key)
                raw = aesgcm.decrypt(raw[:12], raw[12:], None)
            self._emit(on_output, f"[STEGO] RECOVERED: {len(raw)}B\n")
            return raw
        except Exception as e:
            self._emit(on_output, f"[STEGO] ERROR: {e}\n")
            return None

    def capacity(self, path: str) -> int:
        if not HAS_PIL:
            return 0
        try:
            img = Image.open(path)
            return (img.width * img.height * 3) // 8
        except Exception:
            return 0

    def ipfs_publish(self, file_path: str, on_output=None) -> str:
        import shutil
        import subprocess
        ipfs = shutil.which("ipfs")
        if not ipfs:
            self._emit(on_output, "[STEGO] IPFS not found\n")
            return ""
        try:
            r = subprocess.run([ipfs, "add", "-q", "--pin=true", file_path],
                               capture_output=True, text=True, timeout=30)
            cid = r.stdout.strip()
            if cid:
                self._emit(on_output, f"[STEGO] IPFS CID: {cid}\n"
                                      f"[STEGO] https://ipfs.io/ipfs/{cid}\n")
            return cid
        except Exception as e:
            self._emit(on_output, f"[STEGO] IPFS_ERROR: {e}\n")
            return ""

    @staticmethod
    def _emit(cb, msg):
        if cb:
            try:
                cb(msg)
            except Exception:
                pass


stego = StegoEngine()
