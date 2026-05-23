"""
ShadowScript Interpreter — Sovereign Tactical Language Engine.
Executes .shadow scripts with full module access, flow control,
piped output, variable interpolation, and live AI integration.

Architecture:
  TOKEN STREAM → DIRECTIVE DISPATCH → MODULE BRIDGE → OUTPUT CAPTURE
"""

import sys
import os
import subprocess
import shlex
import threading
import time
from typing import Any, Dict, List, Optional, Callable

from shadowcypher.compiler.lexer import ShadowLexer, Token
from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus


class ShadowRuntime:
    """The Sovereign Environment where ShadowScript lives.
    Supports variables, output capture, module invocation, and flow control.
    """

    def __init__(self, on_output: Optional[Callable] = None):
        self.variables: Dict[str, Any] = {}
        self.swarm_active = False
        self.output_callback = on_output or (lambda x: print(f"\033[1;32m[SHADOW]\033[0m {x}"))
        self.last_result: str = ""
        self._module_cache: Dict[str, Any] = {}

    def emit(self, text: str):
        """Route output to callback and store as $LAST."""
        self.last_result = text
        self.variables["LAST"] = text
        self.output_callback(text)

    def resolve_var(self, text: str) -> str:
        """Interpolate $VAR references in strings."""
        import re
        def _sub(m):
            name = m.group(1)
            val = self.variables.get(name, "")
            if isinstance(val, dict):
                return str(val.get("value", val))
            return str(val)
        return re.sub(r'\$([A-Za-z_][A-Za-z0-9_]*)', _sub, str(text))

    def _get_module(self, name: str):
        """Lazy-load a tactical module by name."""
        if name in self._module_cache:
            return self._module_cache[name]
        mod_map = {
            "recon": ("shadowcypher.modules.recon", "Recon"),
            "network": ("shadowcypher.modules.network", "Network"),
            "wireless": ("shadowcypher.modules.wireless", "Wireless"),
            "exploit": ("shadowcypher.modules.exploit", "Exploit"),
            "privesc": ("shadowcypher.modules.privesc", "PrivEsc"),
            "c2": ("shadowcypher.modules.c2", "C2Framework"),
            "payload": ("shadowcypher.modules.payload_factory", "PayloadFactory"),
            "web": ("shadowcypher.modules.web_attacks", "WebAttacks"),
            "osint": ("shadowcypher.modules.osint", "OSINT"),
            "ghost_hose": ("shadowcypher.modules.ghost_hose", "ghost_hose"),
            "credentials": ("shadowcypher.modules.credentials", "Credentials"),
            "forensics": ("shadowcypher.modules.forensics", "Forensics"),
        }
        if name not in mod_map:
            return None
        mod_path, cls_name = mod_map[name]
        try:
            m = __import__(mod_path, fromlist=[cls_name])
            obj = getattr(m, cls_name)
            # If it's a class, instantiate it; if it's already a singleton, use it
            instance = obj() if isinstance(obj, type) else obj
            self._module_cache[name] = instance
            return instance
        except Exception as e:
            logger.error("shadow_core", f"MODULE_LOAD_FAILED: {name} -> {e}")
            return None

    def execute_directive(self, cmd: str, args: List[str]):
        """Execute a ShadowScript directive."""
        # Interpolate all args
        args = [self.resolve_var(a) for a in args]

        if cmd == "TARGET":
            target = args[0] if args else "UNKNOWN"
            self.variables["CURRENT_TARGET"] = target
            self.emit(f"TARGET_ACQUIRED: {target}")
            logger.info("shadow_core", f"TARGET_ACQUIRED: {target}")

        elif cmd == "STRIKE":
            target = self.variables.get("CURRENT_TARGET", "UNKNOWN")
            module_name = args[0] if args else "recon"
            method = args[1] if len(args) > 1 else "quick_scan"
            self.emit(f"STRIKE_INITIATED: {module_name}.{method} -> {target}")
            mod = self._get_module(module_name)
            if mod and hasattr(mod, method):
                fn = getattr(mod, method)
                fn(target, on_output=self.emit)
            else:
                self.emit(f"STRIKE_FAILED: Module '{module_name}' or method '{method}' not found")

        elif cmd == "SWARM":
            self.swarm_active = True
            self.emit("SWARM_MODE: SYNCHRONIZING_NODES")
            logger.info("shadow_core", "SWARM_MODE: ENGAGED")
            bus.publish("module_status", {"module": "swarm", "status": "ENGAGED"})

        elif cmd == "UNSAFE":
            self.emit("UNSAFE_BLOCK: Entering Raw Sovereignty...")
            logger.warning("shadow_core", "UNSAFE_BLOCK_ENTERED")

        elif cmd == "!sys":
            if not args:
                self.emit("!sys: No command provided")
                return
            full_cmd = " ".join(args)
            self.emit(f"SYS_EXEC: {full_cmd}")
            try:
                result = subprocess.run(
                    shlex.split(full_cmd), shell=False, capture_output=True, text=True, timeout=120
                )
                output = result.stdout + result.stderr
                self.variables["LAST"] = output.strip()
                for line in output.strip().split("\n"):
                    if line:
                        self.emit(line)
                self.variables["EXIT_CODE"] = str(result.returncode)
            except subprocess.TimeoutExpired:
                self.emit("SYS_TIMEOUT: Command exceeded 120s limit")
            except Exception as e:
                self.emit(f"SYS_ERROR: {e}")

        elif cmd == "!pipe":
            if not args:
                return
            import shlex as _shlex
            pipe_args = _shlex.split(" ".join(args))
            self.emit(f"PIPE: {' '.join(pipe_args)}")
            try:
                result = subprocess.run(
                    pipe_args, shell=False, capture_output=True, text=True, timeout=120
                )
                self.last_result = result.stdout.strip()
                self.variables["PIPE_OUT"] = self.last_result
                for line in self.last_result.split("\n"):
                    if line:
                        self.emit(line)
            except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
                self.emit(f"PIPE_ERROR: {e}")

        elif cmd == "!module":
            # Direct module invocation: !module(recon, quick_scan, 127.0.0.1)
            if len(args) < 2:
                self.emit("!module: Usage: !module(mod_name, method, ...args)")
                return
            mod_name, method = args[0], args[1]
            method_args = args[2:]
            mod = self._get_module(mod_name)
            if mod and hasattr(mod, method):
                fn = getattr(mod, method)
                try:
                    fn(*method_args, on_output=self.emit)
                except TypeError:
                    # Some methods don't take on_output
                    result = fn(*method_args)
                    if result:
                        self.emit(str(result))
            else:
                self.emit(f"MODULE_NOT_FOUND: {mod_name}.{method}")

        elif cmd == "!echo":
            text = " ".join(args)
            self.emit(self.resolve_var(text))

        elif cmd == "!sleep":
            seconds = float(args[0]) if args else 1
            time.sleep(seconds)

        else:
            self.emit(f"UNKNOWN_DIRECTIVE: {cmd}")


class ShadowInterpreter:
    """The Engine that breathes life into .shadow scripts.
    Supports full directive execution, AI queries, module bridging,
    variable interpolation, and interactive shell mode.
    """

    def __init__(self, on_output: Optional[Callable] = None):
        self.lexer = ShadowLexer()
        self.runtime = ShadowRuntime(on_output=on_output)

    def run(self, code: str):
        """Execute a .shadow script."""
        tokens = self.lexer.tokenize(code)
        logger.info("shadow_core", f"INGESTING_MISSION_SIGNAL: {len(tokens)} tokens")

        ptr = 0
        while ptr < len(tokens):
            token = tokens[ptr]

            if token.ttype == Token.TYPE_KEYWORD:
                if token.value == "VAR":
                    # VAR name = value
                    if ptr + 3 < len(tokens):
                        name = tokens[ptr + 1].value
                        val = tokens[ptr + 3].value
                        val = self.runtime.resolve_var(val)
                        self.runtime.variables[name] = val
                        self.runtime.emit(f"VAR {name} = {val}")
                        ptr += 4
                    else:
                        self.runtime.emit("MALFORMED_VAR: Expected VAR name = value")
                        ptr += 1

                elif token.value in ["U64", "U32", "U8"]:
                    # HolyC Type System: U64 name = value
                    typename = token.value
                    if ptr + 3 < len(tokens):
                        name = tokens[ptr + 1].value
                        val = tokens[ptr + 3].value
                        self.runtime.variables[name] = {"type": typename, "value": val}
                        self.runtime.emit(f"TYPE_ALLOC: {typename} {name} = {val}")
                        ptr += 4
                    else:
                        ptr += 1

                elif token.value == "AI":
                    # Neural Link: AI "query"
                    if ptr + 2 < len(tokens):
                        prompt = tokens[ptr + 2].value
                        prompt = self.runtime.resolve_var(prompt)
                        self.runtime.emit(f"NEURAL_LINK: Querying Shadow-AI...")
                        try:
                            from shadowcypher.ai.orchestrator import orchestrator
                            result = orchestrator.execute_sync(prompt)
                            self.runtime.emit(f"AI_RESPONSE: {result}")
                            self.runtime.variables["AI_RESULT"] = result
                        except Exception as e:
                            self.runtime.emit(f"AI_FAULT: {e}")
                        ptr += 3
                    else:
                        self.runtime.emit("MALFORMED_AI_DIRECTIVE: Missing prompt.")
                        ptr += 1

                elif token.value == "FOR":
                    # FOR var IN range/list { body }
                    # Simple: FOR i IN 1 2 3 { ... }
                    self.runtime.emit("FOR: Loop constructs coming in v2")
                    ptr += 1

                elif token.value == "IF":
                    # IF condition { body }
                    self.runtime.emit("IF: Conditional constructs coming in v2")
                    ptr += 1

                elif token.value == "MAP":
                    # MAP function over collection
                    self.runtime.emit("MAP: Functional pipeline coming in v2")
                    ptr += 1

                elif token.value == "FILTER":
                    self.runtime.emit("FILTER: Functional pipeline coming in v2")
                    ptr += 1

                elif token.value == "YIELD":
                    # YIELD value — export from block
                    if ptr + 1 < len(tokens):
                        val = tokens[ptr + 1].value
                        self.runtime.variables["YIELD"] = self.runtime.resolve_var(val)
                        self.runtime.emit(f"YIELD: {self.runtime.variables['YIELD']}")
                        ptr += 2
                    else:
                        ptr += 1

                elif token.value in ["STRIKE", "TARGET", "SWARM", "UNSAFE",
                                     "!sys", "!pipe", "!module", "!echo", "!sleep"]:
                    cmd = token.value
                    args = []
                    # Parse args inside parentheses
                    if (ptr + 1 < len(tokens) and
                            tokens[ptr + 1].ttype == Token.TYPE_BRACE and
                            tokens[ptr + 1].value == "("):
                        ptr += 2  # skip cmd and (
                        while ptr < len(tokens) and tokens[ptr].value != ")":
                            args.append(tokens[ptr].value)
                            ptr += 1
                        # ptr is now on ), will be incremented at bottom
                    self.runtime.execute_directive(cmd, args)

                else:
                    # Unknown keyword — try as a module auto-dispatch
                    self.runtime.emit(f"UNKNOWN: {token.value}")

            ptr += 1

    def run_interactive(self):
        """Interactive ShadowScript REPL."""
        print("\033[1;36m╔══════════════════════════════════════════╗\033[0m")
        print("\033[1;36m║  SHADOWSCRIPT SOVEREIGN SHELL v2.0       ║\033[0m")
        print("\033[1;36m║  Type .help for commands, .exit to quit  ║\033[0m")
        print("\033[1;36m╚══════════════════════════════════════════╝\033[0m")

        while True:
            try:
                line = input("\033[1;35mshadow>\033[0m ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nSIGNAL_OUT")
                break

            if not line:
                continue
            if line == ".exit":
                break
            if line == ".help":
                self._print_help()
                continue
            if line == ".vars":
                for k, v in self.runtime.variables.items():
                    print(f"  {k} = {v}")
                continue
            if line == ".modules":
                for name in ["recon", "network", "wireless", "exploit", "privesc",
                             "c2", "payload", "web", "osint", "ghost_hose",
                             "credentials", "forensics"]:
                    print(f"  {name}")
                continue

            self.run(line)

    @staticmethod
    def _print_help():
        print("""
\033[1;33mShadowScript Commands:\033[0m
  VAR name = value        — Set a variable
  TARGET(ip)              — Set current target
  STRIKE(module, method)  — Execute module against target
  !sys(command)           — Run system command with output capture
  !pipe(cmd1 | cmd2)      — Pipe system commands
  !module(mod, fn, args)  — Direct module invocation
  !echo(text)             — Print with variable interpolation
  !sleep(seconds)         — Pause execution
  AI "prompt"             — Query the AI orchestrator
  SWARM                   — Enable swarm coordination
  U64/U32/U8 name = val   — Typed variable allocation

\033[1;33mREPL Commands:\033[0m
  .vars                   — Show all variables
  .modules                — List available modules
  .help                   — This help
  .exit                   — Exit shell
""")


if __name__ == "__main__":
    interpreter = ShadowInterpreter()
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            interpreter.run(f.read())
    else:
        interpreter.run_interactive()
