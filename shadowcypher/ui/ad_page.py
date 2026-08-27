"""Active Directory pivot and lateral movement page."""

import gi

gi.require_version("Gtk", "3.0")
import threading

from gi.repository import Gtk

from shadowcypher.ui.base_page import BasePage
from shadowcypher.ui.components import DataPod


class AdPage(BasePage):
    """AD lateral movement — Kerberoast, SMB relay, CrackMapExec, tunnels."""

    def __init__(self):
        super().__init__("🏰 AD Pivot")
        self.pod_domain = DataPod("Domain", "—", "cyan")
        self.pod_dc = DataPod("DC", "—", "violet")
        self.pod_tickets = DataPod("Tickets", "0", "amber")
        for p in [self.pod_domain, self.pod_dc, self.pod_tickets]:
            self.metric_strip.pack_start(p, True, True, 0)

        self._build_ui()

    def _build_ui(self):
        nb = Gtk.Notebook()
        nb.append_page(self._build_target_tab(), Gtk.Label(label="Target"))
        nb.append_page(self._build_kerberos_tab(), Gtk.Label(label="Kerberos"))
        nb.append_page(self._build_smb_tab(), Gtk.Label(label="SMB / Relay"))
        nb.append_page(self._build_cme_tab(), Gtk.Label(label="CrackMapExec"))
        nb.append_page(self._build_pivot_tab(), Gtk.Label(label="Pivot Tunnel"))
        self.workspace.pack_start(nb, True, True, 0)

    # ── Shared target fields ──────────────────────────────────────────────────

    def _build_target_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_property("margin", 15)

        desc = Gtk.Label(xalign=0)
        desc.set_markup("<span color='#94a3b8'>Set domain and DC IP — used by all tabs below.</span>")
        box.pack_start(desc, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)

        labels = ["Domain", "DC IP", "Username", "Password / Hash", "Output file"]
        self._target_entries = {}
        placeholders = ["corp.local", "192.168.1.10", "administrator", "Password1 or NTLM hash", "findings/kerberoast.txt"]

        for i, (lbl, ph) in enumerate(zip(labels, placeholders, strict=False)):
            k = Gtk.Label(label=lbl + ":", xalign=0)
            entry = Gtk.Entry()
            entry.set_placeholder_text(ph)
            if "Password" in lbl:
                entry.set_visibility(False)
                entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
            grid.attach(k, 0, i, 1, 1)
            grid.attach(entry, 1, i, 1, 1)
            self._target_entries[lbl] = entry

        box.pack_start(grid, False, False, 0)

        save_btn = Gtk.Button(label="Save Target Config")
        save_btn.get_style_context().add_class("suggested-action")
        save_btn.connect("clicked", self._on_save_target)
        box.pack_start(save_btn, False, False, 0)

        from shadowcypher.ui.components import TacticalTerminal
        self._ad_terminal = TacticalTerminal(height=180)
        box.pack_start(self._ad_terminal, True, True, 0)
        return box

    def _get(self, key, default=""):
        return self._target_entries[key].get_text().strip() or default

    def _on_save_target(self, btn):
        domain = self._get("Domain")
        dc = self._get("DC IP")
        if domain:
            self.pod_domain.set_value(domain)
        if dc:
            self.pod_dc.set_value(dc)
        self.log(f"Target: {domain} @ {dc}", "INFO")

    # ── Kerberos tab ──────────────────────────────────────────────────────────

    def _build_kerberos_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_property("margin", 15)

        frm = Gtk.Frame(label="Kerberoasting")
        bx = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        bx.set_property("margin", 10)
        bx.pack_start(Gtk.Label(label="Requests TGS tickets for SPNs — hash extracted for offline cracking.", xalign=0), False, False, 0)
        btn = self.make_action_btn("🎣 Kerberoast", self._on_kerberoast)
        bx.pack_start(btn, False, False, 0)
        frm.add(bx)
        box.pack_start(frm, False, False, 0)

        frm2 = Gtk.Frame(label="AS-REP Roasting")
        bx2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        bx2.set_property("margin", 10)
        bx2.pack_start(Gtk.Label(label="Target accounts with Kerberos pre-auth disabled.", xalign=0), False, False, 0)
        btn2 = self.make_action_btn("🔓 AS-REP Roast", self._on_asrep)
        bx2.pack_start(btn2, False, False, 0)
        frm2.add(bx2)
        box.pack_start(frm2, False, False, 0)

        return box

    def _on_kerberoast(self, btn):
        from shadowcypher.modules.ad_pivot import ADPivot
        domain = self._get("Domain", "corp.local")
        dc = self._get("DC IP", "")
        out = self._get("Output file", "findings/kerberoast.txt")
        if not dc:
            self.log("Set DC IP in the Target tab first.", "ERROR")
            return
        self.log(f"Kerberoasting {domain} via {dc}...", "PIVOT")
        threading.Thread(
            target=lambda: ADPivot.kerberoast(domain, dc, output_file=out, on_output=self.on_output),
            daemon=True
        ).start()
        self.pod_tickets.set_value("?")

    def _on_asrep(self, btn):
        domain = self._get("Domain", "corp.local")
        dc = self._get("DC IP", "")
        if not dc:
            self.log("Set DC IP in the Target tab first.", "ERROR")
            return
        self.run_mission(f"AS-REP roasting attack on {domain} domain controller {dc}")

    # ── SMB / Relay tab ───────────────────────────────────────────────────────

    def _build_smb_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_property("margin", 15)

        frm = Gtk.Frame(label="SMB Relay (Responder + ntlmrelayx)")
        bx = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        bx.set_property("margin", 10)

        iface_row = Gtk.Box(spacing=8)
        iface_row.pack_start(Gtk.Label(label="Interface:"), False, False, 0)
        self._iface_entry = Gtk.Entry()
        self._iface_entry.set_placeholder_text("eth0")
        self._iface_entry.set_width_chars(10)
        iface_row.pack_start(self._iface_entry, False, False, 0)
        bx.pack_start(iface_row, False, False, 0)

        target_row = Gtk.Box(spacing=8)
        target_row.pack_start(Gtk.Label(label="Target list file:"), False, False, 0)
        self._relay_targets = Gtk.Entry()
        self._relay_targets.set_placeholder_text("targets.txt")
        target_row.pack_start(self._relay_targets, True, True, 0)
        bx.pack_start(target_row, False, False, 0)

        btn = self.make_action_btn("⚡ Start SMB Relay", self._on_smb_relay, "destructive-action")
        bx.pack_start(btn, False, False, 0)
        frm.add(bx)
        box.pack_start(frm, False, False, 0)

        return box

    def _on_smb_relay(self, btn):
        from shadowcypher.modules.ad_pivot import ADPivot
        iface = self._iface_entry.get_text().strip() or "eth0"
        targets = self._relay_targets.get_text().strip() or "targets.txt"
        self.log(f"Starting SMB relay on {iface}...", "PIVOT")
        threading.Thread(
            target=lambda: ADPivot.smb_relay_start([targets], interface=iface, on_output=self.on_output),
            daemon=True
        ).start()

    # ── CrackMapExec tab ──────────────────────────────────────────────────────

    def _build_cme_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_property("margin", 15)

        proto_row = Gtk.Box(spacing=8)
        proto_row.pack_start(Gtk.Label(label="Protocol:"), False, False, 0)
        self._cme_proto = Gtk.ComboBoxText()
        for p in ["smb", "winrm", "rdp", "ssh", "ldap", "mssql"]:
            self._cme_proto.append(p, p.upper())
        self._cme_proto.set_active(0)
        proto_row.pack_start(self._cme_proto, False, False, 0)
        box.pack_start(proto_row, False, False, 0)

        actions = [
            ("🔍 Enumerate Shares", self._on_cme_shares),
            ("👥 List Users", self._on_cme_users),
            ("🔑 Pass-the-Hash", self._on_cme_pth),
            ("📋 Dump SAM", self._on_cme_sam),
            ("🧠 Dump LSA", self._on_cme_lsa),
        ]
        flow = Gtk.FlowBox()
        flow.set_max_children_per_line(3)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        for label, handler in actions:
            flow.add(self.make_action_btn(label, handler))
        box.pack_start(flow, False, False, 0)

        return box

    def _cme_run(self, extra_args=""):
        from shadowcypher.modules.ad_pivot import ADPivot
        target = self._get("DC IP", "")
        domain = self._get("Domain", "")
        user = self._get("Username", "")
        pwd = self._get("Password / Hash", "")
        proto = self._cme_proto.get_active_text() or "smb"
        if not target:
            self.log("Set DC IP in the Target tab first.", "ERROR")
            return
        threading.Thread(
            target=lambda: ADPivot.crackmapexec_scan(
                target, protocol=proto, domain=domain, user=user, password=pwd,
                on_output=self.on_output
            ),
            daemon=True
        ).start()

    def _on_cme_shares(self, btn): self._cme_run("--shares")
    def _on_cme_users(self, btn): self._cme_run("--users")
    def _on_cme_pth(self, btn): self._cme_run()
    def _on_cme_sam(self, btn): self._cme_run("--sam")
    def _on_cme_lsa(self, btn): self._cme_run("--lsa")

    # ── Pivot Tunnel tab ──────────────────────────────────────────────────────

    def _build_pivot_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_property("margin", 15)

        frm = Gtk.Frame(label="SOCKS5 Pivot Tunnel")
        bx = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        bx.set_property("margin", 10)

        port_row = Gtk.Box(spacing=8)
        port_row.pack_start(Gtk.Label(label="Local SOCKS port:"), False, False, 0)
        self._pivot_port = Gtk.SpinButton()
        self._pivot_port.set_adjustment(Gtk.Adjustment(value=1080, lower=1024, upper=65535, step_increment=1))
        port_row.pack_start(self._pivot_port, False, False, 0)
        bx.pack_start(port_row, False, False, 0)

        btn = self.make_action_btn("🌀 Setup Pivot Tunnel", self._on_pivot)
        bx.pack_start(btn, False, False, 0)

        hint = Gtk.Label(xalign=0)
        hint.set_markup("<span size='small' color='#64748b'>Set proxychains to use 127.0.0.1:PORT after establishing the tunnel.</span>")
        hint.set_line_wrap(True)
        bx.pack_start(hint, False, False, 0)

        frm.add(bx)
        box.pack_start(frm, False, False, 0)
        return box

    def _on_pivot(self, btn):
        from shadowcypher.modules.ad_pivot import ADPivot
        target = self._get("DC IP", "")
        port = int(self._pivot_port.get_value())
        if not target:
            self.log("Set DC IP in the Target tab first.", "ERROR")
            return
        self.log(f"Setting up SOCKS5 pivot → {target}:{port}...", "PIVOT")
        threading.Thread(
            target=lambda: ADPivot.setup_pivot_tunnel(target, local_port=port, on_output=self.on_output),
            daemon=True
        ).start()
