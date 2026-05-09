import sys
import os
import random
import string
from shadowcypher.core.logger import logger
from shadowcypher.compiler.interpreter import ShadowInterpreter

class ShadowEngine:
    """
    SHADOW-ENGINE (v1.2-DELTA)
    Minimalist entry point for .shadow missions.
    """
    def __init__(self):
        self.interpreter = ShadowInterpreter()

    def _morph_code(self, code: str) -> str:
        """Adds randomized chaff to eliminate code-fingerprints."""
        lines = code.split('\n')
        morphed = []
        for line in lines:
            morphed.append(line)
            if random.random() > 0.8:
                junk = f"# {''.join(random.choices(string.ascii_uppercase + string.digits, k=12))}"
                morphed.append(junk)
        return "\n".join(morphed)

    def run(self, code: str):
        """Executes a mission after polymorphic shredding."""
        morphed_code = self._morph_code(code)
        logger.info("engine", "IGNITING_MISSION_KERNEL_ZETA...")
        try:
            self.interpreter.run(morphed_code)
        except Exception as e:
            logger.error("engine", f"MISSION_CRASH: {e}")

if __name__ == "__main__":
    engine = ShadowEngine()
    if len(sys.argv) > 1:
        fpath = sys.argv[1]
        if os.path.exists(fpath):
            with open(fpath, 'r') as f:
                engine.run(f.read())
        else:
            print(f"FAILED: Mission file {fpath} not found.")
    else:
        print("\033[0;36mSHADOW-ENGINE ALPHA (REPL)\033[0m")
        while True:
            try:
                line = input(">> ")
                if line.lower() in ["exit", "quit"]: break
                engine.run(line)
            except (EOFError, KeyboardInterrupt): break
            except Exception as e: print(f"ERR: {e}")
