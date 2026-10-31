#include <QCoreApplication>
#include "Daemon.h"

int main(int argc, char* argv[]) {
    QCoreApplication app(argc, argv);
    app.setOrganizationName(QStringLiteral("shadowcypher"));
    app.setApplicationName(QStringLiteral("shadowcypher-daemon"));

    Daemon daemon;
    if (!daemon.start())
        return 1;

    return app.exec();
}
