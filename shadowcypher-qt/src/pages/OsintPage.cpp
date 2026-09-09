#include "OsintPage.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QScrollArea>

static TacticalTerminal* makeTerminal(QWidget* parent) {
    auto* t = new TacticalTerminal(parent);
    t->setMinimumHeight(300);
    return t;
}

OsintPage::OsintPage(QWidget* parent) : QWidget(parent) {
    buildUi();
}

void OsintPage::buildUi() {
    auto* outer = new QVBoxLayout(this);
    outer->setContentsMargins(20, 14, 20, 14);
    outer->setSpacing(10);

    // Header
    auto* hdr = new QHBoxLayout;
    auto* title = new QLabel;
    title->setText("<span style='font-weight:900;font-size:16px;color:#00d4ff;letter-spacing:2px;'>OSINT_NEXUS</span>");
    title->setTextFormat(Qt::RichText);
    hdr->addWidget(title);
    hdr->addStretch();
    outer->addLayout(hdr);

    // Target + buttons row
    auto* ctrlRow = new QHBoxLayout;
    ctrlRow->setSpacing(8);

    m_targetEdit = new QLineEdit;
    m_targetEdit->setPlaceholderText("Target domain / IP / company name");
    m_targetEdit->setStyleSheet(R"(
        QLineEdit { background: #060810; border: 1px solid rgba(255,255,255,0.08);
            border-radius: 4px; color: #e2e8f0; font-family: 'JetBrains Mono';
            font-size: 12px; padding: 6px 10px; }
        QLineEdit:focus { border-color: #00d4ff; }
    )");
    ctrlRow->addWidget(m_targetEdit, 2);

    auto mkBtn = [&](const QString& label, const QString& fg, auto slot) {
        auto* btn = new QPushButton(label);
        btn->setStyleSheet(QString(
            "QPushButton { background: rgba(0,0,0,0.3); border: 1px solid %1; color: %1; "
            "font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing:1px; "
            "padding: 6px 12px; border-radius: 4px; font-weight: 700; } "
            "QPushButton:hover { background: rgba(255,255,255,0.06); } "
            "QPushButton:disabled { color: #334155; border-color: #1e293b; } "
        ).arg(fg));
        connect(btn, &QPushButton::clicked, this, slot);
        ctrlRow->addWidget(btn);
        return btn;
    };

    mkBtn("WHOIS",     "#00d4ff", &OsintPage::runWhois);
    mkBtn("DNS",       "#38bdf8", &OsintPage::runDns);
    mkBtn("HARVESTER", "#b44aff", &OsintPage::runHarvester);
    mkBtn("SUBFINDER", "#10b981", &OsintPage::runSubfinder);
    mkBtn("AMASS",     "#f97316", &OsintPage::runAmass);
    mkBtn("SHODAN",    "#fbbf24", &OsintPage::runShodan);

    m_stopBtn = new QPushButton("■ STOP");
    m_stopBtn->setEnabled(false);
    m_stopBtn->setStyleSheet(
        "QPushButton { background: rgba(244,63,94,0.1); border: 1px solid rgba(244,63,94,0.35); "
        "color: #f43f5e; font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing:1px; "
        "padding: 6px 12px; border-radius: 4px; } "
        "QPushButton:hover { background: rgba(244,63,94,0.2); } "
        "QPushButton:disabled { color: #334155; border-color: #1e293b; } ");
    connect(m_stopBtn, &QPushButton::clicked, this, &OsintPage::stopAll);
    ctrlRow->addWidget(m_stopBtn);
    outer->addLayout(ctrlRow);

    // Output tabs
    m_tabs = new QTabWidget;
    m_tabs->setStyleSheet(R"(
        QTabWidget::pane { border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; }
        QTabBar::tab { background: transparent; color: #475569; font-family: 'JetBrains Mono';
            font-size: 11px; letter-spacing: 1px; padding: 6px 16px; }
        QTabBar::tab:selected { color: #00d4ff; border-bottom: 2px solid #00d4ff; }
        QTabBar::tab:hover { color: #94a3b8; }
    )");

    m_whoisOut  = makeTerminal(this); m_tabs->addTab(m_whoisOut,  "  WHOIS  ");
    m_dnsOut    = makeTerminal(this); m_tabs->addTab(m_dnsOut,    "  DNS  ");
    m_harvOut   = makeTerminal(this); m_tabs->addTab(m_harvOut,   "  HARVESTER  ");
    m_subOut    = makeTerminal(this); m_tabs->addTab(m_subOut,    "  SUBFINDER  ");
    m_amassOut  = makeTerminal(this); m_tabs->addTab(m_amassOut,  "  AMASS  ");
    m_shodanOut = makeTerminal(this); m_tabs->addTab(m_shodanOut, "  SHODAN  ");

    outer->addWidget(m_tabs, 1);
}

void OsintPage::startTool(const QStringList& cmd, const QString& label) {
    if (m_proc && m_proc->state() != QProcess::NotRunning) {
        m_activeOut->log("Another tool is running — stop it first", "WARNING");
        return;
    }
    delete m_proc;
    m_proc = new QProcess(this);
    m_activeLabel = label;

    connect(m_proc, &QProcess::readyReadStandardOutput, this, &OsintPage::onOutput);
    connect(m_proc, &QProcess::readyReadStandardError, this, [this]() {
        QString err = m_proc->readAllStandardError().trimmed();
        if (!err.isEmpty() && m_activeOut)
            m_activeOut->log(err, "WARNING");
    });
    connect(m_proc, QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished),
            this, &OsintPage::onFinished);

    m_activeOut->log("▶ " + label + ": " + cmd.join(" "), "SYSTEM");
    m_proc->start(cmd[0], cmd.mid(1));
    if (m_proc->error() == QProcess::FailedToStart) {
        m_activeOut->log("Tool not found: " + cmd[0] + " — install it first", "CRITICAL");
        m_proc->deleteLater(); m_proc = nullptr;
        return;
    }
    m_stopBtn->setEnabled(true);
}

void OsintPage::runWhois() {
    QString t = m_targetEdit->text().trimmed();
    if (t.isEmpty()) { m_whoisOut->log("Enter a target", "WARNING"); return; }
    m_activeOut = m_whoisOut;
    m_tabs->setCurrentWidget(m_whoisOut);
    startTool({"whois", t}, "WHOIS[" + t + "]");
}

void OsintPage::runDns() {
    QString t = m_targetEdit->text().trimmed();
    if (t.isEmpty()) { m_dnsOut->log("Enter a target", "WARNING"); return; }
    m_activeOut = m_dnsOut;
    m_tabs->setCurrentWidget(m_dnsOut);
    startTool({"dig", t, "ANY", "+noall", "+answer", "+additional"}, "DNS[" + t + "]");
}

void OsintPage::runHarvester() {
    QString t = m_targetEdit->text().trimmed();
    if (t.isEmpty()) { m_harvOut->log("Enter a domain", "WARNING"); return; }
    m_activeOut = m_harvOut;
    m_tabs->setCurrentWidget(m_harvOut);
    startTool({"theHarvester", "-d", t, "-b", "google,bing,duckduckgo,sublist3r", "-l", "200"},
              "HARVESTER[" + t + "]");
}

void OsintPage::runSubfinder() {
    QString t = m_targetEdit->text().trimmed();
    if (t.isEmpty()) { m_subOut->log("Enter a domain", "WARNING"); return; }
    m_activeOut = m_subOut;
    m_tabs->setCurrentWidget(m_subOut);
    startTool({"subfinder", "-d", t, "-silent"}, "SUBFINDER[" + t + "]");
}

void OsintPage::runAmass() {
    QString t = m_targetEdit->text().trimmed();
    if (t.isEmpty()) { m_amassOut->log("Enter a domain", "WARNING"); return; }
    m_activeOut = m_amassOut;
    m_tabs->setCurrentWidget(m_amassOut);
    startTool({"amass", "enum", "-passive", "-d", t}, "AMASS[" + t + "]");
}

void OsintPage::runShodan() {
    QString t = m_targetEdit->text().trimmed();
    if (t.isEmpty()) { m_shodanOut->log("Enter an IP or hostname", "WARNING"); return; }
    m_activeOut = m_shodanOut;
    m_tabs->setCurrentWidget(m_shodanOut);
    startTool({"shodan", "host", t}, "SHODAN[" + t + "]");
}

void OsintPage::stopAll() {
    if (m_proc && m_proc->state() != QProcess::NotRunning) {
        m_proc->terminate();
        m_proc->waitForFinished(2000);
        if (m_proc->state() != QProcess::NotRunning) m_proc->kill();
        if (m_activeOut) m_activeOut->log("■ Stopped: " + m_activeLabel, "WARNING");
    }
    m_stopBtn->setEnabled(false);
}

void OsintPage::onOutput() {
    while (m_proc->canReadLine()) {
        QString line = m_proc->readLine().trimmed();
        if (!line.isEmpty() && m_activeOut)
            m_activeOut->log(line, "INFO");
    }
}

void OsintPage::onFinished(int code, QProcess::ExitStatus) {
    QString rest = m_proc->readAll().trimmed();
    if (!rest.isEmpty() && m_activeOut) m_activeOut->log(rest, "INFO");
    if (m_activeOut)
        m_activeOut->log(QString("✓ %1 finished (exit %2)").arg(m_activeLabel).arg(code), "SUCCESS");
    m_stopBtn->setEnabled(false);
}
