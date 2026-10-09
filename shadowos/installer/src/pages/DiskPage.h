#pragma once
#include <QWidget>
#include <QButtonGroup>
#include <QVBoxLayout>
#include "../InstallState.h"
#include "../DiskUtil.h"

class DiskPage : public QWidget {
    Q_OBJECT
public:
    explicit DiskPage(InstallState* state, QWidget* parent = nullptr);
    bool validate();
    void refresh();

private:
    InstallState*  m_state;
    QButtonGroup*  m_group;
    QVBoxLayout*   m_diskList;
};
