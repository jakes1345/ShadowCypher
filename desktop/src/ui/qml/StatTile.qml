import QtQuick
import QtQuick.Layouts

Rectangle {
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
