#include "FinishPage.h"
#include "../theme.h"
#include <QVBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QProcess>

FinishPage::FinishPage(bool success, QWidget* parent)
    : QWidget(parent)
{
    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(48, 60, 48, 60);
    lay->setSpacing(20);
    lay->addStretch();

    if (success) {
        auto* ico = new QLabel("✓");
        ico->setStyleSheet(QString("font-size:64px;color:%1;").arg(Theme::ACCENT));
        ico->setAlignment(Qt::AlignCenter);

        auto* title = new QLabel("ShadowOS Installed");
        title->setStyleSheet("font-size:32px;font-weight:900;color:#E6EDF3;");
        title->setAlignment(Qt::AlignCenter);

        auto* sub = new QLabel(
            "Installation completed successfully.\n"
            "Remove the installation media and reboot to start ShadowOS."
        );
        sub->setStyleSheet(QString("font-size:14px;color:%1;").arg(Theme::TEXT_SEC));
        sub->setAlignment(Qt::AlignCenter);
        sub->setWordWrap(true);

        auto* btnRow = new QHBoxLayout;
        btnRow->addStretch();

        auto* btnReboot = new QPushButton("Reboot Now");
        btnReboot->setFixedWidth(180);
        btnReboot->setStyleSheet(QString(
            "QPushButton { background:%1; border:none; border-radius:8px;"
            " padding:12px 28px; color:#060C14; font-size:14px; font-weight:700; }"
            "QPushButton:hover { background:%2; }"
        ).arg(Theme::ACCENT, Theme::ACCENT2));
        connect(btnReboot, &QPushButton::clicked, []() {
            QProcess::startDetached("reboot", {});
        });

        auto* btnQuit = new QPushButton("Quit Installer");
        btnQuit->setFixedWidth(160);
        btnQuit->setStyleSheet(QString(
            "QPushButton { background:transparent; border:1px solid %1;"
            " border-radius:8px; padding:12px 28px; color:%1; font-size:14px; }"
            "QPushButton:hover { background:rgba(255,255,255,0.05); }"
        ).arg(Theme::TEXT_SEC));
        connect(btnQuit, &QPushButton::clicked, []() {
            qApp->quit();
        });

        btnRow->addWidget(btnQuit);
        btnRow->addSpacing(12);
        btnRow->addWidget(btnReboot);
        btnRow->addStretch();

        lay->addWidget(ico);
        lay->addWidget(title);
        lay->addWidget(sub);
        lay->addLayout(btnRow);
    } else {
        auto* ico = new QLabel("✗");
        ico->setStyleSheet(QString("font-size:64px;color:%1;").arg(Theme::DANGER));
        ico->setAlignment(Qt::AlignCenter);

        auto* title = new QLabel("Installation Failed");
        title->setStyleSheet(QString("font-size:32px;font-weight:900;color:%1;").arg(Theme::DANGER));
        title->setAlignment(Qt::AlignCenter);

        auto* sub = new QLabel(
            "The installer encountered an error. Check the log on the previous screen.\n"
            "Common causes: no internet connection, insufficient disk space, wrong disk selected."
        );
        sub->setStyleSheet(QString("font-size:14px;color:%1;").arg(Theme::TEXT_SEC));
        sub->setAlignment(Qt::AlignCenter);
        sub->setWordWrap(true);

        auto* btnQuit = new QPushButton("Quit Installer");
        btnQuit->setFixedWidth(180);
        btnQuit->setStyleSheet(QString(
            "QPushButton { background:transparent; border:1px solid %1;"
            " border-radius:8px; padding:12px 28px; color:%1; font-size:14px; }"
            "QPushButton:hover { background:rgba(248,113,113,0.08); }"
        ).arg(Theme::DANGER));
        connect(btnQuit, &QPushButton::clicked, []() {
            qApp->quit();
        });

        auto* btnRow = new QHBoxLayout;
        btnRow->addStretch();
        btnRow->addWidget(btnQuit);
        btnRow->addStretch();

        lay->addWidget(ico);
        lay->addWidget(title);
        lay->addWidget(sub);
        lay->addLayout(btnRow);
    }

    lay->addStretch();
}
