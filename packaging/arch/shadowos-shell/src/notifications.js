// ShadowOS notifications — replaces mako with stylable cards.

import { App, Astal, Gtk } from "astal/gtk4";
import { bind } from "astal";
import Notifd from "gi://AstalNotifd?version=0.1";

const notifd = Notifd.get_default();

function NotificationCard(n) {
    const sevClass = ({
        0: "low", 1: "normal", 2: "critical",
    })[n.urgency] || "normal";
    return <box cssClasses={["notification", `sev-${sevClass}`]} spacing={12}>
        <box cssClasses={["sev-bar"]}/>
        <box vertical={true} spacing={4}>
            <label cssClasses={["notif-app"]} label={n.appName} halign={Gtk.Align.START}/>
            <label cssClasses={["notif-title"]} label={n.summary} halign={Gtk.Align.START}
                   wrap={true} maxWidthChars={40}/>
            <label cssClasses={["notif-body"]} label={n.body || ""} halign={Gtk.Align.START}
                   wrap={true} maxWidthChars={50}/>
        </box>
    </box>;
}

export function Notifications() {
    return <window
        name="notifications"
        cssClasses={["notif-window"]}
        application={App}
        layer={Astal.Layer.TOP}
        anchor={Astal.WindowAnchor.TOP | Astal.WindowAnchor.RIGHT}
        marginTop={50}
        marginRight={20}>
        <box vertical={true} spacing={10} cssClasses={["notif-stack"]}>
            {bind(notifd, "notifications").as(notifs =>
                notifs.slice(-5).map(NotificationCard)
            )}
        </box>
    </window>;
}
