import re
from shadowcypher.core.logger import logger
class Kairos:
    def __init__(self): self.vuln_patterns = [r"SQL injection", r"XSS", r"RCE"]
    def analyze(self, line):
        for p in self.vuln_patterns: 
            if re.search(p, line, re.I): logger.info("kairos", f"ALERT: {line.strip()}")
kairos = Kairos()