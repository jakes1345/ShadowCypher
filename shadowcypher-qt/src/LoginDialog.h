#pragma once
#include <QDialog>
#include <QLineEdit>
#include <QPushButton>
#include <QLabel>
#include <QStackedWidget>
#include <QTimer>
#include <QDeadlineTimer>
#include "api/ApiClient.h"

// Sign-in: the browser (device authorization) by default, or a pasted API key.
// The account password is never typed into the desktop app.
class LoginDialog : public QDialog {
    Q_OBJECT
public:
    explicit LoginDialog(ApiClient* api, QWidget* parent = nullptr);

private slots:
    void startBrowserSignIn();
    void cancelBrowserSignIn();
    void openVerifyPage();
    void poll();
    void submitKey();
    void toggleKeyMode();

private:
    enum Page { Start = 0, Waiting = 1, Key = 2 };

    ApiClient* m_api;

    QStackedWidget* m_stack;
    QPushButton* m_browserBtn;
    QLabel*      m_codeLabel;
    QLabel*      m_waitLabel;
    QPushButton* m_openBtn;
    QLineEdit*   m_keyEdit;
    QPushButton* m_keyBtn;
    QLabel*      m_errorLabel;
    QLabel*      m_toggleLink;

    QString        m_deviceCode;
    QString        m_verifyUrl;
    QTimer         m_pollTimer;
    QDeadlineTimer m_deadline;

    void buildUi();
    void showPage(Page p);
    void finishWithKey(const QString& key);
    void stopPolling(const QString& error = {});
    void showError(const QString& msg);
    QString buttonStyle(bool primary = true) const;
    QString inputStyle() const;
};
