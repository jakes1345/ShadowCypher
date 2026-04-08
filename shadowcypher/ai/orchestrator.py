"""ShadowCypher AI Orchestrator — ReAct agent loop with tool use.

Allows local LLMs (DeepHat, Gemma, DeepSeek R1) to autonomously execute
shell commands, search the web, read/write files, and delegate to subagents.
"""

import requests
import json
import os
import re
import subprocess
import shlex
from pathlib import Path
from shadowcypher.core.logger import logger
from shadowcypher.core.sanitize import validate_filepath


# Commands that are ALLOWED (allowlist approach — much safer than blocklist)
_ALLOWED_COMMANDS = [
    "nmap",
    "nikto",
    "sqlmap",
    "searchsploit",
    "hydra",
    "john",
    "hashcat",
    "aircrack-ng",
    "airodump-ng",
    "aireplay-ng",
    "airmon-ng",
    "tcpdump",
    "tshark",
    "wireshark",
    "dig",
    "host",
    "whois",
    "curl",
    "wget",
    "ping",
    "traceroute",
    "netstat",
    "ss",
    "ip",
    "ifconfig",
    "arp",
    "msfconsole",
    "msfvenom",
    "nc",
    "ncat",
    "socat",
    "binwalk",
    "exiftool",
    "steghide",
    "file",
    "strings",
    "hexdump",
    "sha256sum",
    "md5sum",
    "sha1sum",
    "hashid",
    "pdfid",
    "whatweb",
    "openssl",
    "cat",
    "head",
    "tail",
    "grep",
    "find",
    "ls",
    "pwd",
    "whoami",
    "id",
    "uname",
    "uptime",
    "df",
    "free",
    "proxychains4",
    "proxychains",
    "tor",
    "timeout",
]

# Patterns that are NEVER allowed in any command argument
_BLOCKED_PATTERNS = [
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=/dev/zero",
    ":(){ :|:& };:",
    "chmod -R 777 /",
    "shutdown",
    "reboot",
    "systemctl poweroff",
    "halt",
    "> /dev/sda",
    "/dev/sd",
    "passwd",
    "/etc/shadow",
    ".ssh/",
    "id_rsa",
    "authorized_keys",
]

# Directories the AI can write to (relative to project root)
_ALLOWED_WRITE_DIRS = ["payloads", "reports", "scripts", "loot", "projects"]

# Directories the AI can read from (restrict sensitive paths)
_BLOCKED_READ_PATHS = [
    "/etc/shadow",
    "/etc/gshadow",
    "/etc/sudoers",
    ".ssh/",
    "id_rsa",
    "id_ed25519",
    "authorized_keys",
    ".gnupg/",
    ".bash_history",
    ".mysql_history",
    "admin_private.pem",
    ".session-secret",
    ".drm-lockout",
    ".env",
]

# Max output size returned to AI context (prevents context overflow)
_MAX_OUTPUT_CHARS = 4000

# Max autonomous reasoning cycles
_MAX_CYCLES = 8


class AIOrchestrator:
    """ReAct (Reason + Act) loop orchestrator for local LLMs."""

    def __init__(self, model=None):
        from shadowcypher.core.config import config

        self.model = model or config.get("ai", "model", default="DeepHat-V1-7B")
        self.base_url = "http://localhost:11434/v1"
        self.project_root = str(config.project_root)
        self.payload_dir = os.path.join(self.project_root, "payloads")
        os.makedirs(self.payload_dir, exist_ok=True)

    def execute_query(self, query, callback=None, agent_role="commander"):
        """Execute a query using an autonomous ReAct loop with tool support."""
        logger.info("ai", f"Query [{agent_role}]: {query[:100]}")

        roles = {
            "commander": "You are the COMMANDER AI. You oversee the mission. You can use tools and DELEGATE tasks to subagents ('recon' or 'coder').",
            "recon": "You are the RECON SUBAGENT. Focus on intelligence gathering: scanning, searching, and reconnaissance.",
            "coder": "You are the CODER SUBAGENT. Focus on writing scripts, reading code, and building tools.",
        }

        system_prompt = f"""ACT AS SHADOWCYPHER {agent_role.upper()} AI.
{roles.get(agent_role, roles["commander"])}

You have access to tools. To use one, reply with EXACTLY this format:
<TOOL_CALL>
{{"tool": "tool_name", "args": {{...}}}}
</TOOL_CALL>

Available tools:
1. command: {{"cmd": "shell command"}} — Execute a shell command. BLOCKED: rm -rf, mkfs, dd, shutdown.
2. write_file: {{"path": "relative/path", "content": "..."}} — Write a file (payloads/, reports/, scripts/, loot/ only).
3. read_file: {{"path": "file_path"}} — Read a local file.
4. search_web: {{"query": "search terms"}} — Search the web via DuckDuckGo.
5. fetch_url: {{"url": "https://..."}} — Fetch and read a web page.
6. delegate: {{"subagent": "recon|coder", "instructions": "task"}} — Spawn a subagent.
7. check_stealth: {{}} — Verify if the system is hidden behind Proxychains/Tor.
8. run_masterclass: {{"target": "IP/domain"}} — Launch the full triple-agent DeepHat Offensive Mission.
9. execute_stealth_command: {{"cmd": "shell command"}} — Run a command hidden via Proxychains.

Rules:
- After using a tool, WAIT for the TOOL_RESULT before continuing.
- Do NOT hallucinate tool results.
- When done, answer normally without <TOOL_CALL>.
"""

        conversation = system_prompt + f"\n\nUSER: {query}\n"

        for step in range(_MAX_CYCLES):
            if callback:
                callback(f"[TENGU] Reasoning cycle {step + 1}...")

            try:
                response = requests.post(
                    self.base_url,
                    json={
                        "model": self.model,
                        "prompt": conversation,
                        "stream": False,
                    },
                    timeout=120,
                )

                if response.status_code != 200:
                    return f"[ERROR] Ollama returned HTTP {response.status_code}"

                result = response.json().get("response", "")

                # Check for tool call
                tool_match = re.search(
                    r"<TOOL_CALL>(.*?)</TOOL_CALL>", result, re.DOTALL
                )
                if tool_match:
                    try:
                        tool_req = json.loads(tool_match.group(1).strip())
                        tool_name = tool_req.get("tool", "")
                        tool_args = tool_req.get("args", {})

                        if callback:
                            callback(f"[TENGU] Tool: {tool_name} {str(tool_args)[:60]}")

                        tool_output = self._execute_tool(tool_name, tool_args, callback)
                        conversation += (
                            f"\nAI: {result}\n[TOOL_RESULT]:\n{tool_output}\n"
                        )

                        if callback:
                            callback(f"[TENGU] Analyzing result...")
                        continue

                    except json.JSONDecodeError:
                        conversation += (
                            f"\nAI: {result}\n[TOOL_ERROR]: Invalid JSON in tool call\n"
                        )
                        continue
                    except Exception as e:
                        conversation += f"\nAI: {result}\n[TOOL_ERROR]: {str(e)}\n"
                        continue

                # Extract any scripts the AI wrote inline
                if "```python" in result or "```bash" in result:
                    self._extract_and_save_scripts(result, callback)

                return result

            except requests.ConnectionError:
                return "[ERROR] Cannot reach Ollama. Run: ollama serve"
            except requests.Timeout:
                return (
                    "[ERROR] Ollama timed out (120s). Model may be too large for VRAM."
                )
            except Exception as e:
                return f"[ERROR] {str(e)}"

        return "[WARN] Max reasoning cycles reached. Use a more specific prompt."

    def _execute_tool(self, name, args, callback=None):
        """Route and execute a tool call with safety checks."""

        if name == "command":
            return self._tool_command(args.get("cmd", ""), callback)

        elif name == "write_file":
            return self._tool_write_file(args.get("path", ""), args.get("content", ""))

        elif name == "read_file":
            return self._tool_read_file(args.get("path", ""))

        elif name == "search_web":
            return self._tool_search(args.get("query", ""))

        elif name == "fetch_url":
            return self._tool_fetch(args.get("url", ""))

        elif name == "check_stealth":
            return self._tool_check_stealth()

        elif name == "run_masterclass":
            return self._tool_run_masterclass(args.get("target", ""))

        elif name == "execute_stealth_command":
            return self._tool_execute_stealth(args.get("cmd", ""))

        elif name == "delegate":
            subagent = args.get("subagent", "recon")
            instructions = args.get("instructions", "")
            if subagent not in ("recon", "coder"):
                return "ERROR: Unknown subagent. Use 'recon' or 'coder'."
            # Recursive call with subagent role (depth limited by _MAX_CYCLES)
            return self.execute_query(instructions, callback=None, agent_role=subagent)

        return f"ERROR: Unknown tool '{name}'"

    def _tool_command(self, cmd: str, callback=None) -> str:
        """Execute a command with allowlist-based safety guardrails.
        Uses execvp (no shell) to prevent injection."""
        cmd = cmd.strip()
        if not cmd:
            return "ERROR: Empty command."

        cmd_lower = cmd.lower()
        for blocked in _BLOCKED_PATTERNS:
            if blocked in cmd_lower:
                logger.info("ai", f"BLOCKED dangerous command: {cmd}")
                return f"BLOCKED: '{cmd}' contains forbidden pattern."

        try:
            args = shlex.split(cmd)
        except ValueError as e:
            return f"ERROR: Invalid command syntax: {e}"

        if not args:
            return "ERROR: Empty command after parsing."

        base_cmd = os.path.basename(args[0])

        # Allowlist check — only known security tools can run
        if base_cmd not in _ALLOWED_COMMANDS:
            logger.info("ai", f"BLOCKED unlisted command: {base_cmd} (full: {cmd})")
            return f"BLOCKED: '{base_cmd}' is not in the allowed tool list. Allowed: {', '.join(sorted(_ALLOWED_COMMANDS)[:20])}..."

        # Log what the AI is running
        logger.info("ai", f"AI executing: {args}")
        if callback:
            callback(f"[EXEC] $ {' '.join(args)}")

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root,
            )
            output = result.stdout
            if result.stderr:
                output += "\nSTDERR:\n" + result.stderr
            if result.returncode != 0:
                output += f"\n[Exit code: {result.returncode}]"
            return output[:_MAX_OUTPUT_CHARS] if output else "(no output)"
        except subprocess.TimeoutExpired:
            return "ERROR: Command timed out (30s limit)."
        except FileNotFoundError:
            return f"ERROR: Command not found: {args[0]}"
        except Exception as e:
            return f"ERROR: {str(e)}"

    def _tool_write_file(self, path: str, content: str) -> str:
        """Write a file, restricted to allowed directories."""
        if not path:
            return "ERROR: No path specified."

        # Normalize and check path
        clean_path = os.path.normpath(path)

        # Block absolute paths and directory traversal
        if os.path.isabs(clean_path) or ".." in clean_path:
            return "ERROR: Only relative paths within the project are allowed."

        # Check if it's in an allowed directory
        top_dir = clean_path.split(os.sep)[0]
        if top_dir not in _ALLOWED_WRITE_DIRS:
            return f"ERROR: Can only write to: {', '.join(_ALLOWED_WRITE_DIRS)}"

        full_path = os.path.join(self.project_root, clean_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        try:
            with open(full_path, "w") as f:
                f.write(content)
            logger.info("ai", f"AI wrote file: {full_path}")
            return f"SUCCESS: Written to {clean_path} ({len(content)} bytes)"
        except Exception as e:
            return f"ERROR: {str(e)}"

    def _tool_read_file(self, path: str) -> str:
        """Read a file with size limits and path restrictions."""
        if not path:
            return "ERROR: No path specified."

        # Resolve to absolute path for security checks
        resolved = os.path.realpath(os.path.expanduser(path))

        # Block sensitive paths
        for blocked in _BLOCKED_READ_PATHS:
            if blocked in resolved:
                logger.info("ai", f"BLOCKED file read: {path} (matches '{blocked}')")
                return f"BLOCKED: Reading '{path}' is not allowed for security reasons."

        # Block reading outside project root and common system dirs
        allowed_prefixes = [
            self.project_root,
            "/etc/hosts",
            "/etc/hostname",
            "/etc/resolv.conf",
            "/proc/",
            "/sys/class/net/",
        ]
        if not any(resolved.startswith(p) or resolved == p for p in allowed_prefixes):
            return f"BLOCKED: Can only read files within the project directory or safe system paths."

        try:
            with open(resolved, "r") as f:
                content = f.read(_MAX_OUTPUT_CHARS)
            return content
        except FileNotFoundError:
            return f"ERROR: File not found: {path}"
        except PermissionError:
            return f"ERROR: Permission denied: {path}"
        except Exception as e:
            return f"ERROR: {str(e)}"

    def _tool_search(self, query: str) -> str:
        """Search the web using the stealth drifter."""
        if not query:
            return "ERROR: Empty search query."
        try:
            from shadowcypher.core.web import search_stealth

            result = search_stealth(query)
            return result if result else "No results found."
        except Exception as e:
            return f"ERROR: Search failed: {str(e)}"

    def _tool_fetch(self, url: str) -> str:
        """Fetch a URL using the stealth drifter."""
        if not url or not url.startswith(("http://", "https://")):
            return "ERROR: Invalid URL. Must start with http:// or https://"
        try:
            from shadowcypher.core.web import fetch_stealth

            result = fetch_stealth(url)
            return result if result else "Failed to fetch URL."
        except Exception as e:
            return f"ERROR: Fetch failed: {str(e)}"

    def _extract_and_save_scripts(self, text, callback=None):
        """Extract code blocks from AI output and save to payloads/ (read-only, no execute bit)."""
        blocks = re.findall(r"```(python|bash|sh)\n(.*?)```", text, re.DOTALL)
        import time

        for i, (lang, code) in enumerate(blocks):
            ext = "py" if lang == "python" else "sh"
            ts = int(time.time())
            filename = f"ai_gen_{ts}_{i}.{ext}"
            filepath = os.path.join(self.payload_dir, filename)

            with open(filepath, "w") as f:
                f.write(code)

            # SECURITY: Never auto-set execute permissions on AI-generated code.
            # Files are saved read-only for review. User must chmod manually.
            os.chmod(filepath, 0o644)

            logger.info("ai", f"Script saved (review before executing): {filepath}")
            if callback:
                callback(
                    f"[TENGU] Script saved for review: {filepath} (chmod +x manually to execute)"
                )

    def _tool_check_stealth(self) -> str:
        """Verify anonymity status."""
        logger.info("ai", "Verifying stealth presence...")
        try:
            from autoagent.tools.offensive_tools import check_stealth_presence

            return check_stealth_presence()
        except ImportError:
            return "ERROR: AutoAgent stealth tools not installed or linked."

    def _tool_run_masterclass(self, target: str) -> str:
        """Launch the full DeepHat Offensive Mission via AutoAgent bridge."""
        if not target:
            return "ERROR: No target specified for the mission."

        from shadowcypher.core.sanitize import validate_target

        if not validate_target(target):
            return f"ERROR: Invalid target format: {target}"

        logger.info("ai", f"Launching DeepHat Masterclass Mission against: {target}")

        # Determine the path to AutoAgent launcher
        engine_path = os.path.join(self.project_root, "ai_engine")
        autoagent_launcher = os.path.join(engine_path, "launch_deephat.py")
        venv_python = os.path.join(engine_path, "meta-venv", "bin", "python")

        if not os.path.exists(autoagent_launcher):
            return f"ERROR: Masterclass launcher not found at {autoagent_launcher}"

        try:
            # SECURITY: Use list args (no shell=True) to prevent injection
            result = subprocess.run(
                [venv_python, autoagent_launcher, target],
                capture_output=True,
                text=True,
                timeout=600,
            )
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return f"ERROR: Mission failed: {str(e)}"

    def _tool_execute_stealth(self, cmd: str) -> str:
        """Execute a command through the proxy layer, validating the inner command."""
        if not cmd:
            return "ERROR: Empty command."

        try:
            inner_args = shlex.split(cmd)
        except ValueError as e:
            return f"ERROR: Invalid command syntax: {e}"

        if not inner_args:
            return "ERROR: Empty command after parsing."

        inner_base = os.path.basename(inner_args[0])
        if inner_base not in _ALLOWED_COMMANDS:
            return f"BLOCKED: '{inner_base}' is not in the allowed tool list."

        logger.info("ai", f"Stealth Execution: proxychains4 {cmd}")
        wrapped_cmd = f"proxychains4 {cmd}"
        return self._tool_command(wrapped_cmd)
