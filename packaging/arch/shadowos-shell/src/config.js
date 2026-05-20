// ShadowOS Shell — AGS entrypoint
// Renders: top bar, dock, launcher, notifications, lock screen.
// Design language: v9 (glass blur, gradient mesh, purple/indigo accents).

import { App } from "astal/gtk4";
import { TopBar }       from "./topbar.js";
import { Dock }         from "./dock.js";
import { Launcher }     from "./launcher.js";
import { Notifications }from "./notifications.js";
import { Lockscreen }   from "./lockscreen.js";
import { ModeWatcher }  from "./mode.js";

App.start({
    instanceName: "shadowos-shell",
    css: "/usr/share/shadowos-shell/style/style.css",
    main() {
        // Sync mode chip color across the whole shell
        ModeWatcher.start();

        // One window per shell layer
        App.get_monitors().forEach((m) => {
            TopBar(m);
            Dock(m);
        });

        // Modeless overlays (toggled by keybind)
        Launcher();
        Notifications();
        Lockscreen();
    },
    requestHandler(req, res) {
        // CLI control: `ags request "launcher.toggle"` etc.
        switch (req) {
            case "launcher.toggle": Launcher.toggle(); break;
            case "lock":            Lockscreen.show();  break;
            default: res(`unknown: ${req}`);
        }
        res("ok");
    },
});
