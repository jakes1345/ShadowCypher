#include "IpcClient.h"
#include <QTimer>
#include <QJsonArray>

static const QString SOCKET_PATH = "/tmp/shadowcypher-daemon.sock";

IpcClient::IpcClient(QObject* parent) : QObject(parent) {
    m_socket = new QLocalSocket(this);
    connect(m_socket, &QLocalSocket::connected,    this, &IpcClient::onConnected);
    connect(m_socket, &QLocalSocket::disconnected, this, &IpcClient::onDisconnected);
    connect(m_socket, &QLocalSocket::readyRead,    this, &IpcClient::onReadyRead);
    connect(m_socket, &QLocalSocket::errorOccurred, this, &IpcClient::onSocketError);
}

void IpcClient::connectToDaemon() {
    if (m_socket->state() == QLocalSocket::ConnectedState) return;
    m_socket->connectToServer(SOCKET_PATH);
}

bool IpcClient::isConnected() const {
    return m_socket->state() == QLocalSocket::ConnectedState;
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
    m_socket->write(payload);
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
    m_buffer += m_socket->readAll();
    // Messages are newline-delimited JSON
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

void IpcClient::onSocketError(QLocalSocket::LocalSocketError) {
    reconnectAfter(5000);
}

void IpcClient::reconnectAfter(int ms) {
    QTimer::singleShot(ms, this, &IpcClient::connectToDaemon);
}
