"""Shadow Vault Page — Secure artifact and OSINT management."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from shadowcypher.ui.base_page import BasePage

class ShadowVaultPage(BasePage):
    """Encrypted storage management for stolen intelligence and mission artifacts."""

    def __init__(self):
        super().__init__("\U0001f5c4 Shadow Vault (Encrypted Intel)")
        
        # Vault Header
        label = Gtk.Label()
        label.set_markup("<span size='small' color='#94a3b8'>Access encrypted mission artifacts, exfiltrated credentials, and tactical osint reports.</span>")
        self.workspace.pack_start(label, False, False, 10)

        # Artifact List
        self.store = Gtk.ListStore(str, str, str) # Filename, Type, Timestamp
        
        # Dummy data for UI verification
        self.store.append(["dc_dump_2026.ntds", "NTDS_DUMP", "2026-04-11 20:30"])
        self.store.append(["internal_wiki_export.pdf", "EXFILTRATION", "2026-04-10 14:15"])
        
        self.tree = Gtk.TreeView(model=self.store)
        for i, column_title in enumerate(["Filename", "Type", "Timestamp"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            self.tree.append_column(column)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        scroller.add(self.tree)
        self.workspace.pack_start(scroller, True, True, 0)

        # Actions
        btn_box = Gtk.Box(spacing=10)
        self.workspace.pack_start(btn_box, False, False, 10)
        
        decrypt_btn = self.make_action_btn("Decrypt & View", self._on_decrypt)
        btn_box.pack_start(decrypt_btn, False, False, 0)

        self.build_terminal()

    def _on_decrypt(self, btn):
        selection = self.tree.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            filename = model[treeiter][0]
            self.terminal.log(f"DECRYPTING_ARTIFACT: {filename}...", "VAULT")
            self.terminal.log("RSA_4096_CHALLENGE: SIGNATURE_VERIFIED", "INFO")
            self.terminal.log("ACCESS_GRANTED: Artifact moved to /tmp/shadow_decrypted/", "SUCCESS")
        else:
            self.terminal.log("ERROR: Select an artifact to decrypt.", "ERROR")
