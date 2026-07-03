"""First-run welcome dialog — lets the user pick a nickname instead of editing JSON."""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango

from shadowcypher.core.config import config
from shadowcypher.core.onboarding import _default_nick, set_nickname


def needs_onboarding() -> bool:
    """True if the user hasn't picked a handle yet."""
    return not config.get("identity", "handle", default="")


def show_welcome(parent=None) -> str:
    """Modal dialog prompting for nickname. Persists via onboarding.set_nickname.

    Returns the chosen nick (never empty — falls back to auto-generated).
    """
    dlg = Gtk.Dialog(title="Welcome to ShadowCypher", parent=parent, flags=0)
    dlg.set_default_size(480, 280)
    dlg.set_modal(True)

    box = dlg.get_content_area()
    box.set_spacing(12)
    box.set_margin_start(20)
    box.set_margin_end(20)
    box.set_margin_top(16)
    box.set_margin_bottom(16)

    title = Gtk.Label()
    title.set_markup("<span size='x-large' weight='bold' color='#38bdf8'>\u26a1 Welcome, Operator</span>")
    title.set_halign(Gtk.Align.START)
    box.pack_start(title, False, False, 0)

    desc = Gtk.Label(
        label=(
            "Choose a handle for your ShadowCypher operator profile.\n"
            "This is the name you'll use on the Sovereign IRC network,\n"
            "in mission tickets, and in audit logs. You can change it later\n"
            "from the Admin tab."
        )
    )
    desc.set_halign(Gtk.Align.START)
    desc.set_line_wrap(True)
    box.pack_start(desc, False, False, 0)

    entry = Gtk.Entry()
    entry.set_placeholder_text("Pick a handle (letters, digits, _ or -)")
    entry.set_text(_default_nick())
    entry.set_max_length(24)
    box.pack_start(entry, False, False, 0)

    hint = Gtk.Label()
    hint.set_markup(
        "<span size='small' color='#64748b'>3\u201324 chars. Uniqueness is per-network, not enforced locally.</span>"
    )
    hint.set_halign(Gtk.Align.START)
    box.pack_start(hint, False, False, 0)

    dlg.add_button("Use This Handle", Gtk.ResponseType.OK)
    dlg.set_default_response(Gtk.ResponseType.OK)
    entry.set_activates_default(True)

    box.show_all()

    chosen = ""
    while True:
        resp = dlg.run()
        raw = entry.get_text().strip()
        candidate = "".join(c for c in raw if c.isalnum() or c in "_-")[:24]
        if len(candidate) >= 3:
            chosen = candidate
            break
        if resp != Gtk.ResponseType.OK:
            chosen = _default_nick()
            break

    dlg.destroy()

    try:
        _cfg = config.writable_config_path()
        set_nickname(config.project_root, chosen, _cfg)
        config.load_from_json(_cfg)
    except Exception:
        pass

    return chosen
