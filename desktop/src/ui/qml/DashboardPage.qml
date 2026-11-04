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
            spacing: 32

            // Header
            ColumnLayout {
                spacing: 6
                Text { text: "Dashboard"; color: root.textPri; font.pixelSize: 24; font.weight: Font.Bold }
                Text { text: "Network overview and recent incidents"; color: root.textSec; font.pixelSize: 13 }
            }

            // Stat tiles
            GridLayout {
                Layout.fillWidth: true
                columns: 4
                columnSpacing: 16
                rowSpacing: 16

                StatTile { Layout.fillWidth: true; label: "DEVICES"; value: scanner.devices.length.toString(); sub: "on LAN" }
                StatTile { Layout.fillWidth: true; label: "INCIDENTS"; value: "0"; sub: "last 24h"; accent: root.amber }
                StatTile { Layout.fillWidth: true; label: "AI"; value: ai.available ? "Online" : "Offline"; sub: ai.model; accent: ai.available ? root.green : root.textSec }
                StatTile { Layout.fillWidth: true; label: "PRIVACY"; value: privacy.active ? "On" : "Off"; sub: privacy.status; accent: privacy.active ? root.green : root.textSec }
            }

            // Scan button row
            RowLayout {
                spacing: 12
                Button {
                    text: scanner.scanning ? "Scanning…" : "Scan Now"
                    enabled: !scanner.scanning
                    onClicked: scanner.scanNow()
                    background: Rectangle { color: root.accent; radius: 6 }
                    contentItem: Text { text: parent.text; color: "#fff"; font.pixelSize: 13; horizontalAlignment: Text.AlignHCenter }
                    padding: 0; leftPadding: 20; rightPadding: 20; height: 36
                }
                Text { text: scanner.running ? "Monitoring active" : "Manual scan"; color: root.textSec; font.pixelSize: 12 }
            }

            // Device list
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(200, deviceList.contentHeight + 48)
                color: root.bgSurface
                radius: 8
                border.color: root.border

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    // Header row
                    Rectangle {
                        Layout.fillWidth: true; height: 40
                        color: "transparent"
                        border.color: root.border
                        RowLayout {
                            anchors { fill: parent; leftMargin: 16; rightMargin: 16 }
                            Repeater {
                                model: [
                                    { label: "IP",       w: 120 },
                                    { label: "MAC",      w: 150 },
                                    { label: "HOSTNAME", w: -1  },
                                    { label: "STATUS",   w: 70  }
                                ]
                                Text {
                                    text: modelData.label; color: root.textSec; font.pixelSize: 11; font.family: root.monoFont; font.letterSpacing: 2
                                    Layout.minimumWidth: modelData.w > 0 ? modelData.w : 0
                                    Layout.preferredWidth: modelData.w
                                    Layout.fillWidth: modelData.w < 0
                                }
                            }
                        }
                    }

                    ListView {
                        id: deviceList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: scanner.devices
                        clip: true
                        delegate: Rectangle {
                            width: deviceList.width; height: 44
                            color: index % 2 === 0 ? "transparent" : Qt.rgba(1,1,1,0.02)
                            border.color: root.border
                            RowLayout {
                                anchors { fill: parent; leftMargin: 16; rightMargin: 16 }
                                Text { text: modelData.ip;       color: root.textPri; font.pixelSize: 13; font.family: root.monoFont; Layout.minimumWidth: 120 }
                                Text { text: modelData.mac;      color: root.textSec; font.pixelSize: 12; font.family: root.monoFont; Layout.minimumWidth: 150 }
                                Text { text: modelData.hostname; color: root.textSec; font.pixelSize: 12; Layout.fillWidth: true }
                                Rectangle {
                                    Layout.preferredWidth: 70; height: 22; radius: 4
                                    color: modelData.suspect ? Qt.rgba(239/255,68/255,68/255,0.1) :
                                           modelData.trusted ? Qt.rgba(34/255,197/255,94/255,0.08) :
                                                               Qt.rgba(245/255,158/255,11/255,0.1)
                                    Text {
                                        anchors.centerIn: parent
                                        text:  modelData.suspect ? "suspect" : modelData.trusted ? "trusted" : modelData.isNew ? "new" : "untrusted"
                                        color: modelData.suspect ? root.red : modelData.trusted ? root.green : root.amber
                                        font.pixelSize: 10; font.family: root.monoFont
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
