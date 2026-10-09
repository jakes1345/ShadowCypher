#pragma once
#include <QDialog>
#include <QLineEdit>
#include <QPushButton>
#include <QLabel>
#include <QStackedWidget>
#include "api/ApiClient.h"

class LoginDialog : public QDialog {
    Q_OBJECT
public:
    explicit LoginDialog(ApiClient* api, QWidget* parent = nullptr);

private slots:
    void onLoginClicked();
    void toggleKeyMode();

private:
    ApiClient* m_api;
    bool m_keyMode = false;

    QStackedWidget* m_formStack;
    QLineEdit* m_handleEdit;
    QLineEdit* m_passwordEdit;
    QLineEdit* m_keyEdit;
    QPushButton* m_loginBtn;
    QLabel* m_errorLabel;
    QLabel* m_toggleLink;
    QLabel* m_spinner;

    void buildUi();
    void setLoading(bool loading);
    void showError(const QString& msg);
    QString buttonStyle() const;
    QString inputStyle() const;
};
