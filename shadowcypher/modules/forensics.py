"""ShadowCypher Forensics (Analysis) Engine — Absolute Sync (Build V29.1)."""

import os
from shadowcypher.core.runner import runner
from shadowcypher.core.logger import logger

class Forensics:
    """The 'Analysis' engine. Handles file info, hashing, EXIF, and binwalk."""
    
    @staticmethod
    def file_info(target, on_output=None, on_complete=None):
        cmd = f"file {target}"
        runner.execute_task(f"FILE_INFO_{target}", cmd, callback=on_output)

    @staticmethod
    def file_hashes(target, on_output=None, on_complete=None):
        cmd = f"sha256sum {target}"
        runner.execute_task(f"HASHES_{target}", cmd, callback=on_output)

    @staticmethod
    def extract_strings(target, on_output=None, on_complete=None):
        cmd = f"strings {target}"
        runner.execute_task(f"STRINGS_{target}", cmd, callback=on_output)

    @staticmethod
    def hex_dump(target, on_output=None, on_complete=None):
        cmd = f"hexdump -C {target} | head -n 100"
        runner.execute_task(f"HEXDUMP_{target}", cmd, callback=on_output)

    @staticmethod
    def exif_data(target, on_output=None, on_complete=None):
        cmd = f"exiftool {target}"
        runner.execute_task(f"EXIF_{target}", cmd, callback=on_output)

    @staticmethod
    def stego_detect(target, on_output=None, on_complete=None):
        cmd = f"steghide info {target}"
        runner.execute_task(f"STEGO_{target}", cmd, callback=on_output)

    @staticmethod
    def binwalk_analysis(target, on_output=None, on_complete=None):
        cmd = f"binwalk {target}"
        runner.execute_task(f"BINWALK_{target}", cmd, callback=on_output)

    @staticmethod
    def pdf_analysis(target, on_output=None, on_complete=None):
        cmd = f"pdfid {target}"
        runner.execute_task(f"PDF_SCAN_{target}", cmd, callback=on_output)

    # UI Backwards Compatibility Hooks
    @staticmethod
    def strings_extract(target, on_output=None, on_complete=None): Forensics.extract_strings(target, on_output, on_complete)
    @staticmethod
    def binwalk_extract(target, on_output=None, on_complete=None): Forensics.binwalk_analysis(target, on_output, on_complete)
