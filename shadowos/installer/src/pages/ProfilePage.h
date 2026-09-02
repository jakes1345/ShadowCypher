#pragma once
#include <QWidget>
#include <QButtonGroup>
#include "../InstallState.h"

class ProfilePage : public QWidget {
    Q_OBJECT
public:
    explicit ProfilePage(InstallState* state, QWidget* parent = nullptr);
    bool validate();
    void save();

private:
    InstallState* m_state;
    QButtonGroup* m_group;
};
