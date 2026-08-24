"""
ShadowSentinel v2 — Skybot-Grade Modular IRC Orchestrator.
Inspired by rmmh/skybot: Multithreaded, Hook-based, and Self-Healing.
Connects to Ergo IRC (Sovereign) as a standard IRC client.
"""

import hashlib
import random
import re
import threading
import time
import traceback
from typing import Callable, Dict, List, Optional

from shadowcypher.core.bus import bus
from shadowcypher.core.config import config
from shadowcypher.core.forensics import registry
from shadowcypher.core.irc import IRCClient
from shadowcypher.core.logger import logger


class Hook:
    """Skybot-style Hook containers."""
    def __init__(self):
        self.commands: Dict[str, Callable] = {}
        self.regexes: List[tuple] = []

    def command(self, name: str):
        def decorator(func):
            self.commands[name.lower()] = func
            return func
        return decorator

    def regex(self, pattern: str):
        def decorator(func):
            self.regexes.append((re.compile(pattern, re.IGNORECASE), func))
            return func
        return decorator

# Global Hook Registry (Skybot Pattern)
hook = Hook()

class ShadowSentinel:
    """
    Advanced Modular IRC Bot.
    Bridges the ShadowCypher bus to the IRC coordination channel.
    """
    def __init__(self):
        self.client: Optional[IRCClient] = None
        self._active = False
        self._user_states: Dict[str, dict] = {}
        self._states_lock = threading.Lock()

    def start(self):
        """Bootstrap the bot — connects to both external IRC and Sovereign (Ergo)."""
        if self._active: return

        irc_settings = config.irc
        self._bot_nick = config.get("irc", "bot_nick", default="ShadowSentinel")

        # External IRC client (Libera, etc.)
        self.client = IRCClient(
            server=irc_settings.server,
            port=irc_settings.port,
            channel=irc_settings.channel,
            nick=self._bot_nick,
            use_ssl=irc_settings.use_ssl
        )
        self.client.on_message(self._handle_message)
        self.client.on_private(lambda n, m, s: self._handle_message(n, self._bot_nick, m, s))
        self.client.on_join(self._handle_join)
        self.client.on_ctcp(self._handle_ctcp)
        self.client.on_whois(self._handle_whois)

        # Sovereign IRC client (optional — off by default for cross-platform)
        self._sov_irc = None
        if config.get("irc", "sovereign_enabled", default=False):
            sov_server = config.get("irc", "sovereign_server", default="127.0.0.1")
            sov_port = config.get("irc", "sovereign_port", default=6667)
            self._sov_irc = IRCClient(
                server=sov_server,
                port=sov_port,
                channel="#general",
                nick=self._bot_nick,
                use_ssl=False,
                auto_reconnect=True,
                max_reconnect_delay=60,
            )
            self._sov_irc.on_message(self._handle_sov_message)
            self._sov_irc.on_private(lambda n, m, s: self._handle_sov_message(n, self._bot_nick, m, s))
            self._sov_irc.on_join(self._handle_join)

            def _sov_boot():
                self._sov_irc.connect()
                # Autojoin and identify
                time.sleep(2)
                if config.get("irc", "sasl_pass", default=""):
                    self._sov_irc._send_raw(f"PRIVMSG NickServ :IDENTIFY {config.irc.sasl_pass}")
                self._sov_irc._send_raw("JOIN #general")
                self._sov_irc._send_raw("JOIN #intel")

            threading.Thread(target=_sov_boot, daemon=True).start()

        self._active = True

        # Tactical Subscription (Bus -> IRC for module logs)
        bus.subscribe("module_log", self._relay_logs)
        bus.subscribe("pulse_anomaly", self._relay_anomalies)

        logger.info("bot", f"SENTINEL_V2_ACTIVE: Sovereign (Ergo) + External IRC on {irc_settings.channel}")

    # ── Sovereign (Ergo) Message Handling ─────────────────────────

    def _handle_sov_message(self, nick: str, target: str, message: str, full_source: str = ""):
        """Handle messages from Sovereign Ergo IRC."""
        if nick == self._bot_nick:
            return
        self._process_input(nick, "sovereign", message, full_source=full_source, is_sovereign=True)

    def _handle_join(self, nick: str):
        """Auto-greet new operators."""
        bot_nick = self._bot_nick if hasattr(self, '_bot_nick') else "ShadowSentinel"
        if nick == bot_nick:
            return
        welcome = (
            f"Welcome, {nick}. I am {bot_nick}, your autonomous mission advisor. "
            f"Type !help or mention my name to engage."
        )
        if self._sov_irc and self._sov_irc.connected:
            self._sov_irc.send_message(welcome)

    def _relay_logs(self, data: dict):
        if not self.client or not self.client.connected: return
        module = data.get("module", "CORE")
        text = data.get("text", "")
        level = data.get("level", "INFO")

        color = "14" # Gray
        if level == "ERROR": color = "04" # Red
        elif level == "SUCCESS": color = "03" # Green
        elif level == "WARNING": color = "07" # Orange

        self.client.send_message(f"\x03{color}[{module}]\x03 {text}")

    def _relay_anomalies(self, data: dict):
        if not self.client or not self.client.connected: return
        score = data.get("score", 0.0)
        self.client.send_message(f"\x0305[PULSE_ANOMALY]\x03 Score: {score:.2f} | Escalating to AI Swarm...")

    def _handle_message(self, nick: str, target: str, message: str, full_source: str = "Unknown"):
        """Advanced Skybot-style message dispatcher with Forensic Awareness."""
        self._process_input(nick, target, message, full_source=full_source)

    def _process_input(self, nick: str, target: str, message: str, full_source: str = "Unknown", is_sovereign: bool = False):
        """Unified processing for IRC and Sovereign messages."""
        bot_nick = self.client.nick if self.client else "ShadowSentinel"
        is_private = (target == bot_nick)
        is_mention = (bot_nick.lower() in message.lower()) or "sentinel" in message.lower()

        # 1. Regex Hooks
        for pattern, func in hook.regexes:
            match = pattern.search(message)
            if match:
                self._safe_exec(func, nick, target, match.groups())

        # 2. Command Hooks (! prefix)
        if message.startswith("!"):
            parts = message.split(" ", 1)
            cmd = parts[0][1:].lower()
            args = parts[1] if len(parts) > 1 else ""

            if cmd in hook.commands:
                self._safe_exec(hook.commands[cmd], nick, target, args)
                return

        # 3. Determine if we should respond autonomously
        should_respond = is_mention or is_private or is_sovereign

        # SC_CHAOS_PROTOCOL: Random 2% chance to intervene if chaos is extreme
        from shadowcypher.core.buddy import get_current_buddy
        buddy = get_current_buddy()
        if not should_respond and buddy.chaos > 85 and random.random() < 0.02:
            should_respond = True
            logger.info("bot", "CHAOS_INTERVENTION: Sentinel deciding to chime in...")

        if should_respond:
            # For sovereign, we only respond if mentioned or it's a command
            if is_sovereign and not is_mention and not message.startswith("!"):
                return

            clean_msg = message.replace(bot_nick, "").strip().strip(":, ")
            if not clean_msg: return

            # Initialize state if not exists
            if nick not in self._user_states:
                self._user_states[nick] = {
                    "state": "IDLE",
                    "history": [],
                    "hostmask": full_source,
                    "reputation": 100,
                    "nicks": {nick},
                    "last_seen": time.time()
                }

            # Update Behavioral Metadata
            self._user_states[nick]["last_seen"] = time.time()
            self._user_states[nick]["nicks"].add(nick)

            # Heuristic Risk Check: Rep drops if they change nicks frequently
            if len(self._user_states[nick]["nicks"]) > 3:
               self._user_states[nick]["reputation"] -= 20
               logger.warning("bot", f"REPUTATION_DROP: {nick} flagged for Nick-Velocity. Rep: {self._user_states[nick]['reputation']}")

            state = self._user_states[nick]["state"]

            # --- 2026 PoW HANDSHAKE ---
            if "pow_salt" in self._user_states[nick]:
                self._safe_exec(self._verify_pow, nick, target, clean_msg)
                return

            # --- MISSION_COMMANDER BYPASS ---
            from shadowcypher.core.identity import verify_admin
            is_admin = verify_admin(nick)

            if state == "IDLE" and ("code" in clean_msg.lower() or "unlock" in clean_msg.lower()):
                if is_admin:
                    self._reply(target, nick, "ACCESS_GRANTED: [OPERATOR_CLEARANCE_ACTUAL]. Systems unlocked.")
                    return

                self._user_states[nick]["state"] = "AUDITING"
                self._safe_exec(self._ai_initiate_audit, nick, target, clean_msg)
            elif state == "AUDITING":
                self._safe_exec(self._ai_process_audit, nick, target, clean_msg)
            else:
                self._safe_exec(self._ai_converse, nick, target, clean_msg)

    # NOTE: deephat/execute commands registered as standalone functions below
    # (class-body @hook.command breaks because it stores unbound functions)

    def _reply(self, target, nick, msg):
        """Unified reply — routes to Sovereign (Ergo) or external IRC."""
        bot_nick = self._bot_nick if hasattr(self, '_bot_nick') else "ShadowSentinel"
        if target == "sovereign":
            if self._sov_irc and self._sov_irc.connected:
                self._sov_irc.send_message(f"{nick}: {msg}")
        else:
            dest = nick if target == bot_nick else target
            if self.client:
                self.client.send_message(f"{nick}: {msg}" if target != bot_nick else msg, dest)

    def _verify_pow(self, nick: str, target: str, message: str, reply: Callable, is_admin: bool):
        """Validate SHA-256 PoW solution and measure Latency-to-Compute (LTC)."""
        salt = self._user_states[nick].get("pow_salt")
        prefix = self._user_states[nick].get("pow_prefix", "0000")
        start_time = self._user_states[nick].get("pow_start", time.time())

        # Check the challenge
        test_hash = hashlib.sha256(f"{salt}{message}".encode()).hexdigest()
        ltc = time.time() - start_time

        if test_hash.startswith(prefix):
            logger.info("bot", f"POW_SOLVED: {nick} | LTC: {ltc:.3f}s | Hardware Class: {'HIGH' if ltc < 1 else 'THROTTLED'}")
            del self._user_states[nick]["pow_salt"]
            self._user_states[nick]["history"].append(f"SYSTEM_INTEGRITY: PoW Solved in {ltc:.3f}s")
            reply("\u2705 INTEGRITY_VERIFIED. Latency Nominal. Proceed with justification.")
        else:
            logger.error("bot", f"POW_FAILURE: {nick} | Attempt: {message}")
            reply("\u274c INTEGRITY_ERROR: Protocol Violation. Final warning issued.")
            # Penalize the user by resetting audit state
            self._user_states[nick]["state"] = "IDLE"
            del self._user_states[nick]["pow_salt"]

    def _handle_ctcp(self, nick: str, content: str, source: str):
        """Perform Forensic Correlation on CTCP Fingerprints."""
        logger.warning("bot", f"FINGERPRINT_CAPTURED: User {nick} at {source} is using: {content}")
        if nick in self._user_states:
            # Append fingerprint to conversational history for AI context
            self._user_states[nick]["history"].append(f"SYSTEM_FINGERPRINT: {content}")
            # Save it to the user state for the final ticket
            self._user_states[nick]["fingerprint"] = content

    def _handle_whois(self, info: dict):
        """Inject WHOIS Recon into the Forensic state."""
        nick = info.get("nick")
        if not nick: return

        logger.warning("bot", f"RECON_RESULT: Captured Identity for {nick}: {info}")
        if nick in self._user_states:
            # Flatten WHOIS info for AI Context
            intel = f"SERVER: {info.get('server')} | REALNAME: {info.get('realname')} | USER: {info.get('user')}"
            self._user_states[nick]["history"].append(f"RECON_INTEL: {intel}")
            self._user_states[nick]["whois"] = info

    def _ai_initiate_audit(self, nick: str, target: str, message: str, reply: Callable, is_admin: bool):
        """Initiate the 'Worthy' audit flow with 2026-grade 'Proof of Compute'."""
        import secrets

        from shadowcypher.ai.classic_brain import brain

        # 1. Active Forensic Probes
        if self.client:
            self.client._send_raw(f"PRIVMSG {nick} :\x01VERSION\x01")
            self.client.send_whois(nick)

            # 2. Proof of Compute (PoW) Challenge
            rep = self._user_states[nick].get("reputation", 100)
            prefix = "0000" if rep > 50 else "00000"
            if rep <= 20: prefix = "000000"

            salt = secrets.token_hex(4)
            self._user_states[nick]["pow_salt"] = salt
            self._user_states[nick]["pow_prefix"] = prefix
            self._user_states[nick]["pow_start"] = time.time()

            logger.info("bot", f"POW_CHALLENGE_ISSUED: {nick} | Difficulty: {len(prefix)} | Rep: {rep}")
            reply(f"APEX_PROTOCOL: Solve SHA256(salt='{salt}', nonce=?) starting with '{prefix}'. Provide nonce.")

        from shadowcypher.core.hub import hub
        vitals = hub.get_tactical_summary()
        res = (f"{nick}, this post is monitoring {vitals['active_missions']} active ops. "
               f"State your justification. Be precise — I parse patterns, not excuses.")
        brain.remember(nick, message)
        self._update_history(nick, f"User asked for code: {message}", res)
        reply(res)

    def _ai_process_audit(self, nick: str, target: str, message: str, reply: Callable, is_admin: bool):
        """Invoke the 'Trinity Brain' consensus (now local heuristics, no LLM)."""
        def _brain_thread():
            from shadowcypher.ai.classic_brain import brain
            from shadowcypher.core.tickets import create_support_ticket

            history = self._get_history_text(nick)
            hostmask = self._user_states.get(nick, {}).get("hostmask", "Unknown")
            fingerprint = self._user_states.get(nick, {}).get("fingerprint", "N/A")
            whois = self._user_states.get(nick, {}).get("whois", {})

            res_judge = brain.audit_judge(nick, message, history)
            res_hunter = brain.audit_hunter(nick, hostmask, fingerprint, whois)
            res = brain.audit_architect(res_judge, res_hunter)

            if "UNWORTHY" in res.upper():
                # Generate Deep Forensic Report
                reason_packet = f"CONSENSUS_REJECTION: {res.strip()} | JUDGE: {res_judge} | HUNTER: {res_hunter}"

                # 1. Local Ticket Generation (Incidental Record)
                create_support_ticket(
                    handle=nick,
                    message=message,
                    hostmask=hostmask,
                    reason=f"{reason_packet} [FINGERPRINT: {fingerprint}] [WHOIS: {whois}]"
                )

                # 2. Global Forensic Registration (Deep Integration)
                registry.register_threat(
                    handle=nick,
                    hostmask=hostmask,
                    metadata={
                        "reason": reason_packet,
                        "fingerprint": fingerprint,
                        "whois": whois,
                        "justification": message
                    }
                )

                self._user_states[nick]["state"] = "IDLE"
            else:
                self._user_states[nick]["state"] = "COMPLETED"

            # Use GLib.idle_add or similar if this was a GUI, but for IRC we can reply directly
            reply(res.strip())
            self._update_history(nick, message, res.strip())

        threading.Thread(target=_brain_thread, daemon=True, name=f"Trinity-{nick}").start()

    def _ai_converse(self, nick: str, target: str, message: str, reply: Callable, is_admin: bool):
        """Classic-brain conversation — ELIZA + Markov + intents. No LLM."""
        from shadowcypher.ai.classic_brain import brain
        try:
            res = brain.respond(nick, message)
            self._update_history(nick, message, res)
            reply(res)
            # Periodically persist corpus
            if random.random() < 0.1:
                brain.save()
        except Exception as e:
            logger.error("bot", f"CONV_FAULT: {e}")
            reply("Neural pathways saturated. Standing by for protocol refresh.")

    def _update_history(self, nick: str, user_msg: str, bot_res: str):
        """Append to per-user rolling memory."""
        if nick not in self._user_states: return
        history = self._user_states[nick].get("history", [])
        history.append(f"User: {user_msg}")
        history.append(f"ShadowSentinel: {bot_res}")
        # Keep last 10 exchanges (20 lines)
        self._user_states[nick]["history"] = history[-20:]

    def _get_history_text(self, nick: str) -> str:
        """Flatten history into a prompt string."""
        if nick not in self._user_states: return "No preceding data."
        return "\n".join(self._user_states[nick].get("history", []))

    def _safe_exec(self, func, nick, target, args):
        try:
            # Check Admin Permissions (RBAC) via Central Identity Service
            from shadowcypher.core.identity import verify_admin as v_admin
            is_admin = v_admin(nick)

            # Simple reply wrapper (Handles both Channel and PM and Sovereign)
            def reply(msg):
                self._reply(target, nick, msg)

            func(nick, target, args, reply, is_admin)
        except Exception as e:
            logger.error("bot", f"HOOK_CRASH: {e}\n{traceback.format_exc()}")

# --- SKYBOT-STYLE CORE PLUGINS ---

@hook.command("help")
def cmd_help(nick, target, args, reply, admin):
    """List available tactical protocols."""
    reply("\x0303\x02[GENERAL]\x02\x03 !help !info !ping !uptime !status !quote !8ball !dice !calc !seen !channels")
    reply("\x0313\x02[TACTICAL]\x02\x03 !whois <ip> !peek <nick> !banner <text> !slap <nick>")
    reply("\x0314\x02[AI]\x02\x03 Mention me or PM me for conversation. I am stateful with per-user memory.")
    if admin:
        reply("\x0307\x02[ADMIN]\x02\x03 !stealth !char !restart !threat !deephat !execute")

@hook.command("stealth")
def cmd_stealth(nick, target, args, reply, admin):
    """Toggle Stealth Mode (Shadow xat-style)."""
    if not admin: return reply("Permission Denied.")
    from shadowcypher.core.config import config
    current = config.get("irc", "stealth_mode", default=False)
    new_val = not current
    config.set("irc", "stealth_mode", new_val)

    status = "ENGAGED" if new_val else "DISENGAGED"
    reply(f"STEALTH_MODE: {status}. Telemetry broadcast muted.")

@hook.command("whois")
def cmd_whois(nick, target, args, reply, admin):
    """Integrate with ShadowCypher target database."""
    if not args: return reply("Usage: !whois <target_ip>")
    from shadowcypher.core.database import db

    # Query the local mission database for this target
    db.cursor.execute("SELECT * FROM target_grid WHERE ip=?", (args,))
    row = db.cursor.fetchone()

    if row:
        reply(f"[INTEL] Target: {args} | Status: KNOWN | Last Seen: {row[3]}")
    else:
        reply(f"[INTEL] Target: {args} | Status: UNKNOWN. Run !find to initiate recon.")

@hook.command("restart")
def cmd_restart(nick, target, args, reply, admin):
    if not admin: return reply("Permission Denied.")
    reply("REBOOTING_SENTINEL_CORE...")
    # Restart the IRC connection only — do NOT kill the whole application
    def _do_restart():
        if sentinel.client and sentinel.client._sock:
            try:
                sentinel.client._sock.close()
            except Exception:
                pass
    threading.Thread(target=_do_restart, daemon=True, name="Bot-Restart").start()

@hook.command("char")
def cmd_char(nick, target, args, reply, admin):
    """Change the bot's species (Shadow Buddy integration)."""
    if not admin: return reply("Permission Denied.")
    from shadowcypher.core.buddy import Buddy
    if args.title() in Buddy.SPECIES:
        config.set("irc", "bot_species", args.title())
        reply(f"EVOLVED: Sentinel persona shifted to {args.title()}.")
    else:
        reply(f"INVALID_SPECIES: Available: {', '.join(Buddy.SPECIES)}")

# --- SHADOW-OPS FUN PLUGINS ---

@hook.command("slap")
def cmd_slap(nick, target, args, reply, admin):
    """Classic tactical deterrent."""
    victim = args.strip() or nick
    sentinel.client.send_action(f"slaps {victim} around a bit with a large trout.")

@hook.command("peek")
def cmd_peek(nick, target, args, reply, admin):
    """AI analysis of a user's forensic footprint."""
    victim = args.strip() or nick
    if victim not in sentinel._user_states:
        return reply(f"NO_DATA: {victim} has not been audited yet.")

    state = sentinel._user_states[victim]
    host = state.get("hostmask", "Unknown")
    fp = state.get("fingerprint", "N/A")

    from shadowcypher.ai.classic_brain import brain
    profile = f"Host={host} FP={fp}"
    res = brain.respond(victim, f"peek {profile}")
    reply(f"\x02[PEEK_INTEL]\x02 {victim}: {profile} — {res}")

@hook.command("banner")
def cmd_banner(nick, target, args, reply, admin):
    """Generate a tactical ASCII banner."""
    if not args: return reply("Usage: !banner <text>")
    text = args.upper()
    # Simple micro-banner
    banner = f"--- [ {text} ] ---"
    reply(f"\x0303\x02{banner}\x02\x03")

@hook.command("deephat")
def cmd_deephat(nick, target, args, reply, admin):
    """Removed: DeepHat was a broken jailbreak-prompt tool. Use specific commands instead."""
    reply("DEEPHAT_REMOVED: Use specific commands (!scan, !recon, etc.) instead.")

@hook.command("execute")
def cmd_execute(nick, target, args, reply, admin):
    """Execute a payload file via the runner."""
    if not args:
        return reply("EXECUTE_ERROR: Specify payload file.")
    if not admin:
        return reply("ACCESS_DENIED: Execution restricted to Admin.")
    import os
    if not os.path.isfile(args):
        return reply(f"EXECUTE_ERROR: File not found: {args}")
    try:
        from shadowcypher.core.runner import runner
        task_id = f"EXEC_{int(__import__('time').time())}"
        runner.execute_task(task_id, [args], callback=lambda x: reply(x.strip()) if x.strip() else None)
        reply(f"EXECUTING: {task_id} \u2192 {args}")
    except Exception as e:
        reply(f"EXECUTE_FAILURE: {e}")

@hook.command("status")
def cmd_status(nick, target, args, reply, admin):
    """System vitals snapshot."""
    import psutil
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    load = os.getloadavg()
    reply(f"\x0314[SYS]\x03 CPU: {cpu}% | RAM: {mem.percent}% ({mem.used // (1024**3)}/{mem.total // (1024**3)}GB) | Disk: {disk.percent}% | Load: {load[0]:.1f}")

@hook.command("uptime")
def cmd_uptime(nick, target, args, reply, admin):
    """Show system and bot uptime."""
    import psutil
    boot = psutil.boot_time()
    up = time.time() - boot
    days, rem = divmod(int(up), 86400)
    hours, rem = divmod(rem, 3600)
    mins = rem // 60
    reply(f"\x0303[UPTIME]\x03 System: {days}d {hours}h {mins}m")

@hook.command("seen")
def cmd_seen(nick, target, args, reply, admin):
    """When was a user last active?"""
    who = args.strip()
    if not who:
        return reply("Usage: !seen <nick>")
    state = sentinel._user_states.get(who)
    if state and state.get("last_seen"):
        ago = int(time.time() - state["last_seen"])
        if ago < 60:
            reply(f"\x0314[SEEN]\x03 {who} was active {ago}s ago")
        elif ago < 3600:
            reply(f"\x0314[SEEN]\x03 {who} was active {ago // 60}m ago")
        else:
            reply(f"\x0314[SEEN]\x03 {who} was active {ago // 3600}h {(ago % 3600) // 60}m ago")
    else:
        reply(f"\x0314[SEEN]\x03 No record of {who}")

@hook.command("dice")
def cmd_dice(nick, target, args, reply, admin):
    """Roll dice. Usage: !dice [NdS] (default 1d6)."""
    spec = args.strip() or "1d6"
    try:
        n, s = spec.lower().split("d")
        n, s = int(n or 1), int(s)
        if n > 20 or s > 1000:
            return reply("Too many dice or sides.")
        rolls = [random.randint(1, s) for _ in range(n)]
        reply(f"\x0303[DICE]\x03 {spec}: {rolls} = \x02{sum(rolls)}\x02")
    except Exception:
        reply("Usage: !dice NdS (e.g. 2d20)")

@hook.command("calc")
def cmd_calc(nick, target, args, reply, admin):
    """Safe math eval."""
    if not args:
        return reply("Usage: !calc <expression>")
    import ast
    try:
        # Only allow safe math operations
        tree = ast.parse(args.strip(), mode='eval')
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num,
                                     ast.Add, ast.Sub, ast.Mult, ast.Div,
                                     ast.FloorDiv, ast.USub, ast.UAdd)):
                return reply("Only math expressions allowed.")
        result = eval(compile(tree, '<calc>', 'eval'))
        reply(f"\x0303[CALC]\x03 {args.strip()} = \x02{result}\x02")
    except Exception as e:
        reply(f"Calc error: {e}")

@hook.command("register")
def cmd_register(nick, target, args, reply, admin):
    """Register the bot's nick with NickServ. Usage: !register <password>"""
    if not admin: return reply("ADMIN_ONLY")
    if not args: return reply("Usage: !register <password>")
    reply(f"Registering as {nick}...")
    sentinel.client._send_raw(f"PRIVMSG NickServ :REGISTER {args} {nick}@shadowcypher.site")

@hook.command("unmask")
def cmd_unmask(nick, target, args, reply, admin):
    """Perform a high-fidelity unmasking of a user. Usage: !unmask <target>"""
    if not args: return reply("Usage: !unmask <target>")
    who = args.strip()
    reply(f"\u26a1 INITIATING_UNMASK: Targeting {who} via Sovereign Spectrum...")
    # Signal the Hub to perform the unmasking
    bus.publish("module_log", {"module": "bot", "text": f"UNMASK_REQUEST: {who}", "level": "INFO"})
    # In a real setup, we'd wait for a response or query the forensic registry
    from shadowcypher.core.forensics import registry
    threat = registry.get_threat_by_handle(who)
    if threat:
        ip = threat.get("hostmask", "HIDDEN")
        mac = threat.get("hw_mac", "MASKED")
        reply(f"\U0001f50e UNMASKED [{who}]: IP={ip} | MAC={mac} | STATUS=RECON_COMPLETE")
    else:
        reply(f"\u26d4 UNMASK_FAILED: {who} not found in the forensic registry.")

@hook.command("ping")
def cmd_ping(nick, target, args, reply, admin):
    """Pong."""
    reply(f"\x0303PONG\x03 {nick} [{time.strftime('%H:%M:%S')}]")

@hook.command("info")
def cmd_info(nick, target, args, reply, admin):
    """Bot info."""
    reply("\x02ShadowSentinel\x02 v2.0 | Ergo IRC + AI Agent Fleet | Hooks: "
          f"{len(hook.commands)} cmds, {len(hook.regexes)} regex | !help for commands")

@hook.command("channels")
def cmd_channels(nick, target, args, reply, admin):
    """List Sovereign channels."""
    chans = ["#general", "#intel", "#missions", "#chaos", "#dev", "#security"]
    reply(f"\x0314[CHANNELS]\x03 {' '.join(chans)}")

@hook.command("quote")
def cmd_quote(nick, target, args, reply, admin):
    """Random hacker quote."""
    quotes = [
        "The quieter you become, the more you can hear. — BackTrack",
        "There is no patch for human stupidity.",
        "Hackers are breaking the systems for profit. Before, it was about curiosity. — Kevin Mitnick",
        "The best way to predict the future is to invent it. — Alan Kay",
        "In a world of locked doors, the man with the key is king. — Mr. Robot",
        "We are all now connected by the Internet, like neurons in a giant brain. — Stephen Hawking",
        "Privacy is not something that I'm merely entitled to, it's an absolute prerequisite. — Marlon Brando",
        "The only truly secure system is one that is powered off. — Gene Spafford",
    ]
    reply(f"\x0314{random.choice(quotes)}\x03")

@hook.command("8ball")
def cmd_8ball(nick, target, args, reply, admin):
    """Magic 8-ball."""
    answers = [
        "It is certain.", "Without a doubt.", "You may rely on it.",
        "Yes, definitely.", "As I see it, yes.", "Most likely.",
        "Reply hazy, try again.", "Ask again later.", "Cannot predict now.",
        "Don't count on it.", "My reply is no.", "My sources say no.",
        "Outlook not so good.", "Very doubtful.", "Signs point to yes.",
    ]
    reply(f"\x0306[8BALL]\x03 {random.choice(answers)}")

@hook.command("threat")
def cmd_threat(nick, target, args, reply, admin):
    """Query the forensic threat registry."""
    if not admin:
        return reply("ACCESS_DENIED: Threat intel requires clearance.")
    threats = registry.get_all_threats()
    if not threats:
        return reply("\x0303[THREATS]\x03 Registry clear. No active threats.")
    reply(f"\x0304[THREATS]\x03 {len(threats)} registered:")
    for t in threats[:5]:
        reply(f"  \x02{t.get('handle', '?')}\x02 | {t.get('hostmask', '?')} | Risk: {t.get('risk_level', '?')}")

import os


@hook.regex(r'https?://\S+')
def url_title(nick, target, matches, reply, admin):
    """Auto-fetch URL titles."""
    url = matches[0] if matches else ""
    if not url:
        return
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "ShadowSentinel/2.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read(8192).decode("utf-8", errors="replace")
            import re as _re
            m = _re.search(r"<title[^>]*>([^<]+)</title>", html, _re.IGNORECASE)
            if m:
                title = m.group(1).strip()[:120]
                reply(f"\x0314[URL]\x03 {title}")
    except Exception:
        pass  # Silent fail on URL fetch

# Global Instance
sentinel = ShadowSentinel()

if __name__ == "__main__":
    print("[\033[95mSYS\033[0m] SHADOW_SENTINEL_CORE: INITIALIZING...")
    sentinel.start()
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[\033[91mSYS\033[0m] SHADOW_SENTINEL_CORE: SHUTDOWN_SEQUENCE_ENGAGED.")
