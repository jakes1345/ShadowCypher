"""First-run welcome dialog — ask user what name they should be called."""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from shadowcypher.core.config import config
from shadowcypher.core.logger import logger
from shadowcypher.core.onboarding import is_valid_name, set_nickname


def needs_onboarding() -> bool:
	"""True if the user hasn't picked a name yet."""
	return not config.get("identity", "handle", default="")


def show_welcome(parent=None) -> str:
	"""Modal dialog asking for operator name. Validates and persists.

	Returns the chosen name. Never empty.
	"""
	dlg = Gtk.Dialog(title="Welcome to ShadowCypher", parent=parent, flags=0)
	dlg.set_default_size(500, 320)
	dlg.set_modal(True)

	box = dlg.get_content_area()
	box.set_spacing(12)
	box.set_margin_start(20)
	box.set_margin_end(20)
	box.set_margin_top(16)
	box.set_margin_bottom(16)

	title = Gtk.Label()
	title.set_markup("<span size='x-large' weight='bold' color='#38bdf8'>⚡ Welcome, Operator</span>")
	title.set_halign(Gtk.Align.START)
	box.pack_start(title, False, False, 0)

	desc = Gtk.Label(
		label="What should people call you?\nChoose a name for your operator profile."
	)
	desc.set_halign(Gtk.Align.START)
	desc.set_line_wrap(True)
	box.pack_start(desc, False, False, 0)

	entry = Gtk.Entry()
	entry.set_placeholder_text("Enter your name")
	entry.set_max_length(32)
	box.pack_start(entry, False, False, 0)

	error_label = Gtk.Label()
	error_label.set_halign(Gtk.Align.START)
	error_label.set_line_wrap(True)
	box.pack_start(error_label, False, False, 0)

	hint = Gtk.Label()
	hint.set_markup(
		"<span size='small' color='#64748b'>2–32 characters. Letters, numbers, spaces, hyphens, underscores.</span>"
	)
	hint.set_halign(Gtk.Align.START)
	box.pack_start(hint, False, False, 0)

	dlg.add_button("Confirm", Gtk.ResponseType.OK)
	dlg.set_default_response(Gtk.ResponseType.OK)
	entry.set_activates_default(True)

	box.show_all()

	chosen = ""
	while True:
		error_label.set_text("")
		resp = dlg.run()

		if resp != Gtk.ResponseType.OK:
			dlg.destroy()
			return "Operator"  # Fallback if canceled

		raw = entry.get_text().strip()
		is_valid, error_msg = is_valid_name(raw)

		if is_valid:
			chosen = raw
			break
		else:
			error_label.set_markup(f"<span color='#ef4444'>{error_msg}</span>")

	dlg.destroy()

	try:
		_cfg = config.writable_config_path()
		set_nickname(config.project_root, chosen, _cfg)
		config.load_from_json(_cfg)
	except Exception as e:
		logger.warning("welcome_dialog", f"Failed to persist nickname '{chosen}': {e}")

	return chosen
