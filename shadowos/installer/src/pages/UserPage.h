#pragma once
#include <QWidget>
#include <QLineEdit>
#include "../InstallState.h"

class UserPage : public QWidget {
    Q_OBJECT
public:
    explicit UserPage(InstallState* state, QWidget* parent = nullptr);
    bool validate();
    void save();

private:
    InstallState* m_state;
    QLineEdit*    m_username;
    QLineEdit*    m_password;
    QLineEdit*    m_password2;
    QLineEdit*    m_hostname;
};
