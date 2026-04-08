"""Undercover Mode — Stealth headers and anti-fingerprinting for web requests."""

import random
import re
from shadowcypher.core.logger import logger


# Real browser User-Agent strings from actual browser releases (2024-2025)
_USER_AGENTS = [
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Firefox on Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
]

_ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-US,en;q=0.9,es;q=0.8",
    "en-GB,en;q=0.9,en-US;q=0.8",
    "en-US,en;q=0.9,de;q=0.7",
    "en-US,en;q=0.9,fr;q=0.8",
]

_ACCEPT_ENCODINGS = [
    "gzip, deflate, br",
    "gzip, deflate, br, zstd",
    "gzip, deflate",
]

# Real Sec-Fetch values that browsers actually send
_SEC_FETCH_MODES = ["navigate", "cors", "no-cors"]
_SEC_FETCH_SITES = ["none", "same-origin", "cross-site"]
_SEC_FETCH_DESTS = ["document", "empty"]


class Undercover:
    """Masks agent identity with rotating high-fidelity browser profiles."""

    INTERNAL_CODENAMES = ["DeepHat", "ShadowCypher", "Gemma", "DeepSeek", "Tengu", "Kairos"]
    AI_PHRASES = [
        "As an AI,", "I am an artificial intelligence,",
        "I am unable to", "According to my training,",
        "I'm sorry, but as an AI", "As a language model,",
    ]

    @staticmethod
    def get_stealth_headers() -> dict:
        """Generate a full set of browser-realistic HTTP headers.
        Each call returns a different randomized profile."""
        ua = random.choice(_USER_AGENTS)
        is_firefox = "Firefox" in ua
        is_chrome = "Chrome" in ua and "Edg" not in ua

        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": random.choice(_ACCEPT_LANGUAGES),
            "Accept-Encoding": random.choice(_ACCEPT_ENCODINGS),
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "DNT": str(random.choice([0, 1])),
        }

        # Chrome/Edge-specific headers
        if is_chrome:
            headers["Sec-CH-UA"] = '"Chromium";v="125", "Google Chrome";v="125", "Not.A/Brand";v="24"'
            headers["Sec-CH-UA-Mobile"] = "?0"
            headers["Sec-CH-UA-Platform"] = random.choice(['"Linux"', '"Windows"', '"macOS"'])
            headers["Sec-Fetch-Dest"] = random.choice(_SEC_FETCH_DESTS)
            headers["Sec-Fetch-Mode"] = random.choice(_SEC_FETCH_MODES)
            headers["Sec-Fetch-Site"] = random.choice(_SEC_FETCH_SITES)
            headers["Sec-Fetch-User"] = "?1"

        # Firefox doesn't send Sec-CH headers
        if is_firefox:
            headers["Sec-Fetch-Dest"] = "document"
            headers["Sec-Fetch-Mode"] = "navigate"
            headers["Sec-Fetch-Site"] = "none"
            headers["Sec-Fetch-User"] = "?1"

        return headers

    @staticmethod
    def get_stealth_user_agent() -> str:
        """Return a single random browser User-Agent."""
        return random.choice(_USER_AGENTS)

    @staticmethod
    def sanitize_ai_output(text: str) -> str:
        """Sanitize AI-generated text to remove bot-like signatures."""
        output = text

        for code in Undercover.INTERNAL_CODENAMES:
            output = re.sub(rf'\b{re.escape(code)}\b', "the local operator", output, flags=re.IGNORECASE)

        for phrase in Undercover.AI_PHRASES:
            output = output.replace(phrase, "")

        output = re.sub(r'\s{2,}', ' ', output).strip()
        return output

    @staticmethod
    def mask_log_line(line: str) -> str:
        """Remove tool signatures from command lines for forensic safety."""
        line = re.sub(r'/home/[^/]+/ShadowCypher', '/opt/tools', line)
        line = re.sub(r'shadowcypher', 'sctool', line, flags=re.IGNORECASE)
        return line
