import gi
gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.0")
from gi.repository import Gtk, GLib, Gdk, Pango
import threading
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

from shadowcypher.core.config import config
from shadowcypher.core.logger import logger


def _api(method: str, path: str, api_key: str, body: dict | None = None) -> dict:
    base = getattr(config, "api_base_url", "https://api.shadowcypher.site")
    url = f"{base}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as r:  # nosec B310
        return json.loads(r.read())


def _fmt_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        local = dt.astimezone()
        now = datetime.now(timezone.utc).astimezone()
        if local.date() == now.date():
            return local.strftime("%H:%M")
        return local.strftime("%b %d")
    except Exception:
        return ""


SHADOW_CSS = b"""
.mail-row {
    padding: 10px 14px;
    border-bottom: 1px solid #111;
}
.mail-row:hover { background: #0e0e1e; }
.mail-row.unread label { font-weight: bold; }
.mail-subject { font-size: 13px; color: #e6e6e6; }
.mail-from   { font-size: 11px; color: #888; }
.mail-time   { font-size: 11px; color: #555; }
.mail-header-field { font-size: 12px; color: #94a3b8; }
.mail-toolbar button { background: #0a0a0f; border: 1px solid #222; }
.mail-toolbar button:hover { background: #16162a; border-color: #b44aff; }
.compose-dialog entry { background: #0d0d1a; color: #e6e6e6; border: 1px solid #2a2a3a; }
.compose-dialog textview { background: #0d0d1a; color: #e6e6e6; }
"""


class MailPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

        self._api_key: str = ""
        self._messages: list = []
        self._selected_id: str | None = None
        self._polling = False
        self._poll_thread = None
        self._unread_badge: int = 0

        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(SHADOW_CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), style_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self._load_api_key()
        self._build_ui()
        self._start_polling()

    # ── API key ──────────────────────────────────────────────────────────────

    def _load_api_key(self):
        try:
            key_path = getattr(config, "api_key_path", None)
            if key_path:
                import os
                if os.path.exists(key_path):
                    with open(key_path) as f:
                        self._api_key = f.read().strip()
            if not self._api_key:
                self._api_key = getattr(config, "api_key", "") or ""
        except Exception:
            pass

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Left: inbox list ─────────────────────────────────────────
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        left.set_size_request(280, -1)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.get_style_context().add_class("mail-toolbar")
        toolbar.set_margin_start(8)
        toolbar.set_margin_end(8)
        toolbar.set_margin_top(8)
        toolbar.set_margin_bottom(8)

        compose_btn = Gtk.Button(label="+ Compose")
        compose_btn.connect("clicked", self._on_compose)

        refresh_btn = Gtk.Button(label="⟳")
        refresh_btn.set_tooltip_text("Refresh inbox")
        refresh_btn.connect("clicked", lambda _: self._refresh())

        self._unread_lbl = Gtk.Label(label="")
        self._unread_lbl.get_style_context().add_class("tier-badge")

        toolbar.pack_start(compose_btn, False, False, 0)
        toolbar.pack_start(refresh_btn, False, False, 0)
        toolbar.pack_end(self._unread_lbl, False, False, 0)
        left.pack_start(toolbar, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        left.pack_start(sep, False, False, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True)

        self._inbox_list = Gtk.ListBox()
        self._inbox_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._inbox_list.connect("row-selected", self._on_message_selected)
        scroller.add(self._inbox_list)
        left.pack_start(scroller, True, True, 0)

        # ── Right: message view ──────────────────────────────────────
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        right.set_hexpand(True)

        # Message toolbar
        msg_toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        msg_toolbar.get_style_context().add_class("mail-toolbar")
        msg_toolbar.set_margin_start(10)
        msg_toolbar.set_margin_end(10)
        msg_toolbar.set_margin_top(8)
        msg_toolbar.set_margin_bottom(8)

        self._delete_btn = Gtk.Button(label="🗑 Delete")
        self._delete_btn.set_sensitive(False)
        self._delete_btn.connect("clicked", self._on_delete)

        msg_toolbar.pack_end(self._delete_btn, False, False, 0)
        right.pack_start(msg_toolbar, False, False, 0)

        sep2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        right.pack_start(sep2, False, False, 0)

        msg_scroller = Gtk.ScrolledWindow()
        msg_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        msg_scroller.set_vexpand(True)

        msg_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        msg_vbox.set_margin_start(20)
        msg_vbox.set_margin_end(20)
        msg_vbox.set_margin_top(16)

        # Message header fields
        self._msg_subject = Gtk.Label(label="", xalign=0)
        self._msg_subject.get_style_context().add_class("mail-subject")
        attr_list = Pango.AttrList()
        attr_list.insert(Pango.attr_weight_new(Pango.Weight.BOLD))
        attr_list.insert(Pango.attr_scale_new(1.3))
        self._msg_subject.set_attributes(attr_list)
        self._msg_subject.set_line_wrap(True)
        self._msg_subject.set_selectable(True)

        self._msg_from = Gtk.Label(label="", xalign=0)
        self._msg_from.get_style_context().add_class("mail-header-field")

        self._msg_to = Gtk.Label(label="", xalign=0)
        self._msg_to.get_style_context().add_class("mail-header-field")

        self._msg_date = Gtk.Label(label="", xalign=0)
        self._msg_date.get_style_context().add_class("mail-header-field")

        msg_vbox.pack_start(self._msg_subject, False, False, 0)
        msg_vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 8)
        for lbl in [self._msg_from, self._msg_to, self._msg_date]:
            msg_vbox.pack_start(lbl, False, False, 2)
        msg_vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 12)

        # Body text view
        self._body_view = Gtk.TextView()
        self._body_view.set_editable(False)
        self._body_view.set_cursor_visible(False)
        self._body_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._body_view.set_left_margin(0)
        self._body_view.set_right_margin(0)
        self._body_view.set_pixels_above_lines(2)
        self._body_buffer = self._body_view.get_buffer()

        msg_vbox.pack_start(self._body_view, True, True, 0)
        msg_scroller.add(msg_vbox)
        right.pack_start(msg_scroller, True, True, 0)

        # ── Empty state ──────────────────────────────────────────────
        self._empty_label = Gtk.Label()
        self._empty_label.set_markup(
            "<span color='#444' size='large'>Select a message to read</span>"
        )
        self._empty_label.set_valign(Gtk.Align.CENTER)
        self._empty_label.set_halign(Gtk.Align.CENTER)
        self._empty_label.set_vexpand(True)

        # ── Assemble ─────────────────────────────────────────────────
        self._right_stack = Gtk.Stack()
        self._right_stack.add_named(self._empty_label, "empty")
        self._right_stack.add_named(right, "message")
        self._right_stack.set_visible_child_name("empty")
        self._right_stack.set_hexpand(True)

        vsep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.pack_start(left, False, False, 0)
        self.pack_start(vsep, False, False, 0)
        self.pack_start(self._right_stack, True, True, 0)

        self._show_placeholder()

    def _show_placeholder(self):
        lbl = Gtk.Label()
        lbl.set_markup("<span color='#333'>No messages</span>")
        lbl.set_halign(Gtk.Align.CENTER)
        lbl.set_margin_top(40)
        self._inbox_list.add(lbl)
        lbl.show()

    # ── Polling ──────────────────────────────────────────────────────────────

    def _start_polling(self):
        if not self._api_key:
            return
        self._polling = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self):
        while self._polling:
            try:
                data = _api("GET", "/v1/mail/inbox?limit=50", self._api_key)
                messages = data.get("messages", [])
                GLib.idle_add(self._update_inbox, messages)
            except Exception as e:
                logger.warning("mail", f"inbox poll failed: {e}")
            for _ in range(30):
                if not self._polling:
                    return
                import time
                time.sleep(1)

    def _refresh(self):
        if not self._api_key:
            return
        threading.Thread(target=self._do_refresh, daemon=True).start()

    def _do_refresh(self):
        try:
            data = _api("GET", "/v1/mail/inbox?limit=50", self._api_key)
            messages = data.get("messages", [])
            GLib.idle_add(self._update_inbox, messages)
        except Exception as e:
            logger.warning("mail", f"refresh failed: {e}")

    def _update_inbox(self, messages: list):
        self._messages = messages
        for child in self._inbox_list.get_children():
            self._inbox_list.remove(child)

        if not messages:
            self._show_placeholder()
            self._unread_lbl.set_text("")
            return

        unread = sum(1 for m in messages if not m.get("is_read"))
        self._unread_badge = unread
        self._unread_lbl.set_text(f"{unread} unread" if unread else "")

        for msg in messages:
            row = Gtk.ListBoxRow()
            row.message_id = msg["id"]

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            vbox.get_style_context().add_class("mail-row")
            if not msg.get("is_read"):
                vbox.get_style_context().add_class("unread")

            top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            from_lbl = Gtk.Label(label=msg.get("from_addr", ""), xalign=0)
            from_lbl.get_style_context().add_class("mail-from")
            from_lbl.set_ellipsize(Pango.EllipsizeMode.END)
            from_lbl.set_hexpand(True)

            time_lbl = Gtk.Label(label=_fmt_time(msg.get("received_at", "")))
            time_lbl.get_style_context().add_class("mail-time")

            top_row.pack_start(from_lbl, True, True, 0)
            top_row.pack_end(time_lbl, False, False, 0)

            subject_lbl = Gtk.Label(label=msg.get("subject", "(no subject)"), xalign=0)
            subject_lbl.get_style_context().add_class("mail-subject")
            subject_lbl.set_ellipsize(Pango.EllipsizeMode.END)

            vbox.pack_start(top_row, False, False, 0)
            vbox.pack_start(subject_lbl, False, False, 0)
            row.add(vbox)
            self._inbox_list.add(row)

        self._inbox_list.show_all()
        return False

    # ── Message view ─────────────────────────────────────────────────────────

    def _on_message_selected(self, lb, row):
        if row is None:
            return
        mid = getattr(row, "message_id", None)
        if not mid:
            return
        self._selected_id = mid
        self._delete_btn.set_sensitive(True)
        threading.Thread(target=self._load_message, args=(mid,), daemon=True).start()

    def _load_message(self, mid: str):
        try:
            msg = _api("GET", f"/v1/mail/{mid}", self._api_key)
            GLib.idle_add(self._display_message, msg)
        except Exception as e:
            logger.warning("mail", f"load message failed: {e}")

    def _display_message(self, msg: dict):
        self._msg_subject.set_text(msg.get("subject") or "(no subject)")
        self._msg_from.set_markup(f"<b>From:</b>  {msg.get('from_addr', '')}")
        self._msg_to.set_markup(f"<b>To:</b>    {msg.get('to_addr', '')}")
        date_str = _fmt_time(msg.get("received_at", ""))
        self._msg_date.set_markup(f"<b>Date:</b>  {date_str}")

        body = msg.get("body_text") or _html_to_text(msg.get("body_html") or "") or "(empty)"
        self._body_buffer.set_text(body)

        self._right_stack.set_visible_child_name("message")

        # Update is_read state in inbox list
        for row in self._inbox_list.get_children():
            if getattr(row, "message_id", None) == msg.get("id"):
                child = row.get_child()
                if child:
                    child.get_style_context().remove_class("unread")
        return False

    # ── Delete ───────────────────────────────────────────────────────────────

    def _on_delete(self, _btn):
        if not self._selected_id:
            return
        mid = self._selected_id

        dialog = Gtk.MessageDialog(
            parent=self.get_toplevel(),
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Delete this message?",
        )
        dialog.format_secondary_text("This cannot be undone.")
        resp = dialog.run()
        dialog.destroy()

        if resp == Gtk.ResponseType.OK:
            threading.Thread(target=self._do_delete, args=(mid,), daemon=True).start()

    def _do_delete(self, mid: str):
        try:
            _api("DELETE", f"/v1/mail/{mid}", self._api_key)
            GLib.idle_add(self._after_delete, mid)
        except Exception as e:
            logger.warning("mail", f"delete failed: {e}")

    def _after_delete(self, mid: str):
        self._selected_id = None
        self._delete_btn.set_sensitive(False)
        self._right_stack.set_visible_child_name("empty")
        self._refresh()
        return False

    # ── Compose ──────────────────────────────────────────────────────────────

    def _on_compose(self, _btn):
        dialog = ComposeDialog(parent=self.get_toplevel(), api_key=self._api_key)
        dialog.run()
        dialog.destroy()
        self._refresh()


class ComposeDialog(Gtk.Dialog):
    def __init__(self, parent, api_key: str):
        super().__init__(title="New Message", transient_for=parent, modal=True)
        self._api_key = api_key
        self.set_default_size(560, 420)
        self.get_style_context().add_class("compose-dialog")

        self.add_button("Send", Gtk.ResponseType.OK)
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)

        box = self.get_content_area()
        box.set_spacing(8)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(12)
        box.set_margin_bottom(8)

        grid = Gtk.Grid()
        grid.set_row_spacing(6)
        grid.set_column_spacing(10)

        to_lbl = Gtk.Label(label="To:", xalign=1)
        self._to_entry = Gtk.Entry()
        self._to_entry.set_hexpand(True)
        self._to_entry.set_placeholder_text("recipient@example.com")

        sub_lbl = Gtk.Label(label="Subject:", xalign=1)
        self._sub_entry = Gtk.Entry()
        self._sub_entry.set_hexpand(True)

        grid.attach(to_lbl, 0, 0, 1, 1)
        grid.attach(self._to_entry, 1, 0, 1, 1)
        grid.attach(sub_lbl, 0, 1, 1, 1)
        grid.attach(self._sub_entry, 1, 1, 1, 1)
        box.pack_start(grid, False, False, 0)

        body_scroller = Gtk.ScrolledWindow()
        body_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        body_scroller.set_vexpand(True)

        self._body_view = Gtk.TextView()
        self._body_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._body_view.set_left_margin(8)
        self._body_view.set_right_margin(8)
        self._body_view.set_top_margin(8)
        self._body_buffer = self._body_view.get_buffer()
        body_scroller.add(self._body_view)
        box.pack_start(body_scroller, True, True, 0)

        self._status_lbl = Gtk.Label(label="")
        self._status_lbl.set_halign(Gtk.Align.START)
        box.pack_start(self._status_lbl, False, False, 0)

        box.show_all()

        # Override OK button to send asynchronously
        ok_btn = self.get_widget_for_response(Gtk.ResponseType.OK)
        ok_btn.connect("clicked", self._on_send)

    def _on_send(self, _btn):
        to = self._to_entry.get_text().strip()
        subject = self._sub_entry.get_text().strip()
        body_start = self._body_buffer.get_start_iter()
        body_end = self._body_buffer.get_end_iter()
        text = self._body_buffer.get_text(body_start, body_end, False).strip()

        if not to or not subject:
            self._status_lbl.set_markup("<span color='#f87171'>To and Subject are required.</span>")
            return

        self._status_lbl.set_markup("<span color='#888'>Sending…</span>")
        threading.Thread(target=self._do_send, args=(to, subject, text), daemon=True).start()

    def _do_send(self, to: str, subject: str, text: str):
        try:
            _api("POST", "/v1/mail/send", self._api_key, {"to": to, "subject": subject, "text": text})
            GLib.idle_add(self._send_done, True, "")
        except Exception as e:
            GLib.idle_add(self._send_done, False, str(e))

    def _send_done(self, ok: bool, err: str):
        if ok:
            self._status_lbl.set_markup("<span color='#34d399'>Sent.</span>")
            GLib.timeout_add(1000, self.response, Gtk.ResponseType.OK)
        else:
            self._status_lbl.set_markup(f"<span color='#f87171'>Failed: {err[:80]}</span>")
        return False


# ── Utilities ─────────────────────────────────────────────────────────────────

def _html_to_text(html: str) -> str:
    import re
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    return re.sub(r"\n{3,}", "\n\n", text).strip()
