#include "DiskUtil.h"
#include <QProcess>
#include <QStringList>

QVector<DiskInfo> DiskUtil::listDisks() {
    QVector<DiskInfo> result;
    QProcess p;
    p.start("lsblk", {"-dpno", "NAME,SIZE,MODEL,TRAN"});
    p.waitForFinished(5000);

    const QString out = p.readAllStandardOutput();
    for (const QString& line : out.split('\n', Qt::SkipEmptyParts)) {
        QStringList parts = line.split(QRegularExpression("\\s{2,}"), Qt::SkipEmptyParts);
        if (parts.isEmpty()) continue;
        QString name = parts[0].trimmed();
        if (name.contains("loop") || name.contains("rom")) continue;
        DiskInfo d;
        d.path      = name;
        d.size      = parts.size() > 1 ? parts[1].trimmed() : "?";
        d.model     = parts.size() > 2 ? parts[2].trimmed() : "";
        d.transport = parts.size() > 3 ? parts[3].trimmed() : "";
        d.isNvme    = name.contains("nvme");
        result.append(d);
    }
    return result;
}

bool DiskUtil::isOnline() {
    QProcess p;
    p.start("curl", {"-sf", "--max-time", "5", "https://archlinux.org"});
    p.waitForFinished(8000);
    return p.exitCode() == 0;
}
