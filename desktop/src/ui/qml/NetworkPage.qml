import QtQuick
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
            RowLayout {
                Layout.fillWidth: true
                ColumnLayout {
                    spacing: 4
                    Text { text: "Network Monitor"; color: root.textPri; font.pixelSize: 24; font.weight: Font.Bold }
                    Text { text: "ARP table, device tracking, spoof detection"; color: root.textSec; font.pixelSize: 13 }
                }
                Item { Layout.fillWidth: true }
                Button {
                    text: scanner.running ? "Stop" : "Start Monitor"
                    onClicked: scanner.running ? scanner.stop() : scanner.start()
                    background: Rectangle {
                        color: scanner.running ? Qt.rgba(239/255,68/255,68/255,0.12) : root.accent
                        border.color: scanner.running ? root.red : "transparent"
                        radius: 6
                    }
                    contentItem: Text {
                        text: parent.text
                        color: scanner.running ? root.red : "#fff"
                        font.pixelSize: 13
                        horizontalAlignment: Text.AlignHCenter
                    }
                    padding: 0; leftPadding: 20; rightPadding: 20; height: 36
                }
            }

            // Stats row
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Repeater {
                    model: [
                        { label: "TOTAL DEVICES", value: scanner.devices.length.toString(), accent: root.accent },
                        { label: "NEW THIS SESSION", value: scanner.newCount !== undefined ? scanner.newCount.toString() : "0", accent: root.amber },
                        { label: "ALERTS", value: scanner.alertCount !== undefined ? scanner.alertCount.toString() : "0", accent: root.red }
                    ]
                    Rectangle {
                        Layout.fillWidth: true; height: 80
                        color: root.bgPanel; radius: 8; border.color: root.border
                        ColumnLayout {
                            anchors { fill: parent; margins: 16 }
                            spacing: 4
                            Text { text: modelData.label; color: root.textSec; font.pixelSize: 10; font.family: root.monoFont; font.letterSpacing: 2 }
                            Text { text: modelData.value; color: modelData.accent; font.pixelSize: 26; font.weight: Font.Bold }
                        }
                    }
                }
            }

            // Alert banner (shown when spoofs detected)
            Rectangle {
                Layout.fillWidth: true
                height: 48
                radius: 6
                visible: scanner.alertCount > 0
                color: Qt.rgba(239/255,68/255,68/255,0.08)
                border.color: Qt.rgba(239/255,68/255,68/255,0.3)
                RowLayout {
                    anchors { fill: parent; leftMargin: 16; rightMargin: 16 }
                    spacing: 8
                    Rectangle { width: 8; height: 8; radius: 4; color: root.red }
                    Text { text: "ARP spoofing detected — possible MITM attack on your network"; color: root.red; font.pixelSize: 13 }
                }
            }

            // Device table
            Rectangle {
                Layout.fillWidth: true
                height: Math.max(300, deviceView.contentHeight + 52)
                color: root.bgSurface; radius: 8; border.color: root.border

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    // Table header
                    Rectangle {
                        Layout.fillWidth: true; height: 44
                        color: root.bgPanel
                        radius: 8
                        Rectangle {
                            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                            height: 1; color: root.border
                        }
                        RowLayout {
                            anchors { fill: parent; leftMargin: 16; rightMargin: 16 }
                            spacing: 0
                            Repeater {
                                model: [
                                    { label: "IP ADDRESS",  fw: 130 },
                                    { label: "MAC ADDRESS", fw: 160 },
                                    { label: "HOSTNAME",    fw: -1  },
                                    { label: "VENDOR",      fw: 160 },
                                    { label: "LAST SEEN",   fw: 120 },
                                    { label: "STATUS",      fw: 80  }
                                ]
                                Text {
                                    text: modelData.label
                                    color: root.textSec
                                    font.pixelSize: 10
                                    font.family: root.monoFont
                                    font.letterSpacing: 1.5
                                    Layout.preferredWidth: modelData.fw > 0 ? modelData.fw : -1
                                    Layout.fillWidth: modelData.fw < 0
                                }
                            }
                        }
                    }

                    ListView {
                        id: deviceView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: scanner.devices
                        clip: true
                        delegate: Rectangle {
                            width: deviceView.width; height: 44
                            color: modelData.suspect
                                   ? Qt.rgba(239/255,68/255,68/255,0.05)
                                   : index % 2 === 0 ? "transparent" : Qt.rgba(1,1,1,0.015)
                            Rectangle {
                                anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                                height: 1; color: root.border; opacity: 0.5
                            }
                            RowLayout {
                                anchors { fill: parent; leftMargin: 16; rightMargin: 16 }
                                spacing: 0
                                Text { text: modelData.ip;       color: root.textPri; font.pixelSize: 13; font.family: root.monoFont; Layout.preferredWidth: 130 }
                                Text { text: modelData.mac;      color: root.textSec; font.pixelSize: 12; font.family: root.monoFont; Layout.preferredWidth: 160 }
                                Text { text: modelData.hostname || "—"; color: root.textSec; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
                                Text { text: modelData.vendor || "—";   color: root.textSec; font.pixelSize: 11; Layout.preferredWidth: 160; elide: Text.ElideRight }
                                Text { text: modelData.lastSeen || "—"; color: root.textSec; font.pixelSize: 11; font.family: root.monoFont; Layout.preferredWidth: 120 }
                                Rectangle {
                                    width: 72; height: 22; radius: 4
                                    color: modelData.suspect ? Qt.rgba(239/255,68/255,68/255,0.12)
                                         : modelData.isNew   ? Qt.rgba(245/255,158/255,11/255,0.1)
                                                             : Qt.rgba(34/255,197/255,94/255,0.08)
                                    Text {
                                        anchors.centerIn: parent
                                        text:  modelData.suspect ? "SUSPECT" : modelData.isNew ? "NEW" : "KNOWN"
                                        color: modelData.suspect ? root.red : modelData.isNew ? root.amber : root.green
                                        font.pixelSize: 9; font.family: root.monoFont; font.letterSpacing: 1
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
