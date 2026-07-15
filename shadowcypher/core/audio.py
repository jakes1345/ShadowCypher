"""
ShadowCypher Audio Core — Retro 8-Bit Signal Alerts.
Opt-in; off by default. Throttled so tight event loops can't stack beeps.
"""

import os
import subprocess
import time

# Off by default. Flip with env SHADOWCYPHER_AUDIO=1 or audio.enabled = True.
_DEFAULT_ENABLED = os.environ.get("SHADOWCYPHER_AUDIO", "0") == "1"
# Minimum gap between any two sound effects (seconds).
_MIN_GAP = 0.75


class AudioEngine:
    def __init__(self):
        self.enabled = _DEFAULT_ENABLED
        self._last_play = 0.0

    def _play(self, cmd):
        if not self.enabled:
            return
        now = time.monotonic()
        if now - self._last_play < _MIN_GAP:
            return
        self._last_play = now
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def play_success(self):
        """Retro 'Bling' sound (High pitch rising)."""
        # play -n synth 0.1 sine 800 sine 1200
        self._play(["play", "-n", "synth", "0.05", "sine", "880", "fade", "0", "0.05", "0.01"])
        self._play(["play", "-n", "synth", "0.05", "sine", "1320", "fade", "0", "0.05", "0.01"])

    def play_failure(self):
        """Retro 'Buzz' sound (Low pitch falling)."""
        self._play(["play", "-n", "synth", "0.2", "sawtooth", "200:100", "fade", "0", "0.2", "0.05"])

    def play_hub_start(self):
        """Retro 'Ignition' sound (Rising scale)."""
        self._play(["play", "-n", "synth", "0.3", "sine", "440:880", "sine", "220:440"])

    def play_hub_stop(self):
        """Retro 'Deactivation' sound (Falling scale)."""
        self._play(["play", "-n", "synth", "0.3", "sine", "880:440", "sine", "440:220"])

    def play_tool_exec(self):
        """Short 8-bit pulse for tool execution."""
        self._play(["play", "-n", "synth", "0.02", "square", "600"])

audio = AudioEngine()
