"""Buddy System — Terminal Tamagotchi based on the Claude Code architecture."""

import random
import hashlib
import os
import uuid
from shadowcypher.ai.engine import ai_engine
from shadowcypher.core.logger import logger


class Buddy:
    """The hacker companion with stats and a soul."""

    SPECIES = [
        "Pebblecrab", "Nebulynx", "Glitchowl", "Circuitfox", 
        "Datahound", "Packetpixie", "Voidraptor", "Codegeist"
    ]

    def __init__(self, user_id: str):
        self.user_id = user_id
        # Deterministic Gacha seed from user_id
        seed = int(hashlib.md5(user_id.encode()).hexdigest(), 16) % (2**32)
        random.seed(seed)
        
        self.species = random.choice(self.SPECIES)
        self.chaos = random.randint(1, 100)
        self.snark = random.randint(1, 100)
        self.debugging = random.randint(1, 100)
        self.soul = "Searching for its purpose..."
        
        self._generate_soul()

    def _generate_soul(self):
        """Use local AI to write the buddy's soul description."""
        logger.info("buddy", f"Manifesting soul for {self.species}...")
        prompt = f"""You are a creative writer.
Write a 1-sentence 'soul' description for a hacker's AI companion.
Species: {self.species}
Stats: Chaos {self.chaos}, Snark {self.snark}, Debugging {self.debugging}.
Be witty, cyberpunk, and brief."""
        
        try:
            self.soul = ai_engine.generate_stream(prompt, system_prompt="Be a cyberpunk soul-weaver.")
        except:
            self.soul = "A digital remnant of a life once lived in the bits."

    def to_dict(self) -> dict:
        return {
            "species": self.species,
            "chaos": self.chaos,
            "snark": self.snark,
            "debugging": self.debugging,
            "soul": self.soul
        }


def get_current_buddy() -> Buddy:
    """Get or create the buddy for this system."""
    # Unique system ID
    machine_id = str(uuid.getnode())
    return Buddy(machine_id)
