"""ShadowCypher Forensics (Analysis) Engine — Absolute Sync (Build V29.1)."""

import os
from shadowcypher.core.runner import runner
from shadowcypher.core.logger import logger
from shadowcypher.core.sanitize import validate_filepath


class Forensics:
    """The 'Analysis' engine. Handles file info, hashing, EXIF, and binwalk."""

    @staticmethod
    def _check_target(target, on_output):
        if not validate_filepath(target):
            if on_output: on_output(f"[ERROR] Invalid or dangerous file path: {target}")
            return False
        return True

    @staticmethod
    def file_info(target, on_output=None, on_complete=None):
        if not Forensics._check_target(target, on_output): return
        runner.execute_task(f"FILE_INFO", ["file", target], callback=on_output)

    @staticmethod
    def file_hashes(target, on_output=None, on_complete=None):
        if not Forensics._check_target(target, on_output): return
        runner.execute_task(f"HASHES", ["sha256sum", target], callback=on_output)

    @staticmethod
    def extract_strings(target, on_output=None, on_complete=None):
        if not Forensics._check_target(target, on_output): return
        runner.execute_task(f"STRINGS", ["strings", target], callback=on_output)

    @staticmethod
    def hex_dump(target, on_output=None, on_complete=None):
        if not Forensics._check_target(target, on_output): return
        import shlex
        cmd = f"hexdump -C {shlex.quote(target)} | head -n 100"
        runner.execute_task_shell(f"HEXDUMP", cmd, callback=on_output)

    @staticmethod
    def exif_data(target, on_output=None, on_complete=None):
        if not Forensics._check_target(target, on_output): return
        runner.execute_task(f"EXIF", ["exiftool", target], callback=on_output)

    @staticmethod
    def stego_detect(target, on_output=None, on_complete=None):
        if not Forensics._check_target(target, on_output): return
        runner.execute_task(f"STEGO", ["steghide", "info", target], callback=on_output)

    @staticmethod
    def binwalk_analysis(target, on_output=None, on_complete=None):
        if not Forensics._check_target(target, on_output): return
        runner.execute_task(f"BINWALK", ["binwalk", target], callback=on_output)

    @staticmethod
    def pdf_analysis(target, on_output=None, on_complete=None):
        if not Forensics._check_target(target, on_output): return
        runner.execute_task(f"PDF_SCAN", ["pdfid", target], callback=on_output)

    # UI Backwards Compatibility Hooks
    @staticmethod
    def strings_extract(target, on_output=None, on_complete=None): Forensics.extract_strings(target, on_output, on_complete)
    @staticmethod
    def binwalk_extract(target, on_output=None, on_complete=None): Forensics.binwalk_analysis(target, on_output, on_complete)
