#pragma once
#include <QWidget>
#include <QLineEdit>
#include <QCheckBox>
#include "../InstallState.h"

class EncryptPage : public QWidget {
    Q_OBJECT
public:
    explicit EncryptPage(InstallState* state, QWidget* parent = nullptr);
    bool validate();
    void save();

private:
    InstallState* m_state;
    QCheckBox*    m_enableBox;
    QLineEdit*    m_pass1;
    QLineEdit*    m_pass2;
    QWidget*      m_fields;
};
