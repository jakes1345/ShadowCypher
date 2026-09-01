#pragma once
#include <QLocalSocket>
#include <QObject>
#include <QJsonDocument>
#include <QJsonObject>
#include <functional>

// JSON-RPC 2.0 client over QLocalSocket
// Python daemon listens at /tmp/shadowcypher-daemon.sock
class IpcClient : public QObject {
    Q_OBJECT
public:
    explicit IpcClient(QObject* parent = nullptr);

    void connectToDaemon();
    bool isConnected() const;

    // Fire-and-forget call — result delivered via resultReady(id, result)
    int call(const QString& method, const QJsonObject& params = {});

signals:
    void connected();
    void disconnected();
    void resultReady(int id, QJsonObject result);
    void errorOccurred(int id, QString message);

private slots:
    void onConnected();
    void onDisconnected();
    void onReadyRead();
    void onSocketError(QLocalSocket::LocalSocketError err);

private:
    QLocalSocket* m_socket;
    QByteArray    m_buffer;
    int           m_nextId = 1;

    void reconnectAfter(int ms);
};
