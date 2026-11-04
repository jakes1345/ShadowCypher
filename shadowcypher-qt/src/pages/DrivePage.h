#pragma once
#include <QWidget>
#include <QTableWidget>
#include <QPushButton>
#include <QLabel>
#include <QJsonArray>

class DrivePage : public QWidget {
    Q_OBJECT
public:
    explicit DrivePage(QWidget* parent = nullptr);

protected:
    void showEvent(QShowEvent* e) override;

private slots:
    void refresh();
    void uploadFiles();
    void downloadSelected();
    void deleteSelected();

private:
    QTableWidget* m_table;
    QPushButton*  m_downloadBtn;
    QPushButton*  m_deleteBtn;
    QLabel*       m_status;
    QLabel*       m_usage;
    bool          m_loadedOnce = false;

    void buildUi();
    void populate(const QJsonArray& files);
    void setStatus(const QString& msg, bool error = false);
    QString selectedKey() const;
    QString selectedName() const;
    void updateButtons();
    static QString humanSize(qint64 bytes);
    static QString mimeFor(const QString& fileName);
};
