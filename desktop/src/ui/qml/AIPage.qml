import QtQuick
import QtQuick.Layouts

Rectangle {
    color: root.bgBase

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Header bar
        Rectangle {
            Layout.fillWidth: true
            height: 72
            color: root.bgSurface
            border.color: root.border
            RowLayout {
                anchors { fill: parent; leftMargin: 32; rightMargin: 32 }
                ColumnLayout {
                    spacing: 4
                    Text { text: "AI Assistant"; color: root.textPri; font.pixelSize: 20; font.weight: Font.Bold }
                    RowLayout {
                        spacing: 6
                        Rectangle {
                            width: 7; height: 7; radius: 3.5
                            color: ai.available ? root.green : root.textSec
                        }
                        Text {
                            text: ai.available ? ("Ollama · " + ai.model) : "Ollama offline"
                            color: ai.available ? root.green : root.textSec
                            font.pixelSize: 12
                            font.family: root.monoFont
                        }
                    }
                }
                Item { Layout.fillWidth: true }
                Button {
                    text: "Check Ollama"
                    visible: !ai.available
                    onClicked: ai.checkAvailability()
                    background: Rectangle { color: root.bgPanel; border.color: root.border; radius: 6 }
                    contentItem: Text { text: parent.text; color: root.textSec; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter }
                    padding: 0; leftPadding: 16; rightPadding: 16; height: 32
                }
            }
        }

        // Offline notice
        Rectangle {
            Layout.fillWidth: true
            height: 56
            color: Qt.rgba(245/255,158/255,11/255,0.07)
            border.color: Qt.rgba(245/255,158/255,11/255,0.25)
            visible: !ai.available
            RowLayout {
                anchors { fill: parent; leftMargin: 24; rightMargin: 24 }
                spacing: 12
                Text { text: "⚠"; color: root.amber; font.pixelSize: 16 }
                Text {
                    text: "Ollama is not running. Start it with: ollama serve  •  Model: " + ai.model
                    color: root.amber; font.pixelSize: 13; font.family: root.monoFont
                }
            }
        }

        // Message list
        ListView {
            id: msgList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 16
            topMargin: 24
            bottomMargin: 24
            leftMargin: 32
            rightMargin: 32
            model: chatModel

            delegate: RowLayout {
                width: msgList.width - 64
                layoutDirection: role === "user" ? Qt.RightToLeft : Qt.LeftToRight
                spacing: 10

                // Avatar dot
                Rectangle {
                    width: 28; height: 28; radius: 14
                    color: role === "user" ? root.accent : root.bgPanel
                    border.color: root.border
                    Text {
                        anchors.centerIn: parent
                        text: role === "user" ? "U" : "AI"
                        color: role === "user" ? "#fff" : root.textSec
                        font.pixelSize: 10
                        font.family: root.monoFont
                    }
                }

                Rectangle {
                    Layout.maximumWidth: msgList.width * 0.72
                    height: bubble.implicitHeight + 20
                    radius: 8
                    color: role === "user"
                           ? Qt.rgba(180/255,74/255,255/255,0.12)
                           : root.bgPanel
                    border.color: role === "user"
                                  ? Qt.rgba(180/255,74/255,255/255,0.3)
                                  : root.border
                    Text {
                        id: bubble
                        anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 14 }
                        text: content
                        color: root.textPri
                        font.pixelSize: 13
                        wrapMode: Text.Wrap
                        lineHeight: 1.5
                    }
                }
                Item { Layout.fillWidth: true }
            }

            ScrollBar.vertical: ScrollBar {}

            onCountChanged: Qt.callLater(() => msgList.positionViewAtEnd())
        }

        // Thinking indicator
        Rectangle {
            Layout.fillWidth: true; height: 40
            color: "transparent"
            visible: ai.busy
            RowLayout {
                anchors { left: parent.left; leftMargin: 32; verticalCenter: parent.verticalCenter }
                spacing: 5
                Repeater {
                    model: 3
                    Rectangle {
                        width: 7; height: 7; radius: 3.5
                        color: root.accent
                        SequentialAnimation on opacity {
                            running: ai.busy; loops: Animation.Infinite
                            PauseAnimation  { duration: index * 180 }
                            NumberAnimation { to: 0.2; duration: 400 }
                            NumberAnimation { to: 1.0; duration: 400 }
                        }
                    }
                }
                Text { text: "Thinking…"; color: root.textSec; font.pixelSize: 12 }
            }
        }

        // Input bar
        Rectangle {
            Layout.fillWidth: true
            height: 72
            color: root.bgSurface
            border.color: root.border

            RowLayout {
                anchors { fill: parent; leftMargin: 24; rightMargin: 24; topMargin: 12; bottomMargin: 12 }
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true; height: 44
                    radius: 8
                    color: root.bgPanel
                    border.color: inputField.activeFocus ? root.accent : root.border

                    TextInput {
                        id: inputField
                        anchors { fill: parent; leftMargin: 16; rightMargin: 16; topMargin: 12; bottomMargin: 12 }
                        color: root.textPri
                        font.pixelSize: 13
                        clip: true
                        placeholderText: ai.available ? "Ask anything about your network…" : "Ollama offline"
                        enabled: ai.available && !ai.busy
                        Keys.onReturnPressed: sendMsg()
                    }
                }

                Button {
                    width: 80; height: 44
                    enabled: ai.available && !ai.busy && inputField.text.trim().length > 0
                    onClicked: sendMsg()
                    background: Rectangle {
                        color: parent.enabled ? root.accent : root.bgPanel
                        border.color: parent.enabled ? "transparent" : root.border
                        radius: 8
                        opacity: parent.enabled ? 1 : 0.5
                    }
                    contentItem: Text { text: "Send"; color: "#fff"; font.pixelSize: 13; horizontalAlignment: Text.AlignHCenter }
                }
            }
        }
    }

    ListModel { id: chatModel }

    property int _reqId: 0

    function sendMsg() {
        const text = inputField.text.trim()
        if (!text) return
        chatModel.append({ role: "user", content: text })
        inputField.text = ""
        _reqId++
        ai.query(text, _reqId)
    }

    Connections {
        target: ai
        function onQueryResult(requestId, response) {
            chatModel.append({ role: "assistant", content: response })
        }
        function onAvailableChanged() {
            if (ai.available && chatModel.count === 0) {
                chatModel.append({ role: "assistant", content: "Hello! I'm your local AI assistant running on " + ai.model + ". I can help you analyze network activity, explain security concepts, and answer questions about your system." })
            }
        }
    }
}
