#pragma once
#include <QMainWindow>
#include <QStackedWidget>
#include <QPushButton>
#include <QListWidget>
#include "InstallState.h"
#include "pages/WelcomePage.h"
#include "pages/DiskPage.h"
#include "pages/EncryptPage.h"
#include "pages/UserPage.h"
#include "pages/ProfilePage.h"
#include "pages/SummaryPage.h"
#include "pages/InstallPage.h"
#include "pages/FinishPage.h"

class Installer : public QMainWindow {
    Q_OBJECT
public:
    explicit Installer(QWidget* parent = nullptr);

private slots:
    void next();
    void back();
    void onInstallFinished(bool success);

private:
    void    goTo(int index);
    bool    validateCurrent();
    void    saveCurrent();
    QWidget* buildSidebar();

    InstallState   m_state;
    QStackedWidget* m_stack;
    QPushButton*    m_btnBack;
    QPushButton*    m_btnNext;
    QListWidget*    m_steps;

    WelcomePage*  m_welcome;
    DiskPage*     m_disk;
    EncryptPage*  m_encrypt;
    UserPage*     m_user;
    ProfilePage*  m_profile;
    SummaryPage*  m_summary;
    InstallPage*  m_install;
    FinishPage*   m_finish  = nullptr;

    int m_current = 0;
    static constexpr int PAGE_INSTALL = 6;
};
