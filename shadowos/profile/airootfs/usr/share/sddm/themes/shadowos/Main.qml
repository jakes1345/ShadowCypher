// ShadowOS SDDM theme — pure QtQuick, no Controls/Layouts imports
// so it works across Qt5 and Qt6 SDDM builds.
import QtQuick 2.15

Rectangle {
    id: root
    width: 1920
    height: 1080
    color: "#05080C"

    property string accent: "#00E0A4"
    property string fg:     "#E6EDF3"
    property string muted:  "#6B7785"

    Image {
        anchors.fill: parent
        source: "/usr/share/backgrounds/shadowos/wallpaper.png"
        fillMode: Image.PreserveAspectCrop
        opacity: 0.55
        smooth: true
    }

    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: 0.45
    }

    // === Corner brackets ===
    Item {
        anchors.fill: parent
        anchors.margins: 40
        Rectangle { width: 40; height: 2; color: "#1F2A36"; anchors.top: parent.top; anchors.left: parent.left }
        Rectangle { width: 2; height: 40; color: "#1F2A36"; anchors.top: parent.top; anchors.left: parent.left }
        Rectangle { width: 40; height: 2; color: "#1F2A36"; anchors.top: parent.top; anchors.right: parent.right }
        Rectangle { width: 2; height: 40; color: "#1F2A36"; anchors.top: parent.top; anchors.right: parent.right }
        Rectangle { width: 40; height: 2; color: "#1F2A36"; anchors.bottom: parent.bottom; anchors.left: parent.left }
        Rectangle { width: 2; height: 40; color: "#1F2A36"; anchors.bottom: parent.bottom; anchors.left: parent.left }
        Rectangle { width: 40; height: 2; color: "#1F2A36"; anchors.bottom: parent.bottom; anchors.right: parent.right }
        Rectangle { width: 2; height: 40; color: "#1F2A36"; anchors.bottom: parent.bottom; anchors.right: parent.right }
    }

    // === Top-left mark ===
    Row {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: 70
        spacing: 14
        Rectangle { width: 50; height: 2; color: root.accent; anchors.verticalCenter: parent.verticalCenter }
        Text {
            text: "SHADOWOS  ·  v0.3"
            color: root.muted
            font.family: "JetBrainsMono Nerd Font"
            font.pixelSize: 12
            font.letterSpacing: 3
        }
    }

    // === Top-right clock ===
    Text {
        id: clock
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 70
        color: root.fg
        opacity: 0.85
        font.family: "JetBrainsMono Nerd Font"
        font.pixelSize: 14
        font.letterSpacing: 2
        text: Qt.formatDateTime(new Date(), "HH:mm  ·  ddd MMM dd")
    }
    Timer { interval: 1000; running: true; repeat: true
        onTriggered: clock.text = Qt.formatDateTime(new Date(), "HH:mm  ·  ddd MMM dd")
    }

    // === Center stack ===
    Column {
        anchors.centerIn: parent
        spacing: 28

        // Hex monogram
        Item {
            width: 160; height: 160
            anchors.horizontalCenter: parent.horizontalCenter

            Canvas {
                anchors.fill: parent
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.clearRect(0, 0, width, height)
                    var cx = width/2, cy = height/2, r = 72
                    ctx.beginPath()
                    for (var i = 0; i < 6; i++) {
                        var a = (Math.PI/3) * i - Math.PI/2
                        var x = cx + r * Math.cos(a)
                        var y = cy + r * Math.sin(a)
                        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
                    }
                    ctx.closePath()
                    ctx.fillStyle = "#0B1018"
                    ctx.fill()
                    ctx.strokeStyle = root.accent
                    ctx.lineWidth = 2.5
                    ctx.stroke()
                }
            }
            Text {
                anchors.centerIn: parent
                text: "S"
                color: root.fg
                font.family: "JetBrainsMono Nerd Font"
                font.pixelSize: 90
                font.bold: true
            }
        }

        Text {
            text: "SHADOWOS"
            color: root.fg
            font.family: "JetBrainsMono Nerd Font"
            font.pixelSize: 32
            font.letterSpacing: 10
            font.bold: true
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Text {
            text: "privacy is a posture"
            color: root.muted
            font.family: "JetBrainsMono Nerd Font"
            font.pixelSize: 12
            font.letterSpacing: 6
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Item { height: 18; width: 1 }

        // User name
        Text {
            text: userModel && userModel.lastUser ? userModel.lastUser : "shadow"
            color: root.fg
            font.family: "JetBrainsMono Nerd Font"
            font.pixelSize: 16
            anchors.horizontalCenter: parent.horizontalCenter
        }

        // === Password field — pure QtQuick TextInput, no Controls ===
        Rectangle {
            id: pwdBox
            width: 340; height: 52
            radius: 10
            color: "#11161DCC"
            border.color: pwd.activeFocus ? root.accent : "#1F2A36"
            border.width: pwd.activeFocus ? 2 : 1
            anchors.horizontalCenter: parent.horizontalCenter

            Text {
                anchors.left: parent.left
                anchors.leftMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                text: "password"
                color: root.muted
                font.family: "JetBrainsMono Nerd Font"
                font.pixelSize: 15
                visible: pwd.text.length === 0
            }

            TextInput {
                id: pwd
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                verticalAlignment: TextInput.AlignVCenter
                echoMode: TextInput.Password
                color: root.fg
                selectionColor: root.accent
                font.family: "JetBrainsMono Nerd Font"
                font.pixelSize: 15
                focus: true
                onAccepted: sddm.login(
                    userModel && userModel.lastUser ? userModel.lastUser : "shadow",
                    text,
                    sessionModel ? sessionModel.lastIndex : 0
                )
                Component.onCompleted: forceActiveFocus()
            }
        }

        Text {
            text: "press enter to unlock"
            color: root.muted
            opacity: 0.55
            font.family: "JetBrainsMono Nerd Font"
            font.pixelSize: 10
            font.letterSpacing: 3
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }

    // === Bottom-right tagline ===
    Text {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 70
        text: "SECURE  ·  ISOLATED  ·  AMNESIC"
        color: "#3D4651"
        font.family: "JetBrainsMono Nerd Font"
        font.pixelSize: 11
        font.letterSpacing: 3
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            pwd.text = ""
            pwd.forceActiveFocus()
        }
    }
}
