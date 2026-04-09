"""Gaming Shadow-Ops — Multi-Platform Asset Discovery & Steam Intelligence."""
import gi
import webbrowser
import threading

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, Pango
from shadowcypher.ui.base_page import BasePage
from shadowcypher.core.logger import logger
from shadowcypher.modules.gaming_osint import scraper


class SteamAuditPage(BasePage):
    """Gaming Shadow-Ops Terminal — Multi-Platform Asset Discovery, Library Analysis & Deal Sniping."""

    def __init__(self):
        super().__init__("GAMING SHADOW-OPS")
        self._build_ui()

    def _build_ui(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.workspace.pack_start(vbox, True, True, 0)

        # ═══ 1. STATS ROW ═══
        stats_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.stat_labels = {}
        for key, title, val, sub in [
            ("LIBRARY", "LOCAL LIBRARY", "—", "Installed Games"),
            ("STORAGE", "DISK USAGE", "—", "Total Size"),
            ("FREE", "FREE GAMES", "—", "Claimable Now"),
            ("DEALS", "ACTIVE DEALS", "—", "On Sale"),
            ("WISHLIST", "WISHLIST DEALS", "—", "Sale Items"),
        ]:
            card = self._stat_card(title, val, sub)
            self.stat_labels[key] = card["value"]
            stats_row.pack_start(card["box"], True, True, 0)
        vbox.pack_start(stats_row, False, False, 0)

        # ═══ 2. CONFIG ROW ═══
        config_row = Gtk.Box(spacing=8)
        config_row.pack_start(Gtk.Label(label="Steam ID:"), False, False, 0)
        self.steam_id_entry = Gtk.Entry()
        self.steam_id_entry.set_placeholder_text("76561198xxxxxxxxx")
        self.steam_id_entry.set_width_chars(22)
        if scraper.steam_id:
            self.steam_id_entry.set_text(scraper.steam_id)
        config_row.pack_start(self.steam_id_entry, False, False, 0)

        config_row.pack_start(Gtk.Label(label="API Key:"), False, False, 0)
        self.api_key_entry = Gtk.Entry()
        self.api_key_entry.set_placeholder_text("Steam Web API key")
        self.api_key_entry.set_visibility(False)
        self.api_key_entry.set_width_chars(20)
        if scraper.steam_api_key:
            self.api_key_entry.set_text(scraper.steam_api_key)
        config_row.pack_start(self.api_key_entry, False, False, 0)

        save_btn = Gtk.Button(label="💾 Save")
        save_btn.get_style_context().add_class("suggested-action")
        save_btn.connect("clicked", self._on_save_config)
        config_row.pack_start(save_btn, False, False, 0)
        vbox.pack_start(config_row, False, False, 0)

        # ═══ 3. ACTION BUTTONS ═══
        btn_row = Gtk.Box(spacing=8)
        actions = [
            ("🔍 Scan Free Games", self._on_scan_free, "suggested-action"),
            ("📚 Sync Library", self._on_sync_library, None),
            ("🔥 Steam Deals", self._on_fetch_deals, None),
            ("💰 Wishlist Deals", self._on_wishlist_deals, None),
            ("🎮 My Profile", self._on_fetch_profile, None),
            ("🔎 Search Store", self._on_search_store, None),
        ]
        for label, handler, style in actions:
            btn = Gtk.Button(label=label)
            if style:
                btn.get_style_context().add_class(style)
            btn.connect("clicked", handler)
            btn_row.pack_start(btn, False, False, 0)
        vbox.pack_start(btn_row, False, False, 0)

        # Search bar (hidden by default, shown on Search Store click)
        self.search_box = Gtk.Box(spacing=8)
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Search Steam Store...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("activate", self._on_search_submit)
        self.search_box.pack_start(self.search_entry, True, True, 0)
        go_btn = Gtk.Button(label="Go")
        go_btn.connect("clicked", self._on_search_submit)
        self.search_box.pack_start(go_btn, False, False, 0)
        self.search_box.set_no_show_all(True)
        vbox.pack_start(self.search_box, False, False, 0)

        # ═══ 4. MULTI-TAB RESULTS ═══
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        tabs = ["🎁 Free Games", "🔥 Specials", "📈 Top Sellers", "🆕 New Releases",
                "💰 Wishlist", "📚 My Library", "🔎 Search"]
        self.lists = {}
        for name in tabs:
            scroller = Gtk.ScrolledWindow()
            scroller.set_min_content_height(400)
            listbox = Gtk.ListBox()
            listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
            listbox.connect("row-activated", self._on_row_activated)
            scroller.add(listbox)
            self.stack.add_titled(scroller, name, name)
            self.lists[name] = listbox

        switcher = Gtk.StackSwitcher()
        switcher.set_stack(self.stack)
        switcher.set_halign(Gtk.Align.CENTER)
        vbox.pack_start(switcher, False, False, 0)
        vbox.pack_start(self.stack, True, True, 0)

        # Status bar
        self.status = Gtk.Label(label="SYSTEM: Standing by. Configure Steam ID + API Key for full features.")
        self.status.get_style_context().add_class("text-muted")
        self.status.set_halign(Gtk.Align.START)
        self.status.set_ellipsize(Pango.EllipsizeMode.END)
        vbox.pack_start(self.status, False, False, 5)

    def _stat_card(self, title, val, subtitle):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        card.get_style_context().add_class("glass-pod")
        card.set_margin_start(3)
        card.set_margin_end(3)
        card.set_margin_top(5)
        card.set_margin_bottom(5)

        lbl_t = Gtk.Label(label=title, xalign=0.5)
        lbl_t.get_style_context().add_class("card-title")
        lbl_v = Gtk.Label(label=val, xalign=0.5)
        lbl_v.get_style_context().add_class("card-value")
        lbl_s = Gtk.Label(label=subtitle, xalign=0.5)
        lbl_s.get_style_context().add_class("text-muted")

        card.pack_start(lbl_t, False, False, 8)
        card.pack_start(lbl_v, False, False, 0)
        card.pack_start(lbl_s, False, False, 8)
        return {"box": card, "value": lbl_v}

    # ═══════════════════════════════════════════════
    # ── Actions ──
    # ═══════════════════════════════════════════════

    def _set_status(self, text):
        GLib.idle_add(self.status.set_text, f"SYSTEM: {text}")

    def _on_save_config(self, btn):
        sid = self.steam_id_entry.get_text().strip()
        key = self.api_key_entry.get_text().strip()
        scraper.set_credentials(steam_api_key=key, steam_id=sid)
        self._set_status(f"Credentials saved. Steam ID: {sid[:8]}... | API Key: {'SET' if key else 'NOT SET'}")

    def _on_sync_library(self, btn):
        self._set_status("Scanning local Steam library manifests...")
        threading.Thread(target=self._worker_sync_library, daemon=True).start()

    def _worker_sync_library(self):
        summary = scraper.get_local_library_summary()
        games = summary["games"]

        def _update():
            self.stat_labels["LIBRARY"].set_text(str(summary["total_games"]))
            self.stat_labels["STORAGE"].set_text(f"{summary['total_size_gb']} GB")
            self._clear_list("📚 My Library")
            for g in games:
                status = "✅ Installed" if g["installed"] else "📦 Registered"
                size = f"{g['size_gb']} GB" if g['size_gb'] > 0 else ""
                self._add_row("📚 My Library", g["name"], f"{status} {size}",
                              f"https://store.steampowered.com/app/{g['app_id']}")
            self.lists["📚 My Library"].show_all()
            self._set_status(f"Library: {summary['total_games']} games, {summary['total_size_gb']} GB total")
            return False
        GLib.idle_add(_update)

    def _on_scan_free(self, btn):
        self._set_status("Deploying multi-platform free game crawler...")
        threading.Thread(target=self._worker_scan_free, daemon=True).start()

    def _worker_scan_free(self):
        data = scraper.fetch_global_assets()
        total = sum(len(v) for v in data.values())

        def _update():
            self._clear_list("🎁 Free Games")
            for platform, items in data.items():
                for item in items:
                    owned = item.get("already_owned", False)
                    score = item.get("score", 0)
                    prefix = f"[{platform}]"
                    owned_tag = " ✅ OWNED" if owned else ""
                    price_tag = ""
                    if item.get("original_price"):
                        price_tag = f" (was ${item['original_price']:.2f})"
                    label = f"{prefix} {item['title']}{price_tag}{owned_tag}"
                    sub = f"⬆ {score}" if score else item.get("source", "")
                    self._add_row("🎁 Free Games", label, sub, item.get("url", ""))

            self.stat_labels["FREE"].set_text(str(total))
            self.lists["🎁 Free Games"].show_all()
            self._set_status(f"Found {total} free/claimable assets across all platforms")
            return False
        GLib.idle_add(_update)

    def _on_fetch_deals(self, btn):
        self._set_status("Fetching live Steam deals & specials...")
        threading.Thread(target=self._worker_deals, daemon=True).start()

    def _worker_deals(self):
        deals = scraper.get_featured_deals()

        def _update():
            # Specials
            self._clear_list("🔥 Specials")
            for item in deals.get("specials", []):
                owned = " ✅" if item["already_owned"] else ""
                linux = " 🐧" if item["linux"] else ""
                self._add_row("🔥 Specials",
                              f"{item['name']}{linux}{owned}",
                              f"-{item['discount_pct']}%  ${item['original_price']:.2f} → ${item['final_price']:.2f}",
                              f"https://store.steampowered.com/app/{item['app_id']}")

            # Top sellers
            self._clear_list("📈 Top Sellers")
            for item in deals.get("top_sellers", []):
                linux = " 🐧" if item["linux"] else ""
                disc = f" -{item['discount_pct']}%" if item["discount_pct"] > 0 else ""
                self._add_row("📈 Top Sellers",
                              f"{item['name']}{linux}",
                              f"${item['final_price']:.2f}{disc}",
                              f"https://store.steampowered.com/app/{item['app_id']}")

            # New releases
            self._clear_list("🆕 New Releases")
            for item in deals.get("new_releases", []):
                linux = " 🐧" if item["linux"] else ""
                self._add_row("🆕 New Releases",
                              f"{item['name']}{linux}",
                              f"${item['final_price']:.2f}",
                              f"https://store.steampowered.com/app/{item['app_id']}")

            total = sum(len(v) for v in deals.values())
            self.stat_labels["DEALS"].set_text(str(total))
            for key in ["🔥 Specials", "📈 Top Sellers", "🆕 New Releases"]:
                self.lists[key].show_all()
            self._set_status(f"Loaded {total} deals from Steam Store")
            return False
        GLib.idle_add(_update)

    def _on_wishlist_deals(self, btn):
        if not scraper.steam_id:
            self._set_status("⚠ Set your Steam ID first to check wishlist deals")
            return
        self._set_status("Scanning wishlist for active deals...")
        threading.Thread(target=self._worker_wishlist, daemon=True).start()

    def _worker_wishlist(self):
        deals = scraper.snipe_wishlist_deals()

        def _update():
            self._clear_list("💰 Wishlist")
            if isinstance(deals, dict) and "error" in deals:
                self._set_status(f"⚠ Wishlist error: {deals['error']}")
                return False

            for item in deals:
                self._add_row("💰 Wishlist",
                              f"{item['name']}",
                              f"-{item['discount_pct']}% → ${item['sale_price']:.2f}  ⭐{item['review_score']}/10",
                              f"https://store.steampowered.com/app/{item['app_id']}")

            self.stat_labels["WISHLIST"].set_text(str(len(deals)))
            self.lists["💰 Wishlist"].show_all()
            self._set_status(f"Found {len(deals)} wishlist items on sale!")
            return False
        GLib.idle_add(_update)

    def _on_fetch_profile(self, btn):
        if not scraper.is_authenticated:
            self._set_status("⚠ Set Steam ID + API Key to view profile")
            return
        self._set_status("Fetching player profile...")
        threading.Thread(target=self._worker_profile, daemon=True).start()

    def _worker_profile(self):
        profile = scraper.get_player_profile()
        owned = scraper.get_owned_games()
        recent = scraper.get_recently_played()

        def _update():
            if "error" in profile:
                self._set_status(f"⚠ Profile error: {profile['error']}")
                return False

            name = profile.get("personaname", "Unknown")
            total = owned.get("total", 0)
            self.stat_labels["LIBRARY"].set_text(str(total))

            # Show owned games in library tab
            self._clear_list("📚 My Library")
            for g in owned.get("games", []):
                hours = g.get("playtime_forever", 0) / 60
                self._add_row("📚 My Library",
                              g.get("name", f"App {g.get('appid', '?')}"),
                              f"{hours:.1f} hrs played",
                              f"https://store.steampowered.com/app/{g.get('appid', '')}")
            self.lists["📚 My Library"].show_all()
            self._set_status(
                f"Profile: {name} | {total} games owned | "
                f"{len(recent)} recently played"
            )
            return False
        GLib.idle_add(_update)

    def _on_search_store(self, btn):
        vis = self.search_box.get_visible()
        self.search_box.set_visible(not vis)
        self.search_box.set_no_show_all(vis)
        if not vis:
            self.search_box.show_all()
            self.search_entry.grab_focus()

    def _on_search_submit(self, widget):
        term = self.search_entry.get_text().strip()
        if not term:
            return
        self._set_status(f"Searching Steam Store: '{term}'...")
        threading.Thread(target=self._worker_search, args=(term,), daemon=True).start()

    def _worker_search(self, term):
        results = scraper.search_store(term)

        def _update():
            self._clear_list("🔎 Search")
            for item in results:
                price = item.get("price", {})
                if isinstance(price, dict):
                    price_str = price.get("final", "Free")
                    if isinstance(price_str, int):
                        price_str = f"${price_str / 100:.2f}"
                else:
                    price_str = "Free"
                linux = " 🐧" if item.get("linux") else ""
                self._add_row("🔎 Search",
                              f"{item['name']}{linux}",
                              price_str,
                              f"https://store.steampowered.com/app/{item['app_id']}")
            self.lists["🔎 Search"].show_all()
            self.stack.set_visible_child_name("🔎 Search")
            self._set_status(f"Found {len(results)} results for '{term}'")
            return False
        GLib.idle_add(_update)

    # ═══════════════════════════════════════════════
    # ── UI Helpers ──
    # ═══════════════════════════════════════════════

    def _clear_list(self, tab):
        lb = self.lists[tab]
        for row in lb.get_children():
            lb.remove(row)

    def _add_row(self, tab, title, subtitle, url=""):
        row = Gtk.ListBoxRow()
        row.set_name(url)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        box.set_margin_start(15)
        box.set_margin_end(15)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        icon = Gtk.Label(label="🎮")
        title_lbl = Gtk.Label(label=title, xalign=0)
        title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        title_lbl.set_max_width_chars(60)

        sub_lbl = Gtk.Label(label=subtitle, xalign=1)
        sub_lbl.get_style_context().add_class("cyan-text")

        claim_lbl = Gtk.Label(label="[ OPEN ]", xalign=1)
        claim_lbl.get_style_context().add_class("text-muted")

        box.pack_start(icon, False, False, 0)
        box.pack_start(title_lbl, True, True, 0)
        box.pack_start(sub_lbl, False, False, 0)
        box.pack_end(claim_lbl, False, False, 0)
        row.add(box)
        self.lists[tab].add(row)

    def _on_row_activated(self, lb, row):
        url = row.get_name()
        if url and url.startswith("http"):
            self._set_status(f"Opening: {url}")
            webbrowser.open(url)
