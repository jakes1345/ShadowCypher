"""Credentials page — hydra, john, hashcat attacks UI."""

import os

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from shadowcypher.modules.secret_audit import Credentials
from shadowcypher.ui.base_page import BasePage


class SecretsPage(BasePage):
    """Credential attacks UI — brute force and hash cracking."""

    def __init__(self):
        super().__init__("\U0001f511 Credential Attacks")

        # ── Notebook for different attack types ──
        notebook = Gtk.Notebook()
        notebook.append_page(self._build_hydra_tab(), Gtk.Label(label="Hydra Brute Force"))
        notebook.append_page(self._build_hash_tab(), Gtk.Label(label="Hash Cracking"))
        notebook.append_page(self._build_identify_tab(), Gtk.Label(label="Hash Identify"))
        notebook.append_page(self._build_cred_sprayer_tab(), Gtk.Label(label="Cred Sprayer"))
        notebook.append_page(self._build_deep_breach_tab(), Gtk.Label(label="Deep Breach"))
        self.workspace.pack_start(notebook, False, False, 0)

        self.build_terminal()

        # Stop button at bottom
        stop_box = Gtk.Box()
        stop_box.pack_start(self.build_stop_button(), False, False, 0)
        self.workspace.pack_start(stop_box, False, False, 0)

    def _build_hydra_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        # Target + service
        row1 = Gtk.Box(spacing=8)
        row1.pack_start(Gtk.Label(label="Target:"), False, False, 0)
        self.hydra_target = Gtk.Entry()
        self.hydra_target.set_placeholder_text("IP or hostname")
        self.hydra_target.set_hexpand(True)
        row1.pack_start(self.hydra_target, True, True, 0)

        row1.pack_start(Gtk.Label(label="Service:"), False, False, 0)
        self.hydra_service = Gtk.ComboBoxText()
        for svc in ["ssh", "ftp", "http-get", "http-post-form", "rdp", "smb", "mysql", "postgres", "vnc", "telnet", "pop3", "imap", "smtp"]:
            self.hydra_service.append_text(svc)
        self.hydra_service.set_active(0)
        row1.pack_start(self.hydra_service, False, False, 0)

        row1.pack_start(Gtk.Label(label="Port:"), False, False, 0)
        self.hydra_port = Gtk.Entry()
        self.hydra_port.set_placeholder_text("auto")
        self.hydra_port.set_width_chars(6)
        row1.pack_start(self.hydra_port, False, False, 0)
        box.pack_start(row1, False, False, 0)

        # Username + wordlist
        row2 = Gtk.Box(spacing=8)
        row2.pack_start(Gtk.Label(label="Username:"), False, False, 0)
        self.hydra_user = Gtk.Entry()
        self.hydra_user.set_text("admin")
        self.hydra_user.set_width_chars(15)
        row2.pack_start(self.hydra_user, False, False, 0)

        row2.pack_start(Gtk.Label(label="Wordlist:"), False, False, 0)
        self.hydra_wordlist = Gtk.Entry()
        self.hydra_wordlist.set_placeholder_text("default: rockyou.txt")
        self.hydra_wordlist.set_hexpand(True)
        row2.pack_start(self.hydra_wordlist, True, True, 0)

        wl_btn = Gtk.Button(label="Browse")
        wl_btn.connect("clicked", lambda b: self._browse_file(self.hydra_wordlist))
        row2.pack_start(wl_btn, False, False, 0)
        box.pack_start(row2, False, False, 0)

        btn = self.make_action_btn("\U0001f680 Launch Hydra", self._on_hydra, "danger-btn")
        box.pack_start(btn, False, False, 0)
        return box

    def _build_hash_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        row1 = Gtk.Box(spacing=8)
        row1.pack_start(Gtk.Label(label="Hash:"), False, False, 0)
        self.hash_entry = Gtk.Entry()
        self.hash_entry.set_placeholder_text("Paste hash here or enter hash file path")
        self.hash_entry.set_hexpand(True)
        row1.pack_start(self.hash_entry, True, True, 0)
        box.pack_start(row1, False, False, 0)

        row2 = Gtk.Box(spacing=8)
        row2.pack_start(Gtk.Label(label="Type:"), False, False, 0)
        self.hash_type = Gtk.ComboBoxText()
        for ht in ["md5", "sha1", "sha256", "sha512", "ntlm", "bcrypt", "sha512crypt", "md5crypt", "wpa", "mysql", "kerberos_tgs"]:
            self.hash_type.append_text(ht)
        self.hash_type.set_active(0)
        row2.pack_start(self.hash_type, False, False, 0)

        row2.pack_start(Gtk.Label(label="Tool:"), False, False, 0)
        self.hash_tool = Gtk.ComboBoxText()
        self.hash_tool.append_text("hashcat (GPU)")
        self.hash_tool.append_text("john (CPU)")
        self.hash_tool.set_active(0)
        row2.pack_start(self.hash_tool, False, False, 0)

        row2.pack_start(Gtk.Label(label="Wordlist:"), False, False, 0)
        self.hash_wordlist = Gtk.Entry()
        self.hash_wordlist.set_placeholder_text("default: rockyou.txt")
        self.hash_wordlist.set_hexpand(True)
        row2.pack_start(self.hash_wordlist, True, True, 0)
        box.pack_start(row2, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        btn_row.pack_start(self.make_action_btn("\U0001f513 Crack Hash", self._on_crack, "danger-btn"), False, False, 0)
        btn_row.pack_start(self.make_action_btn("\U0001f4ca Benchmark GPU", self._on_benchmark), False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    def _build_identify_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        row = Gtk.Box(spacing=8)
        row.pack_start(Gtk.Label(label="Hash:"), False, False, 0)
        self.identify_entry = Gtk.Entry()
        self.identify_entry.set_placeholder_text("Paste a hash to identify its type")
        self.identify_entry.set_hexpand(True)
        row.pack_start(self.identify_entry, True, True, 0)

        id_btn = self.make_action_btn("Identify", self._on_identify)
        row.pack_start(id_btn, False, False, 0)
        box.pack_start(row, False, False, 0)
        return box

    def _browse_file(self, entry):
        dialog = Gtk.FileChooserDialog(title="Select file", action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        if dialog.run() == Gtk.ResponseType.OK:
            entry.set_text(dialog.get_filename())
        dialog.destroy()

    def _on_hydra(self, btn):
        target = self.hydra_target.get_text().strip()
        if not target:
            self.clear_output("Enter a target.")
            return
        service = self.hydra_service.get_active_text()
        username = self.hydra_user.get_text().strip() or "admin"
        wordlist = self.hydra_wordlist.get_text().strip() or None
        port = self.hydra_port.get_text().strip()
        extra = f"-s {port}" if port and port.isdigit() else ""

        self.clear_output(f"Hydra {service} attack on {target} as {username}...\n\n")
        self.run_job(Credentials.hydra_attack(
            target, service, username=username, passlist=wordlist,
            extra_args=extra, on_output=self.on_output, on_complete=self.on_complete
        ))

    def _on_crack(self, btn):
        hash_val = self.hash_entry.get_text().strip()
        if not hash_val:
            self.clear_output("Enter a hash or hash file path.")
            return
        hash_type = self.hash_type.get_active_text()
        wordlist = self.hash_wordlist.get_text().strip() or None
        tool = self.hash_tool.get_active_text()

        self.clear_output(f"Cracking {hash_type} with {tool}...\n\n")

        if "hashcat" in tool:
            if os.path.isfile(hash_val):
                self.run_job(Credentials.hashcat_crack(
                    hash_val, hash_type, wordlist, on_output=self.on_output, on_complete=self.on_complete
                ))
            else:
                self.run_job(Credentials.hashcat_crack_string(
                    hash_val, hash_type, wordlist, on_output=self.on_output, on_complete=self.on_complete
                ))
        else:
            if os.path.isfile(hash_val):
                self.run_job(Credentials.john_crack(
                    hash_val, wordlist, on_output=self.on_output, on_complete=self.on_complete
                ))
            else:
                self.run_job(Credentials.john_crack_string(
                    hash_val, on_output=self.on_output, on_complete=self.on_complete
                ))

    def _on_benchmark(self, btn):
        self.clear_output("Running hashcat GPU benchmark...\n\n")
        self.run_job(Credentials.hashcat_benchmark(self.on_output, self.on_complete))

    def _on_identify(self, btn):
        hash_val = self.identify_entry.get_text().strip()
        if not hash_val:
            self.clear_output("Enter a hash to identify.")
            return
        result = Credentials.identify_hash(hash_val)
        self.clear_output(result)

    def _build_deep_breach_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        self.breach_target = Gtk.Entry()
        self.breach_target.set_placeholder_text("Target Email (e.g. ceo@target.com)")
        box.pack_start(self.breach_target, False, False, 0)

        btn = self.make_action_btn("\U0001f50e CORRELATE_BREACH_DATA", self._on_deep_breach, "danger-btn")
        box.pack_start(btn, False, False, 0)
        return box

    def _on_deep_breach(self, btn):
        email = self.breach_target.get_text().strip()
        self.terminal.log(f"INITIATING_DDEEPHAT_BREACH_CORRELATION: {email}", "AI")
        c = Credentials()
        c.deep_leak_correlation(email, on_output=self.on_output)

    # ── Cred Sprayer tab (pure-Python, SSH/FTP/HTTP) ─────────────────────────

    def _build_cred_sprayer_tab(self):
        from shadowcypher.core.stealth import require_stealth
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        row = Gtk.Box(spacing=6)
        row.pack_start(Gtk.Label(label="Target:"), False, False, 0)
        self._cs_target = Gtk.Entry()
        self._cs_target.set_placeholder_text("IP or http://target/login")
        self._cs_target.set_hexpand(True)
        row.pack_start(self._cs_target, True, True, 0)
        row.pack_start(Gtk.Label(label="Service:"), False, False, 0)
        self._cs_service = Gtk.ComboBoxText()
        for s in ["ssh", "ftp", "http-post"]:
            self._cs_service.append_text(s)
        self._cs_service.set_active(0)
        row.pack_start(self._cs_service, False, False, 0)
        box.pack_start(row, False, False, 0)

        row2 = Gtk.Box(spacing=6)
        row2.pack_start(Gtk.Label(label="User:"), False, False, 0)
        self._cs_user = Gtk.Entry()
        self._cs_user.set_placeholder_text("single user (or leave blank)")
        self._cs_user.set_width_chars(14)
        row2.pack_start(self._cs_user, False, False, 0)
        row2.pack_start(Gtk.Label(label="Userlist:"), False, False, 0)
        self._cs_ulist = Gtk.Entry()
        self._cs_ulist.set_placeholder_text("/path/to/users.txt")
        self._cs_ulist.set_hexpand(True)
        row2.pack_start(self._cs_ulist, True, True, 0)
        box.pack_start(row2, False, False, 0)

        row3 = Gtk.Box(spacing=6)
        row3.pack_start(Gtk.Label(label="Passlist:"), False, False, 0)
        self._cs_plist = Gtk.Entry()
        self._cs_plist.set_placeholder_text("/path/to/passwords.txt")
        self._cs_plist.set_hexpand(True)
        row3.pack_start(self._cs_plist, True, True, 0)
        row3.pack_start(Gtk.Label(label="Threads:"), False, False, 0)
        self._cs_threads = Gtk.SpinButton.new_with_range(1, 100, 5)
        self._cs_threads.set_value(10)
        row3.pack_start(self._cs_threads, False, False, 0)
        box.pack_start(row3, False, False, 0)

        btn_row = Gtk.Box(spacing=6)
        btn_row.pack_start(self.make_action_btn("Spray", self._on_cred_sprayer), False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    def _on_cred_sprayer(self, btn):
        from shadowcypher.core.stealth import require_stealth
        target = self._cs_target.get_text().strip()
        plist = self._cs_plist.get_text().strip()
        if not target or not plist:
            self.terminal.log("Target and password list required.", "WARN")
            return
        require_stealth(on_output=self.on_output)
        svc = self._cs_service.get_active_text()
        args = ["-t", target, "-s", svc, "-P", plist]
        user = self._cs_user.get_text().strip()
        ulist = self._cs_ulist.get_text().strip()
        if user:
            args += ["-u", user]
        elif ulist:
            args += ["-U", ulist]
        args += ["--threads", str(int(self._cs_threads.get_value()))]
        self.run_script("auth_tester.py", args)
