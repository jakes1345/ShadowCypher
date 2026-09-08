#include "OsintPage.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QFrame>
#include <QJsonArray>

// ── Helpers ───────────────────────────────────────────────────────────────────

static const QString INPUT_STYLE = R"(
    QLineEdit {
        background: #111827; border: 1px solid #1e2a3a; border-radius: 4px;
        color: #e2e8f0; padding: 6px 10px;
        font-family: 'JetBrains Mono'; font-size: 12px;
    }
    QLineEdit:focus { border-color: #b44aff; }
)";

static const QString BTN_PURPLE = R"(
    QPushButton {
        background: rgba(180,74,255,0.12); border: 1px solid #b44aff;
        border-radius: 4px; color: #b44aff; font-family: 'JetBrains Mono';
        font-size: 12px; letter-spacing: 1px; padding: 6px 18px;
    }
    QPushButton:hover   { background: rgba(180,74,255,0.22); }
    QPushButton:disabled { color: #334155; border-color: #334155; background: transparent; }
)";

static const QString CHECK_STYLE = R"(
    QCheckBox {
        color: #94a3b8; font-family: 'JetBrains Mono'; font-size: 12px; spacing: 6px;
    }
    QCheckBox::indicator {
        width: 14px; height: 14px; border: 1px solid #334155; border-radius: 2px;
        background: #0d0f1a;
    }
    QCheckBox::indicator:checked {
        background: #b44aff; border-color: #b44aff;
    }
    QCheckBox:hover { color: #e2e8f0; }
)";

QCheckBox* OsintPage::makeCheck(const QString& label, bool checked) {
    auto* c = new QCheckBox(label);
    c->setChecked(checked);
    c->setStyleSheet(CHECK_STYLE);
    return c;
}

// ── Domain Intel tab ──────────────────────────────────────────────────────────

QWidget* OsintPage::buildDomainTab() {
    auto* w   = new QWidget;
    auto* lay = new QVBoxLayout(w);
    lay->setContentsMargins(16, 12, 16, 12);
    lay->setSpacing(10);

    // Target row
    auto* targetRow = new QHBoxLayout;
    targetRow->setSpacing(8);
    auto* lbl = new QLabel("Target:");
    lbl->setStyleSheet("color: #64748b; font-family: 'JetBrains Mono'; font-size: 12px;");
    m_domainInput = new QLineEdit;
    m_domainInput->setPlaceholderText("example.com  or  192.168.1.1");
    m_domainInput->setStyleSheet(INPUT_STYLE);
    m_domainStatusLbl = new QLabel;
    m_domainStatusLbl->setStyleSheet("color: #334155; font-family: 'JetBrains Mono'; font-size: 11px;");
    m_domainRunBtn = new QPushButton("RUN SCAN");
    m_domainRunBtn->setStyleSheet(BTN_PURPLE);
    targetRow->addWidget(lbl);
    targetRow->addWidget(m_domainInput, 1);
    targetRow->addWidget(m_domainStatusLbl);
    targetRow->addWidget(m_domainRunBtn);
    lay->addLayout(targetRow);

    // Check boxes: 3 columns
    auto* checksBox = new QWidget;
    auto* grid = new QGridLayout(checksBox);
    grid->setContentsMargins(0, 4, 0, 4);
    grid->setHorizontalSpacing(24);
    grid->setVerticalSpacing(6);

    m_chkWhois   = makeCheck("WHOIS",          true);
    m_chkDns     = makeCheck("DNS Records",    true);
    m_chkSsl     = makeCheck("SSL Certificate",true);
    m_chkHeaders = makeCheck("HTTP Headers",   true);
    m_chkTech    = makeCheck("Tech Detect",    false);
    m_chkMx      = makeCheck("MX / SPF",       false);
    m_chkSubnet  = makeCheck("Subnet / ASN",   false);
    m_chkZone    = makeCheck("Zone Transfer",  false);
    m_chkWayback = makeCheck("Wayback Recon",  false);

    const QList<QCheckBox*> checks = {
        m_chkWhois, m_chkDns, m_chkSsl,
        m_chkHeaders, m_chkTech, m_chkMx,
        m_chkSubnet, m_chkZone, m_chkWayback
    };
    for (int i = 0; i < checks.size(); ++i)
        grid->addWidget(checks[i], i / 3, i % 3);

    lay->addWidget(checksBox);

    // Divider
    auto* line = new QFrame;
    line->setFrameShape(QFrame::HLine);
    line->setStyleSheet("border: none; border-top: 1px solid #1e2a3a;");
    lay->addWidget(line);

    // Terminal
    m_domainTerminal = new TacticalTerminal;
    lay->addWidget(m_domainTerminal, 1);

    connect(m_domainRunBtn, &QPushButton::clicked, this, &OsintPage::runDomainScan);
    connect(m_domainInput, &QLineEdit::returnPressed, this, &OsintPage::runDomainScan);
    return w;
}

// ── Identity Intel tab ────────────────────────────────────────────────────────

QWidget* OsintPage::buildIdentityTab() {
    auto* w   = new QWidget;
    auto* lay = new QVBoxLayout(w);
    lay->setContentsMargins(16, 12, 16, 12);
    lay->setSpacing(10);

    // Query + mode row
    auto* row = new QHBoxLayout;
    row->setSpacing(8);
    auto* qLbl = new QLabel("Query:");
    qLbl->setStyleSheet("color: #64748b; font-family: 'JetBrains Mono'; font-size: 12px;");
    m_identInput = new QLineEdit;
    m_identInput->setPlaceholderText("username  or  user@example.com  or  domain.com");
    m_identInput->setStyleSheet(INPUT_STYLE);

    m_modeBox = new QComboBox;
    m_modeBox->addItem("Breach Check  (HaveIBeenPwned)",     "breach");
    m_modeBox->addItem("Social Footprint  (Sherlock)",        "social");
    m_modeBox->addItem("Email Audit  (Holehe)",               "email");
    m_modeBox->addItem("Domain Harvest  (theHarvester)",      "harvest");
    m_modeBox->addItem("Wayback Recon",                       "wayback");
    m_modeBox->setStyleSheet(R"(
        QComboBox {
            background: #111827; border: 1px solid #1e2a3a; border-radius: 4px;
            color: #e2e8f0; padding: 6px 10px;
            font-family: 'JetBrains Mono'; font-size: 12px;
        }
        QComboBox::drop-down { border: none; width: 24px; }
        QComboBox QAbstractItemView {
            background: #111827; border: 1px solid #1e2a3a;
            color: #e2e8f0; selection-background-color: rgba(180,74,255,0.2);
        }
    )");

    m_identStatusLbl = new QLabel;
    m_identStatusLbl->setStyleSheet("color: #334155; font-family: 'JetBrains Mono'; font-size: 11px;");
    m_identRunBtn = new QPushButton("RUN INTEL");
    m_identRunBtn->setStyleSheet(BTN_PURPLE);
    row->addWidget(qLbl);
    row->addWidget(m_identInput, 1);
    row->addWidget(m_modeBox);
    row->addWidget(m_identStatusLbl);
    row->addWidget(m_identRunBtn);
    lay->addLayout(row);

    // Mode info label
    auto* infoLbl = new QLabel(
        "Breach Check uses the HaveIBeenPwned k-Anonymity API (no email sent).  "
        "Social/Email/Harvest require Sherlock / Holehe / theHarvester to be installed."
    );
    infoLbl->setStyleSheet("color: #334155; font-family: 'JetBrains Mono'; font-size: 10px;");
    infoLbl->setWordWrap(true);
    lay->addWidget(infoLbl);

    // Divider
    auto* line = new QFrame;
    line->setFrameShape(QFrame::HLine);
    line->setStyleSheet("border: none; border-top: 1px solid #1e2a3a;");
    lay->addWidget(line);

    // Terminal
    m_identTerminal = new TacticalTerminal;
    lay->addWidget(m_identTerminal, 1);

    connect(m_identRunBtn, &QPushButton::clicked, this, &OsintPage::runIdentityScan);
    connect(m_identInput, &QLineEdit::returnPressed, this, &OsintPage::runIdentityScan);
    return w;
}

// ── Main UI ───────────────────────────────────────────────────────────────────

void OsintPage::buildUi() {
    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(0, 0, 0, 0);
    lay->setSpacing(0);

    // Header
    auto* header = new QWidget;
    header->setFixedHeight(52);
    header->setStyleSheet("background: #080c1a; border-bottom: 1px solid rgba(255,255,255,0.05);");
    auto* hLay = new QHBoxLayout(header);
    hLay->setContentsMargins(20, 0, 20, 0);
    auto* titleLbl = new QLabel(
        "<span style='color:#b44aff;font-weight:900;letter-spacing:3px;font-size:13px;'>OSINT</span>"
        "<span style='color:#e2e8f0;font-weight:300;letter-spacing:2px;font-size:13px;'> INTELLIGENCE</span>"
    );
    titleLbl->setTextFormat(Qt::RichText);
    auto* subLbl = new QLabel("WHOIS • DNS • SSL • Sherlock • Holehe • HIBP • theHarvester • Wayback");
    subLbl->setStyleSheet("color: #334155; font-family: 'JetBrains Mono'; font-size: 11px;");
    hLay->addWidget(titleLbl);
    hLay->addStretch();
    hLay->addWidget(subLbl);
    lay->addWidget(header);

    // Tabs
    m_tabs = new QTabWidget;
    m_tabs->setStyleSheet(R"(
        QTabWidget::pane { background: #0d0f1a; border: none; }
        QTabBar::tab {
            background: #080c1a; color: #475569;
            font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing: 1px;
            padding: 8px 20px; border: none; border-bottom: 2px solid transparent;
        }
        QTabBar::tab:selected        { color: #b44aff; border-bottom: 2px solid #b44aff; }
        QTabBar::tab:hover:!selected { color: #94a3b8; background: rgba(255,255,255,0.03); }
    )");
    m_tabs->addTab(buildDomainTab(),   "DOMAIN INTEL");
    m_tabs->addTab(buildIdentityTab(), "IDENTITY INTEL");
    lay->addWidget(m_tabs);
}

// ── Constructor ───────────────────────────────────────────────────────────────

OsintPage::OsintPage(IpcClient* ipc, QWidget* parent)
    : QWidget(parent), m_ipc(ipc)
{
    buildUi();
    connect(m_ipc, &IpcClient::resultReady, this, &OsintPage::onIpcResult);
}

// ── Slots ─────────────────────────────────────────────────────────────────────

void OsintPage::runDomainScan() {
    if (m_domainRunning) return;
    QString target = m_domainInput->text().trimmed();
    if (target.isEmpty()) {
        m_domainTerminal->log("Enter a target domain or IP.", "ERROR");
        return;
    }
    if (!m_ipc->isConnected()) {
        m_domainTerminal->log("Daemon offline.", "ERROR");
        return;
    }

    QJsonArray checks;
    if (m_chkWhois->isChecked())   checks.append("whois");
    if (m_chkDns->isChecked())     checks.append("dns");
    if (m_chkSsl->isChecked())     checks.append("ssl");
    if (m_chkHeaders->isChecked()) checks.append("headers");
    if (m_chkTech->isChecked())    checks.append("tech");
    if (m_chkMx->isChecked())      checks.append("mx");
    if (m_chkSubnet->isChecked())  checks.append("subnet");
    if (m_chkZone->isChecked())    checks.append("zone");
    if (m_chkWayback->isChecked()) checks.append("wayback");

    if (checks.isEmpty()) {
        m_domainTerminal->log("Select at least one check.", "ERROR");
        return;
    }

    m_domainRunning = true;
    m_domainRunBtn->setEnabled(false);
    m_domainTerminal->clear();
    m_domainStatusLbl->setText("Running…");
    m_domainTerminal->log(QString("OSINT scan: %1 (%2 checks)").arg(target).arg(checks.size()));
    m_domainReqId = m_ipc->call("osint_domain_scan", {{"target", target}, {"checks", checks}});
}

void OsintPage::runIdentityScan() {
    if (m_identRunning) return;
    QString query = m_identInput->text().trimmed();
    if (query.isEmpty()) {
        m_identTerminal->log("Enter a username or email address.", "ERROR");
        return;
    }
    if (!m_ipc->isConnected()) {
        m_identTerminal->log("Daemon offline.", "ERROR");
        return;
    }

    QString mode = m_modeBox->currentData().toString();
    m_identRunning = true;
    m_identRunBtn->setEnabled(false);
    m_identTerminal->clear();
    m_identStatusLbl->setText("Running…");
    m_identTerminal->log(QString("[OSINT] %1 → %2").arg(mode.toUpper(), query));
    m_identReqId = m_ipc->call("osint_identity_scan", {{"query", query}, {"mode", mode}});
}

void OsintPage::onIpcResult(int id, QJsonObject result) {
    if (id == m_domainReqId) {
        QString out = result["output"].toString();
        if (!out.isEmpty())
            m_domainTerminal->log(out, result["level"].toString("INFO"));
        if (result["complete"].toBool()) {
            m_domainRunning = false;
            m_domainReqId   = -1;
            m_domainRunBtn->setEnabled(true);
            m_domainStatusLbl->setText("Done");
        }
    } else if (id == m_identReqId) {
        QString out = result["output"].toString();
        if (!out.isEmpty())
            m_identTerminal->log(out, result["level"].toString("INFO"));
        if (result["complete"].toBool()) {
            m_identRunning = false;
            m_identReqId   = -1;
            m_identRunBtn->setEnabled(true);
            m_identStatusLbl->setText("Done");
        }
    }
}
