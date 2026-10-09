#pragma once
#include <QWidget>
#include <QTabWidget>
#include <QLineEdit>
#include <QPushButton>
#include <QPlainTextEdit>
#include <QProcess>
#include <QComboBox>
#include "../widgets/TacticalTerminal.h"

class SmartContractPage : public QWidget {
    Q_OBJECT
public:
    explicit SmartContractPage(QWidget* parent = nullptr);
    ~SmartContractPage() override;

private slots:
    void browseFile();
    void scanFile();
    void scanPaste();
    void stopScan();
    void onOutput();
    void onScanFinished(int code, QProcess::ExitStatus status);

private:
    void buildUi();
    void startScan(const QString& filePath, TacticalTerminal* out);
    void renderFindings(const QByteArray& jsonData, TacticalTerminal* out);

    QTabWidget*       m_tabs;

    // File scan tab
    QLineEdit*        m_filePath;
    QComboBox*        m_minSeverity;
    TacticalTerminal* m_fileOut;

    // Paste source tab
    QPlainTextEdit*   m_pasteEdit;
    TacticalTerminal* m_pasteOut;

    QPushButton*      m_stopBtn;

    QProcess*         m_proc{nullptr};
    TacticalTerminal* m_activeOut{nullptr};
    QByteArray        m_jsonBuf;
    QString           m_tempFile;
};
