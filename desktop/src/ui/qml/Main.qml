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

                    // ── Browser (device-code) sign-in ──────────────────────────
                    Button {
                        Layout.fillWidth: true; height: 44
                        visible: !app.deviceAuthActive
                        text: "Sign in with browser"
                        enabled: !app.authBusy
                        onClicked: { loginError.text = ""; app.startDeviceLogin(loginBaseInput.text) }
                        background: Rectangle { color: root.accent; radius: 8; opacity: parent.enabled ? 1 : 0.6 }
                        contentItem: Text { text: parent.text; color: "#fff"; font.pixelSize: 14; font.weight: Font.Medium; horizontalAlignment: Text.AlignHCenter }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        visible: app.deviceAuthActive
                        implicitHeight: deviceCol.implicitHeight + 36
                        color: root.bgPanel; radius: 8; border.color: root.border
                        ColumnLayout {
                            id: deviceCol
                            anchors { fill: parent; margins: 18 }
                            spacing: 10
                            Text {
                                text: app.deviceUserCode ? "Enter this code on the ShadowCypher sign-in page:" : "Requesting a sign-in code…"
                                color: root.textSec; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true
                            }
                            Text {
                                visible: app.deviceUserCode.length > 0
                                Layout.alignment: Qt.AlignHCenter
                                text: app.deviceUserCode
                                color: root.textPri; font.pixelSize: 28; font.family: root.monoFont; font.letterSpacing: 4
                            }
                            Button {
                                visible: app.deviceUserCode.length > 0
                                Layout.fillWidth: true; height: 40
                                text: "Open sign-in page"
                                onClicked: app.openDeviceVerifyPage()
                                background: Rectangle { color: root.accent; radius: 8 }
                                contentItem: Text { text: parent.text; color: "#fff"; font.pixelSize: 13; horizontalAlignment: Text.AlignHCenter }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    visible: app.deviceUserCode.length > 0
                                    text: "Waiting for approval…"; color: root.textSec; font.pixelSize: 12
                                    Layout.fillWidth: true
                                }
                                Item { Layout.fillWidth: true; visible: app.deviceUserCode.length === 0 }
                                Text {
                                    text: "Cancel"; color: root.accent; font.pixelSize: 12
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: app.cancelDeviceLogin() }
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: !app.deviceAuthActive
                        spacing: 10
                        Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                        Text { text: "or paste an API key"; color: root.textSec; font.pixelSize: 11 }
                        Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                    }

                    ColumnLayout {
                        spacing: 8
                        visible: !app.deviceAuthActive
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

                    ColumnLayout {
                        spacing: 8
                        visible: !app.deviceAuthActive
                        Text { text: "API SERVER"; color: root.textSec; font.pixelSize: 10; font.family: root.monoFont; font.letterSpacing: 2 }
                        Rectangle {
                            Layout.fillWidth: true; height: 44; radius: 8
                            color: root.bgPanel; border.color: loginBaseInput.activeFocus ? root.accent : root.border
                            TextField {
                                id: loginBaseInput
                                anchors.fill: parent
                                leftPadding: 16; rightPadding: 16
                                color: root.textPri; font.pixelSize: 13; font.family: root.monoFont
                                text: config.apiBase
                                placeholderText: "https://api.shadowcypher.site"
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
                        visible: !app.deviceAuthActive
                        text: app.authBusy ? "Checking…" : "Sign in with key"
                        enabled: !app.authBusy
                        onClicked: doLogin()
                        background: Rectangle { color: "transparent"; border.color: root.accent; radius: 8; opacity: parent.enabled ? 1 : 0.6 }
                        contentItem: Text { text: parent.text; color: root.accent; font.pixelSize: 14; font.weight: Font.Medium; horizontalAlignment: Text.AlignHCenter }
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
            loginError.text = ""
            app.login(loginKeyInput.text, loginBaseInput.text)
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
