// ShadowOS SDDM — login screen (QtQuick 2.15, no Controls import)
import QtQuick 2.15

Rectangle {
    id: root
    width: 1920
    height: 1080
    color: "#080c12"

    property string accent: "#00e0a4"
    property string fg: "#e6edf3"
    property string muted: "#8b949e"
    property string panel: "#0d1117"
    property bool liveDemo: userModel && userModel.lastUser === "shadow"

    Image {
        anchors.fill: parent
        source: "wallpaper.png"
        fillMode: Image.PreserveAspectCrop
        opacity: 0.42
        smooth: true
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#cc080c12" }
            GradientStop { position: 0.55; color: "#99080c12" }
            GradientStop { position: 1.0; color: "#dd080c12" }
        }
    }

    // Top bar — matches desktop Waybar tone
    Rectangle {
        id: topBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 24
        height: 44
        radius: 12
        color: "#cc0d1117"
        border.color: "#1fffffff"
        border.width: 1

        Row {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 18
            spacing: 10
            Text {
                text: "S"
                color: root.accent
                font.pixelSize: 15
                font.bold: true
            }
            Text {
                text: "ShadowOS"
                color: root.fg
                font.pixelSize: 14
                font.bold: true
            }
            Text {
                text: "·"
                color: root.muted
                font.pixelSize: 14
            }
            Text {
                text: "v0.3"
                color: root.muted
                font.pixelSize: 13
            }
        }

        Text {
            id: clock
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.rightMargin: 18
            color: root.fg
            font.pixelSize: 14
            font.bold: true
            text: Qt.formatDateTime(new Date(), "HH:mm · ddd MMM d")
        }
    }

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: clock.text = Qt.formatDateTime(new Date(), "HH:mm · ddd MMM d")
    }

    // Live ISO demo banner
    Rectangle {
        visible: root.liveDemo
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: topBar.bottom
        anchors.topMargin: 16
        width: liveText.width + 32
        height: 34
        radius: 17
        color: "#332196f3"
        border.color: "#552196f3"
        border.width: 1
        Text {
            id: liveText
            anchors.centerIn: parent
            text: "Live demo  ·  user shadow  ·  password shadow  ·  install for your own account"
            color: "#79c0ff"
            font.pixelSize: 11
        }
    }

    // Login card
    Rectangle {
        id: loginCard
        width: 400
        height: loginCol.height + 48
        anchors.centerIn: parent
        radius: 16
        color: "#ee0d1117"
        border.color: pwd.activeFocus ? root.accent : "#22ffffff"
        border.width: pwd.activeFocus ? 2 : 1

        Column {
            id: loginCol
            anchors.centerIn: parent
            spacing: 18
            width: parent.width - 56

            Text {
                text: "Sign in"
                color: root.fg
                font.pixelSize: 22
                font.bold: true
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Text {
                text: "Sovereign security workstation"
                color: root.muted
                font.pixelSize: 12
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Item { width: 1; height: 4 }

            Text {
                text: userModel && userModel.lastUser ? userModel.lastUser : "shadow"
                color: root.accent
                font.pixelSize: 15
                font.bold: true
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Rectangle {
                id: pwdBox
                width: parent.width
                height: 48
                radius: 10
                color: "#161b22"
                border.color: pwd.activeFocus ? root.accent : "#33ffffff"
                border.width: 1

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 14
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Password"
                    color: root.muted
                    font.pixelSize: 14
                    visible: pwd.text.length === 0 && !pwd.activeFocus
                }

                TextInput {
                    id: pwd
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14
                    verticalAlignment: TextInput.AlignVCenter
                    echoMode: TextInput.Password
                    color: root.fg
                    selectionColor: root.accent
                    font.pixelSize: 14
                    focus: true
                    onAccepted: {
                        // Find shadowos session index, fall back to 0
                        var idx = 0
                        if (sessionModel) {
                            for (var i = 0; i < sessionModel.rowCount(); i++) {
                                var name = sessionModel.data(sessionModel.index(i, 0), Qt.DisplayRole) || ""
                                if (name.toLowerCase().indexOf("shadowos") >= 0) { idx = i; break }
                            }
                        }
                        sddm.login(
                            userModel && userModel.lastUser ? userModel.lastUser : "shadow",
                            text,
                            idx
                        )
                    }
                    Component.onCompleted: forceActiveFocus()
                }
            }

            Text {
                text: "Enter to unlock  ·  Hyprland session"
                color: root.muted
                opacity: 0.7
                font.pixelSize: 10
                anchors.horizontalCenter: parent.horizontalCenter
            }
        }
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 36
        text: "Security  ·  Development  ·  Gaming"
        color: "#484f58"
        font.pixelSize: 11
        font.letterSpacing: 1
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            pwd.text = ""
            pwd.forceActiveFocus()
            loginCard.border.color = "#ff6b6b"
        }
    }
}
