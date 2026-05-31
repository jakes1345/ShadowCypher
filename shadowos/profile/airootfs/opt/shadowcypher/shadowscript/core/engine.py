"""ShadowScript execution entry point — runs .shadow files or drops into REPL."""

import sys
import os

from shadowcypher.compiler.interpreter import ShadowInterpreter


class ShadowEngine:
    """Entry point for running .shadow mission scripts."""

    def __init__(self):
        self.interpreter = ShadowInterpreter()

    def run(self, code: str):
        try:
            self.interpreter.run(code)
        except Exception as e:
            from shadowcypher.core.logger import logger
            logger.error("engine", f"MISSION_CRASH: {e}")
            print(f"\033[1;31m[SHADOWSCRIPT ERROR]\033[0m {e}")

    def run_file(self, path: str):
        if not os.path.exists(path):
            print(f"\033[1;31m[ERROR]\033[0m Script not found: {path}")
            sys.exit(1)
        with open(path) as f:
            self.run(f.read())


if __name__ == "__main__":
    engine = ShadowEngine()
    if len(sys.argv) > 1:
        engine.run_file(sys.argv[1])
    else:
        engine.interpreter.run_interactive()
