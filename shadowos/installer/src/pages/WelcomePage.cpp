#include "WelcomePage.h"
#include "../theme.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QGridLayout>

WelcomePage::WelcomePage(QWidget* parent) : QWidget(parent) {
    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(48, 40, 48, 40);
    lay->setSpacing(20);

    auto* tag = new QLabel("WELCOME");
    tag->setStyleSheet(QString("font-size:9px;font-weight:800;letter-spacing:5px;"
                               "color:%1;font-family:'JetBrains Mono',monospace;").arg(Theme::ACCENT));

    auto* title = new QLabel("ShadowOS Installer");
    title->setStyleSheet("font-size:32px;font-weight:900;color:#E6EDF3;");

    auto* sub = new QLabel(
        "A sovereign security platform built on Arch Linux.\n"
        "This wizard will install ShadowOS to your machine in a few steps."
    );
    sub->setStyleSheet(QString("font-size:13px;color:%1;line-height:1.5;").arg(Theme::TEXT_SEC));
    sub->setWordWrap(true);

    // Divider
    auto* divider = new QFrame;
    divider->setFrameShape(QFrame::HLine);
    divider->setStyleSheet("border: none; border-top: 1px solid rgba(0,224,164,0.15);");

    // Feature grid
    struct Feature { const char* icon; const char* name; const char* desc; };
    static const Feature features[] = {
        {"⟳", "Shadow Modes",      "Hot-swap posture: normal, pentest, privacy, ghost, amnesia"},
        {"⊛", "AnonSurf",          "System-wide Tor routing via nftables — one keybind"},
        {"◌", "Amnesia Mode",      "Ephemeral home on RAM, RAM wipe on shutdown (Tails-inspired)"},
        {"⬢", "VM Compartments",   "Trust-level isolation via KVM/QEMU (Qubes-inspired)"},
        {"◈", "Gaming & SteamOS",  "gamescope Big Picture, Steam Proton, MangoHUD"},
        {"⬡", "ShadowCypher",      "Local AI, Guardian agent, tactical arsenal — built in"},
    };

    auto* grid = new QGridLayout;
    grid->setSpacing(12);
    for (int i = 0; i < 6; ++i) {
        auto* card = new QWidget;
        card->setStyleSheet(QString(
            "QWidget { background:%1; border:1px solid %2; border-radius:10px; padding:14px 18px; }"
        ).arg(Theme::BG_SURFACE, Theme::BORDER));
        auto* cl = new QVBoxLayout(card);
        cl->setContentsMargins(14, 12, 14, 12);
        cl->setSpacing(4);
        auto* top = new QHBoxLayout;
        auto* ico = new QLabel(features[i].icon);
        ico->setStyleSheet(QString("font-size:16px;color:%1;").arg(Theme::ACCENT));
        auto* nm  = new QLabel(features[i].name);
        nm->setStyleSheet("font-size:12px;font-weight:700;color:#E6EDF3;");
        top->addWidget(ico);
        top->addWidget(nm);
        top->addStretch();
        cl->addLayout(top);
        auto* dl = new QLabel(features[i].desc);
        dl->setStyleSheet(QString("font-size:11px;color:%1;").arg(Theme::TEXT_SEC));
        dl->setWordWrap(true);
        cl->addWidget(dl);
        grid->addWidget(card, i / 2, i % 2);
    }

    auto* note = new QLabel(
        "  Before continuing: connect to the internet, and identify the disk you want to erase."
    );
    note->setStyleSheet(QString(
        "font-size:12px;color:%1;"
        "background:rgba(255,221,0,0.06);"
        "border:1px solid rgba(255,221,0,0.28);"
        "border-radius:7px;padding:10px 14px;"
    ).arg(Theme::WARNING));
    note->setWordWrap(true);

    lay->addWidget(tag);
    lay->addWidget(title);
    lay->addWidget(sub);
    lay->addWidget(divider);
    lay->addLayout(grid);
    lay->addWidget(note);
    lay->addStretch();
}
