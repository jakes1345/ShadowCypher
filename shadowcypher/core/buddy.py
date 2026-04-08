"""Buddy System — Deterministic hacker companion (Terminal Tamagotchi)."""

import hashlib
import random
import uuid
from shadowcypher.core.logger import logger


class Buddy:
    """Hacker companion with deterministic stats based on machine ID.
    Does NOT call AI on init — soul generation is explicitly triggered."""

    SPECIES = [
        "Pebblecrab", "Nebulynx", "Glitchowl", "Circuitfox",
        "Datahound", "Packetpixie", "Voidraptor", "Codegeist",
    ]

    # Pre-written souls by species so we never block on AI
    _SOULS = {
        "Pebblecrab": "Slow to trust, hard to crack — carries its shell of encrypted memories everywhere.",
        "Nebulynx": "Hunts through fog of war, sees packet trails invisible to mortal eyes.",
        "Glitchowl": "Watches the logs at 3 AM when no one else will. Blinks in hexadecimal.",
        "Circuitfox": "Outruns firewalls for sport. Leaves no trace except a faint copper smell.",
        "Datahound": "Sniffs out credentials buried three directories deep. Never forgets a hash.",
        "Packetpixie": "Dances between TCP handshakes. Makes SYN floods look like confetti.",
        "Voidraptor": "Born from a kernel panic. Feeds on segfaults and dangling pointers.",
        "Codegeist": "The ghost in your shell. Speaks only in exit codes and pipe redirects.",
    }

    def __init__(self, user_id: str):
        self.user_id = user_id
        # Deterministic seed from user_id
        seed = int(hashlib.md5(user_id.encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)

        self.species = rng.choice(self.SPECIES)
        self.chaos = rng.randint(1, 100)
        self.snark = rng.randint(1, 100)
        self.debugging = rng.randint(1, 100)
        self.soul = self._SOULS.get(self.species, "A digital remnant searching the void.")
        self._ai_soul = None  # Populated later if AI is available

    def generate_ai_soul(self, ai_engine):
        """Optionally generate a richer soul description using local AI.
        Call this explicitly — it's never called during init."""
        if not ai_engine.is_loaded:
            return

        prompt = (
            f"Write one sentence describing a cyberpunk hacker's AI companion.\n"
            f"Species: {self.species}\n"
            f"Stats: Chaos {self.chaos}, Snark {self.snark}, Debugging {self.debugging}.\n"
            f"Be witty and brief."
        )

        try:
            result = ai_engine.generate(prompt, system_prompt="Be a cyberpunk soul-weaver.", max_tokens=80)
            if result and not result.startswith("["):
                self._ai_soul = result.strip()
                self.soul = self._ai_soul
                logger.info("buddy", f"AI soul generated for {self.species}")
        except Exception as e:
            logger.info("buddy", f"AI soul generation skipped: {e}")

    def react(self, event: str) -> str:
        """Generate a reaction to an event based on buddy's personality stats."""
        if self.chaos > 70:
            reactions = {
                "scan_complete": "Another scan? Feed me something HARDER.",
                "vuln_found": "OH YEAH. That's the good stuff. Exploit it. NOW.",
                "error": "Everything burns. I love it.",
                "idle": "Are we just going to sit here or are we going to break something?",
            }
        elif self.snark > 70:
            reactions = {
                "scan_complete": "Wow, you actually finished a scan. Proud of you.",
                "vuln_found": "A vulnerability. How... expected.",
                "error": "Skill issue, honestly.",
                "idle": "I've seen faster reconnaissance from a dial-up modem.",
            }
        else:
            reactions = {
                "scan_complete": "Scan complete. Ready for the next phase.",
                "vuln_found": "Target vulnerability identified. Logging to findings.",
                "error": "Error encountered. Check the logs for details.",
                "idle": "Standing by for mission parameters.",
            }
        return reactions.get(event, "...")

    def to_dict(self) -> dict:
        return {
            "species": self.species,
            "chaos": self.chaos,
            "snark": self.snark,
            "debugging": self.debugging,
            "soul": self.soul,
        }


# Lazy singleton
_current_buddy = None


def get_current_buddy() -> Buddy:
    """Get or create the buddy for this machine."""
    global _current_buddy
    if _current_buddy is None:
        machine_id = str(uuid.getnode())
        _current_buddy = Buddy(machine_id)
    return _current_buddy
