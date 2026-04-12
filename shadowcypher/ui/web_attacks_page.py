import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from shadowcypher.modules.web_attacks import WebAttacks
from shadowcypher.ui.base_page import BasePage


class WebAttacksPage(BasePage):
    def __init__(self):
        super().__init__("\U0001f310 Web Assault (Ffuf & Nuclei)")

        from shadowcypher.ui.components import DataPod

        # Metric Strip
        self.pod_vulns = DataPod("VULNS_FOUND", "0", "cyan")
        self.pod_speed = DataPod("SCAN_SPEED", "NORMAL", "violet")
        self.pod_status = DataPod("ENGINE_STATUS", "IDLE", "amber")

        self.metric_strip.pack_start(self.pod_vulns, True, True, 0)
        self.metric_strip.pack_start(self.pod_speed, True, True, 0)
        self.metric_strip.pack_start(self.pod_status, True, True, 0)

        # Operations Notebook
        notebook = Gtk.Notebook()
        notebook.append_page(self._build_nuclei_tab(), Gtk.Label(label="Nuclei"))
        notebook.append_page(self._build_ffuf_tab(), Gtk.Label(label="Ffuf Fuzzing"))
        self.workspace.pack_start(notebook, False, False, 0)

    def _build_nuclei_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        row = Gtk.Box(spacing=8)
        row.pack_start(Gtk.Label(label="Target URL:"), False, False, 0)
        self.nuclei_target = Gtk.Entry()
        self.nuclei_target.set_placeholder_text("https://target.com")
        self.nuclei_target.set_hexpand(True)
        row.pack_start(self.nuclei_target, True, True, 0)
        box.pack_start(row, False, False, 0)

        row2 = Gtk.Box(spacing=8)
        row2.pack_start(Gtk.Label(label="Tags:"), False, False, 0)
        self.nuclei_tags = Gtk.Entry()
        self.nuclei_tags.set_placeholder_text("cve,misconfig,exposure")
        row2.pack_start(self.nuclei_tags, True, True, 0)

        row2.pack_start(Gtk.Label(label="Severity:"), False, False, 0)
        self.nuclei_sev = Gtk.ComboBoxText()
        for s in ["", "critical", "high", "medium", "low", "info"]:
            self.nuclei_sev.append_text(s)
        self.nuclei_sev.set_active(0)
        row2.pack_start(self.nuclei_sev, False, False, 0)
        box.pack_start(row2, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        btn_row.pack_start(
            self.make_action_btn("\u26a1 Launch Nuclei", self._on_nuclei, "danger-btn"),
            False,
            False,
            0,
        )
        btn_row.pack_start(
            self.make_action_btn("\U0001f504 Update Templates", self._on_nuclei_update),
            False,
            False,
            0,
        )
        box.pack_start(btn_row, False, False, 0)

        return box

    def _build_ffuf_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        row = Gtk.Box(spacing=8)
        row.pack_start(Gtk.Label(label="Target URL:"), False, False, 0)
        self.ffuf_target = Gtk.Entry()
        self.ffuf_target.set_placeholder_text("https://target.com")
        self.ffuf_target.set_hexpand(True)
        row.pack_start(self.ffuf_target, True, True, 0)
        box.pack_start(row, False, False, 0)

        row2 = Gtk.Box(spacing=8)
        row2.pack_start(Gtk.Label(label="Wordlist:"), False, False, 0)
        self.ffuf_wordlist = Gtk.Entry()
        self.ffuf_wordlist.set_text("/usr/share/wordlists/dirb/common.txt")
        self.ffuf_wordlist.set_hexpand(True)
        row2.pack_start(self.ffuf_wordlist, True, True, 0)
        box.pack_start(row2, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        btn_row.pack_start(
            self.make_action_btn("\U0001f50d Directory Fuzz", self._on_ffuf_dir),
            False,
            False,
            0,
        )
        box.pack_start(btn_row, False, False, 0)

        return box

    def _on_nuclei(self, btn):
        target = self.nuclei_target.get_text().strip()
        tags = self.nuclei_tags.get_text().strip()
        sev = self.nuclei_sev.get_active_text().strip()
        self.clear_output(f"Launching Nuclei against {target}...\n\n")
        self.run_job(
            WebAttacks.nuclei_scan(
                target,
                template_tags=tags,
                severity=sev,
                on_output=self.on_output,
                on_complete=self.on_complete,
            )
        )

    def _on_nuclei_update(self, btn):
        self.clear_output("Updating Nuclei Templates...\n\n")
        self.run_job(
            WebAttacks.nuclei_update(
                on_output=self.on_output, on_complete=self.on_complete
            )
        )

    def _on_ffuf_dir(self, btn):
        target = self.ffuf_target.get_text().strip()
        wlist = self.ffuf_wordlist.get_text().strip()
        self.clear_output(f"Launching Ffuf Fuzzing against {target}...\n\n")
        self.run_job(
            WebAttacks.ffuf_dir_fuzz(
                target,
                wordlist=wlist,
                on_output=self.on_output,
                on_complete=self.on_complete,
            )
        )
