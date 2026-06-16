"""Shadow Guardian AI — Privacy-hardened corporate cloud AI interface.

BYOK (bring your own key) for every provider.
All cloud requests flow through PrivacyGateway:
  • PII scrubbing before the prompt leaves the machine
  • Optional Tor routing (hides your real IP from the provider)
  • Zero-retention headers where the provider supports them
  • Local SQLite response cache (repeat queries never hit the cloud)

Hard limit displayed in the UI:
  Your API key is your identity. Tor hides your IP — it does NOT
  make you anonymous to the provider who issued your key.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
import threading

from shadowcypher.ui.base_page import BasePage
from shadowcypher.ui.components import DataPod, TacticalTerminal, TacticalHeader
from shadowcypher.ai.providers import provider_registry, PROVIDERS
from shadowcypher.ai.privacy_proxy import privacy_gateway
from shadowcypher.core.config import config
from shadowcypher.core.logger import logger


_CLOUD_PROVIDERS = [pid for pid, pd in PROVIDERS.items() if pid != "ollama"]

_FREE_PROVIDERS = {pid for pid, pd in PROVIDERS.items() if pd.get("free") and pid != "ollama"}


class GuardianAIPage(BasePage):
    """Shadow Guardian AI — BYOK cloud AI with full privacy layer."""

    def __init__(self):
        super().__init__("SHADOW GUARDIAN AI")
        self._history: list[dict] = []
        self._thinking = False

        # ── Metric strip ─────────────────────────────────────────────────────
        self.pod_provider = DataPod("PROVIDER", "—", "cyan")
        self.pod_model    = DataPod("MODEL", "—", "cyan")
        self.pod_privacy  = DataPod("PRIVACY", "OFF", "amber")
        self.pod_circuit  = DataPod("CIRCUIT", "DIRECT", "violet")
        self.pod_cache    = DataPod("CACHE HITS", "0", "emerald")
        for pod in (self.pod_provider, self.pod_model, self.pod_privacy,
                    self.pod_circuit, self.pod_cache):
            self.metric_strip.pack_start(pod, True, True, 0)

        # ── Notebook (Config / Chat) ──────────────────────────────────────────
        nb = Gtk.Notebook()
        nb.append_page(self._build_config_tab(), Gtk.Label(label="Providers & Privacy"))
        nb.append_page(self._build_chat_tab(),   Gtk.Label(label="Chat"))
        self.workspace.pack_start(nb, True, True, 0)

        # Pull initial cache stats into the pod
        GLib.timeout_add_seconds(10, self._tick_cache_stats)
        self._refresh_pods()

    # ── Config tab ────────────────────────────────────────────────────────────

    def _build_config_tab(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_start(16)
        outer.set_margin_end(16)
        outer.set_margin_top(12)
        outer.set_margin_bottom(12)

        # ─ Privacy controls ──────────────────────────────────────────────────
        priv_frame = Gtk.Frame(label="Privacy Layer")
        priv_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        priv_box.set_margin_start(12)
        priv_box.set_margin_end(12)
        priv_box.set_margin_top(8)
        priv_box.set_margin_bottom(8)

        warning = Gtk.Label()
        warning.set_markup(
            "<span color='#f59e0b' size='small'>"
            "⚠  Your API key is your identity with the provider. "
            "Tor hides your IP — it does NOT anonymise you from the issuer."
            "</span>"
        )
        warning.set_line_wrap(True)
        warning.set_xalign(0)
        priv_box.pack_start(warning, False, False, 4)

        def make_toggle(label: str, tooltip: str, initial: bool,
                        on_toggled) -> Gtk.CheckButton:
            cb = Gtk.CheckButton(label=label)
            cb.set_active(initial)
            cb.set_tooltip_text(tooltip)
            cb.connect("toggled", on_toggled)
            return cb

        self._cb_scrub = make_toggle(
            "PII Scrub — strip IPs, emails, hostnames before sending",
            "Applies regex rules to the prompt before it leaves the machine.",
            privacy_gateway.scrub_enabled,
            self._on_scrub_toggled,
        )
        self._cb_tor = make_toggle(
            "Tor Routing — route through Tor exit node (adds ~3–8s latency)",
            "Uses torsocks to send API calls through Tor. Provider sees a Tor exit IP.",
            privacy_gateway.tor_enabled,
            self._on_tor_toggled,
        )
        self._cb_zdr = make_toggle(
            "Zero-Retention Headers — opt-out of prompt storage where supported",
            "Adds anthropic-policy: no-training and store: false where providers accept it.",
            privacy_gateway.zdr_enabled,
            self._on_zdr_toggled,
        )
        self._cb_cache = make_toggle(
            "Local Cache — serve identical queries from local SQLite (no cloud hit)",
            "Caches responses keyed on sha256(provider+model+prompt).",
            privacy_gateway.cache_enabled,
            self._on_cache_toggled,
        )

        for cb in (self._cb_scrub, self._cb_tor, self._cb_zdr, self._cb_cache):
            priv_box.pack_start(cb, False, False, 0)

        # Tor status row
        tor_row = Gtk.Box(spacing=8)
        tor_row.pack_start(Gtk.Label(label="Tor circuit:"), False, False, 0)
        self._tor_status_lbl = Gtk.Label(label="—")
        self._tor_status_lbl.get_style_context().add_class("text-muted")
        tor_row.pack_start(self._tor_status_lbl, False, False, 0)
        btn_check_tor = Gtk.Button(label="Check")
        btn_check_tor.connect("clicked", self._on_check_tor)
        tor_row.pack_start(btn_check_tor, False, False, 0)
        priv_box.pack_start(tor_row, False, False, 4)

        # Cache controls
        cache_row = Gtk.Box(spacing=8)
        self._cache_stats_lbl = Gtk.Label(label="Cache: 0 entries")
        self._cache_stats_lbl.get_style_context().add_class("text-muted")
        cache_row.pack_start(self._cache_stats_lbl, False, False, 0)
        btn_clear = Gtk.Button(label="Clear Cache")
        btn_clear.connect("clicked", self._on_clear_cache)
        cache_row.pack_start(btn_clear, False, False, 0)
        priv_box.pack_start(cache_row, False, False, 0)

        priv_frame.add(priv_box)
        outer.pack_start(priv_frame, False, False, 0)

        # ─ Provider / key setup ──────────────────────────────────────────────
        prov_frame = Gtk.Frame(label="API Keys (BYOK — your key, your account)")
        prov_grid = Gtk.Grid(column_spacing=10, row_spacing=6)
        prov_grid.set_margin_start(12)
        prov_grid.set_margin_end(12)
        prov_grid.set_margin_top(8)
        prov_grid.set_margin_bottom(8)

        headers = ["Provider", "Free?", "Model", "API Key", ""]
        for col, h in enumerate(headers):
            lbl = Gtk.Label(label=h)
            lbl.get_style_context().add_class("text-muted")
            lbl.set_xalign(0)
            prov_grid.attach(lbl, col, 0, 1, 1)

        self._key_entries: dict[str, Gtk.Entry] = {}
        self._model_entries: dict[str, Gtk.Entry] = {}

        for row_idx, pid in enumerate(_CLOUD_PROVIDERS, start=1):
            pdef = PROVIDERS[pid]
            provider = provider_registry.get(pid)

            # Name
            name_lbl = Gtk.Label(label=pdef["name"])
            name_lbl.set_xalign(0)
            name_lbl.set_tooltip_text(pdef["description"])
            prov_grid.attach(name_lbl, 0, row_idx, 1, 1)

            # Free badge
            free_lbl = Gtk.Label(label="FREE" if pdef.get("free") else "paid")
            free_lbl.get_style_context().add_class(
                "badge-success" if pdef.get("free") else "text-muted"
            )
            prov_grid.attach(free_lbl, 1, row_idx, 1, 1)

            # Model entry
            model_entry = Gtk.Entry()
            model_entry.set_placeholder_text(pdef["default_model"])
            model_entry.set_text(provider.model if provider else "")
            model_entry.set_width_chars(28)
            self._model_entries[pid] = model_entry
            prov_grid.attach(model_entry, 2, row_idx, 1, 1)

            # Key entry
            key_entry = Gtk.Entry()
            key_entry.set_visibility(False)
            key_entry.set_placeholder_text(
                pdef.get("env_key") or "paste API key here"
            )
            key_entry.set_text(provider.api_key if provider else "")
            key_entry.set_width_chars(32)
            self._key_entries[pid] = key_entry
            prov_grid.attach(key_entry, 3, row_idx, 1, 1)

            # Save + Activate button
            btn = Gtk.Button(label="Save & Use")
            btn.connect("clicked", self._on_save_provider, pid)
            prov_grid.attach(btn, 4, row_idx, 1, 1)

        prov_frame.add(prov_grid)
        outer.pack_start(prov_frame, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(outer)
        return scroll

    # ── Chat tab ─────────────────────────────────────────────────────────────

    def _build_chat_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        # Output
        self.terminal = TacticalTerminal()
        box.pack_start(self.terminal, True, True, 0)

        # System prompt (collapsible)
        sp_revealer = Gtk.Revealer()
        sp_revealer.set_reveal_child(False)
        sp_box = Gtk.Box(spacing=6)
        sp_lbl = Gtk.Label(label="System:")
        sp_lbl.set_xalign(0)
        self._system_entry = Gtk.Entry()
        self._system_entry.set_placeholder_text(
            "You are a cybersecurity expert. Be concise and technical."
        )
        self._system_entry.set_hexpand(True)
        sp_box.pack_start(sp_lbl, False, False, 0)
        sp_box.pack_start(self._system_entry, True, True, 0)
        sp_revealer.add(sp_box)

        # Toggle button for system prompt
        sp_toggle = Gtk.ToggleButton(label="System Prompt ▸")
        sp_toggle.connect("toggled", lambda b: sp_revealer.set_reveal_child(b.get_active()))
        box.pack_start(sp_toggle, False, False, 0)
        box.pack_start(sp_revealer, False, False, 0)

        # Input row
        input_row = Gtk.Box(spacing=8)
        self._input = Gtk.Entry()
        self._input.set_placeholder_text("Ask the AI anything… (Enter to send)")
        self._input.set_hexpand(True)
        self._input.connect("activate", self._on_send)
        input_row.pack_start(self._input, True, True, 0)

        btn_send = Gtk.Button(label="Send")
        btn_send.get_style_context().add_class("suggested-action")
        btn_send.connect("clicked", self._on_send)
        input_row.pack_start(btn_send, False, False, 0)

        btn_clear = Gtk.Button(label="Clear")
        btn_clear.connect("clicked", lambda _: (self.terminal.clear(),
                                                self._history.clear()))
        input_row.pack_start(btn_clear, False, False, 0)
        box.pack_start(input_row, False, False, 0)

        return box

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _on_save_provider(self, btn, pid: str):
        key = self._key_entries[pid].get_text().strip()
        model = self._model_entries[pid].get_text().strip()
        provider_registry.add_provider(pid, api_key=key,
                                       model=model or PROVIDERS[pid]["default_model"])
        provider_registry.switch(pid)
        self._refresh_pods()
        self.terminal.log(
            f"[Guardian AI] Provider set: {PROVIDERS[pid]['name']} / "
            f"{model or PROVIDERS[pid]['default_model']}", "SUCCESS"
        )

    def _on_scrub_toggled(self, cb):
        privacy_gateway.scrub_enabled = cb.get_active()
        self._refresh_pods()

    def _on_tor_toggled(self, cb):
        privacy_gateway.tor_enabled = cb.get_active()
        privacy_gateway.refresh_tor_status()
        self._refresh_pods()
        if cb.get_active():
            threading.Thread(target=self._check_tor_bg, daemon=True).start()

    def _on_zdr_toggled(self, cb):
        privacy_gateway.zdr_enabled = cb.get_active()
        self._refresh_pods()

    def _on_cache_toggled(self, cb):
        privacy_gateway.cache_enabled = cb.get_active()
        self._refresh_pods()

    def _on_check_tor(self, btn):
        btn.set_sensitive(False)
        self._tor_status_lbl.set_text("checking…")
        threading.Thread(target=self._check_tor_bg, daemon=True).start()

    def _check_tor_bg(self):
        status = privacy_gateway.tor_status()

        def update():
            if status["available"]:
                ip = status["ip"] or "connected"
                self._tor_status_lbl.set_markup(
                    f"<span color='#22c55e'>● {ip}</span>"
                )
                self.pod_circuit.update(ip)
            else:
                self._tor_status_lbl.set_markup(
                    "<span color='#ef4444'>● unavailable</span>"
                )
                self.pod_circuit.update("NO TOR")
            # Re-enable the check button if it exists
            return False

        GLib.idle_add(update)

    def _on_clear_cache(self, btn):
        privacy_gateway.clear_cache()
        self._cache_stats_lbl.set_text("Cache: 0 entries")
        self.pod_cache.update("0")
        self.terminal.log("[Guardian AI] Cache cleared.", "INFO")

    def _on_send(self, widget):
        if self._thinking:
            return
        prompt = self._input.get_text().strip()
        if not prompt:
            return

        active = provider_registry.active
        if not active or not active.is_configured:
            self.terminal.log(
                "[Guardian AI] No provider configured. Go to 'Providers & Privacy' tab "
                "and add an API key.", "ERROR"
            )
            return

        self._input.set_text("")
        self._thinking = True

        # Build privacy context label for the output
        flags = []
        if privacy_gateway.scrub_enabled:
            flags.append("SCRUB")
        if privacy_gateway.tor_enabled:
            flags.append("TOR")
        if privacy_gateway.zdr_enabled:
            flags.append("ZDR")
        if privacy_gateway.cache_enabled:
            flags.append("CACHE")
        tag = "[" + "|".join(flags) + "]" if flags else "[NO PRIVACY]"

        self.terminal.log(f"\n[YOU] {prompt}", "INFO")
        self.terminal.log(
            f"[{active.name} / {active.model}] {tag} Generating…", "EXEC"
        )

        system_prompt = self._system_entry.get_text().strip()
        history = list(self._history)

        def _worker():
            try:
                # Build messages with history
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                for turn in history[-10:]:  # last 10 turns
                    messages.append({"role": "user",      "content": turn["user"]})
                    messages.append({"role": "assistant", "content": turn["assistant"]})

                response = active.generate(
                    prompt,
                    system_prompt=system_prompt,
                    max_tokens=config.get("ai", "max_tokens", default=2048),
                    temperature=config.get("ai", "temperature", default=0.7),
                )

                self._history.append({"user": prompt, "assistant": response})

                def _show():
                    self.terminal.log(f"\n[{active.name}] {response}", "SUCCESS")
                    stats = privacy_gateway.cache_stats()
                    self.pod_cache.update(str(stats["hits"]))
                    self._cache_stats_lbl.set_text(
                        f"Cache: {stats['entries']} entries, {stats['hits']} hits"
                    )
                    self._thinking = False
                    return False

                GLib.idle_add(_show)
            except Exception as e:
                GLib.idle_add(self.terminal.log, f"[ERROR] {e}", "ERROR")
                GLib.idle_add(setattr, self, "_thinking", False)

        threading.Thread(target=_worker, daemon=True).start()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _refresh_pods(self):
        active = provider_registry.active
        if active:
            self.pod_provider.update(active.name.split()[0])
            self.pod_model.update(active.model.split(":")[0][:16])

        flags = []
        if privacy_gateway.scrub_enabled:
            flags.append("SCR")
        if privacy_gateway.tor_enabled:
            flags.append("TOR")
        if privacy_gateway.zdr_enabled:
            flags.append("ZDR")
        if privacy_gateway.cache_enabled:
            flags.append("CACHE")
        self.pod_privacy.update("+".join(flags) if flags else "OFF")

        if not privacy_gateway.tor_enabled:
            self.pod_circuit.update("DIRECT")

    def _tick_cache_stats(self) -> bool:
        stats = privacy_gateway.cache_stats()
        self.pod_cache.update(str(stats["hits"]))
        return True  # keep ticking
