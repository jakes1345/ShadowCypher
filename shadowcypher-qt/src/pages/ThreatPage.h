#pragma once
#include <QWidget>
#include <QTimer>
#include <QTableWidget>
#include <QLabel>
#include <QLineEdit>
#include <QPushButton>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QComboBox>
#include <QProcess>
#include "../ipc/IpcClient.h"
#include "../widgets/TacticalTerminal.h"

class ThreatPage : public QWidget {
    Q_OBJECT
public:
    explicit ThreatPage(IpcClient* ipc, QWidget* parent = nullptr);

private slots:
    void fetchCves();
    void onCveReply(QNetworkReply* reply);
    void runLocalCheck();
    void onLocalCheckOutput();
    void onLocalCheckFinished(int code, QProcess::ExitStatus);

private:
    void buildUi();
    void populateCveTable(const QJsonArray& items);
    QString cvssColor(double score);

    IpcClient*              m_ipc;
    QNetworkAccessManager*  m_nam;
    QTimer*                 m_autoRefresh;

    QLineEdit*      m_keywordEdit;
    QComboBox*      m_severityCombo;
    QPushButton*    m_fetchBtn;
    QPushButton*    m_localBtn;
    QLabel*         m_lastUpdated;

    QTableWidget*   m_cveTable;
    TacticalTerminal* m_output;

    QProcess*       m_localProc{nullptr};
};
