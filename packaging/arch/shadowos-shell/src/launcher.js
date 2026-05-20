// ShadowOS launcher — full-screen overlay opened by Super.
// Cmd-K search bar + hex grid of apps + workspace thumbnails.

import { App, Astal, Gtk, Gdk } from "astal/gtk4";
import { Variable, bind } from "astal";
import Apps from "gi://AstalApps?version=0.1";

const apps = new Apps.Apps();

const visible = Variable(false);
const query   = Variable("");
const results = Variable.derive([query], q =>
    q ? apps.fuzzy_query(q).slice(0, 32) : apps.list.slice(0, 32)
);

function AppTile(app) {
    return <button cssClasses={["app-tile"]}
                   onClicked={() => { app.launch(); visible.set(false); }}>
        <box vertical={true} spacing={6}>
            <image iconName={app.iconName} pixelSize={48}/>
            <label label={app.name} cssClasses={["app-label"]}/>
        </box>
    </button>;
}

function Search() {
    const entry = <entry
        cssClasses={["search-input"]}
        placeholderText="search apps · commands · files…"
        primaryIconName="system-search-symbolic"
        onChanged={(e) => query.set(e.text)}
        onActivate={() => {
            const r = results.get();
            if (r.length > 0) { r[0].launch(); visible.set(false); }
        }}/>;
    return entry;
}

export function Launcher() {
    Launcher.toggle = () => visible.set(!visible.get());

    return <window
        name="launcher"
        cssClasses={["launcher-window"]}
        application={App}
        layer={Astal.Layer.OVERLAY}
        keymode={Astal.Keymode.EXCLUSIVE}
        visible={bind(visible)}
        onKeyPressed={(_, keyval) => {
            if (keyval === Gdk.KEY_Escape) visible.set(false);
        }}>
        <box cssClasses={["launcher-overlay"]} vertical={true}
             halign={Gtk.Align.CENTER} valign={Gtk.Align.CENTER}>
            <box cssClasses={["launcher-panel"]} vertical={true} spacing={20}>
                <Search/>
                <scrolledwindow heightRequest={520} widthRequest={1100}
                                  cssClasses={["app-grid-scroll"]}>
                    <box cssClasses={["app-grid"]}>
                        {bind(results).as(list => list.map(AppTile))}
                    </box>
                </scrolledwindow>
            </box>
        </box>
    </window>;
}
