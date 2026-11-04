import QtQuick
import QtQuick.Layouts

Rectangle {
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
