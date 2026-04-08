import gi
import webbrowser

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk
from shadowcypher.ui.base_page import BasePage
from shadowcypher.core.logger import logger
from shadowcypher.modules.gaming_osint import scraper


class SteamAuditPage(BasePage):
    """Gaming Shadow-Ops Terminal — Multi-Platform Asset Discovery & Library Scans."""

    def __init__(self):
        super().__init__("GAMING SHADOW-OPS")
        self._build_ui()

    def _build_ui(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        vbox.set_margin_top(25)
        vbox.set_margin_start(30)
        vbox.set_margin_end(30)
        self.pack_start(vbox, True, True, 0)

        # 1. Mission Stats Row
        stats_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        self.stat_cards = {
            "CLAIMABLE": self._create_stat_card("CLAIMABLE", "0", "Awaiting Sync"),
            "SYNCED": self._create_stat_card("SYNCED", "SCANNING", "Local Assets"),
            "THREATS": self._create_stat_card("THREATS", "CLEAN", "System Integrity"),
        }
        for card in self.stat_cards.values():
            stats_row.pack_start(card, True, True, 0)
        vbox.pack_start(stats_row, False, False, 0)

        # 2. Action Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)

        self.scan_btn = Gtk.Button(label="\U0001f50e DEPLOY_SHADOW_CRAWLER")
        self.scan_btn.get_style_context().add_class("action-btn")
        self.scan_btn.connect("clicked", self._on_scan_clicked)
        header.pack_start(self.scan_btn, False, False, 0)

        self.sync_btn = Gtk.Button(label="\U0001f504 SYNC_LIBRARY_MANIFEST")
        self.sync_btn.get_style_context().add_class("suggested-action")
        self.sync_btn.connect("clicked", self._on_sync_clicked)
        header.pack_start(self.sync_btn, False, False, 0)

        vbox.pack_start(header, False, False, 0)

        # 3. Multi-Platform Stack
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        platforms = ["Steam", "Epic Games", "GOG", "Global OSINT"]
        self.lists = {p: Gtk.ListBox() for p in platforms}

        for name, list_box in self.lists.items():
            scroller = Gtk.ScrolledWindow()
            scroller.set_min_content_height(450)
            scroller.get_style_context().add_class("glass-pod")
            list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
            list_box.connect("row-activated", self._on_row_activated)
            scroller.add(list_box)
            self.stack.add_titled(scroller, name, name)

        switcher = Gtk.StackSwitcher()
        switcher.set_stack(self.stack)
        switcher.set_halign(Gtk.Align.START)
        vbox.pack_start(switcher, False, False, 0)
        vbox.pack_start(self.stack, True, True, 0)

        self.status = Gtk.Label(label="SYSTEM: Standing by for Global Giveaway Sync.")
        self.status.get_style_context().add_class("text-muted")
        vbox.pack_start(self.status, False, False, 10)

    def _create_stat_card(self, title, val, subtitle):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        card.get_style_context().add_class("glass-pod")
        card.set_margin_start(5)
        card.set_margin_end(5)
        card.set_margin_top(5)
        card.set_margin_bottom(5)

        lbl_t = Gtk.Label(label=title, xalign=0)
        lbl_t.get_style_context().add_class("card-title")
        lbl_v = Gtk.Label(label=val, xalign=0)
        lbl_v.get_style_context().add_class("card-value")
        lbl_s = Gtk.Label(label=subtitle, xalign=0)
        lbl_s.get_style_context().add_class("text-muted")

        card.pack_start(lbl_t, False, False, 15)
        card.pack_start(lbl_v, False, False, 0)
        card.pack_start(lbl_s, False, False, 15)
        return card

    def _on_scan_clicked(self, btn):
        self.status.set_text(
            "SYSTEM: Initializing Multi-Platform Scraper via Tor Bridge..."
        )
        self.scan_btn.set_sensitive(False)
        for lst in self.lists.values():
            for row in lst.get_children():
                lst.remove(row)
        import threading

        threading.Thread(target=self._run_discovery_worker, daemon=True).start()

    def _run_discovery_worker(self):
        try:
            data = scraper.fetch_global_assets()
            GLib.idle_add(self._populate_results, data)
        except Exception as e:
            logger.error("ui", f"Gaming Discovery Failed: {e}")
            GLib.idle_add(self.status.set_text, "SYSTEM_ERROR: Sync cycle aborted.")
            GLib.idle_add(self.scan_btn.set_sensitive, True)

    def _on_sync_clicked(self, btn):
        self.status.set_text(
            "SYSTEM: Scanning local .acf manifests for library synchronization..."
        )
        count = len(scraper.scan_local_library())
        self.stat_cards["SYNCED"].get_children()[1].set_text(str(count))
        self.status.set_text(
            f"SYSTEM: {count} local assets synchronized from Shadow-Library."
        )

    def _on_row_activated(self, lb, row):
        url = row.get_name()
        if url and url.startswith("http"):
            self.status.set_text(f"SYSTEM: Opening asset portal: {url}")
            webbrowser.open(url)

    def _populate_results(self, data):
        mapping = {
            "Steam": data.get("Steam", []),
            "Epic Games": data.get("Epic", []),
            "GOG": data.get("GOG", []),
            "Global OSINT": data.get("Other", []),
        }
        total = 0
        for label, findings in mapping.items():
            target_list = self.lists[label]
            for f in findings:
                target_list.add(self._create_finding_row(f))
                total += 1
        self.stat_cards["CLAIMABLE"].get_children()[1].set_text(str(total))
        self.status.set_text(
            f"SYSTEM: Found {total} unowned critical assets across mission-tiers."
        )
        for lst in self.lists.values():
            lst.show_all()
        self.scan_btn.set_sensitive(True)
        return False

    def _create_finding_row(self, data):
        row = Gtk.ListBoxRow()
        row.set_name(data.get("url", ""))  # Store URL for activation
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        icon = Gtk.Label(label="\U0001f3ae")
        title = Gtk.Label(label=data.get("title", "Asset Discovery"), xalign=0)
        title.get_style_context().add_class("text-bold")
        url_lbl = Gtk.Label(label=" [ CLICK_TO_CLAIM ]", xalign=1)
        url_lbl.get_style_context().add_class("cyan-text")
        box.pack_start(icon, False, False, 0)
        box.pack_start(title, True, True, 0)
        box.pack_end(url_lbl, False, False, 0)
        row.add(box)
        return row
