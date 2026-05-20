// ShadowOS dock — floating glass dock at bottom-center, hex-tile icons.
// Reads pinned apps from ~/.config/shadowos-shell/dock.json.
// Shows running indicator (purple dot) for each app.

import { App, Astal, Gtk } from "astal/gtk4";
import { Variable, bind, exec, GLib } from "astal";
import Apps     from "gi://AstalApps?version=0.1";
import Hyprland from "gi://AstalHyprland?version=0.1";

const apps = new Apps.Apps();
const hypr = Hyprland.get_default();

const DEFAULT_PINNED = [
    "org.shadowcypher.ShadowCypher",
    "shadowbrowser",
    "org.gnome.thunar",
    "code",
    "foot",
    "helix",
    "org.signal.Signal",
    "discord",
    "steam",
];

function loadPinned() {
    try {
        const path = GLib.build_filenamev([
            GLib.get_home_dir(), ".config", "shadowos-shell", "dock.json"
        ]);
        const [, data] = GLib.file_get_contents(path);
        return JSON.parse(data.toString()).pinned ?? DEFAULT_PINNED;
    } catch { return DEFAULT_PINNED; }
}

const pinned = Variable(loadPinned());

// Watch for file changes (hot-reload)
const dockJson = Gio.File.new_for_path(GLib.build_filenamev([
    GLib.get_home_dir(), ".config", "shadowos-shell", "dock.json"]));
try {
    const mon = dockJson.monitor(Gio.FileMonitorFlags.NONE, null);
    mon.connect("changed", () => pinned.set(loadPinned()));
} catch {}

function DockItem(appId) {
    const app = apps.fuzzy_query(appId)[0];
    if (!app) return null;

    const running = Variable.derive([bind(hypr, "clients")], (clients) =>
        clients.some(c => c.class?.toLowerCase().includes(app.name?.toLowerCase()))
    );

    return <button
        cssClasses={bind(running).as(r => r ? ["dock-icon", "running"] : ["dock-icon"])}
        tooltipText={app.name}
        onClicked={() => app.launch()}>
        <box vertical={true}>
            <image iconName={app.iconName} pixelSize={32}/>
        </box>
    </button>;
}

export function Dock(monitor) {
    return <window
        name={`dock-${monitor.id}`}
        cssClasses={["dock-window"]}
        application={App}
        gdkmonitor={monitor}
        layer={Astal.Layer.TOP}
        anchor={Astal.WindowAnchor.BOTTOM}
        marginBottom={18}>
        <box cssClasses={["dock"]} spacing={8}>
            {bind(pinned).as(list =>
                list.map(id => DockItem(id)).filter(Boolean)
            )}
        </box>
    </window>;
}
