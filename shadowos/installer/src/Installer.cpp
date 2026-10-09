#include "Installer.h"
#include "theme.h"
#include <QHBoxLayout>
#include <QVBoxLayout>
#include <QLabel>
#include <QFrame>
#include <QSizePolicy>

static const QStringList STEP_LABELS = {
    "Welcome",
    "Disk",
    "Encryption",
    "User Account",
    "Profile",
    "Review",
    "Installing",
};

Installer::Installer(QWidget* parent)
    : QMainWindow(parent)
{
    setWindowTitle("ShadowOS Installer");
    setMinimumSize(Theme::WIN_W, Theme::WIN_H);
    resize(Theme::WIN_W, Theme::WIN_H);

    auto* central = new QWidget;
    setCentralWidget(central);
    auto* rootLay = new QHBoxLayout(central);
    rootLay->setContentsMargins(0, 0, 0, 0);
    rootLay->setSpacing(0);

    // Sidebar
    rootLay->addWidget(buildSidebar());

    // Right side
    auto* rightBox = new QWidget;
    auto* rightLay = new QVBoxLayout(rightBox);
    rightLay->setContentsMargins(0, 0, 0, 0);
    rightLay->setSpacing(0);

    // Page stack
    m_stack = new QStackedWidget;
    m_welcome = new WelcomePage;
    m_disk    = new DiskPage(&m_state);
    m_encrypt = new EncryptPage(&m_state);
    m_user    = new UserPage(&m_state);
    m_profile = new ProfilePage(&m_state);
    m_summary = new SummaryPage(&m_state);
    m_install = new InstallPage(&m_state);

    m_stack->addWidget(m_welcome);
    m_stack->addWidget(m_disk);
    m_stack->addWidget(m_encrypt);
    m_stack->addWidget(m_user);
    m_stack->addWidget(m_profile);
    m_stack->addWidget(m_summary);
    m_stack->addWidget(m_install);

    connect(m_install, &InstallPage::finished, this, &Installer::onInstallFinished);

    // Bottom nav bar
    auto* navBar = new QWidget;
    navBar->setFixedHeight(64);
    navBar->setStyleSheet(QString("background:%1; border-top:1px solid %2;")
                          .arg(Theme::BG_SURFACE, Theme::BORDER_DIM));
    auto* navLay = new QHBoxLayout(navBar);
    navLay->setContentsMargins(32, 0, 32, 0);

    m_btnBack = new QPushButton("← Back");
    m_btnBack->setEnabled(false);
    m_btnBack->setStyleSheet(QString(
        "QPushButton { background:transparent; border:1px solid %1;"
        " border-radius:8px; padding:9px 24px; color:%1; font-size:13px; font-weight:600; }"
        "QPushButton:hover { background:rgba(255,255,255,0.05); }"
        "QPushButton:disabled { color:%2; border-color:%2; }"
    ).arg(Theme::TEXT_SEC, Theme::TEXT_DIM));
    connect(m_btnBack, &QPushButton::clicked, this, &Installer::back);

    m_btnNext = new QPushButton("Next →");
    m_btnNext->setStyleSheet(QString(
        "QPushButton { background:%1; border:none; border-radius:8px;"
        " padding:9px 28px; color:#060C14; font-size:13px; font-weight:700; }"
        "QPushButton:hover { background:%2; }"
        "QPushButton:disabled { background:%3; color:%4; }"
    ).arg(Theme::ACCENT, Theme::ACCENT2, Theme::BG_CARD, Theme::TEXT_DIM));
    connect(m_btnNext, &QPushButton::clicked, this, &Installer::next);

    navLay->addWidget(m_btnBack);
    navLay->addStretch();
    navLay->addWidget(m_btnNext);

    rightLay->addWidget(m_stack, 1);
    rightLay->addWidget(navBar);

    rootLay->addWidget(rightBox, 1);

    setStyleSheet(Theme::appStyleSheet());
    goTo(0);
}

QWidget* Installer::buildSidebar() {
    auto* bar = new QWidget;
    bar->setFixedWidth(Theme::SIDEBAR_W);
    bar->setStyleSheet(QString("background:%1; border-right:1px solid %2;")
                       .arg(Theme::BG_SURFACE, Theme::BORDER_DIM));

    auto* lay = new QVBoxLayout(bar);
    lay->setContentsMargins(0, 32, 0, 24);
    lay->setSpacing(0);

    // Logo area
    auto* logoArea = new QWidget;
    auto* logoLay  = new QVBoxLayout(logoArea);
    logoLay->setContentsMargins(20, 0, 20, 24);
    logoLay->setSpacing(2);

    auto* logoBrand = new QLabel("SHADOWOS");
    logoBrand->setStyleSheet(QString("font-size:11px;font-weight:900;letter-spacing:4px;color:%1;"
                                     "font-family:'JetBrains Mono',monospace;").arg(Theme::ACCENT));
    auto* logoSub = new QLabel("INSTALLER");
    logoSub->setStyleSheet(QString("font-size:9px;letter-spacing:3px;color:%1;").arg(Theme::TEXT_DIM));

    logoLay->addWidget(logoBrand);
    logoLay->addWidget(logoSub);
    lay->addWidget(logoArea);

    auto* sep = new QFrame;
    sep->setFrameShape(QFrame::HLine);
    sep->setStyleSheet(QString("border: none; border-top: 1px solid %1;").arg(Theme::BORDER_DIM));
    lay->addWidget(sep);
    lay->addSpacing(16);

    // Step list
    m_steps = new QListWidget;
    m_steps->setStyleSheet(QString(
        "QListWidget { background:transparent; border:none; outline:none; }"
        "QListWidget::item { color:%1; font-size:12px; font-weight:500;"
        " padding:10px 20px; border:none; border-left:3px solid transparent; }"
        "QListWidget::item:selected { background:rgba(0,224,164,0.08);"
        " color:#E6EDF3; border-left:3px solid %2; font-weight:700; }"
    ).arg(Theme::TEXT_DIM, Theme::ACCENT));
    m_steps->setSelectionMode(QAbstractItemView::NoSelection);
    m_steps->setFocusPolicy(Qt::NoFocus);

    for (const auto& label : STEP_LABELS) {
        m_steps->addItem(label);
    }

    lay->addWidget(m_steps, 1);
    lay->addStretch();

    auto* verLbl = new QLabel("v1.0.0");
    verLbl->setStyleSheet(QString("font-size:10px;color:%1;").arg(Theme::TEXT_DIM));
    verLbl->setContentsMargins(20, 0, 0, 0);
    lay->addWidget(verLbl);

    return bar;
}

void Installer::goTo(int index) {
    m_current = index;
    m_stack->setCurrentIndex(index);
    m_steps->setCurrentRow(index);

    m_btnBack->setEnabled(index > 0 && index < PAGE_INSTALL);
    m_btnNext->setEnabled(index < PAGE_INSTALL);

    if (index == PAGE_INSTALL - 1) {
        m_btnNext->setText("Install →");
    } else if (index >= PAGE_INSTALL) {
        m_btnNext->setText("Done");
        m_btnNext->setEnabled(false);
        m_btnBack->setEnabled(false);
    } else {
        m_btnNext->setText("Next →");
    }
}

bool Installer::validateCurrent() {
    switch (m_current) {
    case 1: return m_disk->validate();
    case 2: return m_encrypt->validate();
    case 3: return m_user->validate();
    case 4: return m_profile->validate();
    default: return true;
    }
}

void Installer::saveCurrent() {
    switch (m_current) {
    case 2: m_encrypt->save(); break;
    case 3: m_user->save();    break;
    case 4: m_profile->save(); break;
    default: break;
    }
}

void Installer::next() {
    if (!validateCurrent()) return;
    saveCurrent();

    // Summary page (index 5) — "Install" button launches installation
    if (m_current == PAGE_INSTALL - 1) {
        goTo(PAGE_INSTALL);
        m_install->begin();
        return;
    }

    // Moving into summary — refresh its display
    if (m_current == PAGE_INSTALL - 2) {
        m_summary->refresh();
    }

    goTo(m_current + 1);
}

void Installer::back() {
    if (m_current > 0 && m_current < PAGE_INSTALL) {
        goTo(m_current - 1);
    }
}

void Installer::onInstallFinished(bool success) {
    m_finish = new FinishPage(success);
    m_stack->addWidget(m_finish);
    m_steps->addItem(success ? "Complete ✓" : "Failed ✗");
    goTo(m_stack->count() - 1);
}
