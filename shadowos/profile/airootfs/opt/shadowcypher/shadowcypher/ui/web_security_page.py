import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from shadowcypher.modules.web_security import WebSecurity
from shadowcypher.ui.base_page import BasePage


class WebSecurityPage(BasePage):
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
        notebook.append_page(self._build_mhddos_tab(), Gtk.Label(label="MHDDoS (Elite)"))
        notebook.append_page(self._build_sql_venom_tab(), Gtk.Label(label="SQL Venom"))
        notebook.append_page(self._build_dir_buster_tab(), Gtk.Label(label="Dir Buster"))
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

    def _build_mhddos_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        row = Gtk.Box(spacing=8)
        row.pack_start(Gtk.Label(label="Target:"), False, False, 0)
        self.mh_target = Gtk.Entry()
        self.mh_target.set_placeholder_text("https://target.com OR ip:port")
        self.mh_target.set_hexpand(True)
        row.pack_start(self.mh_target, True, True, 0)
        box.pack_start(row, False, False, 0)

        row2 = Gtk.Box(spacing=8)
        row2.pack_start(Gtk.Label(label="Method:"), False, False, 0)
        self.mh_method = Gtk.ComboBoxText()
        for m in ["GET", "POST", "CFB", "CFBUAM", "OVH", "RHEX", "STOMP", "TCP", "UDP", "SYN"]:
            self.mh_method.append_text(m)
        self.mh_method.set_active(0)
        row2.pack_start(self.mh_method, False, False, 0)

        row2.pack_start(Gtk.Label(label="Threads:"), False, False, 0)
        self.mh_threads = Gtk.Entry()
        self.mh_threads.set_text("100")
        self.mh_threads.set_width_chars(6)
        row2.pack_start(self.mh_threads, False, False, 0)

        row2.pack_start(Gtk.Label(label="Duration (s):"), False, False, 0)
        self.mh_duration = Gtk.Entry()
        self.mh_duration.set_text("60")
        self.mh_duration.set_width_chars(6)
        row2.pack_start(self.mh_duration, False, False, 0)
        box.pack_start(row2, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        btn_row.pack_start(
            self.make_action_btn("\U0001f525 Ignite MHDDoS", self._on_mhddos, "danger-btn"),
            False,
            False,
            0,
        )
        box.pack_start(btn_row, False, False, 0)

        return box

    def _on_mhddos(self, btn):
        target = self.mh_target.get_text().strip()
        method = self.mh_method.get_active_text()
        try:
            threads = int(self.mh_threads.get_text().strip() or "100")
            duration = int(self.mh_duration.get_text().strip() or "60")
        except ValueError:
            threads, duration = 100, 60
        
        self.clear_output(f"IGNITING_MHDDoS_STRIKE: {target} [{method}]\n\n")
        self.run_job(
            WebSecurity.mhddos_strike(
                target,
                method=method,
                threads=threads,
                duration=duration,
                on_output=self.on_output
            )
        )

    def _on_nuclei(self, btn):
        target = self.nuclei_target.get_text().strip()
        tags = self.nuclei_tags.get_text().strip()
        sev = self.nuclei_sev.get_active_text().strip()
        self.clear_output(f"Launching Nuclei against {target}...\n\n")
        self.run_job(
            WebSecurity.nuclei_scan(
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
            WebSecurity.nuclei_update(
                on_output=self.on_output, on_complete=self.on_complete
            )
        )

    def _on_ffuf_dir(self, btn):
        target = self.ffuf_target.get_text().strip()
        wlist = self.ffuf_wordlist.get_text().strip()
        self.clear_output(f"Launching Ffuf Fuzzing against {target}...\n\n")
        self.run_job(
            WebSecurity.ffuf_dir_fuzz(
                target,
                wordlist=wlist,
                on_output=self.on_output,
                on_complete=self.on_complete,
            )
        )

    # ── SQL Venom tab (pure-Python SQLi, no sqlmap) ──────────────────────────

    def _build_sql_venom_tab(self):
        from shadowcypher.core.stealth import require_stealth
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        row = Gtk.Box(spacing=6)
        row.pack_start(Gtk.Label(label="URL:"), False, False, 0)
        self._sqv_url = Gtk.Entry()
        self._sqv_url.set_placeholder_text("http://target.com/page?id=1")
        self._sqv_url.set_hexpand(True)
        row.pack_start(self._sqv_url, True, True, 0)
        box.pack_start(row, False, False, 0)

        row2 = Gtk.Box(spacing=6)
        row2.pack_start(Gtk.Label(label="Param:"), False, False, 0)
        self._sqv_param = Gtk.Entry()
        self._sqv_param.set_placeholder_text("id (leave blank = auto)")
        self._sqv_param.set_width_chars(16)
        row2.pack_start(self._sqv_param, False, False, 0)
        self._sqv_dump = Gtk.CheckButton(label="--dump")
        self._sqv_dump.set_active(False)
        self._sqv_dbs = Gtk.CheckButton(label="--dbs")
        self._sqv_dbs.set_active(False)
        row2.pack_start(self._sqv_dump, False, False, 0)
        row2.pack_start(self._sqv_dbs, False, False, 0)
        box.pack_start(row2, False, False, 0)

        btn_row = Gtk.Box(spacing=6)
        btn_row.pack_start(self.make_action_btn("Inject", self._on_sql_venom), False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    def _on_sql_venom(self, btn):
        from shadowcypher.core.stealth import require_stealth
        url = self._sqv_url.get_text().strip()
        if not url:
            self.log("URL required.", "WARN")
            return
        require_stealth(on_output=self.on_output)
        args = ["-u", url]
        p = self._sqv_param.get_text().strip()
        if p:
            args += ["-p", p]
        if self._sqv_dump.get_active():
            args.append("--dump")
        if self._sqv_dbs.get_active():
            args.append("--dbs")
        self.run_script("sql_probe.py", args)

    # ── Dir Buster tab (pure-Python, no feroxbuster/gobuster needed) ─────────

    def _build_dir_buster_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        row = Gtk.Box(spacing=6)
        row.pack_start(Gtk.Label(label="URL:"), False, False, 0)
        self._db_url = Gtk.Entry()
        self._db_url.set_placeholder_text("http://target.com")
        self._db_url.set_hexpand(True)
        row.pack_start(self._db_url, True, True, 0)
        box.pack_start(row, False, False, 0)

        row2 = Gtk.Box(spacing=6)
        row2.pack_start(Gtk.Label(label="Wordlist:"), False, False, 0)
        self._db_wl = Gtk.Entry()
        self._db_wl.set_placeholder_text("(built-in)")
        self._db_wl.set_hexpand(True)
        row2.pack_start(self._db_wl, True, True, 0)
        row2.pack_start(Gtk.Label(label="Ext:"), False, False, 0)
        self._db_ext = Gtk.Entry()
        self._db_ext.set_text("php,html,txt")
        self._db_ext.set_width_chars(16)
        row2.pack_start(self._db_ext, False, False, 0)
        row2.pack_start(Gtk.Label(label="Threads:"), False, False, 0)
        self._db_threads = Gtk.SpinButton.new_with_range(1, 200, 10)
        self._db_threads.set_value(50)
        row2.pack_start(self._db_threads, False, False, 0)
        box.pack_start(row2, False, False, 0)

        btn_row = Gtk.Box(spacing=6)
        btn_row.pack_start(self.make_action_btn("Bust", self._on_dir_buster), False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    def _on_dir_buster(self, btn):
        from shadowcypher.core.stealth import require_stealth
        url = self._db_url.get_text().strip()
        if not url:
            self.log("URL required.", "WARN")
            return
        require_stealth(on_output=self.on_output)
        args = [url]
        wl = self._db_wl.get_text().strip()
        if wl:
            args += ["-w", wl]
        ext = self._db_ext.get_text().strip()
        if ext:
            args += ["-x", ext]
        args += ["-t", str(int(self._db_threads.get_value()))]
        self.run_script("dir_buster.py", args)
