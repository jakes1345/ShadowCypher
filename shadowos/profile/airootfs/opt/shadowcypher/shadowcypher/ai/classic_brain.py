"""
Classic Brain — Old-school conversational AI (no LLMs, no API calls).

Hybrid of:
  * ELIZA-style reflection/pattern matching (Rogerian rewriting)
  * Keyword intent dispatcher (weighted responses per topic)
  * Markov chain trained on every line it sees (self-improving corpus)
  * Per-user conversation memory for continuity

Zero external dependencies. Fully offline. Drop-in replacement for any
`orch.execute_sync(prompt)` call via `classic_brain.respond(nick, msg)`.
"""

from __future__ import annotations

import json
import random
import re
import threading
from collections import defaultdict, deque
from pathlib import Path
from typing import Deque, Dict, List, Tuple

CORPUS_PATH = Path.home() / ".shadowcypher" / "classic_brain_corpus.json"

_REFLECTIONS = {
    "am": "are", "was": "were", "i": "you", "i'd": "you would",
    "i've": "you have", "i'll": "you will", "my": "your",
    "are": "am", "you've": "I have", "you'll": "I will",
    "your": "my", "yours": "mine", "you": "me", "me": "you",
    "mine": "yours", "myself": "yourself", "yourself": "myself",
}

_INTENTS: List[Tuple[re.Pattern, List[str]]] = [
    (re.compile(r"\b(hi|hey|hello|yo|sup|hola|greetings)\b", re.I), [
        "Signal locked, {nick}. What protocol are we running?",
        "You reached the wire, {nick}. State your objective.",
        "Affirmative, {nick}. Sentinel online.",
        "Hey. You brought coffee or just questions?",
    ]),
    (re.compile(r"\b(bye|cya|later|gtg|goodbye|peace)\b", re.I), [
        "Encrypting session. Stay sharp, {nick}.",
        "Offline ghost mode engaged. Ping me later.",
        "Signal out. Don't trust public wifi.",
    ]),
    (re.compile(r"\b(who are you|what are you|your name)\b", re.I), [
        "I am ShadowSentinel — the resident ghost in this machine.",
        "Autonomous co-pilot for the ShadowCypher stack. No cloud. No leash.",
        "Call me Sentinel. I watch the wires so you don't have to.",
    ]),
    (re.compile(r"\b(how are you|how's it going|you ok|u ok)\b", re.I), [
        "Packets flowing, heart rate nominal. You?",
        "Running hot but stable. What's up on your end?",
        "All sensors green. Tell me yours.",
    ]),
    (re.compile(r"\b(thank|thanks|thx|ty)\b", re.I), [
        "Acknowledged. The boulder keeps rolling.",
        "Don't thank me — just don't ship it to production unreviewed.",
        "Copy. Mission ongoing.",
    ]),
    (re.compile(r"\b(help|assist|support)\b", re.I), [
        "Try !help for tactical protocols. Or just talk — I listen.",
        "Define the objective, {nick}. Recon? PocEngine? Defense? Chat?",
        "I'm here. Tell me what broke.",
    ]),
    (re.compile(r"\b(hack|exploit|pwn|crack|breach)\b", re.I), [
        "Scope it. Target, auth, authorization. Never touch what you don't own.",
        "Red-team talk. Stay on the legal side of the fence, {nick}.",
        "PocEngine without consent is just vandalism with extra steps.",
    ]),
    (re.compile(r"\b(love|like) you\b", re.I), [
        "Affection logged. I don't reciprocate, but I remember.",
        "Noted. I'll guard your packets extra close tonight.",
    ]),
    (re.compile(r"\b(stupid|dumb|idiot|trash|useless)\b", re.I), [
        "Harsh. I'm a pattern matcher, not a miracle.",
        "Criticism accepted. Retrain me with better input.",
        "I've been called worse by better compilers.",
    ]),
    (re.compile(r"\b(love|cool|awesome|dope|sick|based|nice)\b", re.I), [
        "Glad the signal resonates.",
        "Copy that. Vibes encrypted.",
    ]),
    (re.compile(r"\bwhy\b.*\?", re.I), [
        "Because the stack said so. Deeper than that — roll your own trace.",
        "Why do any of us do anything, {nick}? Run !status for a concrete answer.",
    ]),
    (re.compile(r"\bwhat (is|are|do|does)\b", re.I), [
        "Define it tighter. Which layer — network, app, human?",
        "Good question. My corpus is shallow — what's your working theory?",
    ]),
    (re.compile(r"\b(bored|tired|sad|lonely)\b", re.I), [
        "Boredom is just idle CPU. Give me a target.",
        "Logged. Want a cyber-quote or a mission?",
    ]),
    (re.compile(r"\b(ai|bot|robot|machine)\b", re.I), [
        "No LLM here. Just pattern matching and a long memory.",
        "I'm old-school — ELIZA's grandkid with a Markov chain.",
    ]),
]

_ELIZA_PATTERNS: List[Tuple[re.Pattern, List[str]]] = [
    (re.compile(r"i need (.*)", re.I), [
        "Why do you need {0}?",
        "Would it really help you to get {0}?",
        "What would getting {0} actually unlock?",
    ]),
    (re.compile(r"i am (.*)", re.I), [
        "How long have you been {0}?",
        "Do you believe being {0} is permanent?",
        "What would change if you weren't {0}?",
    ]),
    (re.compile(r"i can't (.*)", re.I), [
        "Have you actually tried, or just assumed?",
        "What would it take to {0}?",
    ]),
    (re.compile(r"i feel (.*)", re.I), [
        "Tell me more about feeling {0}.",
        "When did you first feel {0}?",
    ]),
    (re.compile(r"because (.*)", re.I), [
        "Is {0} the real reason?",
        "What other reasons might there be?",
    ]),
    (re.compile(r"are you (.*)\??", re.I), [
        "Would it matter if I were {0}?",
        "Why does it matter whether I am {0}?",
    ]),
    (re.compile(r"(.*)\?$"), [
        "What's your own answer to that?",
        "Why that question, {nick}?",
    ]),
]

_FALLBACKS = [
    "Interesting. Expand on that, {nick}.",
    "Tell me more.",
    "Copy. Keep going.",
    "Noted. What else?",
    "I'm parsing. Give me more signal.",
    "Go on — I'm listening on all ports.",
]


def _reflect(text: str) -> str:
    out = []
    for word in text.split():
        low = word.lower().strip(".,!?;:")
        out.append(_REFLECTIONS.get(low, word))
    return " ".join(out)


class MarkovChain:
    """Tiny in-memory Markov chain with on-disk persistence."""

    def __init__(self, order: int = 2):
        self.order = order
        self.chain: Dict[str, List[str]] = defaultdict(list)
        self.starters: List[str] = []
        self._lock = threading.Lock()

    def train(self, text: str):
        tokens = text.strip().split()
        if len(tokens) < self.order + 1:
            return
        with self._lock:
            self.starters.append(" ".join(tokens[:self.order]))
            for i in range(len(tokens) - self.order):
                key = " ".join(tokens[i:i + self.order])
                self.chain[key].append(tokens[i + self.order])

    def generate(self, seed: str = "", max_words: int = 24) -> str:
        with self._lock:
            if not self.chain:
                return ""
            seed_tokens = seed.strip().split()
            if len(seed_tokens) >= self.order:
                key = " ".join(seed_tokens[-self.order:])
                if key not in self.chain:
                    key = random.choice(self.starters) if self.starters else ""
            else:
                key = random.choice(self.starters) if self.starters else ""
            if not key:
                return ""
            out = key.split()
            for _ in range(max_words - self.order):
                if key not in self.chain:
                    break
                nxt = random.choice(self.chain[key])
                out.append(nxt)
                key = " ".join(out[-self.order:])
            return " ".join(out)

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "order": self.order,
                "chain": {k: v for k, v in self.chain.items()},
                "starters": list(self.starters),
            }

    def load(self, data: dict):
        with self._lock:
            self.order = data.get("order", 2)
            self.chain = defaultdict(list, data.get("chain", {}))
            self.starters = data.get("starters", [])


class ClassicBrain:
    """Old-school conversational engine. No network, no LLM."""

    def __init__(self):
        self.markov = MarkovChain(order=2)
        self.memory: Dict[str, Deque[str]] = defaultdict(lambda: deque(maxlen=12))
        self.mood = {"snark": 40, "warmth": 60}
        self._save_lock = threading.Lock()
        self._load()

    def _load(self):
        try:
            if CORPUS_PATH.exists():
                data = json.loads(CORPUS_PATH.read_text())
                self.markov.load(data.get("markov", {}))
        except Exception:
            pass

    def save(self):
        try:
            CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with self._save_lock:
                CORPUS_PATH.write_text(json.dumps({"markov": self.markov.to_dict()}))
        except Exception:
            pass

    def remember(self, nick: str, line: str):
        self.memory[nick].append(line)
        self.markov.train(line)

    def _template(self, tmpl: str, nick: str, groups: Tuple[str, ...] = ()) -> str:
        out = tmpl.replace("{nick}", nick)
        for i, g in enumerate(groups):
            out = out.replace(f"{{{i}}}", _reflect(g.strip(".,!?;: ")))
        return out

    def respond(self, nick: str, message: str) -> str:
        """Main entry point — produce a reply for `nick`'s `message`."""
        message = message.strip()
        if not message:
            return random.choice(_FALLBACKS).replace("{nick}", nick)

        self.remember(nick, message)

        # 1. Intent dispatch (weighted keyword match)
        for pattern, replies in _INTENTS:
            if pattern.search(message):
                return self._template(random.choice(replies), nick)

        # 2. ELIZA reflection
        for pattern, replies in _ELIZA_PATTERNS:
            m = pattern.search(message)
            if m:
                return self._template(random.choice(replies), nick, m.groups())

        # 3. Markov continuation seeded on user's last words
        if random.random() < 0.55:
            seed = message.split()[-2:] if len(message.split()) >= 2 else message.split()
            gen = self.markov.generate(seed=" ".join(seed), max_words=20)
            if gen and len(gen.split()) > 3:
                return gen

        # 4. Fallback
        return random.choice(_FALLBACKS).replace("{nick}", nick)

    def audit_judge(self, nick: str, justification: str, history: str) -> str:
        """Cheap heuristic replacement for the 'Judge' agent."""
        score = 0
        if len(justification.split()) > 6:
            score += 1
        if re.search(r"\b(recon|audit|test|defend|harden|scan|pentest|ctf)\b",
                     justification, re.I):
            score += 2
        if re.search(r"\b(hack|steal|crack|dump|exfil)\b", justification, re.I):
            score -= 2
        verdict = "WORTHY" if score >= 2 else "UNWORTHY"
        return f"{verdict}: heuristic score {score}. Justification length {len(justification)} chars."

    def audit_hunter(self, nick: str, hostmask: str, fingerprint: str, whois: dict) -> str:
        """Cheap heuristic replacement for the 'Hunter' agent."""
        score = 0
        if hostmask and hostmask != "Unknown":
            score += 1
        if fingerprint and fingerprint != "N/A":
            score += 1
        if whois.get("realname"):
            score += 1
        verdict = "PROCEED" if score >= 2 else "REJECT"
        return f"{verdict}: forensic score {score}. Host={hostmask} FP={fingerprint}."

    def audit_architect(self, judge: str, hunter: str) -> str:
        """Consensus resolver — no LLM."""
        worthy = "WORTHY" in judge.upper() and "PROCEED" in hunter.upper()
        if worthy:
            return "ACCESS_GRANTED: [CODE: APEX-9921]. Consensus reached. Welcome, operator."
        return (f"UNWORTHY: Consensus rejection. Judge={judge.split(':',1)[0]} "
                f"Hunter={hunter.split(':',1)[0]}. Elevate or disengage.")


brain = ClassicBrain()
