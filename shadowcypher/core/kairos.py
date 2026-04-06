import re
from shadowcypher.core.logger import logger
from shadowcypher.core.database import db

class Kairos:
    def __init__(self):
        self.vuln_patterns = [r"SQL injection", r"XSS", r"RCE"]
        self.ip_regex = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
        
    def analyze(self, line):
        # Scan for IPs to register in the SQLite Matrix
        ip_hits = self.ip_regex.findall(line)
        for ip in ip_hits:
            if not ip.startswith("127.0.") and not ip.startswith("0.0."):
                db.register_target(ip)
                
        # Scan for vulnerable patterns
        for p in self.vuln_patterns: 
            if re.search(p, line, re.I): 
                logger.info("kairos", f"ALERT: {line.strip()}")
                
kairos = Kairos()