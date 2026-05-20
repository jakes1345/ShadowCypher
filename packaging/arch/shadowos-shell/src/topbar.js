// ShadowOS top bar — slim, glass-blur, threat-aware
// Renders the v9 top-bar design: ◆ logo + Activities + focused window |
//   workspace dots · mode pill · tray · clock

import { App, Astal, Gtk, Gdk } from "astal/gtk4";
import { Variable, bind, exec, execAsync, GLib } from "astal";
import Hyprland from "gi://AstalHyprland?version=0.1";
import Mpris    from "gi://AstalMpris?version=0.1";

const hypr = Hyprland.get_default();

// ── State variables ─────────────────────────────────────────────────────
const time = Variable("").poll(1000, () => GLib.DateTime.new_now_local().format("%H:%M"));
const date = Variable("").poll(60_000, () => GLib.DateTime.new_now_local().format("%a · %b %d"));
const mode = Variable("normal").poll(2_000, () => {
    try { return GLib.file_get_contents("/var/lib/shadowos/current-mode")[1].toString().trim(); }
    catch { return "normal"; }
});

// Threat telemetry — polled from shadowos-diag JSON output
const telemetry = Variable({}).poll(15_000, () => {
    try {
        const out = exec(["bash", "-c",
            "shadowos-diag --json 2>/dev/null || echo '{}'"]);
        return JSON.parse(out);
    } catch { return {}; }
});

const modeColors = {
    normal:  ["#22c55e", "rgba(34,197,94,0.20)"],
    dev:     ["#6366f1", "rgba(99,102,241,0.20)"],
    pentest: ["#f7a33a", "rgba(247,163,58,0.20)"],
    privacy: ["#f87171", "rgba(248,113,113,0.20)"],
    ghost:   ["#e5e7eb", "rgba(229,231,235,0.20)"],
};

function Diamond() {
    return <box cssClasses={["logo"]} widthRequest={22} heightRequest={22}/>;
}

function ModeChip() {
    return <box cssClasses={["mode-chip"]}>
        <box cssClasses={bind(mode).as(m => ["mode-dot", `mode-${m}`])}/>
        <label label={bind(mode)}/>
    </box>;
}

function Telemetry() {
    return <box cssClasses={["telemetry"]} spacing={18}>
        <box>
            <label cssClasses={["tel-l"]} label="PORTS"/>
            <label cssClasses={["tel-v"]}
                   label={bind(telemetry).as(t => `${t.open_ports ?? 0}`)}/>
        </box>
        <box>
            <label cssClasses={["tel-l"]} label="CONNS"/>
            <label cssClasses={["tel-v"]}
                   label={bind(telemetry).as(t => `${t.connections ?? 0}`)}/>
        </box>
        <box>
            <label cssClasses={["tel-l"]} label="TOR"/>
            <label cssClasses={["tel-v"]}
                   label={bind(telemetry).as(t => t.tor_circuit ?? "—")}/>
        </box>
        <box>
            <label cssClasses={["tel-l"]} label="THREAT"/>
            <label cssClasses={["tel-v", "ok"]}
                   label={bind(telemetry).as(t => t.threat_level ?? "LOW")}/>
        </box>
    </box>;
}

function Workspaces() {
    const wsVar = Variable.derive([bind(hypr, "workspaces"), bind(hypr, "focusedWorkspace")],
        (all, focused) => ({ all, focused }));
    return <box cssClasses={["workspaces"]}>
        {bind(wsVar).as(({ all, focused }) => {
            const list = [];
            for (let i = 1; i <= 5; i++) {
                const w = all.find(w => w.id === i);
                const active = focused?.id === i;
                list.push(
                    <button cssClasses={active ? ["ws", "active"] : ["ws"]}
                            onClicked={() => hypr.dispatch("workspace", String(i))}>
                        <label label={active ? String(i) : ""}/>
                    </button>
                );
            }
            return list;
        })}
    </box>;
}

function FocusedApp() {
    const focused = Variable.derive([bind(hypr, "focusedClient")], (c) =>
        c ? `${c.class}  —  ${c.title?.slice(0, 60) ?? ""}` : "Desktop");
    return <label cssClasses={["focused-app"]} label={bind(focused)}/>;
}

function Clock() {
    return <box cssClasses={["clock-box"]} spacing={8}>
        <label cssClasses={["clock"]} label={bind(time)}/>
        <label cssClasses={["date"]}  label={bind(date)}/>
    </box>;
}

export function TopBar(monitor) {
    return <window
        name={`topbar-${monitor.id}`}
        cssClasses={["topbar"]}
        application={App}
        gdkmonitor={monitor}
        layer={Astal.Layer.TOP}
        anchor={Astal.WindowAnchor.TOP | Astal.WindowAnchor.LEFT | Astal.WindowAnchor.RIGHT}
        exclusivity={Astal.Exclusivity.EXCLUSIVE}>
        <centerbox cssClasses={["topbar-content"]}>
            {/* Start */}
            <box spacing={12}>
                <button cssClasses={["activities"]}
                        onClicked={() => execAsync(["ags", "request", "launcher.toggle"])}>
                    <box spacing={8}>
                        <Diamond/>
                        <label label="ShadowOS"/>
                    </box>
                </button>
                <FocusedApp/>
            </box>
            {/* Center — empty (focused window goes left) */}
            <box/>
            {/* End */}
            <box spacing={16}>
                <Telemetry/>
                <Workspaces/>
                <ModeChip/>
                <Clock/>
            </box>
        </centerbox>
    </window>;
}
