"""Undercover Mode — Stealth and anti-forensics for AI-driven operations."""

import re
from shadowcypher.core.logger import logger


class Undercover:
    """Masks the agent's identity and sanitizes footprints."""

    INTERNAL_CODENAMES = ["DeepHat", "ShadowCypher", "Gemma", "DeepSeek", "Tengu"]
    AI_PHRASES = ["As an AI,", "I am an artificial intelligence,", "I am unable to", "According to my training,"]

    @staticmethod
    def sanitize_ai_output(text: str) -> str:
        """Sanitize AI-generated text to remove 'bot-like' signatures."""
        output = text
        
        # 1. Mask internal codenames
        for code in Undercover.INTERNAL_CODENAMES:
            output = re.sub(rf'\b{code}\b', "the local operator", output, flags=re.IGNORECASE)
            
        # 2. Strip AI disclosure phrases (Undercover mode doesn't volunteer its identity)
        for phrase in Undercover.AI_PHRASES:
            output = re.sub(rf'\b{phrase}\b', "", output, flags=re.IGNORECASE)
            
        # 3. Clean up grammar after removals
        output = re.sub(r'\s+', ' ', output).strip()
        
        return output

    @staticmethod
    def get_stealth_user_agent() -> str:
        """Return a perfectly normal, non-suspicious browser signature."""
        # Porting the most common Linux Chrome signature for 2024
        return "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

    @staticmethod
    def mask_log_line(line: str) -> str:
        """Remove tool signatures from command lines for forensic safety."""
        # Hide any shadowcypher internal paths or names
        line = re.sub(r'/home/.*/ShadowCypher', '/usr/local/bin', line)
        return line
