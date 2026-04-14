"""ShadowCypher Tactical AI Swarm — Multi-Provider AI Chat + MetaChain Bridge."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
import os
import threading

from shadowcypher.ui.components import TacticalTerminal, TacticalHeader, DataPod
from shadowcypher.core.hub import hub
from shadowcypher.core.logger import logger
from shadowcypher.ai.providers import provider_registry, PROVIDERS


class AIPage(Gtk.Box):
    """Deep-Spectrum AI Hub. Chat with the AI + Launch autonomous missions."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.attachments = []
        self.history = []
        self._build_ui()

    def _build_ui(self):
        self.main_pod = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.main_pod.get_style_context().add_class("card")
        self.pack_start(self.main_pod, True, True, 0)

        # 1. Header
        self.header = TacticalHeader("SHADOWCYPHER AI COMMAND")
        self.main_pod.pack_start(self.header, False, False, 0)

        # 2. Metric Strip
        strip = Gtk.Box(spacing=10)
        strip.set_margin_start(20)
        strip.set_margin_end(20)
        active = provider_registry.active
        self.pod_provider = DataPod("PROVIDER", active.name if active else "None", "cyan")
        self.pod_model = DataPod("MODEL", active.model if active else "—", "cyan")
        self.pod_status = DataPod("STATUS", "STANDBY", "violet")
        self.pod_missions = DataPod("MISSIONS", "0", "amber")
        strip.pack_start(self.pod_provider, True, True, 0)
        strip.pack_start(self.pod_model, True, True, 0)
        strip.pack_start(self.pod_status, True, True, 0)
        strip.pack_start(self.pod_missions, True, True, 0)
        self.main_pod.pack_start(strip, False, False, 0)

        # 3. Provider Settings (collapsible)
        self.settings_revealer = Gtk.Revealer()
        self.settings_revealer.set_reveal_child(False)
        settings_frame = Gtk.Frame(label="AI Provider Configuration")
        settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        settings_box.set_margin_start(15)
        settings_box.set_margin_end(15)
        settings_box.set_margin_top(10)
        settings_box.set_margin_bottom(10)

        # Provider selector
        prov_row = Gtk.Box(spacing=10)
        prov_row.pack_start(Gtk.Label(label="Provider:"), False, False, 0)
        self.provider_combo = Gtk.ComboBoxText()
        for pid, pdef in PROVIDERS.items():
            label = f"{'✅' if provider_registry.get(pid) and provider_registry.get(pid).is_configured else '⚪'} {pdef['name']}"
            if pdef["free"]:
                label += " (Free)"
            self.provider_combo.append(pid, label)
        # Set active to current
        idx = list(PROVIDERS.keys()).index(provider_registry.active_id) if provider_registry.active_id in PROVIDERS else 0
        self.provider_combo.set_active(idx)
        self.provider_combo.connect("changed", self._on_provider_changed)
        prov_row.pack_start(self.provider_combo, True, True, 0)
        settings_box.pack_start(prov_row, False, False, 0)

        # Provider description
        self.prov_desc = Gtk.Label(xalign=0)
        self.prov_desc.set_line_wrap(True)
        self.prov_desc.get_style_context().add_class("text-muted")
        if active:
            self.prov_desc.set_text(active.description)
        settings_box.pack_start(self.prov_desc, False, False, 0)

        # API Key
        key_row = Gtk.Box(spacing=10)
        key_row.pack_start(Gtk.Label(label="API Key:"), False, False, 0)
        self.api_key_entry = Gtk.Entry()
        self.api_key_entry.set_placeholder_text("Enter API key (or set env var)")
        self.api_key_entry.set_visibility(False)
        self.api_key_entry.set_width_chars(40)
        key_row.pack_start(self.api_key_entry, True, True, 0)
        settings_box.pack_start(key_row, False, False, 0)

        # Model selection
        model_row = Gtk.Box(spacing=10)
        model_row.pack_start(Gtk.Label(label="Model:"), False, False, 0)
        self.model_combo = Gtk.ComboBoxText()
        if active:
            for m in active.list_models():
                self.model_combo.append(m, m)
            self.model_combo.set_active_id(active.model)
        model_row.pack_start(self.model_combo, True, True, 0)
        
        refresh_btn = Gtk.Button(label="🔄")
        refresh_btn.set_tooltip_text("REFRESH_MODEL_SWARM")
        refresh_btn.connect("clicked", lambda b: self._update_settings_list(self.provider_combo.get_active_id()))
        model_row.pack_start(refresh_btn, False, False, 0)
        
        settings_box.pack_start(model_row, False, False, 0)

        # Custom URL (for custom endpoint)
        url_row = Gtk.Box(spacing=10)
        url_row.pack_start(Gtk.Label(label="Base URL:"), False, False, 0)
        self.url_entry = Gtk.Entry()
        self.url_entry.set_placeholder_text("https://api.example.com/v1 (custom only)")
        self.url_entry.set_width_chars(40)
        url_row.pack_start(self.url_entry, True, True, 0)
        settings_box.pack_start(url_row, False, False, 0)

        # Action buttons
        btn_row = Gtk.Box(spacing=8)
        save_btn = Gtk.Button(label="💾 Save & Activate")
        save_btn.get_style_context().add_class("suggested-action")
        save_btn.connect("clicked", self._on_save_provider)
        btn_row.pack_start(save_btn, False, False, 0)

        test_btn = Gtk.Button(label="🔌 Test Connection")
        test_btn.connect("clicked", self._on_test_connection)
        btn_row.pack_start(test_btn, False, False, 0)

        settings_box.pack_start(btn_row, False, False, 0)

        # Env var hint
        self.env_hint = Gtk.Label(xalign=0)
        self.env_hint.get_style_context().add_class("text-muted")
        settings_box.pack_start(self.env_hint, False, False, 0)
        self._update_env_hint()

        settings_frame.add(settings_box)
        self.settings_revealer.add(settings_frame)
        self.main_pod.pack_start(self.settings_revealer, False, False, 0)

        # 4. Chat Terminal
        self.terminal = TacticalTerminal(height=380)
        self.main_pod.pack_start(self.terminal, True, True, 0)

        self.terminal.log("APEX_COMMANDER: AI swarm initialized. Send a message to begin.", "SYSTEM")
        self.terminal.log("TIP: Click ⚙ Settings to configure cloud AI providers (Claude, GPT-4, Gemini, etc.)", "SYSTEM")

        # 5. Controls
        ctrl_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        ctrl_box.set_margin_start(20)
        ctrl_box.set_margin_end(20)
        ctrl_box.set_margin_bottom(10)

        # Role & Intensity Row
        opts_row = Gtk.Box(spacing=15)

        settings_btn = Gtk.Button(label="⚙ Settings")
        settings_btn.connect("clicked", self._toggle_settings)
        opts_row.pack_start(settings_btn, False, False, 0)

        opts_row.pack_start(Gtk.Label(label="ROLE:"), False, False, 0)
        self.role_combo = Gtk.ComboBoxText()
        for r in ["commander", "red_team", "blue_team", "devops"]:
            self.role_combo.append_text(r)
        self.role_combo.set_active(0)
        opts_row.pack_start(self.role_combo, False, False, 0)

        # 6. QUICK MODEL SWITCHER (Enterprise HUD)
        opts_row.pack_start(Gtk.Label(label="MODEL:"), False, False, 0)
        self.quick_model_combo = Gtk.ComboBoxText()
        self.quick_model_combo.connect("changed", self._on_quick_model_changed)
        opts_row.pack_start(self.quick_model_combo, True, True, 0)

        # Start Lazy Model Discovery
        GLib.timeout_add_seconds(1, self._lazy_model_discovery, 0)

        self.intensity_toggle = Gtk.CheckButton(label="HIGH_INTENSITY")
        self.intensity_toggle.set_tooltip_text("Routes queries through the AutoAgent engine with 88-feature ULTRAPLAN mode.")
        opts_row.pack_start(self.intensity_toggle, False, False, 0)

        ctrl_box.pack_start(opts_row, False, False, 0)

        # Attachment label
        self.attach_lbl = Gtk.Label(xalign=0)
        self.attach_lbl.set_markup("<span size='small' color='#94a3b8'>ATTACHMENTS: NONE</span>")
        ctrl_box.pack_start(self.attach_lbl, False, False, 0)

        # Input Row
        entry_row = Gtk.Box(spacing=10)

        btn_attach = Gtk.Button()
        btn_attach.set_image(Gtk.Image.new_from_icon_name("mail-attachment", Gtk.IconSize.BUTTON))
        btn_attach.set_tooltip_text("Attach image for multimodal analysis")
        btn_attach.connect("clicked", self._on_attach)
        entry_row.pack_start(btn_attach, False, False, 0)

        self.msg_entry = Gtk.Entry()
        self.msg_entry.set_placeholder_text("Enter command, question, or offensive directive...")
        self.msg_entry.connect("activate", self._on_send)
        entry_row.pack_start(self.msg_entry, True, True, 0)

        btn_send = Gtk.Button(label="⚡ ENGAGE")
        btn_send.get_style_context().add_class("suggested-action")
        btn_send.connect("clicked", self._on_send)
        entry_row.pack_end(btn_send, False, False, 0)

        ctrl_box.pack_start(entry_row, False, False, 0)
        
        # 7. Quantum Agent Dashboard (Experimental)
        self.quantum_revealer = Gtk.Revealer()
        self.quantum_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.quantum_box.set_margin_top(10)
        
        q_label = Gtk.Label()
        q_label.set_markup("<span weight='bold' color='#00ff9d'>QUANTUM_AGENT_STATUS (88_FEATURES_ACTIVE)</span>")
        self.quantum_box.pack_start(q_label, False, False, 0)
        
        # Featured active flags
        flags_flow = Gtk.FlowBox()
        flags_flow.set_max_children_per_line(4)
        flags_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        
        active_flags = ["ULTRAPLAN", "KAIROS", "TRIGGERS", "ULTRATHINK", "TEAMMEM", "BASH_CLASSIFIER"]
        for flag in active_flags:
            btn = Gtk.Button(label=flag)
            btn.set_sensitive(False)
            btn.get_style_context().add_class("quantum-badge")
            flags_flow.add(btn)
        
        self.quantum_box.pack_start(flags_flow, False, False, 0)
        self.quantum_revealer.add(self.quantum_box)
        self.main_pod.pack_start(self.quantum_revealer, False, False, 0)
        
        self.main_pod.pack_start(ctrl_box, False, False, 0)

    # ══════════════════════════════════════════════
    # Settings / Provider Management
    # ══════════════════════════════════════════════

    def _toggle_settings(self, btn):
        self.settings_revealer.set_reveal_child(not self.settings_revealer.get_reveal_child())

    def _on_provider_changed(self, combo):
        pid = combo.get_active_id()
        if not pid:
            return
        pdef = PROVIDERS.get(pid, {})
        self.prov_desc.set_text(pdef.get("description", ""))
        self._update_env_hint()
        self._update_quick_model_list()

    def _update_quick_model_list(self):
        """Sync the HUD model switcher with the current provider."""
        self.quick_model_combo.remove_all()
        active = provider_registry.active
        if active:
            for m in active.list_models():
                self.quick_model_combo.append(m, m)
            self.quick_model_combo.set_active_id(active.model)

    def _on_quick_model_changed(self, combo):
        """Handle on-the-fly model switching from the main HUD."""
        model_id = combo.get_active_id()
        if not model_id:
            return
        
        active = provider_registry.active
        if active and active.model != model_id:
            provider_registry.switch(active.id, model=model_id)
            self.pod_model.set_value(model_id)
            # Sync the settings entry
            self.model_combo.set_active_id(model_id)
            self.terminal.log(f"HOT_SWAP_COMPLETE: {model_id}", "SUCCESS")
            
    def _update_settings_list(self, pid):
        """Sync the internal settings dropdown when provider changes."""
        self.model_combo.remove_all()
        provider = provider_registry.get(pid)
        pdef = PROVIDERS.get(pid, {})
        
        if provider:
            for m in provider.list_models():
                self.model_combo.append(m, m)
            self.model_combo.set_active_id(provider.model)
        else:
            default_model = pdef.get("default_model", "gemma4")
            self.model_combo.append(default_model, default_model)
            self.model_combo.set_active_id(default_model)

    def _lazy_model_discovery(self, attempt):
        """Persistent discovery protocol for slow-loading providers."""
        active = provider_registry.active
        if not active:
            return False # Stop if no provider
            
        models = active.list_models()
        if models:
            self.terminal.log(f"ENGINE_SYNC_SUCCESS: {len(models)} models discovered.", "SUCCESS")
            self._update_quick_model_list()
            self._update_settings_list(active.id)
            self.pod_status.set_value("READY")
            return False # Success! Stop timer
            
        if attempt < 5:
            self.pod_status.set_value(f"SYNCING ({attempt+1}/5)")
            return True # Try again next second
            
        # Handshake Fault
        self.pod_status.set_value("SYNC_FAULT")
        self.quick_model_combo.append("err", "<NO_MODELS_FOUND>")
        self.quick_model_combo.set_active_id("err")
        self.terminal.log(f"ENGINE_SYNC_FAULT: {active.name} failed to return models. Check local service status.", "ERROR")
        return False # Give up

    def _update_env_hint(self):
        pid = self.provider_combo.get_active_id()
        if not pid:
            return
        pdef = PROVIDERS.get(pid, {})
        env_key = pdef.get("env_key")
        val = os.environ.get(env_key or "", "")
        if val:
            self.env_hint.set_markup(f"<span color='#00ff9d'>✔ ENVIRONMENT: {env_key} IS SET</span>")
        else:
            self.env_hint.set_markup(f"<span color='#ef4444'>✘ ENVIRONMENT: {env_key} NOT DETECTED</span>")

    def _on_save_provider(self, btn):
        pid = self.provider_combo.get_active_id()
        if not pid:
            return
        api_key = self.api_key_entry.get_text().strip()
        model = self.model_combo.get_active_text() or ""
        base_url = self.url_entry.get_text().strip()

        provider = provider_registry.add_provider(pid, api_key=api_key,
                                                   base_url=base_url, model=model)
        provider_registry.switch(pid, model=model)

        self.pod_provider.set_value(provider.name)
        self.pod_model.set_value(provider.model)
        self.terminal.log(f"PROVIDER_SWITCH: {provider.name} / {provider.model}", "SYSTEM")
        self.terminal.log(f"Config saved. {'API key configured.' if api_key else 'Using env var or existing key.'}", "SYSTEM")

    def _on_test_connection(self, btn):
        pid = self.provider_combo.get_active_id()
        if not pid:
            return
        self.terminal.log(f"Testing connection to {PROVIDERS[pid]['name']}...", "SYSTEM")

        def _test():
            provider = provider_registry.get(pid)
            if not provider:
                # Create temporary provider for testing
                api_key = self.api_key_entry.get_text().strip()
                model = self.model_combo.get_active_text() or ""
                from shadowcypher.ai.providers import AIProvider
                provider = AIProvider(pid, api_key=api_key, model=model)

            result = provider.test_connection()
            GLib.idle_add(self.terminal.log,
                          f"{'✅' if result['ok'] else '❌'} {PROVIDERS[pid]['name']}: {result['detail']}",
                          "SUCCESS" if result["ok"] else "ERROR")

        threading.Thread(target=_test, daemon=True).start()

    # ══════════════════════════════════════════════
    # Chat
    # ══════════════════════════════════════════════

    def _on_attach(self, btn):
        dialog = Gtk.FileChooserDialog(
            title="SELECT_MISSION_MEDIA", parent=None,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        if dialog.run() == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            self.attachments.append(path)
            self.attach_lbl.set_markup(
                f"<span size='small' color='#38bdf8'>ATTACHMENTS: {len(self.attachments)} item(s)</span>"
            )
        dialog.destroy()

    def _on_send(self, widget):
        msg = self.msg_entry.get_text().strip()
        if not msg and not self.attachments:
            return

        role = self.role_combo.get_active_text() or "commander"
        intensity = "MAX" if self.intensity_toggle.get_active() else None

        # Display user message
        self.terminal.log(f"YOU >> {msg}", "USER")
        if self.attachments:
            self.terminal.log(f"MEDIA_ATTACHED: {[a.split('/')[-1] for a in self.attachments]}", "SYSTEM")

        # Update status
        active = provider_registry.active
        if active:
            self.terminal.log(f"Routing to: {active.name} / {active.model}", "SYSTEM")
        self.header.set_active(True)
        self.pod_status.set_value("PROCESSING")
        self.pod_missions.set_value(str(len(hub.active_missions) + 1))

        # Clear input
        self.msg_entry.set_text("")
        images = self.attachments.copy()
        self.attachments = []
        self.attach_lbl.set_markup("<span size='small' color='#94a3b8'>ATTACHMENTS: NONE</span>")

        # --- OFFENSIVE INTERCEPTION (DEPTH UPGRADE) ---
        cmd_lower = msg.lower()
        if any(w in cmd_lower for w in ["forge", "payload", "stager"]):
            self._handle_autonomous_forge(msg)
            # We still run the AI query in parallel for advice
        elif any(w in cmd_lower for w in ["scan", "recon", "nmap"]):
            self._handle_autonomous_recon(msg)
            # We still run the AI query for analysis
            
        # Dispatch to AI (non-blocking)
        def _callback(txt):
            GLib.idle_add(self.terminal.log, txt, "AI")

        def _complete(result):
            # Append to history for stateful multi-turn
            if result and not result.startswith("CRITICAL_EXCEPTION"):
                self.history.append({"role": "user", "content": msg})
                self.history.append({"role": "assistant", "content": result})
                # Keep last 15 exchanges (30 messages)
                if len(self.history) > 30:
                    self.history = self.history[-30:]
            
            GLib.idle_add(self._on_mission_done, result)

        if intensity == "MAX":
            # Direct Quantum Handoff
            self.terminal.log("QUANTUM_HANDOFF: Escalating mission to Ultraplan Agent...", "SYSTEM")
            self.quantum_revealer.set_reveal_child(True)
            self.pod_status.update_value("PLANNING")
            
            from shadowcypher.ai.engine import ai_engine
            def _quantum_complete(result):
                GLib.idle_add(self._on_mission_done, result)
                
            ai_engine.execute_quantum_task(
                msg, 
                on_output=lambda x: GLib.idle_add(self.terminal.log, x, "QUANTUM")
            )
            # Since Quantum runs via runner.execute_task, we should ideally trigger _complete
            # For now, let's pulse the status as 'COMPLETE' after a short delay or on stream end
        else:
            hub.orchestrator.execute_query_async(
                msg,
                images=images if images else None,
                callback=_callback,
                on_complete=_complete,
                agent_role=role,
                intensity=intensity,
                history=self.history # Pass the meta-chain history
            )

    def _handle_autonomous_forge(self, text):
        """Trigger PayloadFactory from the AI Bridge."""
        from shadowcypher.modules.payload_factory import PayloadFactory
        self.terminal.log("INITIATING_AUTONOMOUS_FORGE: Scanning for optimal evasion...", "AI")
        
        # Determine LHOST/LPORT from text or fallback
        lhost = "10.0.2.15" # This should ideally be your local IP
        lport = "4444"
        
        def _on_output(line):
            GLib.idle_add(self.terminal.log, line.strip(), "FORGE")
        
        PayloadFactory.generate_evasive_elf(lhost, lport, iterations=5, on_output=_on_output)

    def _handle_autonomous_recon(self, text):
        """Trigger Recon module from the AI Bridge."""
        from shadowcypher.modules.recon import Recon
        self.terminal.log("INITIATING_AUTONOMOUS_RECON_SWEEP...", "AI")
        
        r = Recon()
        # Default target if none provided
        target = "127.0.0.1" 
        r.quick_scan(target, on_output=lambda x: GLib.idle_add(self.terminal.log, x.strip(), "RECON"))

    def _on_mission_done(self, result):
        self.header.set_active(False)
        self.pod_status.set_value("STANDBY")
        self.pod_missions.set_value(str(len(hub.active_missions)))
        if result and not result.startswith("CRITICAL_EXCEPTION"):
            self.terminal.log("MISSION_COMPLETE", "SUCCESS")
        else:
            self.terminal.log(f"MISSION_FAULT: {result}", "ERROR")
