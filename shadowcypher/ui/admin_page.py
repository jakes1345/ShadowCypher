"""Admin UI Extension — Embedded directly into ShadowCypher if Master Keys are present."""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.fernet import Fernet
import base64
import os

from shadowcypher.ui.base_page import BasePage
from shadowcypher.core.config import config
from shadowcypher.core.security import hardener
from shadowcypher.core.forensics import registry


class AdminPage(BasePage):
    """The God-Mode tab. Only visible via asymmetric private key presence."""

    def __init__(self):
        super().__init__("\U0001f5dd ADMIN_MASTER_CONTROL")

        from shadowcypher.ui.components import DataPod
        
        # 1. Populate Metrics (Mainframe Status)
        self.pod_uptime = DataPod("CITADEL_UPTIME", "0:00:00", "cyan")
        self.pod_crypt = DataPod("CRYPT_LINK", "ACTIVE", "violet")
        self.pod_auth = DataPod("MASTER_AUTH", "ROOT", "amber")
        
        self.metric_strip.pack_start(self.pod_uptime, True, True, 0)
        self.metric_strip.pack_start(self.pod_crypt, True, True, 0)
        self.metric_strip.pack_start(self.pod_auth, True, True, 0)

        # ── 1. Ticket Decryption Box ──
        frm_decrypt = Gtk.Frame(label="Ticket Decryption Matrix (RSA-OAEP)")
        box_dec = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box_dec.set_margin_start(10)
        box_dec.set_margin_end(10)
        box_dec.set_margin_top(10)
        box_dec.set_margin_bottom(10)

        lbl_in = Gtk.Label(label="Paste the user's Encrypted Ticket (Base64) below:")
        lbl_in.set_halign(Gtk.Align.START)
        box_dec.pack_start(lbl_in, False, False, 0)

        self.buf_in = Gtk.TextBuffer()
        tv_in = Gtk.TextView(buffer=self.buf_in)
        tv_in.set_wrap_mode(Gtk.WrapMode.CHAR)
        tv_in.get_style_context().add_class("terminal-view")
        scroll_in = Gtk.ScrolledWindow()
        scroll_in.set_propagate_natural_width(False)
        scroll_in.set_min_content_height(120)
        scroll_in.add(tv_in)
        box_dec.pack_start(scroll_in, True, True, 0)

        btn_dec = Gtk.Button(label="\U0001f5dd Execute Neural Decryption")
        btn_dec.get_style_context().add_class("danger-btn")
        btn_dec.connect("clicked", self._on_decrypt)
        box_dec.pack_start(btn_dec, False, False, 0)

        frm_decrypt.add(box_dec)
        self.workspace.pack_start(frm_decrypt, True, True, 0)

        # ── 3. Sovereign Spectrum Audit (Node Discovery) ── Moved to Sidebar
        frm_nodes = Gtk.Frame(label="Sovereign Hub Spectrum Audit")
        box_nodes = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box_nodes.set_margin_start(10)
        box_nodes.set_margin_end(10)
        box_nodes.set_margin_top(10)
        box_nodes.set_margin_bottom(10)
        
        self.node_list_box = Gtk.ListBox()
        self.node_list_box.get_style_context().add_class("node-list")
        scroll_nodes = Gtk.ScrolledWindow()
        scroll_nodes.set_min_content_height(250)
        scroll_nodes.add(self.node_list_box)
        box_nodes.pack_start(scroll_nodes, True, True, 0)
        
        btn_refresh = Gtk.Button(label="Synchronize Node Metadata")
        btn_refresh.connect("clicked", self._on_refresh_nodes)
        box_nodes.pack_start(btn_refresh, False, False, 0)
        
        frm_nodes.add(box_nodes)
        self.intel_sidebar.pack_start(frm_nodes, True, True, 0)

        # ── 4. Ghost-Hose Control (Hidden) ──
        frm_ghost = Gtk.Frame(label="Ghost-Hose (High-Entropy Saturation)")
        box_ghost = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box_ghost.set_margin_start(10)
        box_ghost.set_margin_end(10)
        box_ghost.set_margin_top(10)
        box_ghost.set_margin_bottom(10)

        self.ent_target = Gtk.Entry()
        self.ent_target.set_placeholder_text("Target IP:Port")
        box_ghost.pack_start(self.ent_target, True, True, 0)

        self.btn_hose = Gtk.Button(label="Engage Saturation")
        self.btn_hose.connect("clicked", self._on_hose_toggle)
        box_ghost.pack_start(self.btn_hose, False, False, 0)

        frm_ghost.add(box_ghost)
        self.workspace.pack_start(frm_ghost, False, False, 0)

        # Output terminal for Admin tools
        self.build_terminal()

        # ── 4. License Generation Box ──
        frm_gen = Gtk.Frame(label="AES-256 License Generator")
        box_gen = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box_gen.set_margin_start(10)
        box_gen.set_margin_end(10)
        box_gen.set_margin_top(10)
        box_gen.set_margin_bottom(10)

        btn_gen = Gtk.Button(label="\u2699 Forge New License Key")
        btn_gen.get_style_context().add_class("suggested-action")
        btn_gen.connect("clicked", self._on_generate)
        box_gen.pack_start(btn_gen, False, False, 0)

        frm_gen.add(box_gen)
        self.workspace.pack_start(frm_gen, False, False, 0)

        # ── 5. Citadel Emergency Lockdown ── Moved to Sidebar
        frm_lock = Gtk.Frame(label="Wraith Protocol (Emergency)")
        box_lock = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box_lock.set_margin_start(10)
        box_lock.set_margin_end(10)
        box_lock.set_margin_top(10)
        box_lock.set_margin_bottom(10)
        
        btn_wipe = Gtk.Button(label="\u2622 EXECUTE SPECTRE FLASH-WIPE")
        btn_wipe.get_style_context().add_class("destructive-action")
        btn_wipe.connect("clicked", self._on_flash_wipe)
        box_lock.pack_start(btn_wipe, False, False, 0)
        
        lbl_fp = Gtk.Label()
        lbl_fp.set_markup(f"<span size='small' color='gray'>MASTER_FP: {hardener.get_hardware_footprint()[:24]}...</span>")
        box_lock.pack_start(lbl_fp, False, False, 0)
        
        frm_lock.add(box_lock)
        self.intel_sidebar.pack_start(frm_lock, False, False, 0)

        # ── 6. Public Sovereign Bridge ──
        frm_pub = Gtk.Frame(label="Global Sovereign Bridge (Expose Hub)")
        box_pub = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box_pub.set_margin_start(10)
        box_pub.set_margin_end(10)
        box_pub.set_margin_top(10)
        box_pub.set_margin_bottom(10)
        
        self.btn_pub = Gtk.Button(label="Go Public (Cloudflare Tunnel)")
        self.btn_pub.connect("clicked", self._on_go_public)
        box_pub.pack_start(self.btn_pub, False, False, 0)
        
        frm_pub.add(box_pub)
        self.workspace.pack_start(frm_pub, False, False, 0)

        # ── 7. 24/7 Cloud Orchestration (Always-On Hub) ──
        frm_cloud = Gtk.Frame(label="24/7 Cloud Orchestration (Fly.io/VPS)")
        box_cloud = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box_cloud.set_margin_start(10)
        box_cloud.set_margin_end(10)
        box_cloud.set_margin_top(10)
        box_cloud.set_margin_bottom(10)
        
        self.btn_cloud = Gtk.Button(label="Generate 24/7 Deploy Artifacts")
        self.btn_cloud.connect("clicked", self._on_gen_deploy)
        box_cloud.pack_start(self.btn_cloud, False, False, 0)
        
        frm_cloud.add(box_cloud)
        self.workspace.pack_start(frm_cloud, False, False, 0)

        # ── Timers ──
        GLib.timeout_add(1000, self._tick)

    def _tick(self):
        """Update live telemetry."""
        if not self.get_mapped():
            return True
        from shadowcypher.core.hub import hub
        summary = hub.get_tactical_summary()
        self.pod_uptime.set_value(summary["uptime"])
        
        # Throttled node refresh
        if not hasattr(self, "_node_tick_count"): self._node_tick_count = 0
        self._node_tick_count += 1
        if self._node_tick_count >= 5:
            self._on_refresh_nodes(None)
            self._node_tick_count = 0
            
        return True

    def _on_refresh_nodes(self, btn):
        # In a real environment, we'd query the SovereignServer via the internal bus
        # or a local WebSocket. Here we'll simulate the dashboard view.
        for child in self.node_list_box.get_children():
            self.node_list_box.remove(child)
            
        from shadowcypher.core.nexus import nexus
        if nexus:
            for node_id, data in nexus.nodes.items():
                row = Gtk.ListBoxRow()
                box = Gtk.Box(spacing=10)
                box.pack_start(Gtk.Label(label=f"{node_id} ({data['host']})"), True, True, 0)
                
                # De-cloaked info
                info = f"LOCAL_IPS: {','.join(data.get('local_ips', []))} | HW_MAC: {data.get('hw_mac', 'Unknown')}"
                box.pack_start(Gtk.Label(label=info), False, False, 0)
                
                box.pack_start(Gtk.Label(label=f"OS: {data.get('os', 'Unknown')}"), False, False, 0)
                row.add(box)
                self.node_list_box.add(row)
        self.node_list_box.show_all()

    def _on_flash_wipe(self, btn):
        dialog = Gtk.MessageDialog(
            parent=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Confirm Wraith Lockdown?",
        )
        dialog.format_secondary_text("This will purge all ephemeral mission data and lock local vaults.")
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            hardener.execute_flash_wipe()
            self.on_output("[LOCKDOWN] Spectre Flash-Wipe Complete. System isolated.\n")
        dialog.destroy()

    def _on_go_public(self, btn):
        if "Go Public" in btn.get_label():
            hardener.expose_sovereign_hub()
            btn.set_label("Hub Publicly Exposed")
            btn.set_sensitive(False)
            self.on_output("[BRIDGE] Sovereign Hub is now tunneling via Cloudflare. Check logs for URL.\n")
        else:
            pass # implement shutdown if needed

    def _on_gen_deploy(self, btn):
        from shadowcypher.core.deploy import deployer
        if deployer.generate_deploy_artifacts():
            btn.set_label("24/7 Artifacts Ready (\u2705)")
            self.on_output("[DEPLOY] Dockerfile & fly.toml generated. Run 'fly launch' to ignite your cloud hub.\n")
        else:
            self.on_output("[DEPLOY] Error generating artifacts.\n")

    def _on_decrypt(self, btn):
        bounds = self.buf_in.get_bounds()
        b64_ticket = self.buf_in.get_text(bounds[0], bounds[1], True).strip()
        if not b64_ticket:
            return

        try:
            self.clear_output("Locating Offline Master Private Key...\n")
            from shadowcypher.core.identity import identity

            if not identity.is_admin:
                self.on_output("[DENIED] This machine is not the admin node.\n")
                return

            with open(
                os.path.join(config.project_root, "admin_private.pem"), "rb"
            ) as key_file:
                private_key = serialization.load_pem_private_key(
                    key_file.read(), password=None
                )

            self.on_output(
                "Key successfully mounted into RAM. Reversing cipher block...\n\n"
            )

            ciphertext = base64.b64decode(b64_ticket)
            plaintext = private_key.decrypt(
                ciphertext,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
            self.on_output(
                f"══════ DECRYPTED MESSAGE ══════\n{plaintext.decode()}\n═══════════════════════════════\n"
            )

        except Exception as e:
            self.on_output(
                f"\n[FATAL ERROR] Decryption failed: {str(e)}\nEnsure you pasted the correct Base64 string.\n"
            )

    def _on_hose_toggle(self, btn):
        from shadowcypher.modules.ghost_hose import ghost_hose
        target = self.ent_target.get_text()
        if not target or ":" not in target:
            self.on_output("[ERROR] Invalid target. Format: IP:Port\n")
            return
            
        if "Engage" in btn.get_label():
            ip, port = target.split(":")
            ghost_hose.engage(ip, int(port))
            btn.set_label("Terminate Saturation")
            btn.get_style_context().add_class("destructive-action")
            self.on_output(f"[GHOST_HOSE] Saturation active on {target}\n")
        else:
            ghost_hose.terminate()
            btn.set_label("Engage Saturation")
            btn.get_style_context().remove_class("destructive-action")
            self.on_output("[GHOST_HOSE] Saturation terminated.\n")

    def _on_generate(self, btn):
        key = Fernet.generate_key()
        self.clear_output(
            f"====================================\n"
            f"   SHADOWCYPHER LICENSE GENERATOR   \n"
            f"====================================\n\n"
            f"[+] NEW LICENSE KEY FORGED:\n"
            f"\n{key.decode()}\n\n"
            f"Send this exact string to the user to unlock their arsenal."
        )
