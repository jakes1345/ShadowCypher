// Shared inline components — NavItem, Toast, StatTile
// Imported by other QML files as needed.
import QtQuick
import QtQuick.Layouts

// ── NavItem ───────────────────────────────────────────────────────────────
component NavItem: Rectangle {
    property string icon
    property string label
    property bool   selected: false
    signal clicked

    height: 44
    color: selected ? Qt.rgba(180/255, 74/255, 255/255, 0.08) : "transparent"
    radius: 0

    Rectangle {
        visible: selected
        x: 0; width: 3; height: parent.height; radius: 1.5
        color: root.accent
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: selected ? 19 : 20
        anchors.rightMargin: 12
        spacing: 10
        Text {
            text: parent.parent.icon
            color: selected ? root.accent : root.textSec
            font.pixelSize: 14
        }
        Text {
            text: parent.parent.label
            color: selected ? root.textPri : root.textSec
            font.pixelSize: 13
            font.weight: selected ? Font.SemiBold : Font.Normal
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onEntered: if (!selected) parent.color = Qt.rgba(1,1,1,0.03)
        onExited:  if (!selected) parent.color = "transparent"
        onClicked: parent.clicked()
    }
}

// ── StatTile ──────────────────────────────────────────────────────────────
component StatTile: Rectangle {
    property string label
    property string value
    property string sub:   ""
    property color  accent: root.accent

    height: 100
    color: root.bgPanel
    radius: 8
    border.color: root.border

    ColumnLayout {
        anchors { fill: parent; margins: 20 }
        spacing: 4
        Text { text: parent.parent.label; color: root.textSec; font.pixelSize: 11; font.family: root.monoFont; font.letterSpacing: 2 }
        Text { text: parent.parent.value; color: parent.parent.accent; font.pixelSize: 28; font.weight: Font.Bold }
        Text { text: parent.parent.sub; color: root.textSec; font.pixelSize: 11; visible: text.length > 0 }
    }
}

// ── Toast ─────────────────────────────────────────────────────────────────
component Toast: Rectangle {
    id: toastRect
    width: 360; height: visible ? col.implicitHeight + 28 : 0
    radius: 8
    opacity: 0
    visible: false
    color: root.bgPanel
    border.color: _level === "error" ? root.red : _level === "warn" ? root.amber : root.border

    property string _title
    property string _message
    property string _level: "info"

    function show(t, m, l) {
        _title = t; _message = m; _level = l || "info"
        visible = true
        fadeIn.start()
    }

    ColumnLayout {
        id: col
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 14 }
        spacing: 2
        Text { text: toastRect._title;   color: root.textPri; font.pixelSize: 13; font.weight: Font.SemiBold }
        Text { text: toastRect._message; color: root.textSec; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
    }

    SequentialAnimation {
        id: fadeIn
        NumberAnimation { target: toastRect; property: "opacity"; to: 1; duration: 200 }
        PauseAnimation  { duration: 4000 }
        NumberAnimation { target: toastRect; property: "opacity"; to: 0; duration: 300 }
        ScriptAction    { script: toastRect.visible = false }
    }
}
