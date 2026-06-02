"""
Shadow Vault — Encrypted Artifact Storage & Intelligence Crypt.
AES-256-GCM encryption for mission artifacts with integrity verification.
"""

import os
import time
import hashlib
import json

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, Pango

from shadowcypher.ui.base_page import BasePage
from shadowcypher.core.hub import hub
from shadowcypher.core.logger import logger

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


def _file_hash(path: str) -> str:
    """SHA-256 integrity hash."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _human_size(nbytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"


class ShadowVaultPage(BasePage):
    """Encrypted artifact storage with real AES-256-GCM encryption and integrity tracking."""

    def __init__(self):
        super().__init__("🗄 Shadow Vault (Encrypted Intel)")

        # Header
        desc = Gtk.Label()
        desc.set_markup(
            "<span color='#64748b'>Access encrypted mission artifacts, "
            "exfiltrated credentials, and tactical OSINT reports.</span>"
        )
        desc.set_halign(Gtk.Align.START)
        self.workspace.pack_start(desc, False, False, 5)

        # Stats bar
        self.stats_bar = Gtk.Label()
        self.stats_bar.set_halign(Gtk.Align.START)
        self.workspace.pack_start(self.stats_bar, False, False, 5)

        # Artifact TreeView
        # Columns: Filename, Type, Size, Modified, SHA-256, FullPath (hidden)
        self.store = Gtk.ListStore(str, str, str, str, str, str)

        self.tree = Gtk.TreeView(model=self.store)
        self.tree.set_enable_search(True)
        self.tree.set_search_column(0)

        columns = [
            ("Artifact", 0, 280),
            ("Type", 1, 70),
            ("Size", 2, 80),
            ("Modified", 3, 140),
            ("Integrity", 4, 120),
        ]
        for title, idx, width in columns:
            renderer = Gtk.CellRendererText()
            if title == "Integrity":
                renderer.set_property("font", "monospace 10")
            col = Gtk.TreeViewColumn(title, renderer, text=idx)
            col.set_min_width(width)
            col.set_resizable(True)
            col.set_sort_column_id(idx)
            self.tree.append_column(col)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        scroller.add(self.tree)
        self.workspace.pack_start(scroller, True, True, 0)

        # Action buttons
        btn_box = Gtk.Box(spacing=10)
        self.workspace.pack_start(btn_box, False, False, 10)

        scan_btn = self.make_action_btn("🔍 Scan Vault", self._on_scan, "suggested-action")
        btn_box.pack_start(scan_btn, False, False, 0)

        decrypt_btn = self.make_action_btn("🔓 Decrypt & View", self._on_decrypt)
        btn_box.pack_start(decrypt_btn, False, False, 0)

        encrypt_btn = self.make_action_btn("🔒 Encrypt File", self._on_encrypt)
        btn_box.pack_start(encrypt_btn, False, False, 0)

        delete_btn = self.make_action_btn("🗑 Purge", self._on_purge)
        btn_box.pack_start(delete_btn, False, False, 0)

        export_btn = self.make_action_btn("📤 Export Manifest", self._on_export_manifest)
        btn_box.pack_start(export_btn, False, False, 0)

        self.build_terminal()
        self._on_scan(None)

    def _get_vault_key(self) -> bytes:
        """Derive vault encryption key from env or identity."""
        secret = os.environ.get("SHADOWCYPHER_VAULT_KEY", "default_vault_key_change_me")
        return hashlib.sha256(secret.encode()).digest()

    def _on_scan(self, btn):
        """Scan findings directory and index all artifacts."""
        self.store.clear()
        findings_dir = hub.findings_dir
        total_size = 0
        count = 0

        if not os.path.exists(findings_dir):
            os.makedirs(findings_dir, exist_ok=True)
            self.terminal.log(f"VAULT: Created findings directory: {findings_dir}", "WARN")

        for root, dirs, files in os.walk(findings_dir):
            for f in sorted(files):
                path = os.path.join(root, f)
                try:
                    stats = os.stat(path)
                    ts = time.strftime('%Y-%m-%d %H:%M', time.localtime(stats.st_mtime))
                    size = stats.st_size
                    total_size += size

                    # Determine type
                    ext = f.rsplit(".", 1)[-1].upper() if "." in f else "DATA"
                    if f.endswith(".enc"):
                        ext = "🔒 ENC"
                    elif ext in ("JSON", "XML", "CSV"):
                        ext = f"📊 {ext}"
                    elif ext in ("TXT", "LOG", "MD"):
                        ext = f"📄 {ext}"
                    elif ext in ("PNG", "JPG", "BMP"):
                        ext = f"🖼 {ext}"
                    elif ext in ("PY", "SH", "GO"):
                        ext = f"⚙ {ext}"

                    integrity = _file_hash(path)
                    # Show relative path from findings_dir
                    rel_path = os.path.relpath(path, findings_dir)
                    self.store.append([rel_path, ext, _human_size(size), ts, integrity, path])
                    count += 1
                except Exception:
                    pass

        self.stats_bar.set_markup(
            f"<span color='#64748b'>{count} artifacts | "
            f"{_human_size(total_size)} total | "
            f"Crypto: {'AES-256-GCM' if HAS_CRYPTO else 'UNAVAILABLE'}</span>"
        )
        self.terminal.log(f"VAULT_SYNC: {count} artifacts indexed ({_human_size(total_size)})", "SUCCESS")

    def _get_selected_path(self):
        selection = self.tree.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is None:
            self.terminal.log("Select an artifact first.", "ERROR")
            return None, None
        return model[treeiter][0], model[treeiter][5]

    def _on_decrypt(self, btn):
        """Decrypt and display artifact contents."""
        name, path = self._get_selected_path()
        if not path:
            return

        self.terminal.log(f"ACCESSING: {name}...", "VAULT")

        try:
            with open(path, "rb") as f:
                raw = f.read()

            # Check if encrypted (our format: first 12 bytes = nonce)
            if path.endswith(".enc") and HAS_CRYPTO and len(raw) > 12:
                key = self._get_vault_key()
                nonce = raw[:12]
                ct = raw[12:]
                aesgcm = AESGCM(key)
                plaintext = aesgcm.decrypt(nonce, ct, None)
                self.terminal.log("AES-256-GCM DECRYPTION: SUCCESS", "SUCCESS")
            else:
                plaintext = raw

            # Display
            preview = plaintext[:4096]
            try:
                text = preview.decode("utf-8", errors="replace")
            except Exception:
                text = preview.hex()

            self.terminal.log(f"{'='*60}", "INFO")
            for line in text.split("\n")[:100]:
                self.terminal.log(line, "INFO")
            self.terminal.log(f"{'='*60}", "INFO")
            self.terminal.log(f"ACCESS_GRANTED: {name} ({len(plaintext)} bytes)", "SUCCESS")

        except Exception as e:
            self.terminal.log(f"DECRYPTION_ERROR: {e}", "ERROR")

    def _on_encrypt(self, btn):
        """Encrypt the selected artifact in-place using AES-256-GCM."""
        name, path = self._get_selected_path()
        if not path:
            return

        if not HAS_CRYPTO:
            self.terminal.log("CRYPTO UNAVAILABLE: pip install cryptography", "ERROR")
            return

        if path.endswith(".enc"):
            self.terminal.log("Already encrypted.", "WARN")
            return

        try:
            with open(path, "rb") as f:
                plaintext = f.read()

            key = self._get_vault_key()
            nonce = os.urandom(12)
            aesgcm = AESGCM(key)
            ct = aesgcm.encrypt(nonce, plaintext, None)

            enc_path = path + ".enc"
            with open(enc_path, "wb") as f:
                f.write(nonce + ct)

            # Remove original
            os.remove(path)
            self.terminal.log(f"ENCRYPTED: {name} -> {os.path.basename(enc_path)}", "SUCCESS")
            self._on_scan(None)  # Refresh

        except Exception as e:
            self.terminal.log(f"ENCRYPTION_ERROR: {e}", "ERROR")

    def _on_purge(self, btn):
        """Securely delete an artifact (overwrite then unlink)."""
        name, path = self._get_selected_path()
        if not path:
            return

        try:
            # Overwrite with random data before deletion
            size = os.path.getsize(path)
            with open(path, "wb") as f:
                f.write(os.urandom(size))
            os.remove(path)
            self.terminal.log(f"PURGED: {name} ({size} bytes overwritten + unlinked)", "SUCCESS")
            self._on_scan(None)
        except Exception as e:
            self.terminal.log(f"PURGE_ERROR: {e}", "ERROR")

    def _on_export_manifest(self, btn):
        """Export a JSON manifest of all vault contents."""
        manifest = []
        for row in self.store:
            manifest.append({
                "file": row[0],
                "type": row[1],
                "size": row[2],
                "modified": row[3],
                "integrity": row[4],
            })

        manifest_path = os.path.join(hub.findings_dir, "vault_manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        self.terminal.log(f"MANIFEST EXPORTED: {manifest_path} ({len(manifest)} entries)", "SUCCESS")
