#pragma once
#include <QWidget>
#include <QLabel>
#include "../InstallState.h"

class SummaryPage : public QWidget {
    Q_OBJECT
public:
    explicit SummaryPage(InstallState* state, QWidget* parent = nullptr);
    void refresh();

private:
    InstallState* m_state;
    QLabel*       m_disk;
    QLabel*       m_luks;
    QLabel*       m_user;
    QLabel*       m_host;
    QLabel*       m_profile;
    QLabel*       m_locale;
    QLabel*       m_tz;
};
