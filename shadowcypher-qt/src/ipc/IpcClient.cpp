#include "IpcClient.h"
#include <QTimer>
#include <QJsonArray>

#ifdef Q_OS_WIN
#  include <QTcpSocket>
static constexpr quint16 IPC_TCP_PORT = 54321;
#else
static const QString UNIX_SOCKET_PATH = "/tmp/shadowcypher-daemon.sock";
#endif

IpcClient::IpcClient(QObject* parent) : QObject(parent) {
#ifdef Q_OS_WIN
    auto* sock = new QTcpSocket(this);
    connect(sock, &QTcpSocket::connected,     this, &IpcClient::onConnected);
    connect(sock, &QTcpSocket::disconnected,  this, &IpcClient::onDisconnected);
    connect(sock, &QTcpSocket::readyRead,     this, &IpcClient::onReadyRead);
    connect(sock, &QTcpSocket::errorOccurred, this, [this](QAbstractSocket::SocketError) {
        onSocketError();
    });
    m_device = sock;
#else
    auto* sock = new QLocalSocket(this);
    connect(sock, &QLocalSocket::connected,     this, &IpcClient::onConnected);
    connect(sock, &QLocalSocket::disconnected,  this, &IpcClient::onDisconnected);
    connect(sock, &QLocalSocket::readyRead,     this, &IpcClient::onReadyRead);
    connect(sock, &QLocalSocket::errorOccurred, this, [this](QLocalSocket::LocalSocketError) {
        onSocketError();
    });
    m_device = sock;
#endif
}

void IpcClient::connectToDaemon() {
#ifdef Q_OS_WIN
    auto* sock = qobject_cast<QTcpSocket*>(m_device);
    if (sock->state() == QAbstractSocket::ConnectedState) return;
    sock->connectToHost("127.0.0.1", IPC_TCP_PORT);
#else
    auto* sock = qobject_cast<QLocalSocket*>(m_device);
    if (sock->state() == QLocalSocket::ConnectedState) return;
    sock->connectToServer(UNIX_SOCKET_PATH);
#endif
}

bool IpcClient::isConnected() const {
#ifdef Q_OS_WIN
    return qobject_cast<QTcpSocket*>(m_device)->state() == QAbstractSocket::ConnectedState;
#else
    return qobject_cast<QLocalSocket*>(m_device)->state() == QLocalSocket::ConnectedState;
#endif
}

int IpcClient::call(const QString& method, const QJsonObject& params) {
    int id = m_nextId++;
    QJsonObject req{
        {"jsonrpc", "2.0"},
        {"method", method},
        {"params", params},
        {"id", id}
    };
    QByteArray payload = QJsonDocument(req).toJson(QJsonDocument::Compact) + "\n";
    m_device->write(payload);
    return id;
}

void IpcClient::onConnected() {
    m_buffer.clear();
    emit connected();
}

void IpcClient::onDisconnected() {
    emit disconnected();
    reconnectAfter(5000);
}

void IpcClient::onReadyRead() {
    m_buffer += m_device->readAll();
    while (true) {
        int nl = m_buffer.indexOf('\n');
        if (nl == -1) break;
        QByteArray line = m_buffer.left(nl);
        m_buffer.remove(0, nl + 1);
        if (line.trimmed().isEmpty()) continue;

        QJsonParseError err;
        QJsonDocument doc = QJsonDocument::fromJson(line, &err);
        if (err.error != QJsonParseError::NoError) continue;

        QJsonObject obj = doc.object();
        int id = obj.value("id").toInt(-1);
        if (obj.contains("result")) {
            emit resultReady(id, obj.value("result").toObject());
        } else if (obj.contains("error")) {
            emit errorOccurred(id, obj.value("error").toObject().value("message").toString());
        }
    }
}

void IpcClient::onSocketError() {
    reconnectAfter(5000);
}

void IpcClient::reconnectAfter(int ms) {
    QTimer::singleShot(ms, this, &IpcClient::connectToDaemon);
}
