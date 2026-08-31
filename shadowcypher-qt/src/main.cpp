#include <QApplication>
#include <QFontDatabase>
#include "MainWindow.h"
#include "theme.h"

int main(int argc, char* argv[]) {
    QApplication app(argc, argv);
    app.setApplicationName("ShadowCypher");
    app.setApplicationVersion("1.0.0");
    app.setOrganizationName("ShadowCypher");
    app.setOrganizationDomain("shadowcypher.site");

    // Load bundled fonts if present
    QFontDatabase::addApplicationFont(":/fonts/Inter.ttf");
    QFontDatabase::addApplicationFont(":/fonts/JetBrainsMono.ttf");

    app.setStyleSheet(Theme::appStyleSheet());

    MainWindow win;
    win.show();

    return app.exec();
}
