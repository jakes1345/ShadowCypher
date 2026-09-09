#include "ThreatPage.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QHeaderView>
#include <QSplitter>
#include <QNetworkRequest>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QUrl>
#include <QUrlQuery>
#include <QDateTime>
#include <QProcess>
#include <QScrollArea>

ThreatPage::ThreatPage(IpcClient* ipc, QWidget* parent)
    : QWidget(parent), m_ipc(ipc)
{
    m_nam = new QNetworkAccessManager(this);
    connect(m_nam, &QNetworkAccessManager::finished, this, &ThreatPage::onCveReply);

    buildUi();

    // Auto-refresh every 10 minutes
    m_autoRefresh = new QTimer(this);
    m_autoRefresh->setInterval(600'000);
    connect(m_autoRefresh, &QTimer::timeout, this, &ThreatPage::fetchCves);
    m_autoRefresh->start();

    // Initial fetch on first show
    QTimer::singleShot(500, this, &ThreatPage::fetchCves);
}

void ThreatPage::buildUi() {
    auto* outer = new QVBoxLayout(this);
    outer->setContentsMargins(20, 14, 20, 14);
    outer->setSpacing(10);

    // Header
    auto* hdr = new QHBoxLayout;
    auto* title = new QLabel;
    title->setText("<span style='font-weight:900;font-size:16px;color:#f43f5e;letter-spacing:2px;'>THREAT_INTEL</span>");
    title->setTextFormat(Qt::RichText);
    hdr->addWidget(title);
    hdr->addStretch();
    m_lastUpdated = new QLabel("—");
    m_lastUpdated->setStyleSheet("color:#334155;font-family:'JetBrains Mono';font-size:10px;");
    hdr->addWidget(m_lastUpdated);
    outer->addLayout(hdr);

    // Controls
    auto* ctrlRow = new QHBoxLayout;
    ctrlRow->setSpacing(8);

    m_keywordEdit = new QLineEdit;
    m_keywordEdit->setPlaceholderText("CVE keyword (e.g. linux kernel, openssl, apache)");
    m_keywordEdit->setStyleSheet(R"(
        QLineEdit { background: #060810; border: 1px solid rgba(255,255,255,0.08);
            border-radius: 4px; color: #e2e8f0; font-family: 'JetBrains Mono';
            font-size: 12px; padding: 6px 10px; }
        QLineEdit:focus { border-color: #f43f5e; }
    )");
    connect(m_keywordEdit, &QLineEdit::returnPressed, this, &ThreatPage::fetchCves);
    ctrlRow->addWidget(m_keywordEdit, 2);

    m_severityCombo = new QComboBox;
    m_severityCombo->addItems({"All Severity", "CRITICAL", "HIGH", "MEDIUM", "LOW"});
    m_severityCombo->setStyleSheet(R"(
        QComboBox { background: #060810; border: 1px solid rgba(255,255,255,0.08);
            border-radius: 4px; color: #94a3b8; font-family: 'JetBrains Mono';
            font-size: 11px; padding: 6px 10px; min-width: 120px; }
        QComboBox::drop-down { border: none; }
        QComboBox QAbstractItemView { background: #111827; color: #e2e8f0;
            border: 1px solid rgba(255,255,255,0.1); selection-background-color: rgba(244,63,94,0.15); }
    )");
    ctrlRow->addWidget(m_severityCombo);

    m_fetchBtn = new QPushButton("▶ FETCH CVEs");
    m_fetchBtn->setStyleSheet(R"(
        QPushButton { background: rgba(244,63,94,0.1); border: 1px solid rgba(244,63,94,0.35);
            color: #f43f5e; font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing:1px;
            padding: 6px 14px; border-radius: 4px; font-weight: 700; }
        QPushButton:hover { background: rgba(244,63,94,0.2); }
        QPushButton:disabled { color: #334155; border-color: #1e293b; } )");
    connect(m_fetchBtn, &QPushButton::clicked, this, &ThreatPage::fetchCves);
    ctrlRow->addWidget(m_fetchBtn);

    m_localBtn = new QPushButton("LOCAL AUDIT");
    m_localBtn->setStyleSheet(R"(
        QPushButton { background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.35);
            color: #fbbf24; font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing:1px;
            padding: 6px 14px; border-radius: 4px; font-weight: 700; }
        QPushButton:hover { background: rgba(251,191,36,0.2); } )");
    connect(m_localBtn, &QPushButton::clicked, this, &ThreatPage::runLocalCheck);
    ctrlRow->addWidget(m_localBtn);
    outer->addLayout(ctrlRow);

    // CVE table
    m_cveTable = new QTableWidget(0, 6);
    m_cveTable->setHorizontalHeaderLabels({"CVE ID", "CVSS", "Severity", "Published", "Vendor", "Description"});
    m_cveTable->horizontalHeader()->setSectionResizeMode(5, QHeaderView::Stretch);
    m_cveTable->horizontalHeader()->setSectionResizeMode(0, QHeaderView::ResizeToContents);
    m_cveTable->horizontalHeader()->setSectionResizeMode(1, QHeaderView::ResizeToContents);
    m_cveTable->horizontalHeader()->setSectionResizeMode(2, QHeaderView::ResizeToContents);
    m_cveTable->horizontalHeader()->setSectionResizeMode(3, QHeaderView::ResizeToContents);
    m_cveTable->horizontalHeader()->setSectionResizeMode(4, QHeaderView::ResizeToContents);
    m_cveTable->setEditTriggers(QAbstractItemView::NoEditTriggers);
    m_cveTable->setSelectionBehavior(QAbstractItemView::SelectRows);
    m_cveTable->setWordWrap(false);
    m_cveTable->setStyleSheet(R"(
        QTableWidget { background: #060810; border: 1px solid rgba(255,255,255,0.06);
            border-radius: 8px; color: #94a3b8; font-family: 'JetBrains Mono';
            font-size: 11px; gridline-color: rgba(255,255,255,0.03); }
        QTableWidget::item:selected { background: rgba(244,63,94,0.1); color: #f43f5e; }
        QHeaderView::section { background: #111827; color: #475569; border: none;
            font-size: 10px; letter-spacing: 1px; padding: 6px; }
    )");
    m_cveTable->verticalHeader()->setVisible(false);
    m_cveTable->setAlternatingRowColors(false);

    auto* splitter = new QSplitter(Qt::Vertical);
    splitter->addWidget(m_cveTable);

    m_output = new TacticalTerminal(this);
    m_output->setMinimumHeight(140);
    splitter->addWidget(m_output);
    splitter->setSizes({400, 140});

    outer->addWidget(splitter, 1);
}

QString ThreatPage::cvssColor(double score) {
    if (score >= 9.0) return "#f43f5e";   // CRITICAL
    if (score >= 7.0) return "#f97316";   // HIGH
    if (score >= 4.0) return "#fbbf24";   // MEDIUM
    return "#10b981";                      // LOW
}

void ThreatPage::fetchCves() {
    m_fetchBtn->setEnabled(false);
    m_output->log("Fetching CVE feed from NVD (nvd.nist.gov)…", "SYSTEM");

    QUrl url("https://services.nvd.nist.gov/rest/json/cves/2.0");
    QUrlQuery q;
    q.addQueryItem("resultsPerPage", "50");

    QString kw = m_keywordEdit->text().trimmed();
    if (!kw.isEmpty())
        q.addQueryItem("keywordSearch", kw);

    QString sev = m_severityCombo->currentText();
    if (sev != "All Severity")
        q.addQueryItem("cvssV3Severity", sev);

    url.setQuery(q);

    QNetworkRequest req(url);
    req.setRawHeader("User-Agent", "ShadowCypher/1.0 ThreatIntel");
    m_nam->get(req);
}

void ThreatPage::onCveReply(QNetworkReply* reply) {
    m_fetchBtn->setEnabled(true);
    reply->deleteLater();

    if (reply->error() != QNetworkReply::NoError) {
        m_output->log("CVE fetch error: " + reply->errorString(), "CRITICAL");
        return;
    }

    QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
    if (doc.isNull() || !doc.isObject()) {
        m_output->log("Invalid response from NVD", "CRITICAL");
        return;
    }

    QJsonArray vulns = doc.object().value("vulnerabilities").toArray();
    m_output->log(QString("Loaded %1 CVEs").arg(vulns.size()), "SUCCESS");
    m_lastUpdated->setText("Updated: " + QDateTime::currentDateTime().toString("hh:mm:ss"));
    populateCveTable(vulns);
}

void ThreatPage::populateCveTable(const QJsonArray& vulns) {
    m_cveTable->setRowCount(0);

    for (const auto& v : vulns) {
        QJsonObject cve = v.toObject().value("cve").toObject();
        QString id = cve.value("id").toString();

        // Description (first English entry)
        QString desc;
        for (const auto& d : cve.value("descriptions").toArray()) {
            if (d.toObject().value("lang").toString() == "en") {
                desc = d.toObject().value("value").toString();
                break;
            }
        }

        // Published
        QString pub = cve.value("published").toString().left(10);

        // CVSS v3 score + severity
        double cvssScore = 0.0;
        QString severity = "N/A";
        QString vendor;
        QJsonObject metrics = cve.value("metrics").toObject();
        QJsonArray cvss3 = metrics.value("cvssMetricV31").toArray();
        if (cvss3.isEmpty()) cvss3 = metrics.value("cvssMetricV30").toArray();
        if (!cvss3.isEmpty()) {
            QJsonObject cv = cvss3[0].toObject().value("cvssData").toObject();
            cvssScore = cv.value("baseScore").toDouble();
            severity  = cv.value("baseSeverity").toString();
        }

        // Vendor from CPE
        QJsonArray cpes = cve.value("configurations").toArray();
        QStringList vendors;
        for (const auto& cfg : cpes) {
            for (const auto& node : cfg.toObject().value("nodes").toArray()) {
                for (const auto& match : node.toObject().value("cpeMatch").toArray()) {
                    QString cpe = match.toObject().value("criteria").toString();
                    QStringList parts = cpe.split(':');
                    if (parts.size() > 3 && !vendors.contains(parts[3]))
                        vendors << parts[3];
                }
            }
        }
        vendor = vendors.join(", ").left(30);

        int row = m_cveTable->rowCount();
        m_cveTable->insertRow(row);

        auto* idItem = new QTableWidgetItem(id);
        idItem->setForeground(QColor(cvssColor(cvssScore)));
        m_cveTable->setItem(row, 0, idItem);

        auto* scoreItem = new QTableWidgetItem(cvssScore > 0 ? QString::number(cvssScore, 'f', 1) : "—");
        scoreItem->setForeground(QColor(cvssColor(cvssScore)));
        m_cveTable->setItem(row, 1, scoreItem);

        auto* sevItem = new QTableWidgetItem(severity);
        sevItem->setForeground(QColor(cvssColor(cvssScore)));
        m_cveTable->setItem(row, 2, sevItem);

        m_cveTable->setItem(row, 3, new QTableWidgetItem(pub));
        m_cveTable->setItem(row, 4, new QTableWidgetItem(vendor));
        m_cveTable->setItem(row, 5, new QTableWidgetItem(desc.left(120)));
    }
}

void ThreatPage::runLocalCheck() {
    if (m_localProc && m_localProc->state() != QProcess::NotRunning) return;
    delete m_localProc;
    m_localProc = new QProcess(this);

    connect(m_localProc, &QProcess::readyReadStandardOutput, this, &ThreatPage::onLocalCheckOutput);
    connect(m_localProc, &QProcess::readyReadStandardError, this, [this]() {
        m_output->log(m_localProc->readAllStandardError().trimmed(), "WARNING");
    });
    connect(m_localProc, QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished),
            this, &ThreatPage::onLocalCheckFinished);

    m_output->log("Running local package audit (arch-audit / pacman)…", "SYSTEM");
    m_localBtn->setEnabled(false);

    // arch-audit reads Arch security tracker and checks installed packages
    m_localProc->start("arch-audit", {"--upgradable", "--format", "%n %s %c"});
    if (m_localProc->error() == QProcess::FailedToStart) {
        m_output->log("arch-audit not found — falling back to pacman -Q", "WARNING");
        m_localProc->start("pacman", {"-Q"});
    }
}

void ThreatPage::onLocalCheckOutput() {
    while (m_localProc->canReadLine()) {
        QString line = m_localProc->readLine().trimmed();
        if (!line.isEmpty()) {
            bool isCrit = line.contains("Critical", Qt::CaseInsensitive) ||
                          line.contains("High",     Qt::CaseInsensitive);
            m_output->log(line, isCrit ? "CRITICAL" : "INFO");
        }
    }
}

void ThreatPage::onLocalCheckFinished(int code, QProcess::ExitStatus) {
    QString rest = m_localProc->readAll().trimmed();
    if (!rest.isEmpty()) m_output->log(rest, "INFO");
    m_output->log(QString("Local audit complete (exit %1)").arg(code), "SUCCESS");
    m_localBtn->setEnabled(true);
}
