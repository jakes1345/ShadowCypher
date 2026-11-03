import QtQuick
import QtQuick.Layouts

Rectangle {
    id: sidebar
    color: root.bgSurface
    property int currentIndex: 0

    // Right border separator
    Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: root.border }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Logo / brand
        Item {
            Layout.fillWidth: true
            height: 64
            RowLayout {
                anchors.centerIn: parent
                spacing: 10
                Rectangle {
                    width: 28; height: 28
                    radius: 6
                    color: root.accent
                    opacity: 0.15
                    Rectangle {
                        anchors.centerIn: parent
                        width: 14; height: 14; radius: 3
                        color: root.accent
                    }
                }
                Text {
                    text: "ShadowCypher"
                    color: root.textPri
                    font.pixelSize: 14
                    font.weight: Font.SemiBold
                    font.family: root.monoFont
                }
            }
        }

        // Divider
        Rectangle { Layout.fillWidth: true; height: 1; color: root.border }

        // Nav items
        Repeater {
            model: [
                { icon: "⬡", label: "Dashboard",   idx: 0 },
                { icon: "⬢", label: "Network",      idx: 1 },
                { icon: "◈", label: "AI Assistant", idx: 2 },
                { icon: "◎", label: "Privacy",      idx: 3 },
                { icon: "⚙", label: "Settings",     idx: 4 }
            ]
            delegate: NavItem {
                Layout.fillWidth: true
                icon:     modelData.icon
                label:    modelData.label
                selected: sidebar.currentIndex === modelData.idx
                onClicked: sidebar.currentIndex = modelData.idx
            }
        }

        Item { Layout.fillHeight: true }

        // Status pill
        Rectangle {
            Layout.fillWidth: true
            Layout.margins: 12
            height: 36
            radius: 6
            color: scanner.running ? Qt.rgba(34/255, 197/255, 94/255, 0.08) : Qt.rgba(100/255, 116/255, 139/255, 0.06)
            border.color: scanner.running ? Qt.rgba(34/255, 197/255, 94/255, 0.25) : root.border
            RowLayout {
                anchors.centerIn: parent
                spacing: 6
                Rectangle {
                    width: 6; height: 6; radius: 3
                    color: scanner.running ? root.green : root.textSec
                    SequentialAnimation on opacity { running: scanner.running; loops: Animation.Infinite
                        NumberAnimation { to: 0.3; duration: 900 }
                        NumberAnimation { to: 1.0; duration: 900 }
                    }
                }
                Text {
                    text: scanner.running ? "Monitoring" : "Idle"
                    color: scanner.running ? root.green : root.textSec
                    font.pixelSize: 11
                    font.family: root.monoFont
                }
            }
        }
        Item { height: 12 }
    }
}
