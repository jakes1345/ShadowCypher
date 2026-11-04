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

            Text { text: "Settings"; color: root.textPri; font.pixelSize: 24; font.weight: Font.Bold }

            // API section
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: apiCol.implicitHeight + 40
                color: root.bgSurface; radius: 8; border.color: root.border
                ColumnLayout {
                    id: apiCol
                    anchors { fill: parent; margins: 24 }
                    spacing: 20

                    Text { text: "API Connection"; color: root.textPri; font.pixelSize: 15; font.weight: Font.SemiBold }

                    ColumnLayout {
                        spacing: 8
                        Text { text: "API BASE URL"; color: root.textSec; font.pixelSize: 10; font.family: root.monoFont; font.letterSpacing: 2 }
                        Rectangle {
                            Layout.fillWidth: true; height: 40; radius: 6
                            color: root.bgPanel; border.color: apiBaseInput.activeFocus ? root.accent : root.border
                            TextInput {
                                id: apiBaseInput
                                anchors { fill: parent; leftMargin: 14; rightMargin: 14; topMargin: 10; bottomMargin: 10 }
                                text: config.apiBase
                                color: root.textPri; font.pixelSize: 13; font.family: root.monoFont
                                onEditingFinished: if (text !== config.apiBase) config.apiBase = text
                            }
                        }
                    }

                    ColumnLayout {
                        spacing: 8
                        Text { text: "API KEY"; color: root.textSec; font.pixelSize: 10; font.family: root.monoFont; font.letterSpacing: 2 }
                        Rectangle {
                            Layout.fillWidth: true; height: 40; radius: 6
                            color: root.bgPanel; border.color: apiKeyInput.activeFocus ? root.accent : root.border
                            TextInput {
                                id: apiKeyInput
                                anchors { fill: parent; leftMargin: 14; rightMargin: 14; topMargin: 10; bottomMargin: 10 }
                                text: config.apiKey
                                color: root.textPri; font.pixelSize: 13; font.family: root.monoFont
                                echoMode: TextInput.Password
                                passwordCharacter: "•"
                                onEditingFinished: if (text !== config.apiKey) app.login(text)
                            }
                        }
                        Text { text: "Pattern: sc_live_ + 48 hex characters"; color: root.textSec; font.pixelSize: 11 }
                    }
                }
            }

            // Scanner section
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: scanCol.implicitHeight + 40
                color: root.bgSurface; radius: 8; border.color: root.border
                ColumnLayout {
                    id: scanCol
                    anchors { fill: parent; margins: 24 }
                    spacing: 20

                    Text { text: "Network Scanner"; color: root.textPri; font.pixelSize: 15; font.weight: Font.SemiBold }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 24
                        ColumnLayout {
                            spacing: 8
                            Text { text: "SCAN INTERVAL (SECONDS)"; color: root.textSec; font.pixelSize: 10; font.family: root.monoFont; font.letterSpacing: 2 }
                            Rectangle {
                                width: 120; height: 40; radius: 6
                                color: root.bgPanel; border.color: intervalInput.activeFocus ? root.accent : root.border
                                TextInput {
                                    id: intervalInput
                                    anchors { fill: parent; leftMargin: 14; rightMargin: 14; topMargin: 10; bottomMargin: 10 }
                                    text: config.scanInterval.toString()
                                    color: root.textPri; font.pixelSize: 13; font.family: root.monoFont
                                    inputMethodHints: Qt.ImhDigitsOnly
                                    validator: IntValidator { bottom: 30; top: 86400 }
                                    onEditingFinished: config.scanInterval = parseInt(text)
                                }
                            }
                        }
                        ColumnLayout {
                            spacing: 8
                            Text { text: ""; font.pixelSize: 10 }
                            Text { text: "Minimum 30 seconds · Default 600 (10 min)"; color: root.textSec; font.pixelSize: 12 }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 16
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            Text { text: "Sync scans to my ShadowCypher account"; color: root.textPri; font.pixelSize: 13 }
                            Text {
                                text: "Uploads each scan's device list (MAC, IP, hostname) so new devices raise incidents in your account. Off by default; nothing leaves this machine unless you turn it on."
                                color: root.textSec; font.pixelSize: 11; wrapMode: Text.Wrap; Layout.fillWidth: true
                            }
                        }
                        Switch {
                            id: syncSwitch
                            checked: config.syncScans
                            onToggled: config.syncScans = checked
                        }
                    }
                }
            }

            // AI section
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: aiCol.implicitHeight + 40
                color: root.bgSurface; radius: 8; border.color: root.border
                ColumnLayout {
                    id: aiCol
                    anchors { fill: parent; margins: 24 }
                    spacing: 20

                    Text { text: "Local AI (Ollama)"; color: root.textPri; font.pixelSize: 15; font.weight: Font.SemiBold }

                    ColumnLayout {
                        spacing: 8
                        Text { text: "MODEL"; color: root.textSec; font.pixelSize: 10; font.family: root.monoFont; font.letterSpacing: 2 }
                        Rectangle {
                            Layout.fillWidth: true; height: 40; radius: 6
                            color: root.bgPanel; border.color: modelInput.activeFocus ? root.accent : root.border
                            TextInput {
                                id: modelInput
                                anchors { fill: parent; leftMargin: 14; rightMargin: 14; topMargin: 10; bottomMargin: 10 }
                                text: ai.model
                                color: root.textPri; font.pixelSize: 13; font.family: root.monoFont
                                onEditingFinished: ai.model = text
                            }
                        }
                        Text { text: "Examples: mistral:latest, llama3.2, phi4-mini, gemma3:4b"; color: root.textSec; font.pixelSize: 11 }
                    }

                    RowLayout {
                        spacing: 10
                        Button {
                            text: "Check Ollama"
                            onClicked: ai.checkAvailability()
                            background: Rectangle { color: root.bgPanel; border.color: root.border; radius: 6 }
                            contentItem: Text { text: parent.text; color: root.textSec; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter }
                            padding: 0; leftPadding: 16; rightPadding: 16; height: 34
                        }
                        Text {
                            text: ai.available ? ("● Connected · " + ai.model) : "● Offline"
                            color: ai.available ? root.green : root.textSec
                            font.pixelSize: 12; font.family: root.monoFont
                        }
                    }
                }
            }

            // About section
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: aboutRow.implicitHeight + 32
                color: root.bgSurface; radius: 8; border.color: root.border
                RowLayout {
                    id: aboutRow
                    anchors { fill: parent; margins: 24 }
                    spacing: 20
                    ColumnLayout {
                        spacing: 4
                        Text { text: "ShadowCypher Desktop"; color: root.textPri; font.pixelSize: 14; font.weight: Font.SemiBold }
                        Text { text: "v" + app.version; color: root.textSec; font.pixelSize: 12; font.family: root.monoFont }
                        Text { text: "Network monitoring · CVE lookup · Local AI · Privacy mode"; color: root.textSec; font.pixelSize: 12 }
                    }
                    Item { Layout.fillWidth: true }
                    Button {
                        text: "Logout"
                        onClicked: app.logout()
                        background: Rectangle {
                            color: "transparent"; border.color: Qt.rgba(239/255,68/255,68/255,0.3); radius: 6
                        }
                        contentItem: Text { text: parent.text; color: root.red; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter }
                        padding: 0; leftPadding: 20; rightPadding: 20; height: 36
                    }
                }
            }
        }
    }
}
