#include <QApplication>
#include <QFontDatabase>
#include "MainWindow.h"
#include "theme.h"
#include "api/ApiClient.h"
#include "LoginDialog.h"

int main(int argc, char* argv[]) {
    QApplication app(argc, argv);
    app.setApplicationName("ShadowCypher");
    app.setApplicationVersion("1.0.0");
    app.setOrganizationName("ShadowCypher");
    app.setOrganizationDomain("shadowcypher.site");

    QFontDatabase::addApplicationFont(":/fonts/Inter.ttf");
    QFontDatabase::addApplicationFont(":/fonts/JetBrainsMono.ttf");
    app.setStyleSheet(Theme::appStyleSheet());

    ApiClient api;
    ApiClient::setInstance(&api);

    if (!api.isAuthenticated()) {
        LoginDialog dlg(&api);
        if (dlg.exec() != QDialog::Accepted)
            return 0;
    }

    MainWindow win;
    win.show();
    return app.exec();
}
