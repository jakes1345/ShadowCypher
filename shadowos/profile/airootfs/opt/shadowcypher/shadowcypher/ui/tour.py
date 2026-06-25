"""
ShadowCypher interactive tour guide.

A bottom-anchored panel that slides up, navigates the user through the key
pages, and explains what each one does. Triggered automatically on first
launch (after nickname setup) and accessible any time via a sidebar button.

No popups, no focus steal — the user can see and interact with the page
being described while the tour panel sits at the bottom.
"""

from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, Pango
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class TourStep:
    page: str          # maps to app._switch_to_page()
    title: str
    body: str
    icon: str = ""
    is_final: bool = False


TOUR_STEPS: list[TourStep] = [
    TourStep(
        page="Central Command HUD",
        icon="📊",
        title="Command Center",
        body=(
            "This is home base. Live CPU, RAM, and network gauges update every 1.5 seconds. "
            "The mission feed shows what every active tool is doing. "
            "Type a natural language command in the AI terminal at the bottom — "
            "'scan my network', 'am I anonymous?', 'engage ghost mode' — and it executes."
        ),
    ),
    TourStep(
        page="AI Assistant",
        icon="🤖",
        title="Local AI — Zero Cloud",
        body=(
            "Ollama runs entirely on your machine. Your prompts never leave. No API keys, "
            "no rate limits, no logs on someone else's server. Switch models on the fly — "
            "Gemma, LLaMA, DeepSeek, Mistral, Phi. Quantum-Core mode forces step-by-step "
            "reasoning for complex analysis tasks."
        ),
    ),
    TourStep(
        page="Network Scanner",
        icon="🌐",
        title="See Everything on Your Network",
        body=(
            "Discovers every device, fingerprints OS, maps open ports, flags dangerous "
            "services like Telnet, SMB, or TR-069. Run this first whenever you're on an "
            "unfamiliar network. Results feed directly into the forensic registry "
            "so other modules can correlate against them."
        ),
    ),
    TourStep(
        page="Guardian",
        icon="🛡",
        title="24/7 Network Watch",
        body=(
            "Install the lightweight Guardian agent on any machine on your LAN and it watches "
            "continuously. Alerts you the instant a new device joins, ARP spoofing is detected, "
            "your router exposes a management port, or a CVE matches hardware you own. "
            "Push notifications hit your phone in real time."
        ),
    ),
    TourStep(
        page="Ghost Mode",
        icon="👻",
        title="Go Dark — 9 Layers at Once",
        body=(
            "One command: Tor transparent redirect, iptables kill-switch, MAC randomization, "
            "hostname neutralization, timezone → UTC, DNS lockdown, RAM-only workspace, "
            "log suppression, and Hysteria2 QUIC transport (if configured). "
            "Disengage restores every setting exactly as it was. "
            "Shadow Audit scores your anonymity chain and flags any leaks."
        ),
    ),
    TourStep(
        page="Intelligence Center",
        icon="✨",
        title="OSINT — Map Your Target",
        body=(
            "Username enumeration across 300+ platforms via Sherlock. WHOIS, DNS records "
            "(A, AAAA, MX, NS, TXT, SOA), SSL certificate inspection, reverse IP, "
            "infrastructure mapping. Everything lands in the local forensic database "
            "and cross-references against CVEs and prior scan results automatically."
        ),
    ),
    TourStep(
        page="Vuln Scanner",
        icon="🎯",
        title="Find the Holes Before Someone Else Does",
        body=(
            "Nuclei scans with the full Emerging Threats ruleset — severity filtered, "
            "tag targeted. Results are cross-referenced with ExploitDB via SearchSploit "
            "so you see exploitability immediately, not just a CVE number. "
            "Exportable directly into a ShadowScript mission."
        ),
    ),
    TourStep(
        page="Web Security",
        icon="🕵",
        title="Offensive Testing Suite",
        body=(
            "SQL injection, XSS, SSRF, IDOR, directory fuzzing with ffuf, credential "
            "brute-force via Hydra, Hashcat GPU cracking, Aircrack-ng for wireless. "
            "AI-assisted payload generation through DeepHat Apex. "
            "All of this is for authorized targets. That legal responsibility is yours."
        ),
    ),
    TourStep(
        page="Credentials Vault",
        icon="🔑",
        title="Encrypted Local Vault",
        body=(
            "AES-256-GCM encryption with Argon2id key derivation (200k iterations). "
            "Stores secrets, API keys, passwords, certificates. Nothing syncs, "
            "nothing phones home, nothing is stored in plaintext. "
            "RSA-OAEP asymmetric tickets for admin-to-user secure communication."
        ),
    ),
    TourStep(
        page="Community Chat",
        icon="💬",
        title="Encrypted P2P Chat",
        body=(
            "X25519 ECDH ephemeral key exchange on every session gives forward secrecy — "
            "compromise one session and past sessions stay private. "
            "AES-256-GCM encrypted at rest. Zero message persistence on the server. "
            "Connects to both the Sovereign hub and external IRC (Libera)."
        ),
    ),
    TourStep(
        page="Emergency Wipe",
        icon="☢",
        title="Emergency Lockdown",
        body=(
            "If things go sideways: Flash Wipe purges session keys, destroys "
            "forensic artifacts, kills every active process, and scrubs logs — all in one "
            "action. Irreversible by design. The panic button is there for when you need "
            "it to be there. Use it with full intention."
        ),
    ),
    TourStep(
        page="Central Command HUD",
        icon="⚡",
        title="You're set. Go operate.",
        body=(
            "That's ShadowCypher. Everything connects: scan the network → AI explains the results → "
            "Guardian alerts your phone → Ghost Mode cloaks the engagement → "
            "Wraith cleans up after. "
            "Explore the sidebar at your own pace. The full arsenal is there."
        ),
        is_final=True,
    ),
]


class TourPanel(Gtk.Revealer):
    """
    Slide-up tour panel. Add this to the bottom of the main window's vbox.
    Call start() to begin the tour, hide() when done.

    navigate_cb: callable(page_name: str) — should call app._switch_to_page
    """

    def __init__(
        self,
        navigate_cb: Callable[[str], None],
        on_finish: Optional[Callable] = None,
    ):
        super().__init__()
        self.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.set_transition_duration(280)
        self.set_reveal_child(False)

        self._navigate = navigate_cb
        self._on_finish = on_finish
        self._step = 0
        self._steps = TOUR_STEPS
        self._total = len(self._steps)

        self.add(self._build_panel())

    # ── Public API ──────────────────────────────────────────────────────────

    def start(self) -> None:
        self._step = 0
        self.set_reveal_child(True)
        self._apply_step()

    def is_active(self) -> bool:
        return self.get_reveal_child()

    # ── Panel construction ───────────────────────────────────────────────────

    def _build_panel(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Separator line at top
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        outer.pack_start(sep, False, False, 0)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.get_style_context().add_class("tour-panel")

        # Apply dark background via inline CSS
        css = Gtk.CssProvider()
        css.load_from_data(b"""
            .tour-panel {
                background-color: #0c111b;
                border-top: 1px solid rgba(180,74,255,0.3);
                padding: 0;
            }
            .tour-progress-bar progress {
                background-color: #b44aff;
                min-height: 3px;
            }
            .tour-progress-bar trough {
                background-color: rgba(180,74,255,0.12);
                min-height: 3px;
            }
            .tour-title {
                font-size: 1.05rem;
                font-weight: 700;
                color: #b44aff;
            }
            .tour-body {
                font-size: 0.88rem;
                color: #cbd5e1;
                line-height: 1.6;
            }
            .tour-step-label {
                font-family: monospace;
                font-size: 0.7rem;
                color: #475569;
            }
            .tour-page-label {
                font-family: monospace;
                font-size: 0.65rem;
                color: rgba(180,74,255,0.6);
            }
            .tour-btn-skip {
                background: transparent;
                border: none;
                color: #475569;
                font-size: 0.78rem;
            }
            .tour-btn-skip:hover { color: #94a3b8; }
            .tour-btn-nav {
                background-color: rgba(180,74,255,0.15);
                border: 1px solid rgba(180,74,255,0.35);
                color: #b44aff;
                font-weight: 600;
                padding: 6px 18px;
                min-width: 80px;
            }
            .tour-btn-nav:hover {
                background-color: rgba(180,74,255,0.25);
            }
            .tour-btn-finish {
                background-color: #b44aff;
                border: none;
                color: #000;
                font-weight: 700;
                padding: 6px 18px;
            }
            .tour-btn-finish:hover { background-color: #c56fff; }
        """)
        # Apply CSS once a screen is available (widget may not be realized yet)
        def _apply_css():
            screen = Gdk.Screen.get_default()
            if screen:
                Gtk.StyleContext.add_provider_for_screen(
                    screen, css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
            return False
        GLib.idle_add(_apply_css)

        # Progress bar (3px strip at very top)
        self._progress = Gtk.ProgressBar()
        self._progress.get_style_context().add_class("tour-progress-bar")
        self._progress.set_show_text(False)
        inner.pack_start(self._progress, False, False, 0)

        # Content row
        content_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        content_row.set_margin_start(24)
        content_row.set_margin_end(24)
        content_row.set_margin_top(14)
        content_row.set_margin_bottom(14)
        inner.pack_start(content_row, False, False, 0)

        # Left: icon + step counter
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        left.set_valign(Gtk.Align.CENTER)

        self._icon_label = Gtk.Label(label="")
        self._icon_label.set_markup("<span font='28'>📊</span>")
        left.pack_start(self._icon_label, False, False, 0)

        self._step_label = Gtk.Label(label="1 / 12")
        self._step_label.get_style_context().add_class("tour-step-label")
        left.pack_start(self._step_label, False, False, 0)

        content_row.pack_start(left, False, False, 0)

        # Center: page name + title + body
        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        center.set_valign(Gtk.Align.CENTER)
        center.set_hexpand(True)

        self._page_label = Gtk.Label(label="")
        self._page_label.get_style_context().add_class("tour-page-label")
        self._page_label.set_xalign(0)
        center.pack_start(self._page_label, False, False, 0)

        self._title_label = Gtk.Label(label="")
        self._title_label.get_style_context().add_class("tour-title")
        self._title_label.set_xalign(0)
        self._title_label.set_line_wrap(True)
        center.pack_start(self._title_label, False, False, 0)

        self._body_label = Gtk.Label(label="")
        self._body_label.get_style_context().add_class("tour-body")
        self._body_label.set_xalign(0)
        self._body_label.set_line_wrap(True)
        self._body_label.set_max_width_chars(90)
        center.pack_start(self._body_label, False, False, 0)

        content_row.pack_start(center, True, True, 0)

        # Right: navigation buttons
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        right.set_valign(Gtk.Align.CENTER)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_row.set_halign(Gtk.Align.END)

        self._prev_btn = Gtk.Button(label="← Back")
        self._prev_btn.get_style_context().add_class("tour-btn-nav")
        self._prev_btn.connect("clicked", self._on_prev)
        btn_row.pack_start(self._prev_btn, False, False, 0)

        self._next_btn = Gtk.Button(label="Next →")
        self._next_btn.get_style_context().add_class("tour-btn-nav")
        self._next_btn.connect("clicked", self._on_next)
        btn_row.pack_start(self._next_btn, False, False, 0)

        self._finish_btn = Gtk.Button(label="Let's go ✓")
        self._finish_btn.get_style_context().add_class("tour-btn-finish")
        self._finish_btn.connect("clicked", self._on_finish_clicked)
        self._finish_btn.set_no_show_all(True)
        btn_row.pack_start(self._finish_btn, False, False, 0)

        right.pack_start(btn_row, False, False, 0)

        skip_btn = Gtk.Button(label="Skip tour")
        skip_btn.get_style_context().add_class("tour-btn-skip")
        skip_btn.set_relief(Gtk.ReliefStyle.NONE)
        skip_btn.set_halign(Gtk.Align.END)
        skip_btn.connect("clicked", self._on_finish_clicked)
        right.pack_start(skip_btn, False, False, 0)

        content_row.pack_start(right, False, False, 0)

        outer.pack_start(inner, False, False, 0)
        return outer

    # ── Step logic ───────────────────────────────────────────────────────────

    def _apply_step(self) -> None:
        step = self._steps[self._step]
        total = self._total

        # Progress
        self._progress.set_fraction((self._step + 1) / total)

        # Icon
        self._icon_label.set_markup(f"<span font='28'>{step.icon}</span>")

        # Step counter
        self._step_label.set_text(f"{self._step + 1} / {total}")

        # Page breadcrumb
        self._page_label.set_text(f"→  {step.page}")

        # Title
        self._title_label.set_markup(
            f"<span font_weight='bold' color='#b44aff' size='large'>{step.title}</span>"
        )

        # Body
        self._body_label.set_text(step.body)

        # Back button — hide on first step
        self._prev_btn.set_sensitive(self._step > 0)

        # Swap Next ↔ Finish on last step
        if step.is_final:
            self._next_btn.hide()
            self._finish_btn.show()
        else:
            self._next_btn.show()
            self._finish_btn.hide()

        # Navigate the main app
        try:
            self._navigate(step.page)
        except Exception:
            pass

    def _on_next(self, _btn) -> None:
        if self._step < self._total - 1:
            self._step += 1
            self._apply_step()

    def _on_prev(self, _btn) -> None:
        if self._step > 0:
            self._step -= 1
            self._apply_step()

    def _on_finish_clicked(self, _btn) -> None:
        self.set_reveal_child(False)
        GLib.timeout_add(300, self._mark_done)

    def _mark_done(self) -> bool:
        if self._on_finish:
            self._on_finish()
        # Persist that tour has been seen
        try:
            from shadowcypher.core.config import config
            config.set("ui", "tour_completed", True)
        except Exception:
            pass
        return False  # don't repeat


def tour_completed() -> bool:
    """True if the user has already finished or skipped the tour."""
    try:
        from shadowcypher.core.config import config
        return bool(config.get("ui", "tour_completed", default=False))
    except Exception:
        return False
