#include "SmartContractPage.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QFileDialog>
#include <QTemporaryFile>
#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QJsonParseError>

static QString darkInput() {
    return R"(QLineEdit { background: #060810; border: 1px solid rgba(255,255,255,0.08);
        border-radius: 4px; color: #e2e8f0; font-family: 'JetBrains Mono';
        font-size: 12px; padding: 6px 10px; }
    QLineEdit:focus { border-color: #b44aff; })";
}
static QString darkTextArea() {
    return R"(QPlainTextEdit { background: #060810; border: 1px solid rgba(255,255,255,0.08);
        border-radius: 4px; color: #e2e8f0; font-family: 'JetBrains Mono';
        font-size: 11px; padding: 8px; }
    QPlainTextEdit:focus { border-color: #b44aff; })";
}
static QString darkCombo() {
    return R"(QComboBox { background: #060810; border: 1px solid rgba(255,255,255,0.08);
        border-radius: 4px; color: #94a3b8; font-family: 'JetBrains Mono';
        font-size: 11px; padding: 5px 10px; }
    QComboBox::drop-down { border: none; }
    QComboBox QAbstractItemView { background: #111827; color: #e2e8f0;
        border: 1px solid rgba(255,255,255,0.1); })";
}
static QString purpleBtn() {
    return "QPushButton { background: rgba(180,74,255,0.1); border: 1px solid rgba(180,74,255,0.35); "
           "color: #b44aff; font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing:1px; "
           "padding: 6px 14px; border-radius: 4px; font-weight: 700; } "
           "QPushButton:hover { background: rgba(180,74,255,0.2); }";
}

SmartContractPage::SmartContractPage(QWidget* parent) : QWidget(parent) {
    buildUi();
}

SmartContractPage::~SmartContractPage() {
    if (!m_tempFile.isEmpty()) QFile::remove(m_tempFile);
}

void SmartContractPage::buildUi() {
    auto* outer = new QVBoxLayout(this);
    outer->setContentsMargins(20, 14, 20, 14);
    outer->setSpacing(10);

    // Header row
    auto* hdr = new QHBoxLayout;
    auto* title = new QLabel;
    title->setText(
        "<span style='font-weight:900;font-size:16px;color:#b44aff;letter-spacing:2px;'>WEB3_AUDIT</span>"
        "<span style='font-size:11px;color:#475569;letter-spacing:1px;'>"
        " — smart contract vulnerability scanner</span>");
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
    connect(m_stopBtn, &QPushButton::clicked, this, &SmartContractPage::stopScan);
    hdr->addWidget(m_stopBtn);
    outer->addLayout(hdr);

    m_tabs = new QTabWidget;
    m_tabs->setStyleSheet(R"(
        QTabWidget::pane { border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; }
        QTabBar::tab { background: transparent; color: #475569; font-family: 'JetBrains Mono';
            font-size: 11px; letter-spacing: 1px; padding: 6px 16px; }
        QTabBar::tab:selected { color: #b44aff; border-bottom: 2px solid #b44aff; }
        QTabBar::tab:hover { color: #94a3b8; }
    )");

    // ── File Scan tab ──────────────────────────────────────────────────────────
    {
        auto* tab = new QWidget;
        auto* lay = new QVBoxLayout(tab);
        lay->setContentsMargins(12, 12, 12, 12);
        lay->setSpacing(8);

        auto* row = new QHBoxLayout; row->setSpacing(8);

        m_filePath = new QLineEdit;
        m_filePath->setPlaceholderText("Path to .sol file…");
        m_filePath->setStyleSheet(darkInput());
        connect(m_filePath, &QLineEdit::returnPressed, this, &SmartContractPage::scanFile);
        row->addWidget(m_filePath, 3);

        auto* browseBtn = new QPushButton("BROWSE");
        browseBtn->setStyleSheet(
            "QPushButton { background: rgba(100,116,139,0.1); border: 1px solid rgba(100,116,139,0.3); "
            "color: #94a3b8; font-family: 'JetBrains Mono'; font-size: 11px; "
            "padding: 6px 12px; border-radius: 4px; } "
            "QPushButton:hover { background: rgba(100,116,139,0.2); }");
        connect(browseBtn, &QPushButton::clicked, this, &SmartContractPage::browseFile);
        row->addWidget(browseBtn);

        auto* sevLbl = new QLabel("Min Severity:");
        sevLbl->setStyleSheet("color:#64748b;font-size:11px;font-family:'JetBrains Mono';");
        row->addWidget(sevLbl);

        m_minSeverity = new QComboBox;
        m_minSeverity->addItems({"low", "medium", "high", "critical"});
        m_minSeverity->setStyleSheet(darkCombo());
        m_minSeverity->setFixedWidth(110);
        row->addWidget(m_minSeverity);

        auto* scanBtn = new QPushButton("▶ SCAN FILE");
        scanBtn->setStyleSheet(purpleBtn());
        connect(scanBtn, &QPushButton::clicked, this, &SmartContractPage::scanFile);
        row->addWidget(scanBtn);
        lay->addLayout(row);

        m_fileOut = new TacticalTerminal(this);
        m_fileOut->log("WEB3 AUDIT — Smart Contract Vulnerability Scanner", "SYSTEM");
        m_fileOut->log("Detectors: Reentrancy · Access Control · Integer Overflow · Flash Loan", "INFO");
        m_fileOut->log("           Weak Randomness · Timestamp · Precision Loss · Arbitrary Call", "INFO");
        m_fileOut->log("           Storage Collision · Oracle Manipulation · State-After-External", "INFO");
        m_fileOut->log("Reference: SWC Registry · DeFiHackLabs real-world exploit database", "INFO");
        lay->addWidget(m_fileOut, 1);

        m_tabs->addTab(tab, "  FILE SCAN  ");
    }

    // ── Paste Source tab ───────────────────────────────────────────────────────
    {
        auto* tab = new QWidget;
        auto* lay = new QVBoxLayout(tab);
        lay->setContentsMargins(12, 12, 12, 12);
        lay->setSpacing(8);

        auto* topRow = new QHBoxLayout; topRow->setSpacing(8);
        topRow->addStretch();
        auto* scanBtn = new QPushButton("▶ SCAN SOURCE");
        scanBtn->setStyleSheet(purpleBtn());
        connect(scanBtn, &QPushButton::clicked, this, &SmartContractPage::scanPaste);
        topRow->addWidget(scanBtn);
        lay->addLayout(topRow);

        auto* split = new QHBoxLayout; split->setSpacing(10);

        m_pasteEdit = new QPlainTextEdit;
        m_pasteEdit->setPlaceholderText(
            "// Paste Solidity source code here\n"
            "pragma solidity ^0.8.0;\n\n"
            "contract Vulnerable {\n"
            "    mapping(address => uint256) public balances;\n\n"
            "    function withdraw(uint256 amount) public {\n"
            "        require(balances[msg.sender] >= amount);\n"
            "        (bool ok,) = msg.sender.call{value: amount}(\"\");\n"
            "        require(ok);\n"
            "        balances[msg.sender] -= amount;  // state after external call!\n"
            "    }\n"
            "}");
        m_pasteEdit->setStyleSheet(darkTextArea());
        m_pasteEdit->setTabStopDistance(28);
        split->addWidget(m_pasteEdit, 1);

        m_pasteOut = new TacticalTerminal(this);
        m_pasteOut->log("Paste Solidity source on the left, then click SCAN SOURCE", "SYSTEM");
        split->addWidget(m_pasteOut, 1);

        lay->addLayout(split, 1);
        m_tabs->addTab(tab, "  PASTE SOURCE  ");
    }

    outer->addWidget(m_tabs, 1);
}

void SmartContractPage::browseFile() {
    QString path = QFileDialog::getOpenFileName(
        this, "Select Solidity Contract", QDir::homePath(),
        "Solidity Files (*.sol);;All Files (*)");
    if (!path.isEmpty()) m_filePath->setText(path);
}

void SmartContractPage::scanFile() {
    QString path = m_filePath->text().trimmed();
    if (path.isEmpty()) {
        m_fileOut->log("Select or enter a .sol file path first", "WARNING");
        return;
    }
    startScan(path, m_fileOut);
}

void SmartContractPage::scanPaste() {
    QString src = m_pasteEdit->toPlainText().trimmed();
    if (src.isEmpty()) {
        m_pasteOut->log("Paste Solidity source code first", "WARNING");
        return;
    }

    if (!m_tempFile.isEmpty()) {
        QFile::remove(m_tempFile);
        m_tempFile.clear();
    }

    QTemporaryFile tf;
    tf.setAutoRemove(false);
    tf.setFileTemplate(QDir::tempPath() + "/sc_audit_XXXXXX.sol");
    if (!tf.open()) {
        m_pasteOut->log("Could not create temporary file", "CRITICAL");
        return;
    }
    tf.write(src.toUtf8());
    m_tempFile = tf.fileName();
    tf.close();

    startScan(m_tempFile, m_pasteOut);
}

void SmartContractPage::startScan(const QString& filePath, TacticalTerminal* out) {
    if (m_proc && m_proc->state() != QProcess::NotRunning) {
        out->log("Scan already running — stop it first", "WARNING");
        return;
    }
    delete m_proc;
    m_proc      = new QProcess(this);
    m_activeOut = out;
    m_jsonBuf.clear();

    connect(m_proc, &QProcess::readyReadStandardOutput, this, &SmartContractPage::onOutput);
    connect(m_proc, &QProcess::readyReadStandardError, this, [this]() {
        QString err = QString::fromUtf8(m_proc->readAllStandardError()).trimmed();
        if (!err.isEmpty() && m_activeOut) m_activeOut->log(err, "WARNING");
    });
    connect(m_proc, QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished),
            this, &SmartContractPage::onScanFinished);

    QStringList args = {
        "-m", "shadowcypher.modules.smart_contract",
        filePath, "--json",
        "--min-severity", m_minSeverity->currentText()
    };
    out->log("▶ SCANNING: " + filePath, "SYSTEM");
    m_proc->start("python3", args);
    if (m_proc->error() == QProcess::FailedToStart) {
        out->log("python3 not found — ensure Python 3 is installed", "CRITICAL");
        m_proc->deleteLater();
        m_proc = nullptr;
        return;
    }
    m_stopBtn->setEnabled(true);
}

void SmartContractPage::stopScan() {
    if (m_proc && m_proc->state() != QProcess::NotRunning) {
        m_proc->terminate();
        m_proc->waitForFinished(2000);
        if (m_proc->state() != QProcess::NotRunning) m_proc->kill();
        if (m_activeOut) m_activeOut->log("■ Scan stopped by user", "WARNING");
    }
    m_stopBtn->setEnabled(false);
}

void SmartContractPage::onOutput() {
    m_jsonBuf += m_proc->readAllStandardOutput();
}

void SmartContractPage::onScanFinished(int code, QProcess::ExitStatus) {
    m_jsonBuf += m_proc->readAllStandardOutput();
    m_stopBtn->setEnabled(false);

    if (code != 0) {
        if (m_activeOut) {
            m_activeOut->log("Scanner exited with code " + QString::number(code), "CRITICAL");
            QString txt = QString::fromUtf8(m_jsonBuf).trimmed();
            if (!txt.isEmpty()) m_activeOut->log(txt, "CRITICAL");
        }
        return;
    }
    renderFindings(m_jsonBuf, m_activeOut);
}

void SmartContractPage::renderFindings(const QByteArray& jsonData, TacticalTerminal* out) {
    if (!out) return;

    QJsonParseError parseErr;
    QJsonDocument doc = QJsonDocument::fromJson(jsonData, &parseErr);
    if (doc.isNull()) {
        out->log("Failed to parse scanner output: " + parseErr.errorString(), "CRITICAL");
        out->log(QString::fromUtf8(jsonData.left(512)), "INFO");
        return;
    }

    QJsonObject root     = doc.object();
    QJsonObject contract = root["contract"].toObject();
    QJsonObject summary  = root["summary"].toObject();
    QJsonArray  findings = root["findings"].toArray();
    QJsonArray  errors   = root["parse_errors"].toArray();

    out->log("", "INFO");
    out->log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "SYSTEM");
    out->log(QString("CONTRACT  : %1").arg(contract["name"].toString()), "SYSTEM");
    QString pragma = contract["pragma"].toString();
    if (!pragma.isEmpty())
        out->log(QString("SOLIDITY  : %1").arg(pragma), "SYSTEM");
    out->log(QString("CONTRACTS : %1   FUNCTIONS: %2")
             .arg(contract["contract_count"].toInt())
             .arg(contract["function_count"].toInt()), "SYSTEM");

    out->log("", "INFO");
    out->log(QString("FINDINGS  : %1 total  |  %2 CRITICAL  |  %3 HIGH  |  %4 MEDIUM  |  %5 LOW")
             .arg(summary["total"].toInt())
             .arg(summary["critical"].toInt())
             .arg(summary["high"].toInt())
             .arg(summary["medium"].toInt())
             .arg(summary["low"].toInt()),
             summary["critical"].toInt() > 0 ? "CRITICAL" :
             summary["high"].toInt()     > 0 ? "ERROR"    : "SUCCESS");
    out->log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "SYSTEM");

    for (const auto& fv : errors) {
        QJsonObject e = fv.toObject();
        out->log(QString("PARSE ERR  line %1: %2")
                 .arg(e["line"].toInt())
                 .arg(e["message"].toString()), "WARNING");
    }

    if (findings.isEmpty()) {
        out->log("No vulnerabilities detected above threshold.", "SUCCESS");
        out->log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "SYSTEM");
        return;
    }

    for (const auto& fv : findings) {
        QJsonObject f   = fv.toObject();
        QString sev     = f["severity"].toString().toUpper();
        QString swc     = f["swc_id"].toString();
        QString vulnType = f["vuln_type"].toString();
        QString fn      = f["function"].toString();
        int     line    = f["line"].toInt();

        QString level = sev == "CRITICAL" ? "CRITICAL" :
                        sev == "HIGH"     ? "ERROR"    :
                        sev == "MEDIUM"   ? "WARNING"  : "INFO";

        out->log("", "INFO");
        out->log(QString("[%1] %2  %3  %4")
                 .arg(sev, -8)
                 .arg(swc.isEmpty() ? QString() : "[" + swc + "]")
                 .arg(vulnType)
                 .arg(f["title"].toString()),
                 level);

        QString loc;
        if (!fn.isEmpty())  loc += "fn " + fn + "  ";
        if (line > 0)       loc += "line " + QString::number(line);
        if (!loc.isEmpty()) out->log("  Location : " + loc, "INFO");

        out->log("  " + f["description"].toString(), "INFO");

        QJsonArray rw = f["real_world_exploits"].toArray();
        if (!rw.isEmpty()) {
            QStringList rwList;
            for (const auto& r : rw) rwList << r.toString();
            out->log("  ⚡ Real exploits: " + rwList.join(" · "), "WARNING");
        }

        out->log("  Fix: " + f["remediation"].toString(), "SUCCESS");
    }

    out->log("", "INFO");
    out->log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "SYSTEM");
    out->log("Audit complete", "SUCCESS");
}
