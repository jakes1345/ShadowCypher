#pragma once
#include <QString>

struct InstallState {
    QString locale   = "en_US.UTF-8";
    QString timezone = "UTC";
    QString disk;
    bool    luks     = true;
    QString luksPass;
    QString username = "shadow";
    QString password;
    QString hostname = "shadowos";
    QString profile  = "standard";  // standard | pentest | privacy | gaming
};
