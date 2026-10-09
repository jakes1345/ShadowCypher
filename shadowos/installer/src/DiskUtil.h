#pragma once
#include <QString>
#include <QVector>

struct DiskInfo {
    QString path;     // /dev/sda
    QString size;     // 500G
    QString model;    // Samsung SSD 870
    QString transport;// sata, nvme, usb
    bool    isNvme;
};

namespace DiskUtil {
    QVector<DiskInfo> listDisks();
    bool              isOnline();
}
