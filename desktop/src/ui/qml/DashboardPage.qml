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

                StatTile { label: "DEVICES"; value: scanner.devices.length.toString(); sub: "on LAN" }
                StatTile {
                    label: "INCIDENTS"
                    value: !cloud.active ? "—" : cloud.incidentsLoaded ? cloud.openCount.toString() : "…"
                    sub: cloud.active ? "open" : "sign in online"
                    accent: cloud.active && cloud.openCount > 0 ? root.amber : root.textSec
                }
                StatTile { label: "AI"; value: ai.available ? "Online" : "Offline"; sub: ai.model; accent: ai.available ? root.green : root.textSec }
                StatTile { label: "PRIVACY"; value: privacy.active ? "On" : "Off"; sub: privacy.status; accent: privacy.active ? root.green : root.textSec }
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
                Text {
                    visible: cloud.syncStatus.length > 0
                    text: "·  " + cloud.syncStatus; color: root.textSec; font.pixelSize: 12
                }
            }

            // Cloud cards: open incidents + CVE feed
            RowLayout {
                Layout.fillWidth: true
                spacing: 16

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    Layout.alignment: Qt.AlignTop
                    Layout.preferredHeight: incCol.implicitHeight + 36
                    color: root.bgSurface; radius: 8; border.color: root.border
                    ColumnLayout {
                        id: incCol
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 18 }
                        spacing: 10
                        Text { text: "OPEN INCIDENTS"; color: root.textSec; font.pixelSize: 11; font.family: root.monoFont; font.letterSpacing: 2 }
                        Text {
                            visible: !cloud.active || cloud.error.length > 0 || (cloud.incidentsLoaded && cloud.openCount === 0) || !cloud.incidentsLoaded
                            text: !cloud.active ? "Sign in online to see incidents from your ShadowCypher account."
                                : cloud.error.length > 0 ? cloud.error
                                : !cloud.incidentsLoaded ? "Loading…"
                                : "No open incidents."
                            color: cloud.error.length > 0 && cloud.active ? root.red : root.textSec
                            font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true
                        }
                        Repeater {
                            model: cloud.active ? cloud.incidents.slice(0, 5) : []
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                Rectangle {
                                    width: 8; height: 8; radius: 4
                                    color: modelData.severity === "critical" || modelData.severity === "high" ? root.red
                                         : modelData.severity === "warning" || modelData.severity === "medium" ? root.amber
                                         : root.textSec
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    Text { text: modelData.title || "Incident"; color: root.textPri; font.pixelSize: 13; elide: Text.ElideRight; Layout.fillWidth: true }
                                    Text {
                                        text: (modelData.category || "") + (modelData.created_at ? "  ·  " + Qt.formatDateTime(new Date(modelData.created_at), "MMM d, hh:mm") : "")
                                        color: root.textSec; font.pixelSize: 11; font.family: root.monoFont
                                    }
                                }
                                Button {
                                    text: "Ack"
                                    onClicked: cloud.acknowledge(modelData.id)
                                    background: Rectangle { color: "transparent"; border.color: root.border; radius: 4 }
                                    contentItem: Text { text: parent.text; color: root.textSec; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                    padding: 0; leftPadding: 12; rightPadding: 12; implicitHeight: 26
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    Layout.alignment: Qt.AlignTop
                    Layout.preferredHeight: threatCol.implicitHeight + 36
                    color: root.bgSurface; radius: 8; border.color: root.border
                    ColumnLayout {
                        id: threatCol
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 18 }
                        spacing: 10
                        Text { text: "NEW CVEs · LAST 7 DAYS"; color: root.textSec; font.pixelSize: 11; font.family: root.monoFont; font.letterSpacing: 2 }
                        Text {
                            visible: !cloud.active || !cloud.threatsLoaded || cloud.threats.length === 0
                            text: !cloud.active ? "Sign in online to see the threat feed."
                                : !cloud.threatsLoaded ? (cloud.error.length > 0 ? "Threat feed unavailable." : "Loading…")
                                : "No new CVEs."
                            color: root.textSec; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true
                        }
                        Repeater {
                            model: cloud.active ? cloud.threats.slice(0, 6) : []
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                Text {
                                    text: modelData.id
                                    color: root.accent; font.pixelSize: 12; font.family: root.monoFont
                                    Layout.preferredWidth: 150
                                    MouseArea {
                                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                        // URL comes from the API; only open NVD pages.
                                        onClicked: if ((modelData.url || "").startsWith("https://nvd.nist.gov/")) Qt.openUrlExternally(modelData.url)
                                    }
                                }
                                Text {
                                    text: (modelData.severity || "N/A") + (modelData.cvss !== undefined && modelData.cvss !== null ? "  " + Number(modelData.cvss).toFixed(1) : "")
                                    color: modelData.severity === "CRITICAL" || modelData.severity === "HIGH" ? root.red
                                         : modelData.severity === "MEDIUM" ? root.amber : root.textSec
                                    font.pixelSize: 11; font.family: root.monoFont
                                    Layout.fillWidth: true
                                }
                                Text {
                                    text: modelData.published ? Qt.formatDate(new Date(modelData.published), "MMM d") : ""
                                    color: root.textSec; font.pixelSize: 11; font.family: root.monoFont
                                }
                            }
                        }
                    }
                }
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
