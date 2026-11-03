#pragma once
#include <QObject>
#include <QString>

class Config;
class ApiClient;
class NetworkScanner;
class OllamaClient;
class PrivacyMode;

class App : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool authenticated READ authenticated NOTIFY authChanged)
    Q_PROPERTY(QString version READ version CONSTANT)

public:
    explicit App(Config*, ApiClient*, NetworkScanner*, OllamaClient*, PrivacyMode*, QObject* parent = nullptr);

    bool    authenticated() const;
    QString version() const { return "1.0.0"; }

public slots:
    void login(const QString& apiKey);
    void logout();

signals:
    void authChanged();
    void notification(const QString& title, const QString& message, const QString& level);

private:
    Config*         m_config;
    ApiClient*      m_api;
    NetworkScanner* m_scanner;
    OllamaClient*   m_ai;
    PrivacyMode*    m_privacy;
    bool            m_authenticated = false;
};
