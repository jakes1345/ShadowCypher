import QtQuick
import QtQuick.Layouts

Rectangle {
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
