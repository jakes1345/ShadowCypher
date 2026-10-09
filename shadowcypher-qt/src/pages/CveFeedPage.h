#pragma once
#include <QWidget>
#include <QTabWidget>
#include <QTableWidget>
#include <QLineEdit>
#include <QTextEdit>
#include <QPushButton>
#include <QLabel>
#include <QSpinBox>
#include <QJsonArray>
#include <QJsonObject>
#include "../ipc/IpcClient.h"
#include "../widgets/TacticalTerminal.h"

class CveFeedPage : public QWidget {
    Q_OBJECT
public:
    explicit CveFeedPage(IpcClient* ipc, QWidget* parent = nullptr);

private slots:
    void fetchRecent();
    void startScan();
    void doSearch();
    void onIpcResult(int id, QJsonObject result);
    void onRecentRowClicked(int row);
    void onScanRowClicked(int row);
    void onSearchRowClicked(int row);

private:
    IpcClient*  m_ipc;
    QTabWidget* m_tabs;

    // ── Recent tab ───────────────────────────────────────
    QSpinBox*     m_daysBox;
    QPushButton*  m_fetchBtn;
    QLabel*       m_recentStatusLbl;
    QTableWidget* m_recentTable;
    QTextEdit*    m_recentDetail;

    // ── Scan tab ──────────────────────────────────────────
    QLineEdit*        m_targetInput;
    QTextEdit*        m_servicesEdit;
    QPushButton*      m_scanBtn;
    TacticalTerminal* m_terminal;
    QTableWidget*     m_scanTable;
    QTextEdit*        m_scanDetail;

    // ── Search tab ────────────────────────────────────────
    QLineEdit*    m_searchInput;
    QPushButton*  m_searchBtn;
    QLabel*       m_searchStatusLbl;
    QTableWidget* m_searchTable;
    QTextEdit*    m_searchDetail;

    int  m_recentReqId = -1;
    int  m_searchReqId = -1;
    int  m_scanReqId   = -1;
    bool m_scanning    = false;

    void buildUi();
    QWidget* buildRecentTab();
    QWidget* buildScanTab();
    QWidget* buildSearchTab();

    QTableWidget* makeTable(bool withService);
    void populateTable(QTableWidget* table, const QJsonArray& cves, bool withService);
    void showDetail(QTextEdit* detail, const QJsonObject& cve);

    static QString severityColor(const QString& sev);
    static QString severityFg(const QString& sev);
};
