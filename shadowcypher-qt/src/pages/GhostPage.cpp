#include "GhostPage.h"
#include "../theme.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>

// ──────────────────────────────────────────────────────────────────────────────
// Static helpers
// ──────────────────────────────────────────────────────────────────────────────

static constexpr int POLL_INTERVAL_MS = 10000;

static const char* CARD_STYLE = R"(
QWidget#statusCard {
    background: #161d2f;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
}
)";

static const char* TOGGLE_OFF_STYLE = R"(
QPushButton {
    background: rgba(0,212,255,0.06);
    border: 2px solid rgba(0,212,255,0.3);
    color: #00d4ff;
    font-family: 'JetBrains Mono';
    font-size: 13px;
    font-weight: 900;
    letter-spacing: 2px;
    padding: 18px 36px;
    border-radius: 6px;
}
QPushButton:hover {
    background: rgba(0,212,255,0.12);
    border-color: rgba(0,212,255,0.55);
}
QPushButton:disabled {
    color: #475569;
    border-color: rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.02);
}
)";

static const char* TOGGLE_ON_STYLE = R"(
QPushButton {
    background: rgba(0,255,157,0.12);
    border: 2px solid rgba(0,255,157,0.4);
    color: #00ff9d;
    font-family: 'JetBrains Mono';
    font-size: 13px;
    font-weight: 900;
    letter-spacing: 2px;
    padding: 18px 36px;
    border-radius: 6px;
}
QPushButton:hover {
    background: rgba(0,255,157,0.2);
    border-color: rgba(0,255,157,0.7);
}
QPushButton:disabled {
    color: #475569;
    border-color: rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.02);
}
)";

static const char* WAITING_STYLE = R"(
QPushButton {
    background: rgba(255,184,77,0.08);
    border: 2px solid rgba(255,184,77,0.35);
    color: #ffb84d;
    font-family: 'JetBrains Mono';
    font-size: 13px;
    font-weight: 900;
    letter-spacing: 2px;
    padding: 18px 36px;
    border-radius: 6px;
}
)";

static const char* REFRESH_BTN_STYLE = R"(
QPushButton {
    background: rgba(0,212,255,0.06);
    border: 1px solid rgba(0,212,255,0.25);
    color: #00d4ff;
    font-family: 'JetBrains Mono';
    font-size: 11px;
    letter-spacing: 1px;
    padding: 6px 14px;
    border-radius: 4px;
}
QPushButton:hover {
    background: rgba(0,212,255,0.14);
}
)";

// ──────────────────────────────────────────────────────────────────────────────
// Constructor
// ──────────────────────────────────────────────────────────────────────────────

GhostPage::GhostPage(IpcClient* ipc, QWidget* parent)
    : QWidget(parent), m_ipc(ipc)
{
    buildUi();

    m_timer = new QTimer(this);
    m_timer->setInterval(POLL_INTERVAL_MS);
    connect(m_timer, &QTimer::timeout, this, &GhostPage::refresh);
    m_timer->start();

    if (m_ipc) {
        connect(m_ipc, &IpcClient::resultReady, this, &GhostPage::onIpcResult);
        connect(m_ipc, &IpcClient::connected, this, [this]() {
            m_terminal->log("Ghost daemon connected — fetching privacy state", "SUCCESS");
            refresh();
        });
    }

    refresh();
}

// ──────────────────────────────────────────────────────────────────────────────
// UI construction
// ──────────────────────────────────────────────────────────────────────────────

QWidget* GhostPage::makeCard(const QString& title, QLabel*& dot, QLabel*& value,
                              const QString& initValue)
{
    auto* card = new QWidget;
    card->setObjectName("statusCard");
    card->setStyleSheet(CARD_STYLE);

    auto* lay = new QVBoxLayout(card);
    lay->setContentsMargins(16, 14, 16, 14);
    lay->setSpacing(8);

    // Card title
    auto* titleLbl = new QLabel(title);
    titleLbl->setStyleSheet(
        "color: #475569;"
        "font-family: 'JetBrains Mono';"
        "font-size: 10px;"
        "font-weight: 700;"
        "letter-spacing: 2px;"
        "background: transparent;"
        "border: none;"
    );
    lay->addWidget(titleLbl);

    // Dot + value row
    auto* row = new QHBoxLayout;
    row->setSpacing(8);

    dot = new QLabel("●");
    dot->setStyleSheet(
        "color: #334155;"
        "font-size: 14px;"
        "background: transparent;"
        "border: none;"
    );
    row->addWidget(dot);

    value = new QLabel(initValue);
    value->setStyleSheet(
        "color: #e2e8f0;"
        "font-family: 'JetBrains Mono';"
        "font-size: 13px;"
        "font-weight: 700;"
        "letter-spacing: 1px;"
        "background: transparent;"
        "border: none;"
    );
    row->addWidget(value);
    row->addStretch();
    lay->addLayout(row);

    return card;
}

void GhostPage::buildUi()
{
    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(20, 16, 20, 16);
    lay->setSpacing(14);

    // ── Header row ──────────────────────────────────────────────────────────
    auto* header = new QHBoxLayout;
    header->setSpacing(10);

    auto* title = new QLabel;
    title->setText(
        "<span style='font-weight:900;font-size:16px;"
        "color:#00d4ff;letter-spacing:2px;'>GHOST MODE</span>"
    );
    title->setTextFormat(Qt::RichText);
    header->addWidget(title);

    auto* subtitle = new QLabel("Privacy &amp; Anonymity Controls");
    subtitle->setStyleSheet(
        "color: #475569;"
        "font-size: 12px;"
        "margin-left: 8px;"
    );
    header->addWidget(subtitle);
    header->addStretch();

    m_refreshBtn = new QPushButton("\xe2\x9f\xb3 REFRESH");   // ⟳ UTF-8
    m_refreshBtn->setStyleSheet(REFRESH_BTN_STYLE);
    connect(m_refreshBtn, &QPushButton::clicked, this, &GhostPage::refresh);
    header->addWidget(m_refreshBtn);

    lay->addLayout(header);

    // ── Big toggle button ────────────────────────────────────────────────────
    auto* toggleRow = new QHBoxLayout;
    toggleRow->setContentsMargins(0, 4, 0, 4);

    m_toggleBtn = new QPushButton("ENABLE GHOST MODE");
    m_toggleBtn->setStyleSheet(TOGGLE_OFF_STYLE);
    m_toggleBtn->setCursor(Qt::PointingHandCursor);
    m_toggleBtn->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);
    m_toggleBtn->setMinimumHeight(62);
    connect(m_toggleBtn, &QPushButton::clicked, this, &GhostPage::toggleGhostMode);
    toggleRow->addWidget(m_toggleBtn);

    lay->addLayout(toggleRow);

    // ── Status cards (2×2 grid) ──────────────────────────────────────────────
    auto* cardGrid = new QGridLayout;
    cardGrid->setSpacing(10);

    // Tor card
    auto* torCard = makeCard("TOR CIRCUIT", m_torDot, m_torStatus, "CHECKING…");
    cardGrid->addWidget(torCard, 0, 0);

    // Kill-switch card — MAC label reused as plain QLabel; dot/value pattern
    auto* ksCard = makeCard("KILL-SWITCH", m_ksDot, m_ksStatus, "CHECKING…");
    cardGrid->addWidget(ksCard, 0, 1);

    // MAC address card — no dot for this one, just a value label
    {
        auto* card = new QWidget;
        card->setObjectName("statusCard");
        card->setStyleSheet(CARD_STYLE);
        auto* cl = new QVBoxLayout(card);
        cl->setContentsMargins(16, 14, 16, 14);
        cl->setSpacing(8);

        auto* t = new QLabel("MAC ADDRESS");
        t->setStyleSheet(
            "color: #475569;"
            "font-family: 'JetBrains Mono';"
            "font-size: 10px;"
            "font-weight: 700;"
            "letter-spacing: 2px;"
            "background: transparent;"
            "border: none;"
        );
        cl->addWidget(t);

        m_macLabel = new QLabel("CHECKING…");
        m_macLabel->setStyleSheet(
            "color: #e2e8f0;"
            "font-family: 'JetBrains Mono';"
            "font-size: 13px;"
            "font-weight: 700;"
            "letter-spacing: 1px;"
            "background: transparent;"
            "border: none;"
        );
        cl->addWidget(m_macLabel);
        cardGrid->addWidget(card, 1, 0);
    }

    // DNS lock card
    auto* dnsCard = makeCard("DNS LOCK", m_dnsDot, m_dnsStatus, "CHECKING…");
    cardGrid->addWidget(dnsCard, 1, 1);

    lay->addLayout(cardGrid);

    // ── Terminal ─────────────────────────────────────────────────────────────
    auto* termLabel = new QLabel;
    termLabel->setText(
        "<span style='font-weight:800;color:#475569;font-size:10px;"
        "letter-spacing:2px;'>GHOST LOG</span>"
    );
    termLabel->setTextFormat(Qt::RichText);
    lay->addWidget(termLabel);

    m_terminal = new TacticalTerminal(this);
    lay->addWidget(m_terminal, 1);   // stretch — takes remaining space

    m_terminal->log("Ghost Mode control panel ready", "SYSTEM");
}

// ──────────────────────────────────────────────────────────────────────────────
// Toggle button state management
// ──────────────────────────────────────────────────────────────────────────────

void GhostPage::updateToggleButton()
{
    if (m_waiting) {
        m_toggleBtn->setStyleSheet(WAITING_STYLE);
        m_toggleBtn->setEnabled(false);
        return;
    }
    m_toggleBtn->setEnabled(true);
    if (m_ghostActive) {
        m_toggleBtn->setStyleSheet(TOGGLE_ON_STYLE);
        m_toggleBtn->setText("GHOST MODE ACTIVE \xe2\x80\x94 CLICK TO DISABLE");
    } else {
        m_toggleBtn->setStyleSheet(TOGGLE_OFF_STYLE);
        m_toggleBtn->setText("ENABLE GHOST MODE");
    }
}

// ──────────────────────────────────────────────────────────────────────────────
// Refresh — try IPC first, fall back to QProcess
// ──────────────────────────────────────────────────────────────────────────────

void GhostPage::refresh()
{
    if (m_ipc && m_ipc->isConnected()) {
        m_statusReqId = m_ipc->call("ghost_mode_status");
        m_terminal->log("Querying ghost status via IPC…", "INFO");
    } else {
        m_terminal->log("IPC not connected — probing via system commands", "WARNING");
        checkViaProcess();
    }
}

// ──────────────────────────────────────────────────────────────────────────────
// Toggle ghost mode
// ──────────────────────────────────────────────────────────────────────────────

void GhostPage::toggleGhostMode()
{
    if (m_waiting) return;

    m_waiting = true;
    if (m_ghostActive) {
        m_toggleBtn->setText("DISABLING…");
        m_toggleBtn->setStyleSheet(WAITING_STYLE);
        m_toggleBtn->setEnabled(false);
        m_terminal->log("Disabling Ghost Mode…", "WARNING");

        if (m_ipc && m_ipc->isConnected()) {
            m_enableReqId = m_ipc->call("ghost_mode_disable");
        } else {
            // No IPC — nothing we can reliably do without a daemon
            m_terminal->log("IPC daemon not connected — cannot disable Ghost Mode remotely", "ERROR");
            m_waiting = false;
            updateToggleButton();
        }
    } else {
        m_toggleBtn->setText("ENGAGING…");
        m_toggleBtn->setStyleSheet(WAITING_STYLE);
        m_toggleBtn->setEnabled(false);
        m_terminal->log("Enabling Ghost Mode…", "INFO");

        if (m_ipc && m_ipc->isConnected()) {
            m_enableReqId = m_ipc->call("ghost_mode_enable");
        } else {
            m_terminal->log("IPC daemon not connected — cannot enable Ghost Mode remotely", "ERROR");
            m_waiting = false;
            updateToggleButton();
        }
    }
}

// ──────────────────────────────────────────────────────────────────────────────
// IPC result handler
// ──────────────────────────────────────────────────────────────────────────────

void GhostPage::onIpcResult(int id, QJsonObject result)
{
    if (id == m_statusReqId) {
        // ghost_mode_status → { tor, kill_switch, mac, dns_locked, active }
        bool tor      = result.value("tor").toBool(false);
        bool ks       = result.value("kill_switch").toBool(false);
        QString mac   = result.value("mac").toString("—");
        bool dnsLock  = result.value("dns_locked").toBool(false);
        bool active   = result.value("active").toBool(false);
        applyStatus(tor, ks, mac, dnsLock, active);
        m_terminal->log(
            QString("[IPC] status — tor:%1  ks:%2  dns:%3  active:%4")
                .arg(tor ? "ON" : "OFF")
                .arg(ks  ? "ARMED" : "DISARMED")
                .arg(dnsLock ? "LOCKED" : "EXPOSED")
                .arg(active  ? "YES" : "NO"),
            active ? "SUCCESS" : "INFO"
        );

    } else if (id == m_enableReqId) {
        bool ok = result.value("ok").toBool(false);
        m_waiting = false;

        if (ok) {
            m_ghostActive = !m_ghostActive;     // flip after confirmed
            m_terminal->log(
                m_ghostActive ? "Ghost Mode ACTIVATED" : "Ghost Mode DEACTIVATED",
                m_ghostActive ? "SUCCESS" : "WARNING"
            );
        } else {
            QString err = result.value("error").toString("Unknown error");
            m_terminal->log("Ghost Mode toggle failed: " + err, "ERROR");
        }

        updateToggleButton();
        // Re-probe status so cards reflect actual system state
        QTimer::singleShot(800, this, &GhostPage::refresh);
    }
}

// ──────────────────────────────────────────────────────────────────────────────
// Apply status to all UI labels
// ──────────────────────────────────────────────────────────────────────────────

QString GhostPage::dotHtml(const QString& color)
{
    return QString("<span style='color:%1;font-size:14px;'>●</span>").arg(color);
}

void GhostPage::applyStatus(bool tor, bool ks, const QString& mac, bool dns, bool active)
{
    // Tor
    m_torDot->setText(dotHtml(tor ? Theme::SUCCESS : Theme::CRITICAL));
    m_torDot->setTextFormat(Qt::RichText);
    m_torStatus->setText(tor ? "ACTIVE" : "INACTIVE");
    m_torStatus->setStyleSheet(
        QString("color:%1;font-family:'JetBrains Mono';font-size:13px;"
                "font-weight:700;letter-spacing:1px;background:transparent;border:none;")
            .arg(tor ? Theme::SUCCESS : Theme::CRITICAL)
    );

    // Kill-switch
    m_ksDot->setText(dotHtml(ks ? Theme::SUCCESS : Theme::WARNING));
    m_ksDot->setTextFormat(Qt::RichText);
    m_ksStatus->setText(ks ? "ARMED" : "DISARMED");
    m_ksStatus->setStyleSheet(
        QString("color:%1;font-family:'JetBrains Mono';font-size:13px;"
                "font-weight:700;letter-spacing:1px;background:transparent;border:none;")
            .arg(ks ? Theme::SUCCESS : Theme::WARNING)
    );

    // MAC
    m_macLabel->setText(mac.isEmpty() ? "—" : mac.toUpper());

    // DNS
    m_dnsDot->setText(dotHtml(dns ? Theme::SUCCESS : Theme::CRITICAL));
    m_dnsDot->setTextFormat(Qt::RichText);
    m_dnsStatus->setText(dns ? "LOCKED" : "EXPOSED");
    m_dnsStatus->setStyleSheet(
        QString("color:%1;font-family:'JetBrains Mono';font-size:13px;"
                "font-weight:700;letter-spacing:1px;background:transparent;border:none;")
            .arg(dns ? Theme::SUCCESS : Theme::CRITICAL)
    );

    // Update ghost active flag and button (only when not mid-toggle)
    if (!m_waiting) {
        m_ghostActive = active;
        updateToggleButton();
    }
}

// ──────────────────────────────────────────────────────────────────────────────
// QProcess fallback checks
// ──────────────────────────────────────────────────────────────────────────────

void GhostPage::killOldProcesses()
{
    auto killProc = [](QProcess*& p) {
        if (p) {
            p->disconnect();
            if (p->state() != QProcess::NotRunning) {
                p->kill();
                p->waitForFinished(200);
            }
            p->deleteLater();
            p = nullptr;
        }
    };
    killProc(m_torProc);
    killProc(m_ksProc);
    killProc(m_macProc);
    killProc(m_dnsProc);
}

void GhostPage::checkViaProcess()
{
    killOldProcesses();

    // ── 1. Tor: systemctl is-active tor (fallback: which tor) ──
    m_torProc = new QProcess(this);
    connect(m_torProc,
            QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
            this, &GhostPage::onTorCheckFinished);
    m_torProc->start("systemctl", {"is-active", "tor"});

    // ── 2. Kill-switch: check for DROP rule in iptables OUTPUT chain ──
    // We run: iptables -L OUTPUT -n --line-numbers  (no sudo for list in some distros)
    // If that fails, we check for ip6tables similarly.
    m_ksProc = new QProcess(this);
    connect(m_ksProc,
            QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
            this, &GhostPage::onKillSwitchCheckFinished);
    m_ksProc->start("sh", {"-c", "iptables -L OUTPUT -n 2>/dev/null | grep -i drop"});

    // ── 3. MAC address: ip link show — grab default-route interface ──
    m_macProc = new QProcess(this);
    connect(m_macProc,
            QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
            this, &GhostPage::onMacCheckFinished);
    // Get MAC of default-route interface.  ip -o link show $(ip route list default | awk '{print $5;exit}')
    m_macProc->start("sh", {"-c",
        "iface=$(ip route list default 2>/dev/null | awk '{print $5; exit}'); "
        "[ -n \"$iface\" ] && ip -o link show \"$iface\" 2>/dev/null | "
        "awk '/link\\/ether/{print $2}' || echo 'unknown'"
    });

    // ── 4. DNS lock: check /etc/resolv.conf for 127.x nameserver ──
    m_dnsProc = new QProcess(this);
    connect(m_dnsProc,
            QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
            this, &GhostPage::onDnsCheckFinished);
    m_dnsProc->start("sh", {"-c",
        "grep -E '^nameserver[[:space:]]+(127\\.|::1)' /etc/resolv.conf 2>/dev/null | head -1"
    });
}

// Tor check result
void GhostPage::onTorCheckFinished(int exitCode, QProcess::ExitStatus)
{
    if (!m_torProc) return;

    QString out = m_torProc->readAllStandardOutput().trimmed().toLower();
    // "active" means systemctl returned 0 and "active" on stdout
    bool torActive = (exitCode == 0) || out.contains("active");

    m_torDot->setText(dotHtml(torActive ? Theme::SUCCESS : Theme::CRITICAL));
    m_torDot->setTextFormat(Qt::RichText);
    m_torStatus->setText(torActive ? "ACTIVE" : "INACTIVE");
    m_torStatus->setStyleSheet(
        QString("color:%1;font-family:'JetBrains Mono';font-size:13px;"
                "font-weight:700;letter-spacing:1px;background:transparent;border:none;")
            .arg(torActive ? Theme::SUCCESS : Theme::CRITICAL)
    );
    m_terminal->log(
        QString("Tor circuit: %1").arg(torActive ? "ACTIVE" : "INACTIVE"),
        torActive ? "SUCCESS" : "WARNING"
    );

    m_torProc->deleteLater();
    m_torProc = nullptr;
}

// Kill-switch check result
void GhostPage::onKillSwitchCheckFinished(int exitCode, QProcess::ExitStatus)
{
    if (!m_ksProc) return;

    QString out = m_ksProc->readAllStandardOutput().trimmed();
    // If grep found DROP rules the kill-switch is armed (grep exits 0 on match)
    bool armed = (exitCode == 0) && !out.isEmpty();

    m_ksDot->setText(dotHtml(armed ? Theme::SUCCESS : Theme::WARNING));
    m_ksDot->setTextFormat(Qt::RichText);
    m_ksStatus->setText(armed ? "ARMED" : "DISARMED");
    m_ksStatus->setStyleSheet(
        QString("color:%1;font-family:'JetBrains Mono';font-size:13px;"
                "font-weight:700;letter-spacing:1px;background:transparent;border:none;")
            .arg(armed ? Theme::SUCCESS : Theme::WARNING)
    );
    m_terminal->log(
        QString("Kill-switch: %1").arg(armed ? "ARMED" : "DISARMED"),
        armed ? "SUCCESS" : "WARNING"
    );

    m_ksProc->deleteLater();
    m_ksProc = nullptr;
}

// MAC address check result
void GhostPage::onMacCheckFinished(int, QProcess::ExitStatus)
{
    if (!m_macProc) return;

    QString mac = m_macProc->readAllStandardOutput().trimmed();
    if (mac.isEmpty() || mac == "unknown") mac = "—";

    m_macLabel->setText(mac.toUpper());
    m_terminal->log(QString("MAC address: %1").arg(mac.toUpper()), "INFO");

    m_macProc->deleteLater();
    m_macProc = nullptr;
}

// DNS lock check result
void GhostPage::onDnsCheckFinished(int exitCode, QProcess::ExitStatus)
{
    if (!m_dnsProc) return;

    QString out = m_dnsProc->readAllStandardOutput().trimmed();
    // grep exits 0 and outputs the line if a loopback nameserver was found
    bool locked = (exitCode == 0) && !out.isEmpty();

    m_dnsDot->setText(dotHtml(locked ? Theme::SUCCESS : Theme::CRITICAL));
    m_dnsDot->setTextFormat(Qt::RichText);
    m_dnsStatus->setText(locked ? "LOCKED" : "EXPOSED");
    m_dnsStatus->setStyleSheet(
        QString("color:%1;font-family:'JetBrains Mono';font-size:13px;"
                "font-weight:700;letter-spacing:1px;background:transparent;border:none;")
            .arg(locked ? Theme::SUCCESS : Theme::CRITICAL)
    );
    m_terminal->log(
        QString("DNS: %1").arg(locked ? "LOCKED (loopback resolver)" : "EXPOSED (public resolver)"),
        locked ? "SUCCESS" : "ERROR"
    );

    m_dnsProc->deleteLater();
    m_dnsProc = nullptr;
}
