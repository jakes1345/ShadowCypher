// Mode watcher — propagates shadow-mode changes to the shell theme via
// CSS class on the body.

import { App, Gdk } from "astal/gtk4";
import { Variable, GLib, Gio, exec } from "astal";

const modeFile = "/var/lib/shadowos/current-mode";

export const ModeWatcher = {
    current: Variable("normal"),

    start() {
        const update = () => {
            try {
                const [, data] = GLib.file_get_contents(modeFile);
                const m = data.toString().trim();
                if (m && m !== this.current.get()) {
                    this.current.set(m);
                    // Toggle global CSS class on the top-level windows
                    App.get_windows().forEach(w => {
                        w.css_classes = w.css_classes
                            .filter(c => !c.startsWith("mode-"))
                            .concat([`mode-${m}`]);
                    });
                }
            } catch {}
        };
        update();

        // Watch the file for changes
        try {
            const f = Gio.File.new_for_path(modeFile);
            const monitor = f.monitor(Gio.FileMonitorFlags.NONE, null);
            monitor.connect("changed", () => update());
        } catch {}

        // Also re-poll every 3s as a fallback
        setInterval(update, 3000);
    },
};
