"""
Forensics Module — Enterprise Intelligence Build.
Handles data analysis, metadata extraction, and binary auditing.
"""

from shadowcypher.core.module import BaseModule
from shadowcypher.core.sanitize import validate_filepath

class Forensics(BaseModule):
    """The 'Analysis' engine of ShadowCypher."""
    
    def __init__(self):
        super().__init__(module_name="forensics")

    def _check_file(self, target):
        if not validate_filepath(target):
            self.log(f"FILE_ACCESS_DENIED: {target}", "ERROR")
            return False
        return True

    def analyze_file(self, target, on_output=None):
        if not self._check_file(target): return
        self.log(f"ANALYZING_FILE: {target}")
        
        # Binary identification
        return self.execute("FILE_INFO", ["file", target], callback=on_output)

    def extract_metadata(self, target, on_output=None):
        if not self._check_file(target): return
        self.log(f"EXTRACTING_EXIF: {target}")
        
        exiftool = self.get_tool_path("exiftool")
        return self.execute("METADATA", [exiftool, target], callback=on_output)

    def extract_strings(self, target, min_len=4, on_output=None):
        if not self._check_file(target): return
        self.log(f"STRINGS_EXTRACTION: {target} [MIN_LEN={min_len}]")
        
        return self.execute("STRINGS", ["strings", "-n", str(min_len), target], callback=on_output)

    def binwalk_scan(self, target, on_output=None):
        if not self._check_file(target): return
        self.log(f"BINWALK_AUDIT: {target}")
        
        binwalk = self.get_tool_path("binwalk")
        return self.execute("BINWALK", [binwalk, target], callback=on_output)

    def generate_hashes(self, target, on_output=None):
        if not self._check_file(target): return
        self.log(f"HASHING_FILE: {target}")
        
        return self.execute("HASH_SHA256", ["sha256sum", target], callback=on_output)

    def ai_investigate(self, target, on_output=None):
        """Escalate suspicious files to the AI for deep-dive analysis."""
        from shadowcypher.core.hub import hub
        self.log(f"AI_INVESTIGATION_INITIATED: {target}", "AI")
        # We might pass the strings output to the AI here
        return hub.dispatch_mission(f"Investigate the file {target}. Perform static analysis and explain its function/possible malicious attributes.")
