#include "VulnPage.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QLabel>
#include <QGroupBox>

static QString darkInput() {
    return R"(QLineEdit { background: #060810; border: 1px solid rgba(255,255,255,0.08);
        border-radius: 4px; color: #e2e8f0; font-family: 'JetBrains Mono';
        font-size: 12px; padding: 6px 10px; }
    QLineEdit:focus { border-color: #f97316; })";
}
static QString darkCombo() {
    return R"(QComboBox { background: #060810; border: 1px solid rgba(255,255,255,0.08);
        border-radius: 4px; color: #94a3b8; font-family: 'JetBrains Mono';
        font-size: 11px; padding: 5px 10px; }
    QComboBox::drop-down { border: none; }
    QComboBox QAbstractItemView { background: #111827; color: #e2e8f0;
        border: 1px solid rgba(255,255,255,0.1); })";
}

VulnPage::VulnPage(QWidget* parent) : QWidget(parent) {
    buildUi();
}

void VulnPage::buildUi() {
    auto* outer = new QVBoxLayout(this);
    outer->setContentsMargins(20, 14, 20, 14);
    outer->setSpacing(10);

    // Header
    auto* hdr = new QHBoxLayout;
    auto* title = new QLabel;
    title->setText("<span style='font-weight:900;font-size:16px;color:#f97316;letter-spacing:2px;'>VULN_NEXUS</span>");
    title->setTextFormat(Qt::RichText);
    hdr->addWidget(title);
    hdr->addStretch();

    m_stopBtn = new QPushButton("■ STOP");
    m_stopBtn->setEnabled(false);
    m_stopBtn->setStyleSheet(
        "QPushButton { background: rgba(244,63,94,0.1); border: 1px solid rgba(244,63,94,0.35); "
        "color: #f43f5e; font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing:1px; "
        "padding: 6px 14px; border-radius: 4px; } "
        "QPushButton:hover { background: rgba(244,63,94,0.2); } "
        "QPushButton:disabled { color: #334155; border-color: #1e293b; }");
    connect(m_stopBtn, &QPushButton::clicked, this, &VulnPage::stopAll);
    hdr->addWidget(m_stopBtn);
    outer->addLayout(hdr);

    m_tabs = new QTabWidget;
    m_tabs->setStyleSheet(R"(
        QTabWidget::pane { border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; }
        QTabBar::tab { background: transparent; color: #475569; font-family: 'JetBrains Mono';
            font-size: 11px; letter-spacing: 1px; padding: 6px 16px; }
        QTabBar::tab:selected { color: #f97316; border-bottom: 2px solid #f97316; }
        QTabBar::tab:hover { color: #94a3b8; }
    )");

    // ── Nikto tab ──────────────────────────────────────────────
    {
        auto* tab = new QWidget;
        auto* lay = new QVBoxLayout(tab);
        lay->setContentsMargins(12, 12, 12, 12); lay->setSpacing(8);

        auto* row = new QHBoxLayout; row->setSpacing(8);
        m_niktoTarget = new QLineEdit; m_niktoTarget->setPlaceholderText("http://target.com");
        m_niktoTarget->setStyleSheet(darkInput());
        row->addWidget(m_niktoTarget, 2);

        m_niktoSsl = new QCheckBox("SSL");
        m_niktoSsl->setStyleSheet("color: #94a3b8; font-family: 'JetBrains Mono'; font-size: 11px;");
        row->addWidget(m_niktoSsl);

        m_niktoCgiCombo = new QComboBox;
        m_niktoCgiCombo->addItems({"/cgi-bin/", "/cgi-local/", "none"});
        m_niktoCgiCombo->setStyleSheet(darkCombo());
        row->addWidget(m_niktoCgiCombo);

        auto* scanBtn = new QPushButton("▶ NIKTO SCAN");
        scanBtn->setStyleSheet(
            "QPushButton { background: rgba(249,115,22,0.1); border: 1px solid rgba(249,115,22,0.35); "
            "color: #f97316; font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing:1px; "
            "padding: 6px 14px; border-radius: 4px; font-weight: 700; } "
            "QPushButton:hover { background: rgba(249,115,22,0.2); }");
        connect(scanBtn, &QPushButton::clicked, this, &VulnPage::runNikto);
        row->addWidget(scanBtn);
        lay->addLayout(row);

        m_niktoOut = new TacticalTerminal(this);
        m_niktoOut->log("Nikto — web server scanner. Checks for 6700+ dangerous files/CGIs.", "SYSTEM");
        lay->addWidget(m_niktoOut, 1);
        m_tabs->addTab(tab, "  NIKTO  ");
    }

    // ── SQLmap tab ─────────────────────────────────────────────
    {
        auto* tab = new QWidget;
        auto* lay = new QVBoxLayout(tab);
        lay->setContentsMargins(12, 12, 12, 12); lay->setSpacing(8);

        auto* row1 = new QHBoxLayout; row1->setSpacing(8);
        m_sqlUrl = new QLineEdit; m_sqlUrl->setPlaceholderText("http://target.com/page?id=1");
        m_sqlUrl->setStyleSheet(darkInput());
        row1->addWidget(m_sqlUrl, 3);

        auto* row2 = new QHBoxLayout; row2->setSpacing(8);
        row2->addWidget(new QLabel("Level:")); row2->itemAt(0)->widget()->setStyleSheet("color:#64748b;font-size:11px;font-family:'JetBrains Mono';");
        m_sqlLevel = new QComboBox; m_sqlLevel->addItems({"1","2","3","4","5"});
        m_sqlLevel->setStyleSheet(darkCombo()); m_sqlLevel->setFixedWidth(70);
        row2->addWidget(m_sqlLevel);

        row2->addWidget(new QLabel("Risk:")); row2->itemAt(2)->widget()->setStyleSheet("color:#64748b;font-size:11px;font-family:'JetBrains Mono';");
        m_sqlRisk = new QComboBox; m_sqlRisk->addItems({"1","2","3"});
        m_sqlRisk->setStyleSheet(darkCombo()); m_sqlRisk->setFixedWidth(70);
        row2->addWidget(m_sqlRisk);

        m_sqlDbs = new QCheckBox("Enum DBs");
        m_sqlDbs->setStyleSheet("color: #94a3b8; font-family: 'JetBrains Mono'; font-size: 11px;");
        row2->addWidget(m_sqlDbs);
        row2->addStretch();

        auto* sqlBtn = new QPushButton("▶ INJECT TEST");
        sqlBtn->setStyleSheet(
            "QPushButton { background: rgba(244,63,94,0.1); border: 1px solid rgba(244,63,94,0.35); "
            "color: #f43f5e; font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing:1px; "
            "padding: 6px 14px; border-radius: 4px; font-weight: 700; } "
            "QPushButton:hover { background: rgba(244,63,94,0.2); }");
        connect(sqlBtn, &QPushButton::clicked, this, &VulnPage::runSqlmap);
        row2->addWidget(sqlBtn);

        lay->addLayout(row1);
        lay->addLayout(row2);

        m_sqlOut = new TacticalTerminal(this);
        m_sqlOut->log("SQLmap — automatic SQL injection detection and exploitation.", "SYSTEM");
        lay->addWidget(m_sqlOut, 1);
        m_tabs->addTab(tab, "  SQLMAP  ");
    }

    // ── Nmap NSE tab ───────────────────────────────────────────
    {
        auto* tab = new QWidget;
        auto* lay = new QVBoxLayout(tab);
        lay->setContentsMargins(12, 12, 12, 12); lay->setSpacing(8);

        auto* row = new QHBoxLayout; row->setSpacing(8);
        m_nseTarget = new QLineEdit; m_nseTarget->setPlaceholderText("Target IP / hostname");
        m_nseTarget->setStyleSheet(darkInput());
        row->addWidget(m_nseTarget, 2);

        m_nsePorts = new QLineEdit; m_nsePorts->setPlaceholderText("Ports"); m_nsePorts->setText("80,443,22,8080");
        m_nsePorts->setStyleSheet(darkInput()); m_nsePorts->setFixedWidth(180);
        row->addWidget(m_nsePorts);

        m_nseScript = new QComboBox;
        m_nseScript->addItems({"vuln", "exploit", "auth", "safe", "default", "http-enum", "smb-vuln-*", "ssl-*"});
        m_nseScript->setStyleSheet(darkCombo());
        row->addWidget(m_nseScript);

        auto* nseBtn = new QPushButton("▶ RUN NSE");
        nseBtn->setStyleSheet(
            "QPushButton { background: rgba(180,74,255,0.1); border: 1px solid rgba(180,74,255,0.35); "
            "color: #b44aff; font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing:1px; "
            "padding: 6px 14px; border-radius: 4px; font-weight: 700; } "
            "QPushButton:hover { background: rgba(180,74,255,0.2); }");
        connect(nseBtn, &QPushButton::clicked, this, &VulnPage::runNmapNse);
        row->addWidget(nseBtn);
        lay->addLayout(row);

        m_nseOut = new TacticalTerminal(this);
        m_nseOut->log("Nmap NSE — scripted vulnerability detection via nmap script engine.", "SYSTEM");
        lay->addWidget(m_nseOut, 1);
        m_tabs->addTab(tab, "  NSE  ");
    }

    // ── Searchsploit tab ───────────────────────────────────────
    {
        auto* tab = new QWidget;
        auto* lay = new QVBoxLayout(tab);
        lay->setContentsMargins(12, 12, 12, 12); lay->setSpacing(8);

        auto* row = new QHBoxLayout; row->setSpacing(8);
        m_splitQuery = new QLineEdit; m_splitQuery->setPlaceholderText("Search term (e.g. apache 2.4 rce, openssl heartbleed)");
        m_splitQuery->setStyleSheet(darkInput());
        connect(m_splitQuery, &QLineEdit::returnPressed, this, &VulnPage::runSearchsploit);
        row->addWidget(m_splitQuery, 3);

        auto* spBtn = new QPushButton("▶ SEARCHSPLOIT");
        spBtn->setStyleSheet(
            "QPushButton { background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.35); "
            "color: #10b981; font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing:1px; "
            "padding: 6px 14px; border-radius: 4px; font-weight: 700; } "
            "QPushButton:hover { background: rgba(16,185,129,0.2); }");
        connect(spBtn, &QPushButton::clicked, this, &VulnPage::runSearchsploit);
        row->addWidget(spBtn);
        lay->addLayout(row);

        m_splitOut = new TacticalTerminal(this);
        m_splitOut->log("Searchsploit — search ExploitDB offline. Requires exploitdb package.", "SYSTEM");
        lay->addWidget(m_splitOut, 1);
        m_tabs->addTab(tab, "  SEARCHSPLOIT  ");
    }

    outer->addWidget(m_tabs, 1);
}

void VulnPage::startTool(const QStringList& cmd, const QString& label, TacticalTerminal* out) {
    if (m_proc && m_proc->state() != QProcess::NotRunning) {
        out->log("Tool already running — stop it first", "WARNING");
        return;
    }
    delete m_proc;
    m_proc = new QProcess(this);
    m_activeLabel = label;
    m_activeOut   = out;

    connect(m_proc, &QProcess::readyReadStandardOutput, this, &VulnPage::onOutput);
    connect(m_proc, &QProcess::readyReadStandardError, this, [this]() {
        QString err = m_proc->readAllStandardError().trimmed();
        if (!err.isEmpty() && m_activeOut) m_activeOut->log(err, "WARNING");
    });
    connect(m_proc, QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished),
            this, &VulnPage::onFinished);

    out->log("▶ " + label + ": " + cmd.join(" "), "SYSTEM");
    m_proc->start(cmd[0], cmd.mid(1));
    if (m_proc->error() == QProcess::FailedToStart) {
        out->log("Not found: " + cmd[0] + " — install it (pacman -S " + cmd[0] + ")", "CRITICAL");
        m_proc->deleteLater(); m_proc = nullptr;
        return;
    }
    m_stopBtn->setEnabled(true);
}

void VulnPage::runNikto() {
    QString t = m_niktoTarget->text().trimmed();
    if (t.isEmpty()) { m_niktoOut->log("Enter a target URL", "WARNING"); return; }
    m_tabs->setCurrentWidget(m_niktoOut->parentWidget());

    QStringList cmd = {"nikto", "-h", t, "-Format", "txt"};
    if (m_niktoSsl->isChecked()) cmd << "-ssl";
    if (m_niktoCgiCombo->currentText() != "none")
        cmd << "-Cgidirs" << m_niktoCgiCombo->currentText();
    startTool(cmd, "NIKTO", m_niktoOut);
}

void VulnPage::runSqlmap() {
    QString url = m_sqlUrl->text().trimmed();
    if (url.isEmpty()) { m_sqlOut->log("Enter a target URL", "WARNING"); return; }
    m_tabs->setCurrentWidget(m_sqlOut->parentWidget());

    QStringList cmd = {"sqlmap", "-u", url, "--batch",
                       "--level", m_sqlLevel->currentText(),
                       "--risk",  m_sqlRisk->currentText()};
    if (m_sqlDbs->isChecked()) cmd << "--dbs";
    startTool(cmd, "SQLMAP", m_sqlOut);
}

void VulnPage::runNmapNse() {
    QString t = m_nseTarget->text().trimmed();
    if (t.isEmpty()) { m_nseOut->log("Enter a target", "WARNING"); return; }
    m_tabs->setCurrentWidget(m_nseOut->parentWidget());

    QStringList cmd = {"nmap", "--script=" + m_nseScript->currentText(),
                       "-p", m_nsePorts->text().trimmed(), "-sV", t};
    startTool(cmd, "NSE[" + m_nseScript->currentText() + "]", m_nseOut);
}

void VulnPage::runSearchsploit() {
    QString q = m_splitQuery->text().trimmed();
    if (q.isEmpty()) { m_splitOut->log("Enter a search term", "WARNING"); return; }
    m_tabs->setCurrentWidget(m_splitOut->parentWidget());
    startTool({"searchsploit", q, "--colour"}, "SEARCHSPLOIT[" + q + "]", m_splitOut);
}

void VulnPage::stopAll() {
    if (m_proc && m_proc->state() != QProcess::NotRunning) {
        m_proc->terminate();
        m_proc->waitForFinished(2000);
        if (m_proc->state() != QProcess::NotRunning) m_proc->kill();
        if (m_activeOut) m_activeOut->log("■ Stopped: " + m_activeLabel, "WARNING");
    }
    m_stopBtn->setEnabled(false);
}

void VulnPage::onOutput() {
    while (m_proc->canReadLine()) {
        QString line = m_proc->readLine().trimmed();
        if (!line.isEmpty() && m_activeOut) m_activeOut->log(line, "INFO");
    }
}

void VulnPage::onFinished(int code, QProcess::ExitStatus) {
    QString rest = m_proc->readAll().trimmed();
    if (!rest.isEmpty() && m_activeOut) m_activeOut->log(rest, "INFO");
    if (m_activeOut)
        m_activeOut->log(QString("✓ %1 complete (exit %2)").arg(m_activeLabel).arg(code), "SUCCESS");
    m_stopBtn->setEnabled(false);
}
