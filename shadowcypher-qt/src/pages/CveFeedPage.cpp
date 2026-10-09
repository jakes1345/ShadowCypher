#include "CveFeedPage.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QSplitter>
#include <QHeaderView>
#include <QTableWidgetItem>
#include <QColor>
#include <QFont>
#include <QJsonArray>
#include <QJsonValue>

// ── Severity helpers ──────────────────────────────────────────────────────────

QString CveFeedPage::severityColor(const QString& sev) {
    if (sev == "CRITICAL") return "#f43f5e";
    if (sev == "HIGH")     return "#ffb84d";
    if (sev == "MEDIUM")   return "#f5d060";
    if (sev == "LOW")      return "#00ff9d";
    return "#64748b";
}

QString CveFeedPage::severityFg(const QString& sev) {
    if (sev == "HIGH" || sev == "MEDIUM" || sev == "LOW") return "#0d0f1a";
    return "#ffffff";
}

// ── Table factory ─────────────────────────────────────────────────────────────

QTableWidget* CveFeedPage::makeTable(bool withService) {
    auto* t = new QTableWidget(0, withService ? 8 : 7);
    QStringList hdrs;
    hdrs << "Severity" << "CVE ID" << "CVSS" << "EPSS%" << "KEV"
         << "Published" << "Description";
    if (withService) hdrs.insert(6, "Service");
    t->setHorizontalHeaderLabels(hdrs);
    t->setEditTriggers(QAbstractItemView::NoEditTriggers);
    t->setSelectionBehavior(QAbstractItemView::SelectRows);
    t->setSelectionMode(QAbstractItemView::SingleSelection);
    t->setShowGrid(false);
    t->verticalHeader()->hide();
    t->setAlternatingRowColors(false);
    t->horizontalHeader()->setStretchLastSection(true);
    t->horizontalHeader()->setSectionResizeMode(QHeaderView::Interactive);
    t->setColumnWidth(0, 80);
    t->setColumnWidth(1, 130);
    t->setColumnWidth(2, 58);
    t->setColumnWidth(3, 60);
    t->setColumnWidth(4, 48);
    t->setColumnWidth(5, 90);
    if (withService) t->setColumnWidth(6, 120);
    t->setStyleSheet(R"(
        QTableWidget {
            background: #0a0d1a;
            border: 1px solid #1e2a3a;
            border-radius: 6px;
            color: #e2e8f0;
            font-family: "JetBrains Mono";
            font-size: 12px;
            gridline-color: #1e2a3a;
        }
        QTableWidget::item {
            padding: 4px 8px;
            border-bottom: 1px solid #111827;
        }
        QTableWidget::item:selected {
            background: rgba(180,74,255,0.15);
            color: #e2e8f0;
        }
        QHeaderView::section {
            background: #0d111f;
            color: #64748b;
            font-family: "JetBrains Mono";
            font-size: 11px;
            letter-spacing: 1px;
            padding: 6px 8px;
            border: none;
            border-bottom: 1px solid #1e2a3a;
        }
    )");
    return t;
}

void CveFeedPage::populateTable(QTableWidget* table, const QJsonArray& cves,
                                 bool withService) {
    table->setRowCount(0);
    for (const QJsonValue& v : cves) {
        QJsonObject cve = v.toObject();
        int row = table->rowCount();
        table->insertRow(row);

        QString sev   = cve["severity"].toString("UNKNOWN").toUpper();
        QString id    = cve["cve_id"].toString();
        double  score = cve["score"].toDouble();
        double  epss  = cve["epss_score"].toDouble();
        bool    kev   = cve["kev_exploited"].toBool();
        QString pub   = cve["published"].toString();
        QString desc  = cve["description"].toString();
        QString svc   = cve["service"].toString();

        QString bgCol  = severityColor(sev);
        QString fgCol  = severityFg(sev);

        // Col 0 — Severity badge
        auto* sevItem = new QTableWidgetItem(sev);
        sevItem->setTextAlignment(Qt::AlignCenter);
        sevItem->setBackground(QColor(bgCol));
        sevItem->setForeground(QColor(fgCol));
        QFont badgeFont;
        badgeFont.setBold(true);
        badgeFont.setPointSize(9);
        sevItem->setFont(badgeFont);
        table->setItem(row, 0, sevItem);

        // Col 1 — CVE ID
        auto* idItem = new QTableWidgetItem(id);
        idItem->setForeground(QColor("#00d4ff"));
        table->setItem(row, 1, idItem);

        // Col 2 — CVSS score
        QString scoreStr = score > 0 ? QString::number(score, 'f', 1) : "N/A";
        auto* scoreItem = new QTableWidgetItem(scoreStr);
        scoreItem->setTextAlignment(Qt::AlignCenter);
        scoreItem->setForeground(QColor(bgCol));
        QFont scoreFont;
        scoreFont.setBold(true);
        scoreItem->setFont(scoreFont);
        table->setItem(row, 2, scoreItem);

        // Col 3 — EPSS%
        QString epssStr = epss > 0 ? QString::number(epss * 100.0, 'f', 1) + "%" : "—";
        auto* epssItem = new QTableWidgetItem(epssStr);
        epssItem->setTextAlignment(Qt::AlignCenter);
        if (epss >= 0.5) epssItem->setForeground(QColor("#f43f5e"));
        else if (epss >= 0.1) epssItem->setForeground(QColor("#ffb84d"));
        else epssItem->setForeground(QColor("#64748b"));
        table->setItem(row, 3, epssItem);

        // Col 4 — KEV
        auto* kevItem = new QTableWidgetItem(kev ? "⚠ KEV" : "");
        kevItem->setTextAlignment(Qt::AlignCenter);
        if (kev) kevItem->setForeground(QColor("#ffb84d"));
        table->setItem(row, 4, kevItem);

        // Col 5 — Published
        table->setItem(row, 5, new QTableWidgetItem(pub));

        int descCol = 6;
        if (withService) {
            // Col 6 — Service
            auto* svcItem = new QTableWidgetItem(svc);
            svcItem->setForeground(QColor("#94a3b8"));
            table->setItem(row, 6, svcItem);
            descCol = 7;
        }

        // Description (last col)
        QString shortDesc = desc.length() > 100 ? desc.left(97) + "..." : desc;
        auto* descItem = new QTableWidgetItem(shortDesc);
        descItem->setForeground(QColor("#94a3b8"));
        descItem->setData(Qt::UserRole, QVariant::fromValue(cve));
        table->setItem(row, descCol, descItem);

        table->setRowHeight(row, 28);
    }
}

void CveFeedPage::showDetail(QTextEdit* detail, const QJsonObject& cve) {
    QString sev   = cve["severity"].toString("UNKNOWN").toUpper();
    QString id    = cve["cve_id"].toString();
    double  score = cve["score"].toDouble();
    double  epss  = cve["epss_score"].toDouble();
    bool    kev   = cve["kev_exploited"].toBool();
    QString pub   = cve["published"].toString();
    QString desc  = cve["description"].toString();
    QString svc   = cve["service"].toString();
    QString col   = severityColor(sev);
    QJsonArray refs = cve["references"].toArray();

    QString html = QString(
        "<div style='font-family:\"JetBrains Mono\",monospace;font-size:12px;color:#e2e8f0;'>"
        "<span style='background:%1;color:%2;padding:2px 6px;border-radius:3px;font-weight:bold;'>%3</span>"
        "&nbsp;&nbsp;<span style='color:#00d4ff;font-weight:bold;'>%4</span>"
        "&nbsp;&nbsp;<span style='color:%1;font-weight:bold;'>CVSS %5</span>"
    ).arg(col, severityFg(sev), sev, id, QString::number(score, 'f', 1));

    if (epss > 0)
        html += QString("&nbsp;&nbsp;<span style='color:#94a3b8;'>EPSS %1%</span>").arg(epss * 100, 0, 'f', 1);
    if (kev) {
        QString due = cve["kev_due_date"].toString();
        html += QString("&nbsp;&nbsp;<span style='color:#ffb84d;'>⚠ CISA KEV");
        if (!due.isEmpty()) html += " (due " + due + ")";
        html += "</span>";
    }
    if (!svc.isEmpty())
        html += QString("<br><span style='color:#64748b;'>Matched service: %1</span>").arg(svc);

    html += QString("<br><br><span style='color:#cbd5e1;'>%1</span>").arg(desc.toHtmlEscaped());

    if (!refs.isEmpty()) {
        html += "<br><br><span style='color:#475569;font-size:11px;'>References:</span><br>";
        for (const QJsonValue& r : refs) {
            QString url = r.toString();
            if (!url.isEmpty())
                html += QString("<span style='color:#475569;font-size:11px;'>• %1</span><br>").arg(url.toHtmlEscaped());
        }
    }
    html += "</div>";
    detail->setHtml(html);
}

// ── Tab builders ──────────────────────────────────────────────────────────────

QWidget* CveFeedPage::buildRecentTab() {
    auto* w   = new QWidget;
    auto* lay = new QVBoxLayout(w);
    lay->setContentsMargins(16, 12, 16, 12);
    lay->setSpacing(8);

    // Controls row
    auto* bar = new QHBoxLayout;
    bar->setSpacing(8);
    auto* dayLbl = new QLabel("Last");
    dayLbl->setStyleSheet("color: #64748b; font-family: 'JetBrains Mono'; font-size: 12px;");
    m_daysBox = new QSpinBox;
    m_daysBox->setRange(1, 90);
    m_daysBox->setValue(7);
    m_daysBox->setSuffix(" days");
    m_daysBox->setStyleSheet(R"(
        QSpinBox { background: #111827; border: 1px solid #1e2a3a; border-radius: 4px;
                   color: #e2e8f0; padding: 4px 8px; font-family: 'JetBrains Mono'; font-size: 12px; }
        QSpinBox::up-button, QSpinBox::down-button { width: 16px; background: #1e2a3a; }
    )");
    m_fetchBtn = new QPushButton("FETCH RECENT");
    m_fetchBtn->setStyleSheet(R"(
        QPushButton { background: rgba(0,212,255,0.12); border: 1px solid #00d4ff;
                      border-radius: 4px; color: #00d4ff; font-family: 'JetBrains Mono';
                      font-size: 12px; letter-spacing: 1px; padding: 6px 16px; }
        QPushButton:hover { background: rgba(0,212,255,0.2); }
        QPushButton:disabled { color: #334155; border-color: #334155; background: transparent; }
    )");
    m_recentStatusLbl = new QLabel("Ready");
    m_recentStatusLbl->setStyleSheet("color: #334155; font-family: 'JetBrains Mono'; font-size: 11px;");
    bar->addWidget(dayLbl);
    bar->addWidget(m_daysBox);
    bar->addWidget(m_fetchBtn);
    bar->addWidget(m_recentStatusLbl);
    bar->addStretch();
    lay->addLayout(bar);

    // Splitter: table | detail
    auto* splitter = new QSplitter(Qt::Vertical);
    splitter->setStyleSheet("QSplitter::handle { background: #1e2a3a; height: 2px; }");

    m_recentTable = makeTable(false);
    connect(m_recentTable, &QTableWidget::cellClicked, this, &CveFeedPage::onRecentRowClicked);
    splitter->addWidget(m_recentTable);

    m_recentDetail = new QTextEdit;
    m_recentDetail->setReadOnly(true);
    m_recentDetail->setMaximumHeight(140);
    m_recentDetail->setStyleSheet(
        "QTextEdit { background: #080c1a; border: 1px solid #1e2a3a; border-radius: 4px; "
        "            padding: 8px; color: #94a3b8; font-size: 11px; }");
    m_recentDetail->setPlaceholderText("Click a row to see details…");
    splitter->addWidget(m_recentDetail);
    splitter->setStretchFactor(0, 3);
    splitter->setStretchFactor(1, 1);
    lay->addWidget(splitter);

    connect(m_fetchBtn, &QPushButton::clicked, this, &CveFeedPage::fetchRecent);
    return w;
}

QWidget* CveFeedPage::buildScanTab() {
    auto* w   = new QWidget;
    auto* lay = new QVBoxLayout(w);
    lay->setContentsMargins(16, 12, 16, 12);
    lay->setSpacing(8);

    // Input row
    auto* inputRow = new QHBoxLayout;
    inputRow->setSpacing(8);
    auto* tgtLbl = new QLabel("Target:");
    tgtLbl->setStyleSheet("color: #64748b; font-family: 'JetBrains Mono'; font-size: 12px;");
    m_targetInput = new QLineEdit;
    m_targetInput->setPlaceholderText("192.168.1.1  or  hostname");
    m_targetInput->setMaximumWidth(220);
    m_targetInput->setStyleSheet(
        "QLineEdit { background: #111827; border: 1px solid #1e2a3a; border-radius: 4px; "
        "            color: #e2e8f0; padding: 6px 10px; font-family: 'JetBrains Mono'; font-size: 12px; }"
        "QLineEdit:focus { border-color: #b44aff; }");
    m_scanBtn = new QPushButton("SCAN TARGET");
    m_scanBtn->setStyleSheet(R"(
        QPushButton { background: rgba(180,74,255,0.12); border: 1px solid #b44aff;
                      border-radius: 4px; color: #b44aff; font-family: 'JetBrains Mono';
                      font-size: 12px; letter-spacing: 1px; padding: 6px 16px; }
        QPushButton:hover { background: rgba(180,74,255,0.22); }
        QPushButton:disabled { color: #334155; border-color: #334155; background: transparent; }
    )");
    inputRow->addWidget(tgtLbl);
    inputRow->addWidget(m_targetInput);
    inputRow->addWidget(m_scanBtn);
    inputRow->addStretch();
    lay->addLayout(inputRow);

    // Services input
    auto* svcLbl = new QLabel("Services (one per line — e.g. \"apache 2.4.51\", \"openssh 8.2p1\"):");
    svcLbl->setStyleSheet("color: #475569; font-family: 'JetBrains Mono'; font-size: 11px;");
    lay->addWidget(svcLbl);
    m_servicesEdit = new QTextEdit;
    m_servicesEdit->setFixedHeight(70);
    m_servicesEdit->setPlaceholderText("apache 2.4.51\nopenssh 8.2p1\nnginx 1.18.0");
    m_servicesEdit->setStyleSheet(
        "QTextEdit { background: #111827; border: 1px solid #1e2a3a; border-radius: 4px; "
        "            color: #e2e8f0; padding: 6px 10px; font-family: 'JetBrains Mono'; font-size: 12px; }"
        "QTextEdit:focus { border-color: #b44aff; }");
    lay->addWidget(m_servicesEdit);

    // Terminal (streaming output)
    m_terminal = new TacticalTerminal;
    m_terminal->setFixedHeight(120);
    lay->addWidget(m_terminal);

    // Splitter: results table | detail
    auto* splitter = new QSplitter(Qt::Vertical);
    splitter->setStyleSheet("QSplitter::handle { background: #1e2a3a; height: 2px; }");

    m_scanTable = makeTable(true);
    connect(m_scanTable, &QTableWidget::cellClicked, this, &CveFeedPage::onScanRowClicked);
    splitter->addWidget(m_scanTable);

    m_scanDetail = new QTextEdit;
    m_scanDetail->setReadOnly(true);
    m_scanDetail->setMaximumHeight(130);
    m_scanDetail->setStyleSheet(
        "QTextEdit { background: #080c1a; border: 1px solid #1e2a3a; border-radius: 4px; "
        "            padding: 8px; color: #94a3b8; font-size: 11px; }");
    m_scanDetail->setPlaceholderText("Click a CVE row to see details…");
    splitter->addWidget(m_scanDetail);
    splitter->setStretchFactor(0, 3);
    splitter->setStretchFactor(1, 1);
    lay->addWidget(splitter);

    connect(m_scanBtn, &QPushButton::clicked, this, &CveFeedPage::startScan);
    return w;
}

QWidget* CveFeedPage::buildSearchTab() {
    auto* w   = new QWidget;
    auto* lay = new QVBoxLayout(w);
    lay->setContentsMargins(16, 12, 16, 12);
    lay->setSpacing(8);

    // Search bar
    auto* bar = new QHBoxLayout;
    bar->setSpacing(8);
    m_searchInput = new QLineEdit;
    m_searchInput->setPlaceholderText("keyword — e.g. \"log4j\", \"openssl\", \"apache\"");
    m_searchInput->setStyleSheet(
        "QLineEdit { background: #111827; border: 1px solid #1e2a3a; border-radius: 4px; "
        "            color: #e2e8f0; padding: 6px 10px; font-family: 'JetBrains Mono'; font-size: 12px; }"
        "QLineEdit:focus { border-color: #00d4ff; }");
    m_searchBtn = new QPushButton("SEARCH NVD");
    m_searchBtn->setStyleSheet(R"(
        QPushButton { background: rgba(0,212,255,0.12); border: 1px solid #00d4ff;
                      border-radius: 4px; color: #00d4ff; font-family: 'JetBrains Mono';
                      font-size: 12px; letter-spacing: 1px; padding: 6px 16px; }
        QPushButton:hover { background: rgba(0,212,255,0.2); }
        QPushButton:disabled { color: #334155; border-color: #334155; background: transparent; }
    )");
    m_searchStatusLbl = new QLabel;
    m_searchStatusLbl->setStyleSheet("color: #334155; font-family: 'JetBrains Mono'; font-size: 11px;");
    bar->addWidget(m_searchInput);
    bar->addWidget(m_searchBtn);
    bar->addWidget(m_searchStatusLbl);
    bar->addStretch();
    lay->addLayout(bar);

    // Splitter
    auto* splitter = new QSplitter(Qt::Vertical);
    splitter->setStyleSheet("QSplitter::handle { background: #1e2a3a; height: 2px; }");

    m_searchTable = makeTable(false);
    connect(m_searchTable, &QTableWidget::cellClicked, this, &CveFeedPage::onSearchRowClicked);
    splitter->addWidget(m_searchTable);

    m_searchDetail = new QTextEdit;
    m_searchDetail->setReadOnly(true);
    m_searchDetail->setMaximumHeight(140);
    m_searchDetail->setStyleSheet(
        "QTextEdit { background: #080c1a; border: 1px solid #1e2a3a; border-radius: 4px; "
        "            padding: 8px; color: #94a3b8; font-size: 11px; }");
    m_searchDetail->setPlaceholderText("Click a row to see details…");
    splitter->addWidget(m_searchDetail);
    splitter->setStretchFactor(0, 3);
    splitter->setStretchFactor(1, 1);
    lay->addWidget(splitter);

    connect(m_searchBtn, &QPushButton::clicked, this, &CveFeedPage::doSearch);
    connect(m_searchInput, &QLineEdit::returnPressed, this, &CveFeedPage::doSearch);
    return w;
}

// ── Main UI ───────────────────────────────────────────────────────────────────

void CveFeedPage::buildUi() {
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
        "<span style='color:#b44aff;font-weight:900;letter-spacing:3px;font-size:13px;'>CVE</span>"
        "<span style='color:#e2e8f0;font-weight:300;letter-spacing:2px;font-size:13px;'> THREAT FEED</span>"
    );
    titleLbl->setTextFormat(Qt::RichText);
    auto* subLbl = new QLabel("NIST NVD v2.0  •  EPSS  •  CISA KEV");
    subLbl->setStyleSheet("color: #334155; font-family: 'JetBrains Mono'; font-size: 11px;");
    hLay->addWidget(titleLbl);
    hLay->addStretch();
    hLay->addWidget(subLbl);
    lay->addWidget(header);

    // Tabs
    m_tabs = new QTabWidget;
    m_tabs->setStyleSheet(R"(
        QTabWidget::pane {
            background: #0d0f1a;
            border: none;
        }
        QTabBar::tab {
            background: #080c1a;
            color: #475569;
            font-family: 'JetBrains Mono';
            font-size: 11px;
            letter-spacing: 1px;
            padding: 8px 20px;
            border: none;
            border-bottom: 2px solid transparent;
        }
        QTabBar::tab:selected {
            color: #b44aff;
            border-bottom: 2px solid #b44aff;
        }
        QTabBar::tab:hover:!selected {
            color: #94a3b8;
            background: rgba(255,255,255,0.03);
        }
    )");
    m_tabs->addTab(buildRecentTab(), "RECENT CVEs");
    m_tabs->addTab(buildScanTab(),   "TARGET SCAN");
    m_tabs->addTab(buildSearchTab(), "SEARCH NVD");
    lay->addWidget(m_tabs);
}

// ── Constructor ───────────────────────────────────────────────────────────────

CveFeedPage::CveFeedPage(IpcClient* ipc, QWidget* parent)
    : QWidget(parent), m_ipc(ipc)
{
    buildUi();
    connect(m_ipc, &IpcClient::resultReady, this, &CveFeedPage::onIpcResult);
}

// ── Slots ─────────────────────────────────────────────────────────────────────

void CveFeedPage::fetchRecent() {
    if (!m_ipc->isConnected()) {
        m_recentStatusLbl->setText("Daemon offline");
        return;
    }
    m_fetchBtn->setEnabled(false);
    m_recentStatusLbl->setText("Fetching…");
    m_recentReqId = m_ipc->call("cve_feed_recent", {{"days", m_daysBox->value()}});
}

void CveFeedPage::startScan() {
    if (m_scanning) return;
    QString target = m_targetInput->text().trimmed();
    if (target.isEmpty()) {
        m_terminal->log("Target is required.", "ERROR");
        return;
    }
    QStringList svcList = m_servicesEdit->toPlainText().split('\n', Qt::SkipEmptyParts);
    if (svcList.isEmpty()) {
        m_terminal->log("Enter at least one service (e.g. apache 2.4.51).", "ERROR");
        return;
    }
    if (!m_ipc->isConnected()) {
        m_terminal->log("Daemon offline — cannot scan.", "ERROR");
        return;
    }

    m_scanning = true;
    m_scanBtn->setEnabled(false);
    m_scanTable->setRowCount(0);
    m_terminal->clear();
    m_terminal->log(QString("Starting CVE scan for %1 (%2 services)…").arg(target).arg(svcList.size()));

    QJsonArray services;
    for (const QString& s : svcList) services.append(s);
    m_scanReqId = m_ipc->call("cve_feed_scan", {{"target", target}, {"services", services}});
}

void CveFeedPage::doSearch() {
    QString kw = m_searchInput->text().trimmed();
    if (kw.isEmpty()) return;
    if (!m_ipc->isConnected()) {
        m_searchStatusLbl->setText("Daemon offline");
        return;
    }
    m_searchBtn->setEnabled(false);
    m_searchStatusLbl->setText("Querying NVD…");
    m_searchReqId = m_ipc->call("cve_feed_search", {{"keyword", kw}});
}

void CveFeedPage::onIpcResult(int id, QJsonObject result) {
    if (id == m_recentReqId) {
        m_recentReqId = -1;
        m_fetchBtn->setEnabled(true);
        if (result.contains("error") && result["cves"].toArray().isEmpty()) {
            m_recentStatusLbl->setText("Error: " + result["error"].toString());
            return;
        }
        QJsonArray cves = result["cves"].toArray();
        populateTable(m_recentTable, cves, false);
        m_recentStatusLbl->setText(QString("%1 CVEs").arg(cves.size()));

    } else if (id == m_searchReqId) {
        m_searchReqId = -1;
        m_searchBtn->setEnabled(true);
        if (result.contains("error") && result["cves"].toArray().isEmpty()) {
            m_searchStatusLbl->setText("Error: " + result["error"].toString());
            return;
        }
        QJsonArray cves = result["cves"].toArray();
        populateTable(m_searchTable, cves, false);
        m_searchStatusLbl->setText(QString("%1 results").arg(cves.size()));

    } else if (id == m_scanReqId) {
        QString output = result["output"].toString();
        if (!output.isEmpty())
            m_terminal->log(output, result["level"].toString("INFO"));

        if (result["complete"].toBool()) {
            m_scanning  = false;
            m_scanReqId = -1;
            m_scanBtn->setEnabled(true);
            if (result.contains("cves")) {
                QJsonArray cves = result["cves"].toArray();
                populateTable(m_scanTable, cves, true);
                m_terminal->log(QString("Results: %1 CVE(s) matched.").arg(cves.size()), "SUCCESS");
            }
        }
    }
}

void CveFeedPage::onRecentRowClicked(int row) {
    int lastCol = m_recentTable->columnCount() - 1;
    auto* item = m_recentTable->item(row, lastCol);
    if (!item) return;
    showDetail(m_recentDetail, item->data(Qt::UserRole).toJsonObject());
}

void CveFeedPage::onScanRowClicked(int row) {
    int lastCol = m_scanTable->columnCount() - 1;
    auto* item = m_scanTable->item(row, lastCol);
    if (!item) return;
    showDetail(m_scanDetail, item->data(Qt::UserRole).toJsonObject());
}

void CveFeedPage::onSearchRowClicked(int row) {
    int lastCol = m_searchTable->columnCount() - 1;
    auto* item = m_searchTable->item(row, lastCol);
    if (!item) return;
    showDetail(m_searchDetail, item->data(Qt::UserRole).toJsonObject());
}
