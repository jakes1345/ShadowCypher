#pragma once
#include "Process.h"
#include <QJsonArray>
#include <QJsonObject>
#include <QUrl>

namespace shadow {
class NativeTools {
public:
    using Discovery = std::function<QJsonArray(const Cancel&)>;
    explicit NativeTools(QJsonObject config = {}, Discovery discovery = {});
    QString invoke(const QString& method, const QStringList& args, const Cancel& cancel = {}) const;
    QJsonObject portScan(const QString& target, const QString& ports, const Cancel& cancel = {}) const;
    QJsonArray discover(const Cancel& cancel = {}) const;
    QJsonObject chat(const QString& message, const Cancel& cancel = {}) const;
    QJsonObject api(const QString& path, const QJsonObject& body = {}, bool post = false,
                    const Cancel& cancel = {}) const;
    QJsonObject agentCycle(const QString& statePath, bool executeMissions, const Output& output,
                           const Cancel& cancel = {}) const;
    static QJsonObject request(const QUrl& url, const QJsonObject& body = {}, bool post = false,
                               const QByteArray& bearer = {}, const Cancel& cancel = {}, int timeoutMs = 30000);
    static QList<quint16> parsePorts(const QString& ports);
    static void validateTarget(const QString& target);
    static QJsonArray parseNeighbors(const QByteArray& json);
private:
    QJsonObject m_config;
    Discovery m_discovery;
};
}
