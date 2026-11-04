import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Window {
    id: root
    width: 1280
    height: 800
    minimumWidth: 900
    minimumHeight: 600
    visible: true
    title: "ShadowCypher"
    color: "#0a0a0a"

    // ── Palette ──────────────────────────────────────────────────────────────
    readonly property color bgBase:     "#0a0a0a"
    readonly property color bgSurface:  "#111111"
    readonly property color bgPanel:    "#141414"
    readonly property color border:     "#1e1e1e"
    readonly property color accent:     "#b44aff"
    readonly property color accentDim:  "#7c29cc"
    readonly property color textPri:    "#f1f5f9"
    readonly property color textSec:    "#64748b"
    readonly property color green:      "#22c55e"
    readonly property color red:        "#ef4444"
    readonly property color amber:      "#f59e0b"
    readonly property string monoFont:  "JetBrains Mono,Cascadia Code,Consolas,monospace"

    // ── Login overlay (shown when not authenticated) ──────────────────────
    component LoginView: Rectangle {
        color: root.bgBase

        ColumnLayout {
            anchors.centerIn: parent
            width: 380
            spacing: 0

            // Logo
            ColumnLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 12
                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    width: 48; height: 48; radius: 12
                    color: Qt.rgba(180/255,74/255,255/255,0.12)
                    border.color: Qt.rgba(180/255,74/255,255/255,0.35)
                    Text { anchors.centerIn: parent; text: "◈"; color: root.accent; font.pixelSize: 22 }
                }
                Text { Layout.alignment: Qt.AlignHCenter; text: "ShadowCypher"; color: root.textPri; font.pixelSize: 22; font.weight: Font.Bold; font.family: root.monoFont }
                Text { Layout.alignment: Qt.AlignHCenter; text: "Network security platform"; color: root.textSec; font.pixelSize: 13 }
            }

            Item { height: 36 }

            // Card
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: loginCol.implicitHeight + 48
                color: root.bgSurface; radius: 12; border.color: root.border

                ColumnLayout {
                    id: loginCol
                    anchors { fill: parent; margins: 28 }
                    spacing: 20

                    Text { text: "Sign In"; color: root.textPri; font.pixelSize: 18; font.weight: Font.SemiBold }

                    ColumnLayout {
                        spacing: 8
                        Text { text: "API KEY"; color: root.textSec; font.pixelSize: 10; font.family: root.monoFont; font.letterSpacing: 2 }
                        Rectangle {
                            Layout.fillWidth: true; height: 44; radius: 8
                            color: root.bgPanel; border.color: loginKeyInput.activeFocus ? root.accent : root.border
                            TextField {
                                id: loginKeyInput
                                anchors.fill: parent
                                leftPadding: 16; rightPadding: 16
                                color: root.textPri; font.pixelSize: 13; font.family: root.monoFont
                                echoMode: TextField.Password
                                passwordCharacter: "•"
                                placeholderText: "sc_live_…"
                                Keys.onReturnPressed: doLogin()
                                background: Item {}
                            }
                        }
                    }

                    Text {
                        id: loginError
                        text: ""
                        color: root.red
                        font.pixelSize: 12
                        visible: text.length > 0
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }

                    Button {
                        Layout.fillWidth: true; height: 44
                        text: "Sign In"
                        onClicked: doLogin()
                        background: Rectangle { color: root.accent; radius: 8 }
                        contentItem: Text { text: parent.text; color: "#fff"; font.pixelSize: 14; font.weight: Font.Medium; horizontalAlignment: Text.AlignHCenter }
                    }

                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: "Get an API key at shadowcypher.site"
                        color: root.textSec; font.pixelSize: 12
                    }
                }
            }
        }

        function doLogin() {
            const key = loginKeyInput.text.trim()
            if (!key.match(/^sc_live_[a-f0-9]{48}$/)) {
                loginError.text = "Invalid key format. Expected sc_live_ + 48 hex chars."
                return
            }
            loginError.text = ""
            app.login(key)
        }

        Connections {
            target: app
            function onNotification(title, message, level) {
                if (level === "error") loginError.text = message
            }
        }
    }

    Loader {
        anchors.fill: parent
        active: !app.authenticated
        sourceComponent: LoginView {}
        z: 100
    }

    // ── Main layout ───────────────────────────────────────────────────────
    RowLayout {
        anchors.fill: parent
        spacing: 0
        visible: app.authenticated

        Sidebar {
            id: sidebar
            Layout.fillHeight: true
            Layout.preferredWidth: 220
        }

        // Page area
        StackLayout {
            id: pages
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: sidebar.currentIndex

            DashboardPage {}
            NetworkPage    {}
            AIPage         {}
            PrivacyPage    {}
            SettingsPage   {}
        }
    }

    // ── Notification toast ────────────────────────────────────────────────
    Connections {
        target: app
        function onNotification(title, message, level) {
            toast.show(title, message, level)
        }
    }

    Toast { id: toast; anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter; anchors.bottomMargin: 24 }
}
