"""
Wraith Protocol — Emergency Lockdown & Ephemeral Data Destruction.
Dedicated page for flash-wipe, tunnel termination, and evidence purge.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
import os
import threading

from shadowcypher.ui.base_page import BasePage
from shadowcypher.core.config import config
from shadowcypher.core.bus import bus
from shadowcypher.core.logger import logger


class WraithProtocol(BasePage):
    """Emergency lockdown and data purge interface."""

    def __init__(self):
        super().__init__("\u2622 WRAITH PROTOCOL: EMERGENCY LOCKDOWN")
        from shadowcypher.ui.components import DataPod

        self.pod_status = DataPod("LOCKDOWN", "STANDBY", "red")
        self.pod_vaults = DataPod("VAULTS", "SEALED", "amber")
        self.pod_tunnels = DataPod("TUNNELS", "0", "cyan")
        for p in [self.pod_status, self.pod_vaults, self.pod_tunnels]:
            self.metric_strip.pack_start(p, True, True, 0)

        # Warning Banner
        warn = Gtk.Label()
        warn.set_markup(
            "<span size='large' color='#f43f5e' weight='bold'>"
            "\u26a0 THIS PAGE CONTAINS DESTRUCTIVE OPERATIONS</span>\n"
            "<span color='#94a3b8'>All actions are irreversible. Confirm before executing.</span>"
        )
        warn.set_line_wrap(True)
        self.workspace.pack_start(warn, False, False, 10)

        # Flash Wipe
        frm1 = Gtk.Frame(label="SPECTRE FLASH-WIPE")
        bx1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        bx1.set_margin_start(10)
        bx1.set_margin_end(10)
        bx1.set_margin_top(10)
        bx1.set_margin_bottom(10)
        lbl1 = Gtk.Label(xalign=0)
        lbl1.set_line_wrap(True)
        lbl1.set_markup(
            "<span color='#94a3b8'>Purges all ephemeral mission data, session keys, "
            "and forensic artifacts. Resets mission counters and locks the vault.</span>"
        )
        bx1.pack_start(lbl1, False, False, 0)
        btn_wipe = Gtk.Button(label="\u2622 EXECUTE SPECTRE FLASH-WIPE")
        btn_wipe.get_style_context().add_class("destructive-action")
        btn_wipe.connect("clicked", self._on_flash_wipe)
        bx1.pack_start(btn_wipe, False, False, 0)
        frm1.add(bx1)
        self.workspace.pack_start(frm1, False, False, 0)

        # Kill All Tunnels
        frm2 = Gtk.Frame(label="TUNNEL TERMINATION")
        bx2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        bx2.set_margin_start(10)
        bx2.set_margin_end(10)
        bx2.set_margin_top(10)
        bx2.set_margin_bottom(10)
        btn_tunnels = Gtk.Button(label="\U0001f6d1 Kill All Active Tunnels & Processes")
        btn_tunnels.get_style_context().add_class("destructive-action")
        btn_tunnels.connect("clicked", self._on_kill_tunnels)
        bx2.pack_start(btn_tunnels, False, False, 0)
        frm2.add(bx2)
        self.workspace.pack_start(frm2, False, False, 0)

        # Purge Logs
        frm3 = Gtk.Frame(label="LOG PURGE")
        bx3 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        bx3.set_margin_start(10)
        bx3.set_margin_end(10)
        bx3.set_margin_top(10)
        bx3.set_margin_bottom(10)
        btn_logs = Gtk.Button(label="\U0001f5d1 Purge All Operational Logs")
        btn_logs.connect("clicked", self._on_purge_logs)
        bx3.pack_start(btn_logs, False, False, 0)
        frm3.add(bx3)
        self.workspace.pack_start(frm3, False, False, 0)

        # Hardware FP in sidebar
        from shadowcypher.core.security import hardener
        frm_fp = Gtk.Frame(label="MACHINE IDENTITY")
        bx_fp = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        bx_fp.set_margin_start(10)
        bx_fp.set_margin_end(10)
        bx_fp.set_margin_top(10)
        bx_fp.set_margin_bottom(10)
        fp = hardener.get_hardware_footprint()
        lbl_fp = Gtk.Label()
        lbl_fp.set_line_wrap(True)
        lbl_fp.set_xalign(0)
        lbl_fp.set_markup(f"<span size='small' color='#64748b'>MASTER_FP:\n{fp[:32]}...\n{fp[32:]}</span>")
        bx_fp.pack_start(lbl_fp, False, False, 0)
        frm_fp.add(bx_fp)
        self.intel_sidebar.pack_start(frm_fp, False, False, 0)

    def _on_flash_wipe(self, btn):
        dialog = Gtk.MessageDialog(
            parent=self.get_toplevel(), flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Confirm Spectre Flash-Wipe?",
        )
        dialog.format_secondary_text("This will purge all ephemeral mission data and lock local vaults.")
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            from shadowcypher.core.security import hardener
            hardener.execute_flash_wipe()
            self.log("[LOCKDOWN] Spectre Flash-Wipe Complete.", "WARNING")
            self.pod_status.set_value("ENGAGED")
        dialog.destroy()

    def _on_kill_tunnels(self, btn):
        from shadowcypher.core.runner import runner
        count = len(runner.active_processes)
        runner.cleanup() if hasattr(runner, 'cleanup') else None
        for tid in list(runner.active_processes.keys()):
            runner.stop_task(tid)
        self.log(f"Terminated {count} active processes.", "WARNING")
        self.pod_tunnels.set_value("0")

    def _on_purge_logs(self, btn):
        log_dir = os.path.join(str(config.project_root), "logs")
        if os.path.exists(log_dir):
            count = 0
            for f in os.listdir(log_dir):
                fp = os.path.join(log_dir, f)
                if os.path.isfile(fp):
                    os.remove(fp)
                    count += 1
            self.log(f"Purged {count} log files from {log_dir}", "WARNING")
        else:
            self.log("No logs directory found.", "INFO")
