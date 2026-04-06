"""Forensics module — file analysis, hash verification, steganography detection."""

import os
import hashlib
import tempfile
from shadowcypher.core.runner import runner
from shadowcypher.core.logger import logger
from shadowcypher.core.sanitize import quote, validate_filepath


_NOOP = lambda x: None


class Forensics:
    """Digital forensics operations."""

    @staticmethod
    def _check_file(filepath: str, on_output=None, on_complete=None) -> bool:
        """Validate file path. Returns True if valid."""
        if not validate_filepath(filepath):
            (on_output or _NOOP)(f"[ERROR] Invalid file path: {filepath}\n")
            if on_complete:
                on_complete(1)
            return False
        return True

    @staticmethod
    def file_info(filepath: str) -> str:
        """Get detailed file information using 'file' command."""
        if not validate_filepath(filepath):
            return f"Invalid file path: {filepath}"
        output, _ = runner.run_sync(f"file -b {quote(filepath)}", shell=True, timeout=5)
        stat_out, _ = runner.run_sync(f"stat {quote(filepath)}", shell=True, timeout=5)
        return f"Type: {output}\n\n{stat_out}"

    @staticmethod
    def file_hashes(filepath: str) -> str:
        """Calculate MD5, SHA1, SHA256, SHA512 hashes of a file."""
        if not os.path.isfile(filepath):
            return f"Error: {filepath} not found"

        results = []
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            results.append(f"MD5:    {hashlib.md5(data).hexdigest()}")
            results.append(f"SHA1:   {hashlib.sha1(data).hexdigest()}")
            results.append(f"SHA256: {hashlib.sha256(data).hexdigest()}")
            results.append(f"SHA512: {hashlib.sha512(data).hexdigest()}")
            results.append(f"Size:   {len(data)} bytes")
        except Exception as e:
            results.append(f"Error: {e}")

        return "\n".join(results)

    @staticmethod
    def strings_extract(filepath: str, min_length: int = 4, on_output=None, on_complete=None) -> int:
        """Extract printable strings from a file."""
        if not Forensics._check_file(filepath, on_output, on_complete):
            return -1
        min_length = max(1, min(int(min_length), 100))
        cmd = f"strings -n {min_length} {quote(filepath)}"
        logger.info("forensics", f"Extracting strings: {filepath}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def hex_dump(filepath: str, offset: int = 0, length: int = 512) -> str:
        """Hex dump of a file section."""
        if not validate_filepath(filepath):
            return f"Invalid file path: {filepath}"
        offset = max(0, int(offset))
        length = max(1, min(int(length), 65536))
        output, _ = runner.run_sync(
            f"xxd -s {offset} -l {length} {quote(filepath)}", shell=True, timeout=10
        )
        return output

    @staticmethod
    def exif_data(filepath: str) -> str:
        """Extract EXIF metadata from image files."""
        if not validate_filepath(filepath):
            return f"Invalid file path: {filepath}"
        output, rc = runner.run_sync(f"exiftool {quote(filepath)} 2>/dev/null", shell=True, timeout=10)
        if rc != 0:
            output2, _ = runner.run_sync(f"identify -verbose {quote(filepath)} 2>/dev/null | head -50", shell=True, timeout=10)
            return output2 if output2 else "No EXIF tool available (install exiftool)"
        return output

    @staticmethod
    def stego_detect(filepath: str, on_output=None, on_complete=None) -> int:
        """Attempt steganography detection on image files."""
        if not Forensics._check_file(filepath, on_output, on_complete):
            return -1
        safe_path = quote(filepath)
        script = f"""
echo "=== File Type ==="
file {safe_path}
echo ""
echo "=== Entropy Analysis ==="
ent {safe_path} 2>/dev/null || echo "(install 'ent' for entropy analysis)"
echo ""
echo "=== Binwalk Signature Scan ==="
binwalk {safe_path} 2>/dev/null || echo "(install 'binwalk' for embedded file detection)"
echo ""
echo "=== Strings (suspicious) ==="
strings {safe_path} | grep -iE '(password|secret|key|flag|hidden|base64)' | head -20
echo ""
echo "=== Trailing Data Check ==="
python3 -c "
import sys
with open(sys.argv[1], 'rb') as f:
    data = f.read()
    iend = data.find(b'IEND')
    if iend >= 0 and iend + 8 < len(data):
        trailing = len(data) - (iend + 8)
        print(f'WARNING: {{trailing}} bytes of trailing data after PNG IEND chunk')
    eoi = data.rfind(b'\\xff\\xd9')
    if eoi >= 0 and eoi + 2 < len(data):
        trailing = len(data) - (eoi + 2)
        print(f'WARNING: {{trailing}} bytes of trailing data after JPEG EOI marker')
    if iend < 0 and eoi < 0:
        print('Not a PNG/JPEG — skipping trailer check')
" {safe_path} 2>/dev/null
"""
        logger.info("forensics", f"Steganography detection: {filepath}")
        return runner.run(script, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def binwalk_extract(filepath: str, output_dir: str = None,
                        on_output=None, on_complete=None) -> int:
        """Extract embedded files using binwalk."""
        if not Forensics._check_file(filepath, on_output, on_complete):
            return -1
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="sc_binwalk_")
        cmd = f"binwalk -e -C {quote(output_dir)} {quote(filepath)}"
        logger.info("forensics", f"Binwalk extract: {filepath}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def disk_image_info(image_path: str) -> str:
        """Get info about a disk image."""
        if not validate_filepath(image_path):
            return f"Invalid file path: {image_path}"
        output, _ = runner.run_sync(f"fdisk -l {quote(image_path)} 2>/dev/null", shell=True, timeout=10)
        if not output:
            output, _ = runner.run_sync(f"file {quote(image_path)}", shell=True, timeout=5)
        return output

    @staticmethod
    def volatility_info(memory_dump: str, on_output=None, on_complete=None) -> int:
        """Run Volatility framework imageinfo on a memory dump."""
        if not Forensics._check_file(memory_dump, on_output, on_complete):
            return -1
        safe = quote(memory_dump)
        cmd = f"vol.py -f {safe} imageinfo 2>/dev/null || python3 -m volatility3 -f {safe} windows.info 2>/dev/null || echo 'Volatility not installed'"
        logger.info("forensics", f"Memory analysis: {memory_dump}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def pdf_analysis(filepath: str) -> str:
        """Analyze a PDF for suspicious objects."""
        if not validate_filepath(filepath):
            return f"Invalid file path: {filepath}"
        safe = quote(filepath)
        script = f"""
echo "=== PDF Info ==="
pdfinfo {safe} 2>/dev/null || echo "(pdfinfo not available)"
echo ""
echo "=== Suspicious Strings ==="
strings {safe} | grep -iE '(javascript|/JS|/Launch|/OpenAction|/AA |/URI|eval|exec)' | head -20
echo ""
echo "=== Object Streams ==="
strings {safe} | grep -cE 'stream|endstream' | xargs -I{{}} echo "Stream objects: {{}}"
"""
        output, _ = runner.run_sync(script, shell=True, timeout=15)
        return output
