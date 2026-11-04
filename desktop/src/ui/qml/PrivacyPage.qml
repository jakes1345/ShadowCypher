import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    color: root.bgBase

    Flickable {
        anchors { fill: parent; margins: 32 }
        contentHeight: col.implicitHeight
        clip: true

        ColumnLayout {
            id: col
            width: parent.width
            spacing: 24

            // Header
            ColumnLayout {
                spacing: 4
                Text { text: "Privacy Mode"; color: root.textPri; font.pixelSize: 24; font.weight: Font.Bold }
                Text { text: "Tor routing with iptables kill-switch"; color: root.textSec; font.pixelSize: 13 }
            }

            // Status card
            Rectangle {
                Layout.fillWidth: true
                height: 120
                radius: 10
                color: privacy.active
                       ? Qt.rgba(34/255,197/255,94/255,0.06)
                       : root.bgSurface
                border.color: privacy.active
                              ? Qt.rgba(34/255,197/255,94/255,0.25)
                              : root.border

                RowLayout {
                    anchors { fill: parent; margins: 28 }
                    spacing: 24

                    // Big status circle
                    Rectangle {
                        width: 64; height: 64; radius: 32
                        color: privacy.active ? Qt.rgba(34/255,197/255,94/255,0.12) : Qt.rgba(100/255,116/255,139/255,0.1)
                        border.color: privacy.active ? root.green : root.border
                        border.width: 2
                        SequentialAnimation on opacity {
                            running: privacy.active; loops: Animation.Infinite
                            NumberAnimation { to: 0.6; duration: 1400 }
                            NumberAnimation { to: 1.0; duration: 1400 }
                        }
                        Text {
                            anchors.centerIn: parent
                            text: privacy.active ? "◎" : "○"
                            color: privacy.active ? root.green : root.textSec
                            font.pixelSize: 26
                        }
                    }

                    ColumnLayout {
                        spacing: 6
                        Text {
                            text: privacy.active ? "Privacy Mode Active" : "Privacy Mode Off"
                            color: privacy.active ? root.green : root.textPri
                            font.pixelSize: 18
                            font.weight: Font.SemiBold
                        }
                        Text {
                            text: privacy.status
                            color: root.textSec
                            font.pixelSize: 13
                            font.family: root.monoFont
                        }
                    }

                    Item { Layout.fillWidth: true }

                    ColumnLayout {
                        spacing: 10
                        Button {
                            Layout.preferredWidth: 140
                            height: 40
                            text: privacy.busy ? "Working…" : privacy.active ? "Disengage" : "Engage"
                            enabled: !privacy.busy
                            onClicked: privacy.active ? privacy.disengage() : privacy.engage()
                            background: Rectangle {
                                color: privacy.active
                                       ? Qt.rgba(239/255,68/255,68/255,0.1)
                                       : root.accent
                                border.color: privacy.active ? root.red : "transparent"
                                radius: 6
                            }
                            contentItem: Text {
                                text: parent.text
                                color: privacy.active ? root.red : "#fff"
                                font.pixelSize: 13
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                        Button {
                            Layout.preferredWidth: 140
                            height: 36
                            text: "Verify Tor"
                            enabled: privacy.active && !privacy.busy
                            onClicked: privacy.verify()
                            background: Rectangle {
                                color: "transparent"
                                border.color: parent.enabled ? root.border : Qt.rgba(255,255,255,0.05)
                                radius: 6
                            }
                            contentItem: Text {
                                text: parent.text
                                color: parent.enabled ? root.textSec : Qt.rgba(100/255,116/255,139/255,0.4)
                                font.pixelSize: 12
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }
                }
            }

            // How it works
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: infoCol.implicitHeight + 40
                color: root.bgSurface; radius: 8; border.color: root.border
                ColumnLayout {
                    id: infoCol
                    anchors { fill: parent; margins: 24 }
                    spacing: 12
                    Text { text: "How Privacy Mode Works"; color: root.textPri; font.pixelSize: 14; font.weight: Font.SemiBold }

                    Repeater {
                        model: [
                            { step: "1", title: "Starts Tor service", desc: "systemctl start tor — Tor runs as a SOCKS5 proxy on 127.0.0.1:9050" },
                            { step: "2", title: "Applies iptables kill-switch", desc: "OUTPUT chain DROPs all traffic except Tor's own system user and loopback — no leaks even if Tor crashes" },
                            { step: "3", title: "Verify button", desc: "Curl through SOCKS5 to check.torproject.org/api/ip and confirm IsTor:true" }
                        ]
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 14
                            Rectangle {
                                width: 28; height: 28; radius: 14
                                color: Qt.rgba(180/255,74/255,255/255,0.12)
                                border.color: Qt.rgba(180/255,74/255,255/255,0.3)
                                Text { anchors.centerIn: parent; text: modelData.step; color: root.accent; font.pixelSize: 12; font.weight: Font.Bold }
                            }
                            ColumnLayout {
                                spacing: 2
                                Text { text: modelData.title; color: root.textPri; font.pixelSize: 13; font.weight: Font.Medium }
                                Text { text: modelData.desc;  color: root.textSec; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
                            }
                        }
                    }
                }
            }

            // Windows note
            Rectangle {
                Layout.fillWidth: true
                height: 52
                radius: 6
                visible: Qt.platform.os === "windows"
                color: Qt.rgba(245/255,158/255,11/255,0.06)
                border.color: Qt.rgba(245/255,158/255,11/255,0.2)
                RowLayout {
                    anchors { fill: parent; leftMargin: 16; rightMargin: 16 }
                    spacing: 10
                    Text { text: "Windows:"; color: root.amber; font.pixelSize: 12; font.weight: Font.SemiBold }
                    Text { text: "iptables is unavailable. SOCKS5 proxy mode only — system-wide routing not enforced."; color: root.amber; font.pixelSize: 12 }
                }
            }
        }
    }

    Connections {
        target: privacy
        function onVerifyResult(ok, message) {
            app.notification("Tor Verify", message, ok ? "info" : "error")
        }
    }
}
