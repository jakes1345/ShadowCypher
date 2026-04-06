"""ShadowCypher Digital Forensics Engine — High-Fidelity Sync (V23.2)."""

import os
from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner

class Forensics:
    """Universal forensics engine. Handles file analysis, metadata, and memory dumps."""
    
    @staticmethod
    def file_info(filepath):
        """Get detailed file information using 'file' command."""
        os.system(f"file {filepath} > /tmp/file_info.txt")
        with open("/tmp/file_info.txt", "r") as f:
            return f.read()

    @staticmethod
    def file_hashes(filepath):
        """Calculate hashes of a file."""
        os.system(f"sha256sum {filepath} > /tmp/hashes.txt")
        with open("/tmp/hashes.txt", "r") as f:
            return f.read()

    @staticmethod
    def strings_extract(filepath, min_length=4, on_output=None, on_complete=None):
        """Extract printable strings from a file."""
        cmd = f"strings -n {min_length} {filepath}"
        runner.execute_task(f"STRINGS_{filepath}", cmd, callback=on_output)

    @staticmethod
    def hex_dump(filepath, offset=0, length=512):
        """Hex dump of a file section."""
        os.system(f"xxd -s {offset} -l {length} {filepath} > /tmp/hex_dump.txt")
        with open("/tmp/hex_dump.txt", "r") as f:
            return f.read()

    @staticmethod
    def exif_data(filepath):
        """Extract EXIF metadata from image files."""
        os.system(f"exiftool {filepath} > /tmp/exif.txt")
        with open("/tmp/exif.txt", "r") as f:
            return f.read()

    @staticmethod
    def stego_detect(filepath, on_output=None, on_complete=None):
        """Attempt steganography detection."""
        cmd = f"binwalk {filepath}"
        runner.execute_task(f"STEGO_DETECT_{filepath}", cmd, callback=on_output)

    @staticmethod
    def volatility_info(memory_dump, on_output=None, on_complete=None):
        """Run Volatility framework imageinfo on a memory dump."""
        cmd = f"vol.py -f {memory_dump} windows.info"
        runner.execute_task("VOLATILITY_SCAN", cmd, callback=on_output)

    @staticmethod
    def pdf_analysis(filepath):
        """Analyze a PDF for suspicious objects."""
        os.system(f"pdfinfo {filepath} > /tmp/pdfinfo.txt")
        with open("/tmp/pdfinfo.txt", "r") as f:
            return f.read()
