import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

from shadowcypher import __version__


class SupportPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.pack_start(scroll, True, True, 0)

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        container.set_margin_top(32)
        container.set_margin_bottom(32)
        container.set_margin_start(48)
        container.set_margin_end(48)
        scroll.add(container)

        # Header
        header = Gtk.Label()
        header.set_markup(
            f"<span size='xx-large' weight='800' color='#3b82f6'>SUPPORT</span>\n"
            f"<span color='#64748b' size='small'>ShadowCypher v{__version__} — Local-First Security Suite</span>"
        )
        header.set_halign(Gtk.Align.START)
        container.pack_start(header, False, False, 0)

        container.pack_start(Gtk.Separator(), False, False, 0)

        # Quick links
        self._section(container, "QUICK LINKS", [
            ("Documentation",     "https://shadowcypher.site/docs"),
            ("GitHub Repository", "https://github.com/jakes1345/ShadowCypher"),
            ("Report a Bug",      "https://github.com/jakes1345/ShadowCypher/issues/new"),
            ("Web Dashboard",     "https://shadowcypher.site"),
        ])

        # FAQ
        faq = [
            ("App won't launch",
             "Run ./install.sh from the repo root to reinstall dependencies.\n"
             "Make sure python3-gi and gir1.2-gtk-3.0 are installed via apt."),
            ("AI returns no response",
             "Ollama must be running locally (ollama serve).\n"
             "Pull a model first: ollama pull llama3.2"),
            ("Nmap / security tools not found",
             "Install via: sudo apt install nmap nuclei nikto gobuster\n"
             "The app gracefully skips tools that aren't installed."),
            ("Mission never finishes",
             "Check the Ollama model is loaded and responding.\n"
             "Open a terminal and run: ollama run llama3.2"),
            ("How do I update?",
             "git pull && ./install.sh\n"
             "No uninstall needed — the venv is updated in-place."),
        ]

        faq_label = Gtk.Label()
        faq_label.set_markup("<span weight='700' color='#94a3b8' size='small'>FAQ</span>")
        faq_label.set_halign(Gtk.Align.START)
        container.pack_start(faq_label, False, False, 0)

        for q, a in faq:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            box.set_margin_bottom(12)
            qlbl = Gtk.Label()
            qlbl.set_markup(f"<b>{q}</b>")
            qlbl.set_halign(Gtk.Align.START)
            albl = Gtk.Label(label=a)
            albl.set_halign(Gtk.Align.START)
            albl.set_line_wrap(True)
            albl.get_style_context().add_class("dim-label")
            box.pack_start(qlbl, False, False, 0)
            box.pack_start(albl, False, False, 0)
            container.pack_start(box, False, False, 0)

        container.pack_start(Gtk.Separator(), False, False, 0)

        # Keyboard shortcuts
        shortcuts_label = Gtk.Label()
        shortcuts_label.set_markup("<span weight='700' color='#94a3b8' size='small'>KEYBOARD SHORTCUTS</span>")
        shortcuts_label.set_halign(Gtk.Align.START)
        container.pack_start(shortcuts_label, False, False, 0)

        shortcuts = [
            ("Ctrl+Q",       "Quit"),
            ("Ctrl+Shift+T", "Toggle stealth mode"),
            ("F5",           "Refresh current page"),
            ("Ctrl+L",       "Focus AI prompt"),
        ]
        grid = Gtk.Grid()
        grid.set_row_spacing(6)
        grid.set_column_spacing(24)
        for i, (key, desc) in enumerate(shortcuts):
            k = Gtk.Label()
            k.set_markup(f"<span font_family='monospace' color='#3b82f6'>{key}</span>")
            k.set_halign(Gtk.Align.START)
            d = Gtk.Label(label=desc)
            d.set_halign(Gtk.Align.START)
            grid.attach(k, 0, i, 1, 1)
            grid.attach(d, 1, i, 1, 1)
        container.pack_start(grid, False, False, 0)

        self.show_all()

    def _section(self, parent, title, links):
        lbl = Gtk.Label()
        lbl.set_markup(f"<span weight='700' color='#94a3b8' size='small'>{title}</span>")
        lbl.set_halign(Gtk.Align.START)
        parent.pack_start(lbl, False, False, 0)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_bottom(8)
        for text, url in links:
            btn = Gtk.LinkButton.new_with_label(url, text)
            btn.set_halign(Gtk.Align.START)
            box.pack_start(btn, False, False, 0)
        parent.pack_start(box, False, False, 0)
