import QtQuick 2.15
import calamares.slideshow 1.0

Presentation {
    id: presentation

    Slide {
        Text {
            anchors.centerIn: parent
            text: "Welcome to ShadowOS\n\nA sovereign tactical platform."
            wrapMode: Text.WordWrap
            width: parent.width
            horizontalAlignment: Text.Center
            color: "#E6EDF3"
            font.family: "JetBrainsMono Nerd Font"
            font.pixelSize: 22
        }
    }

    Slide {
        Text {
            anchors.centerIn: parent
            text: "privacy is a posture\n\nMAC randomization, Tor toggle, encrypted DNS,\nfirejail-sandboxed browsers — all one keybind away."
            wrapMode: Text.WordWrap
            width: parent.width
            horizontalAlignment: Text.Center
            color: "#C9D1D9"
            font.family: "JetBrainsMono Nerd Font"
            font.pixelSize: 18
        }
    }

    Slide {
        Text {
            anchors.centerIn: parent
            text: "ShadowCypher built in\n\nLocal AI, Guardian agent, tactical arsenal —\nthe full ShadowCypher platform installed by default."
            wrapMode: Text.WordWrap
            width: parent.width
            horizontalAlignment: Text.Center
            color: "#C9D1D9"
            font.family: "JetBrainsMono Nerd Font"
            font.pixelSize: 18
        }
    }
}
