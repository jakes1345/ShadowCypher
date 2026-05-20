// ShadowOS lockscreen — replaces hyprlock with AGS-rendered version.

import { App, Astal, Gtk } from "astal/gtk4";
import { Variable, bind, GLib, exec } from "astal";

const visible = Variable(false);
const time = Variable("").poll(1000, () => GLib.DateTime.new_now_local().format("%H:%M"));
const date = Variable("").poll(60_000, () => GLib.DateTime.new_now_local().format("%A · %B %d"));

function PasswordInput() {
    return <entry
        cssClasses={["lock-input"]}
        visibility={false}
        placeholderText="password"
        onActivate={(e) => {
            try {
                exec(["su", "-c", "true", "shadow"], { stdin: e.text });
                visible.set(false);
            } catch {
                e.text = "";
                // Flash error
            }
        }}/>;
}

export function Lockscreen() {
    Lockscreen.show = () => visible.set(true);

    return <window
        name="lockscreen"
        cssClasses={["lock-window"]}
        application={App}
        layer={Astal.Layer.OVERLAY}
        keymode={Astal.Keymode.EXCLUSIVE}
        visible={bind(visible)}
        anchor={Astal.WindowAnchor.TOP | Astal.WindowAnchor.BOTTOM |
                Astal.WindowAnchor.LEFT | Astal.WindowAnchor.RIGHT}
        exclusivity={Astal.Exclusivity.IGNORE}>
        <box cssClasses={["lock-overlay"]} vertical={true} spacing={24}
             halign={Gtk.Align.CENTER} valign={Gtk.Align.CENTER}>
            <label cssClasses={["lock-clock"]} label={bind(time)}/>
            <label cssClasses={["lock-date"]}  label={bind(date)}/>
            <box cssClasses={["lock-spacer"]} heightRequest={40}/>
            <label cssClasses={["lock-user"]} label="shadow"/>
            <PasswordInput/>
            <label cssClasses={["lock-tag"]}  label="privacy is a posture"/>
        </box>
    </window>;
}
