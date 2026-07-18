"""
ShadowScript Interpreter — ShadowCypher's native tactical scripting engine.

Syntax overview:
  VAR name = value           — assign variable
  SET name = value           — alias for VAR
  TARGET(ip)                 — set current target
  STRIKE(module, method)     — invoke a module against the target
  SCAN(ports)                — network scan (e.g. SCAN(1-1000))
  SWARM()                    — broadcast to linked Shadow Nodes
  AI("prompt")               — query the local AI brain
  LOAD("file.shadow")        — execute another script file
  IF condition { body }      — conditional block
  ELSE { body }              — else clause (follows IF)
  FOR var IN items { body }  — iterate over space-separated items
  WHILE condition { body }   — loop while condition is true
  RETURN value               — set $RESULT and stop execution
  !sys(command)              — run a system command
  !pipe(cmd)                 — run a command, capture output to $PIPE_OUT
  !module(mod, fn, args)     — call a module method directly
  !echo(text)                — print with $VAR interpolation
  !sleep(seconds)            — pause
  UNSAFE { body }            — run body without stealth checks

Conditions:  $VAR == value  |  $VAR != value  |  $VAR > n  |  $VAR < n  |  $VAR
"""

import os
import shlex
import subprocess
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from shadowcypher.compiler.lexer import ShadowLexer, Token
from shadowcypher.core.bus import bus
from shadowcypher.core.logger import logger


# Sentinel to stop execution early (RETURN / BREAK)
class _Return(Exception):
    def __init__(self, value=""):
        self.value = value

class _Break(Exception):
    pass


class ShadowRuntime:
    """Execution environment — variables, output, module cache."""

    def __init__(self, on_output: Optional[Callable] = None):
        self.variables: Dict[str, Any] = {}
        self.swarm_active = False
        self.output_callback = on_output or (lambda x: print(f"\033[1;32m[SHADOW]\033[0m {x}"))
        self.last_result: str = ""
        self._module_cache: Dict[str, Any] = {}

    def emit(self, text: str):
        self.last_result = str(text)
        self.variables["LAST"] = self.last_result
        self.output_callback(str(text))

    def resolve_var(self, text: str) -> str:
        import re
        def _sub(m):
            name = m.group(1)
            val = self.variables.get(name, "")
            return str(val.get("value", val) if isinstance(val, dict) else val)
        return re.sub(r'\$([A-Za-z_][A-Za-z0-9_]*)', _sub, str(text))

    def evaluate_condition(self, tokens: List[Token]) -> bool:
        """Evaluate a simple condition from a token list."""
        if not tokens:
            return False
        # Single token: truthy check on resolved value
        if len(tokens) == 1:
            v = self.resolve_var(tokens[0].value)
            return bool(v and v not in ("0", "false", "False", "none", "None", ""))
        # Binary: left OP right
        if len(tokens) >= 3:
            left  = self.resolve_var(tokens[0].value)
            op    = tokens[1].value
            right = self.resolve_var(tokens[2].value)
            if op == "==":
                return left == right
            if op == "!=":
                return left != right
            try:
                lf, rf = float(left), float(right)
                if op == ">":
                    return lf > rf
                if op == ">=":
                    return lf >= rf
                if op == "<":
                    return lf < rf
                if op == "<=":
                    return lf <= rf
            except (ValueError, TypeError):
                pass
        return False

    def _get_module(self, name: str):
        if name in self._module_cache:
            return self._module_cache[name]
        mod_map = {
            "recon":       ("shadowcypher.modules.recon",            "Recon"),
            "network":     ("shadowcypher.modules.network",          "Network"),
            "wireless":    ("shadowcypher.modules.wireless",         "Wireless"),
            "exploit":     ("shadowcypher.modules.poc_engine",       "PocEngine"),
            "poc":         ("shadowcypher.modules.poc_engine",       "PocEngine"),
            "privesc":     ("shadowcypher.modules.privilege_audit",  "PrivAudit"),
            "c2":          ("shadowcypher.modules.agent_relay",      "AgentRelay"),
            "payload":     ("shadowcypher.modules.craft_factory",    "CraftFactory"),
            "craft":       ("shadowcypher.modules.craft_factory",    "CraftFactory"),
            "web":         ("shadowcypher.modules.web_security",     "WebSecurity"),
            "osint":       ("shadowcypher.modules.osint",            "OSINT"),
            "ghost_hose":  ("shadowcypher.modules.ghost_hose",       "ghost_hose"),
            "credentials": ("shadowcypher.modules.secret_audit",     "Credentials"),
            "secrets":     ("shadowcypher.modules.secret_audit",     "Credentials"),
            "forensics":   ("shadowcypher.modules.forensics",        "Forensics"),
            "vuln":        ("shadowcypher.modules.vuln_scanner",     "VulnScanner"),
        }
        if name not in mod_map:
            return None
        mod_path, cls_name = mod_map[name]
        try:
            m = __import__(mod_path, fromlist=[cls_name])
            obj = getattr(m, cls_name)
            instance = obj() if isinstance(obj, type) else obj
            self._module_cache[name] = instance
            return instance
        except Exception as e:
            logger.error("shadowscript", f"MODULE_LOAD_FAILED: {name} → {e}")
            return None

    def execute_directive(self, cmd: str, args: List[str]):
        """Execute a single directive with its args."""
        args = [self.resolve_var(a) for a in args]

        if cmd == "TARGET":
            target = args[0] if args else ""
            self.variables["CURRENT_TARGET"] = target
            self.emit(f"TARGET_SET: {target}")

        elif cmd == "STRIKE":
            target = self.variables.get("CURRENT_TARGET", "")
            module_name = args[0] if args else "recon"
            method      = args[1] if len(args) > 1 else "quick_scan"
            extra_args  = args[2:] if len(args) > 2 else []
            mod = self._get_module(module_name)
            if mod and hasattr(mod, method):
                self.emit(f"STRIKE: {module_name}.{method} → {target or '(no target)'}")
                fn = getattr(mod, method)
                call_args = ([target] + extra_args) if target else extra_args
                try:
                    fn(*call_args, on_output=self.emit)
                except TypeError:
                    try:
                        fn(*call_args)
                    except Exception as e:
                        self.emit(f"STRIKE_ERROR: {e}")
            else:
                self.emit(f"STRIKE_FAILED: module '{module_name}' or method '{method}' not found")

        elif cmd == "SCAN":
            target = self.variables.get("CURRENT_TARGET", "")
            if not target:
                self.emit("SCAN_SKIPPED: no target set — use TARGET(ip) first")
                return
            port_range = args[0] if args else "1-1000"
            self.emit(f"SCAN: {target} ports {port_range}")
            try:
                from shadowcypher.modules.network import Network
                net = Network()
                threading.Thread(
                    target=net.port_scan_tcp_connect,
                    args=(target, port_range, self.emit),
                    daemon=True,
                ).start()
            except Exception as e:
                self.emit(f"SCAN_ERROR: {e}")

        elif cmd == "SWARM":
            self.swarm_active = True
            self.emit("SWARM: broadcasting to linked Shadow Nodes")
            try:
                from shadowcypher.core.ghost import ghost_orchestrator
                nodes = ghost_orchestrator.get_active_nodes()
                if nodes:
                    cmd_str = args[0] if args else "ping"
                    ok = sum(1 for n in nodes if ghost_orchestrator.execute(n["fp"], cmd_str))
                    self.emit(f"SWARM_RESULT: {ok}/{len(nodes)} nodes responded")
                else:
                    self.emit("SWARM: no Shadow Nodes linked — deploy an agent first")
            except Exception as e:
                self.emit(f"SWARM_ERROR: {e}")
            bus.publish("module_status", {"module": "swarm", "status": "ENGAGED"})

        elif cmd == "AI":
            prompt = " ".join(args) if args else "Summarise the current mission state."
            self.emit(f"AI: querying brain → {prompt[:80]}")
            try:
                from shadowcypher.ai.orchestrator import orchestrator
                result = orchestrator.execute_query_sync(prompt)
                self.variables["AI_RESULT"] = result
                for line in result.splitlines():
                    self.emit(line)
            except Exception as e:
                self.emit(f"AI_ERROR: {e}")

        elif cmd == "LOAD":
            path = args[0] if args else ""
            if not os.path.isabs(path):
                base = os.path.join(os.path.dirname(__file__), "..", "..", "shadowscript", "missions")
                path = os.path.join(base, path)
            if os.path.exists(path):
                self.emit(f"LOAD: executing {path}")
                with open(path) as f:
                    ShadowInterpreter(on_output=self.output_callback).run(f.read())
            else:
                self.emit(f"LOAD_ERROR: file not found: {path}")

        elif cmd == "UNSAFE":
            self.emit("UNSAFE: stealth checks disabled for this block")

        elif cmd == "!sys":
            full_cmd = " ".join(args)
            self.emit(f"SYS: {full_cmd}")
            try:
                result = subprocess.run(
                    shlex.split(full_cmd), shell=False,
                    capture_output=True, text=True, timeout=120,
                )
                output = (result.stdout + result.stderr).strip()
                self.variables["LAST"] = output
                self.variables["EXIT_CODE"] = str(result.returncode)
                for line in output.splitlines():
                    if line:
                        self.emit(line)
            except subprocess.TimeoutExpired:
                self.emit("SYS_TIMEOUT: exceeded 120s")
            except (FileNotFoundError, OSError) as e:
                self.emit(f"SYS_ERROR: {e}")

        elif cmd == "!pipe":
            full_cmd = " ".join(args)
            try:
                result = subprocess.run(
                    shlex.split(full_cmd), shell=False,
                    capture_output=True, text=True, timeout=120,
                )
                out = result.stdout.strip()
                self.variables["PIPE_OUT"] = out
                self.variables["LAST"] = out
                for line in out.splitlines():
                    if line:
                        self.emit(line)
            except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
                self.emit(f"PIPE_ERROR: {e}")

        elif cmd == "!module":
            if len(args) < 2:
                self.emit("!module: usage: !module(mod, method, ...args)")
                return
            mod_name, method = args[0], args[1]
            method_args = args[2:]
            mod = self._get_module(mod_name)
            if mod and hasattr(mod, method):
                fn = getattr(mod, method)
                try:
                    fn(*method_args, on_output=self.emit)
                except TypeError:
                    result = fn(*method_args)
                    if result:
                        self.emit(str(result))
            else:
                self.emit(f"MODULE_NOT_FOUND: {mod_name}.{method}")

        elif cmd == "!echo":
            self.emit(self.resolve_var(" ".join(args)))

        elif cmd == "!sleep":
            try:
                time.sleep(float(args[0]) if args else 1)
            except (ValueError, TypeError):
                pass

        else:
            self.emit(f"UNKNOWN_DIRECTIVE: {cmd}")


class ShadowInterpreter:
    """Runs .shadow scripts — full ShadowScript language support."""

    def __init__(self, on_output: Optional[Callable] = None):
        self.lexer   = ShadowLexer()
        self.runtime = ShadowRuntime(on_output=on_output)

    # ── Block utilities ──────────────────────────────────────────────────────

    def _collect_until_brace_open(self, tokens: List[Token], ptr: int):
        """Collect tokens before '{'. Returns (collected, ptr_at_brace)."""
        collected = []
        while ptr < len(tokens):
            t = tokens[ptr]
            if t.ttype == Token.TYPE_BRACE and t.value == "{":
                return collected, ptr
            collected.append(t)
            ptr += 1
        return collected, ptr

    def _parse_block(self, tokens: List[Token], ptr: int):
        """
        Parse brace-delimited block starting at '{'.
        Returns (body_tokens, ptr_past_close_brace).
        """
        depth  = 0
        body: List[Token] = []
        while ptr < len(tokens):
            t = tokens[ptr]
            if t.ttype == Token.TYPE_BRACE and t.value == "{":
                depth += 1
                if depth > 1:
                    body.append(t)
            elif t.ttype == Token.TYPE_BRACE and t.value == "}":
                depth -= 1
                if depth == 0:
                    return body, ptr
                body.append(t)
            else:
                body.append(t)
            ptr += 1
        return body, ptr

    def _run_tokens(self, tokens: List[Token]):
        """Execute a token list (used for IF/FOR/WHILE bodies)."""
        interp = ShadowInterpreter(on_output=self.runtime.output_callback)
        interp.runtime.variables = self.runtime.variables
        interp.runtime._module_cache = self.runtime._module_cache
        interp._execute(tokens)
        # Propagate variable changes back
        self.runtime.variables = interp.runtime.variables
        self.runtime.last_result = interp.runtime.last_result

    # ── Main execution ───────────────────────────────────────────────────────

    def run(self, code: str):
        """Execute ShadowScript source code."""
        tokens = self.lexer.tokenize(code)
        logger.info("shadowscript", f"EXECUTING: {len(tokens)} tokens")
        try:
            self._execute(tokens)
        except _Return as r:
            self.runtime.variables["RESULT"] = r.value
            self.runtime.emit(f"RETURN: {r.value}")

    def _execute(self, tokens: List[Token]):
        ptr = 0
        while ptr < len(tokens):
            token = tokens[ptr]

            # ── VAR / SET ──────────────────────────────────────────────────
            if token.ttype == Token.TYPE_KEYWORD and token.value in ("VAR", "SET"):
                # VAR name = value
                if ptr + 3 < len(tokens) and tokens[ptr + 2].value == "=":
                    name = tokens[ptr + 1].value
                    val  = self.runtime.resolve_var(tokens[ptr + 3].value)
                    self.runtime.variables[name] = val
                    self.runtime.emit(f"SET {name} = {val}")
                    ptr += 4
                else:
                    ptr += 1
                continue

            # ── IF ─────────────────────────────────────────────────────────
            elif token.ttype == Token.TYPE_KEYWORD and token.value == "IF":
                ptr += 1
                cond_tokens, ptr = self._collect_until_brace_open(tokens, ptr)
                body_tokens, ptr = self._parse_block(tokens, ptr)
                ptr += 1  # skip }

                condition_met = self.runtime.evaluate_condition(cond_tokens)
                if condition_met:
                    self._run_tokens(body_tokens)

                # Check for ELSE
                if ptr < len(tokens) and tokens[ptr].ttype == Token.TYPE_KEYWORD and tokens[ptr].value == "ELSE":
                    ptr += 1  # skip ELSE
                    if ptr < len(tokens) and tokens[ptr].ttype == Token.TYPE_BRACE and tokens[ptr].value == "{":
                        else_body, ptr = self._parse_block(tokens, ptr)
                        ptr += 1  # skip }
                        if not condition_met:
                            self._run_tokens(else_body)
                continue

            # ── FOR ────────────────────────────────────────────────────────
            elif token.ttype == Token.TYPE_KEYWORD and token.value == "FOR":
                # FOR var IN item1 item2 ... {
                ptr += 1
                var_name = tokens[ptr].value if ptr < len(tokens) else "item"
                ptr += 1
                # skip IN keyword
                if ptr < len(tokens) and tokens[ptr].value == "IN":
                    ptr += 1
                # collect items until {
                items = []
                while ptr < len(tokens):
                    t = tokens[ptr]
                    if t.ttype == Token.TYPE_BRACE and t.value == "{":
                        break
                    if t.ttype not in (Token.TYPE_BRACE,) and t.value not in (",",):
                        items.append(self.runtime.resolve_var(t.value))
                    ptr += 1
                body_tokens, ptr = self._parse_block(tokens, ptr)
                ptr += 1  # skip }
                try:
                    for item in items:
                        self.runtime.variables[var_name] = item
                        self._run_tokens(body_tokens)
                except _Break:
                    pass
                continue

            # ── WHILE ──────────────────────────────────────────────────────
            elif token.ttype == Token.TYPE_KEYWORD and token.value == "WHILE":
                ptr += 1
                cond_tokens, ptr = self._collect_until_brace_open(tokens, ptr)
                body_tokens, ptr = self._parse_block(tokens, ptr)
                ptr += 1  # skip }
                max_iter = 1000
                try:
                    while max_iter > 0 and self.runtime.evaluate_condition(cond_tokens):
                        self._run_tokens(body_tokens)
                        max_iter -= 1
                    if max_iter == 0:
                        self.runtime.emit("WHILE_LIMIT: reached 1000-iteration safety cap")
                except _Break:
                    pass
                continue

            # ── RETURN ─────────────────────────────────────────────────────
            elif token.ttype == Token.TYPE_KEYWORD and token.value == "RETURN":
                val = ""
                if ptr + 1 < len(tokens):
                    val = self.runtime.resolve_var(tokens[ptr + 1].value)
                    ptr += 1
                raise _Return(val)

            # ── BREAK ──────────────────────────────────────────────────────
            elif token.ttype == Token.TYPE_KEYWORD and token.value == "BREAK":
                raise _Break()

            # ── YIELD ──────────────────────────────────────────────────────
            elif token.ttype == Token.TYPE_KEYWORD and token.value == "YIELD":
                if ptr + 1 < len(tokens):
                    val = self.runtime.resolve_var(tokens[ptr + 1].value)
                    self.runtime.variables["YIELD"] = val
                    self.runtime.emit(f"YIELD: {val}")
                    ptr += 1

            # ── DIRECTIVES with optional parens ───────────────────────────
            elif token.ttype == Token.TYPE_KEYWORD and token.value in (
                "TARGET", "STRIKE", "SCAN", "SWARM", "AI", "LOAD",
                "UNSAFE", "MAP", "FILTER",
                "!sys", "!pipe", "!module", "!echo", "!sleep",
            ):
                cmd  = token.value
                args = []
                if ptr + 1 < len(tokens) and tokens[ptr + 1].value == "(":
                    ptr += 2  # skip cmd and (
                    depth = 1
                    while ptr < len(tokens):
                        t = tokens[ptr]
                        if t.value == "(":
                            depth += 1
                            args.append(t.value)
                        elif t.value == ")":
                            depth -= 1
                            if depth == 0:
                                break
                            args.append(t.value)
                        elif t.value == ",":
                            pass  # skip commas between args
                        else:
                            args.append(t.value)
                        ptr += 1

                # Handle UNSAFE/MAP/FILTER with a block body
                if cmd in ("UNSAFE", "MAP", "FILTER"):
                    next_ptr = ptr + 1
                    if next_ptr < len(tokens) and tokens[next_ptr].value == "{":
                        body_tokens, next_ptr = self._parse_block(tokens, next_ptr)
                        ptr = next_ptr
                        if cmd == "UNSAFE":
                            self.runtime.execute_directive("UNSAFE", args)
                            self._run_tokens(body_tokens)
                        elif cmd == "MAP":
                            # MAP: run body for each item in $LAST (newline-separated)
                            items = self.runtime.variables.get("LAST", "").splitlines()
                            for item in items:
                                self.runtime.variables["ITEM"] = item
                                self._run_tokens(body_tokens)
                        elif cmd == "FILTER":
                            # FILTER: keep lines from $LAST that match condition
                            items = self.runtime.variables.get("LAST", "").splitlines()
                            kept = []
                            for item in items:
                                self.runtime.variables["ITEM"] = item
                                if self.runtime.evaluate_condition(body_tokens[:3]):
                                    kept.append(item)
                            self.runtime.variables["FILTERED"] = "\n".join(kept)
                            self.runtime.emit(f"FILTER: {len(kept)} items matched")
                    else:
                        self.runtime.execute_directive(cmd, args)
                else:
                    self.runtime.execute_directive(cmd, args)

            # ── Bare identifier — try as module dispatch ───────────────────
            elif token.ttype == Token.TYPE_IDENTIFIER:
                # Ignore standalone identifiers silently
                pass

            ptr += 1

    # ── Interactive REPL ─────────────────────────────────────────────────────

    def run_interactive(self):
        print("\033[1;36m╔══════════════════════════════════════╗\033[0m")
        print("\033[1;36m║  ShadowScript REPL  —  v2.0          ║\033[0m")
        print("\033[1;36m║  .help  .vars  .modules  .exit       ║\033[0m")
        print("\033[1;36m╚══════════════════════════════════════╝\033[0m")
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
            elif line == ".vars":
                for k, v in self.runtime.variables.items():
                    print(f"  {k} = {v}")
            elif line == ".modules":
                for _ in self.runtime._get_module.__func__.__code__.co_consts:
                    pass
                mods = ["recon", "network", "wireless", "exploit", "poc", "privesc",
                        "c2", "payload", "craft", "web", "osint", "credentials",
                        "secrets", "forensics", "vuln"]
                for m in mods:
                    print(f"  {m}")
            else:
                self.run(line)

    @staticmethod
    def _print_help():
        print("""
\033[1;33mShadowScript Language:\033[0m
  VAR name = value           Set a variable (also: SET)
  TARGET(ip)                 Lock onto a target
  STRIKE(module, method)     Execute a module against current target
  SCAN(ports)                Network port scan (e.g. SCAN(22,80,443))
  SWARM()                    Broadcast to linked Shadow Nodes
  AI("prompt")               Query the local AI brain
  LOAD("file.shadow")        Execute another script file

\033[1;33mControl Flow:\033[0m
  IF $VAR == value { body }  Conditional block
  ELSE { body }              Else clause
  FOR item IN a b c { body } Iterate over items
  WHILE $VAR != 0 { body }   Loop while true
  RETURN value               Exit script / return value
  BREAK                      Exit loop

\033[1;33mSystem Commands:\033[0m
  !sys(command)              Run a shell command (output → $LAST)
  !pipe(command)             Run command (output → $PIPE_OUT)
  !module(mod, fn, args)     Call module method directly
  !echo(text)                Print with $VAR interpolation
  !sleep(seconds)            Pause execution

\033[1;33mREPL Metacommands:\033[0m
  .vars      Show all variables
  .modules   List available modules
  .help      This help
  .exit      Exit
""")


if __name__ == "__main__":
    interp = ShadowInterpreter()
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            interp.run(f.read())
    else:
        interp.run_interactive()
