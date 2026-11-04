#include "Config.h"
#include <QStandardPaths>
#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>

Config::Config(QObject* parent) : QObject(parent)
{
    const QString dir = QStandardPaths::writableLocation(QStandardPaths::HomeLocation)
                        + "/.shadowcypher";
    QDir().mkpath(dir);
    // Restrict the config directory to owner-only (700) so the API key isn't world-readable.
    QFile::setPermissions(dir,
        QFileDevice::ReadOwner | QFileDevice::WriteOwner | QFileDevice::ExeOwner);
    m_path = dir + "/config.json";
    load();
}

void Config::load()
{
    QFile f(m_path);
    if (!f.open(QIODevice::ReadOnly)) return;
    m_raw          = QJsonDocument::fromJson(f.readAll()).object();
    m_apiKey       = m_raw["api_key"].toString();
    m_apiBase      = m_raw["api_base"].toString("https://api.shadowcypher.site");
    m_scanInterval = m_raw["scan_interval_sec"].toInt(600);
}

void Config::save()
{
    m_raw["api_key"]           = m_apiKey;
    m_raw["api_base"]          = m_apiBase;
    m_raw["scan_interval_sec"] = m_scanInterval;
    QFile f(m_path);
    if (f.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
        f.setPermissions(QFileDevice::ReadOwner | QFileDevice::WriteOwner);
        f.write(QJsonDocument(m_raw).toJson());
    }
    emit changed();
}

void Config::reload() { load(); emit changed(); }

QString Config::apiKey()       const { return m_apiKey; }
QString Config::apiBase()      const { return m_apiBase; }
int     Config::scanInterval() const { return m_scanInterval; }

void Config::setApiKey(const QString& v)     { m_apiKey = v;       save(); }
void Config::setApiBase(const QString& v)
{
    QString base = v.trimmed();
    while (base.endsWith('/')) base.chop(1);
    m_apiBase = base;
    save();
}
void Config::setScanInterval(int v)          { m_scanInterval = qMax(30, v); save(); }
