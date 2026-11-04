#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QIcon>
#include <QtQuickControls2/QQuickStyle>

#include "App.h"
#include "core/Config.h"
#include "core/ApiClient.h"
#include "core/CloudData.h"
#include "scanner/NetworkScanner.h"
#include "ai/OllamaClient.h"
#include "privacy/PrivacyMode.h"

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    app.setApplicationName("ShadowCypher");
    app.setApplicationVersion("1.0.0");
    app.setOrganizationName("ShadowCypher");
    app.setOrganizationDomain("shadowcypher.site");
    app.setWindowIcon(QIcon(":/icons/sc.png"));

    QQuickStyle::setStyle("Basic");

    // Core services
    Config config;
    ApiClient apiClient(&config);
    NetworkScanner scanner;
    OllamaClient ai;
    PrivacyMode privacy;

    // App controller — bridges C++ to QML
    App controller(&config, &apiClient, &scanner, &ai, &privacy);

    CloudData cloud(&apiClient, &config, &scanner);
    QObject::connect(&controller, &App::authChanged, &cloud, [&]() {
        cloud.setActive(controller.authenticated() && !controller.offline());
    });

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("app", &controller);
    engine.rootContext()->setContextProperty("config", &config);
    engine.rootContext()->setContextProperty("apiClient", &apiClient);
    engine.rootContext()->setContextProperty("cloud", &cloud);
    engine.rootContext()->setContextProperty("scanner", &scanner);
    engine.rootContext()->setContextProperty("ai", &ai);
    engine.rootContext()->setContextProperty("privacy", &privacy);

    const QUrl url(u"qrc:/ShadowCypher/src/ui/qml/Main.qml"_qs);
    QObject::connect(
        &engine, &QQmlApplicationEngine::objectCreationFailed,
        &app, []() { QCoreApplication::exit(-1); },
        Qt::QueuedConnection
    );
    engine.load(url);

    return app.exec();
}
