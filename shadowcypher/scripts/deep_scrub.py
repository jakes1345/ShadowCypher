#!/usr/bin/env python3
# ==============================================================================
# SHADOWCYPHER // SOURCE CODE DATA SANITIZER
# ==============================================================================
# Analyzes the repository and automatically redacts hardcoded IPs, 
# PII, and credentials to prepare the codebase for public distribution.

import os
import re
import logging

# Enterprise Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s | [%(levelname)s] | %(message)s', datefmt='%H:%M:%S')

# Sanitization Mapping (Regex -> Replacement)
REDACTION_MAP = {
    r"(?<!/home/)shadow_operator": "shadow_operator",
    r"shadow_admin": "shadow_admin",
    r"shadow_admin1328!@": "ADMIN_PASSWORD_PLACEHOLDER",
    r"97\.243\.145\.96": "MASTER_NODE_IP",
    r"192\.168\.1\.1": "GATEWAY_IP",
    r"ISP_INFRASTRUCTURE": "ISP_INFRASTRUCTURE",
    r"ISP_SERVICE": "ISP_SERVICE",
    r"REPLACE_WITH_SECURE_HUB_SECRET": "REPLACE_WITH_SECURE_HUB_SECRET",
    r"REPLACE_WITH_ADMIN_KEY": "REPLACE_WITH_ADMIN_KEY",
}

EXTENSIONS = (".py", ".js", ".json", ".sh", ".md", ".conf", ".shadow")

def sanitize_file(filepath):
    """Processes a single file and redacts matched patterns."""
    try:
        with open(filepath, "r") as f:
            content = f.read()
        
        original_content = content
        for pattern, replacement in REDACTION_MAP.items():
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        
        if content != original_content:
            with open(filepath, "w") as f:
                f.write(content)
            logging.info(f"Redacted sensitive data in: {filepath}")
            return True
    except Exception as e:
        logging.error(f"Failed to process {filepath}: {e}")
    return False

def main():
    print("\n==============================================================================")
    print(" SHADOWCYPHER // SOURCE CODE DATA SANITIZER")
    print("==============================================================================\n")
    
    project_root = os.getcwd()
    scrub_count = 0
    file_count = 0
    
    logging.info("Initiating codebase traversal...")

    for root, dirs, files in os.walk(project_root):
        # Exclude directories that do not require source scrubbing
        if any(d in root for d in [".git", "venv", "__pycache__", "logs", "payloads", "configs"]):
            continue
            
        for file in files:
            if file.endswith(EXTENSIONS):
                file_count += 1
                if sanitize_file(os.path.join(root, file)):
                    scrub_count += 1
                    
    print("\n==============================================================================")
    print(f" [SUCCESS] SANITIZATION COMPLETE")
    print("==============================================================================")
    print(f"  -> Total Files Analyzed: {file_count}")
    print(f"  -> Files Modified:       {scrub_count}\n")

if __name__ == "__main__":
    main()
