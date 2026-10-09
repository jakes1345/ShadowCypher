#include <QApplication>
#include <QProcess>
#include <QMessageBox>
#include <cstdlib>
#include <unistd.h>
#include "Installer.h"
#include "theme.h"

int main(int argc, char* argv[]) {
    // Re-exec with pkexec if not root
    if (geteuid() != 0) {
        const QString self = QApplication::applicationFilePath();
        // Construct absolute path from argv[0] if needed
        char path[4096] = {};
        ssize_t len = readlink("/proc/self/exe", path, sizeof(path) - 1);
        const QString exe = len > 0 ? QString::fromUtf8(path, len) : QString::fromUtf8(argv[0]);

        QApplication tmpApp(argc, argv);
        QMessageBox::critical(nullptr, "ShadowOS Installer",
            "This installer must be run as root.\n\n"
            "Re-launch with:\n  sudo shadowos-installer\nor use pkexec.");
        return 1;
    }

    QApplication app(argc, argv);
    app.setApplicationName("ShadowOS Installer");
    app.setApplicationVersion("1.0.0");
    app.setOrganizationName("ShadowCypher");

    // Apply global font priority (JetBrains Mono is available on the live ISO)
    QFont defaultFont("Outfit");
    defaultFont.setStyleHint(QFont::SansSerif);
    defaultFont.setPixelSize(13);
    app.setFont(defaultFont);

    Installer win;
    win.show();
    return app.exec();
}
