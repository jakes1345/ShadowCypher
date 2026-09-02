#include "ProfilePage.h"
#include "../theme.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QLabel>
#include <QFrame>
#include <QRadioButton>

struct ProfileInfo {
    const char* id;
    const char* icon;
    const char* name;
    const char* accent;
    const char* desc;
    const char* tags;
};

static const ProfileInfo PROFILES[] = {
    {
        "standard", "◎", "Standard",
        "#00E0A4",
        "Privacy-hardened daily-driver. Hyprland + Omarchy tools, AnonSurf, hardened kernel, AppArmor.",
        "Daily driver · Privacy · Desktop"
    },
    {
        "pentest", "◈", "Pentest",
        "#F87171",
        "Offensive security suite. Includes Parrot's arsenal: nmap, Metasploit, Burp, aircrack, Ghidra.",
        "Red team · CTF · Exploit dev"
    },
    {
        "privacy", "◌", "Privacy / Ghost",
        "#00B4D8",
        "Maximum anonymity. Amnesia mode on, RAM wipe, Tor-only routing, no swap, minimal footprint.",
        "Anonymity · Journalism · OPSEC"
    },
    {
        "gaming", "◇", "Gaming",
        "#FFDD00",
        "SteamOS-inspired. gamescope, Steam Proton, MangoHUD, gamemode, controller support.",
        "Steam · Proton · Big Picture"
    },
};

ProfilePage::ProfilePage(InstallState* state, QWidget* parent)
    : QWidget(parent), m_state(state)
{
    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(48, 40, 48, 40);
    lay->setSpacing(16);

    auto* tag = new QLabel("STEP 04 — PROFILE");
    tag->setStyleSheet(QString("font-size:9px;font-weight:800;letter-spacing:5px;"
                               "color:%1;font-family:'JetBrains Mono',monospace;").arg(Theme::ACCENT));
    auto* title = new QLabel("Choose Your Profile");
    title->setStyleSheet("font-size:28px;font-weight:900;color:#E6EDF3;");
    auto* sub = new QLabel(
        "Profiles determine which packages and configurations are applied. "
        "You can switch profiles after install using  shadow-mode."
    );
    sub->setStyleSheet(QString("font-size:13px;color:%1;").arg(Theme::TEXT_SEC));
    sub->setWordWrap(true);

    auto* divider = new QFrame;
    divider->setFrameShape(QFrame::HLine);
    divider->setStyleSheet("border: none; border-top: 1px solid rgba(0,224,164,0.12);");

    m_group = new QButtonGroup(this);
    auto* grid = new QGridLayout;
    grid->setSpacing(12);

    for (int i = 0; i < 4; ++i) {
        const auto& p = PROFILES[i];

        auto* card = new QWidget;
        QString accentHex = p.accent;
        card->setStyleSheet(QString(
            "QWidget { background:%1; border:1px solid %2;"
            " border-radius:12px; }"
        ).arg(Theme::BG_SURFACE, Theme::BORDER_DIM));

        auto* cl = new QVBoxLayout(card);
        cl->setContentsMargins(18, 16, 18, 16);
        cl->setSpacing(6);

        auto* topRow = new QHBoxLayout;
        auto* rb = new QRadioButton;
        rb->setStyleSheet(QString(
            "QRadioButton::indicator { width:18px; height:18px; border-radius:9px;"
            " border:2px solid %1; background:transparent; }"
            "QRadioButton::indicator:checked { background:%1; border-color:%1; }"
        ).arg(accentHex));
        m_group->addButton(rb, i);

        auto* ico = new QLabel(p.icon);
        ico->setStyleSheet(QString("font-size:20px;color:%1;").arg(accentHex));
        auto* nm = new QLabel(p.name);
        nm->setStyleSheet("font-size:14px;font-weight:700;color:#E6EDF3;");

        topRow->addWidget(rb);
        topRow->addWidget(ico);
        topRow->addWidget(nm);
        topRow->addStretch();

        auto* dl = new QLabel(p.desc);
        dl->setStyleSheet(QString("font-size:12px;color:%1;").arg(Theme::TEXT_SEC));
        dl->setWordWrap(true);

        auto* taglbl = new QLabel(p.tags);
        taglbl->setStyleSheet(QString("font-size:10px;color:%1;letter-spacing:1px;").arg(accentHex));

        cl->addLayout(topRow);
        cl->addWidget(dl);
        cl->addWidget(taglbl);

        const QString id = p.id;
        connect(rb, &QRadioButton::toggled, this, [this, id, card, accentHex](bool checked) {
            if (checked) {
                m_state->profile = id;
                card->setStyleSheet(QString(
                    "QWidget { background:%1; border:2px solid %2; border-radius:12px; }"
                ).arg(Theme::BG_CARD, accentHex));
            } else {
                card->setStyleSheet(QString(
                    "QWidget { background:%1; border:1px solid %2; border-radius:12px; }"
                ).arg(Theme::BG_SURFACE, Theme::BORDER_DIM));
            }
        });

        if (m_state->profile == p.id) {
            rb->setChecked(true);
        }

        grid->addWidget(card, i / 2, i % 2);
    }

    if (!m_group->checkedButton()) {
        m_group->button(0)->setChecked(true);
    }

    lay->addWidget(tag);
    lay->addWidget(title);
    lay->addWidget(sub);
    lay->addWidget(divider);
    lay->addLayout(grid);
    lay->addStretch();
}

bool ProfilePage::validate() {
    return m_group->checkedButton() != nullptr;
}

void ProfilePage::save() {
    int id = m_group->checkedId();
    if (id >= 0 && id < 4) {
        m_state->profile = PROFILES[id].id;
    }
}
