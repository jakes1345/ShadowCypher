#include "IpcClient.h"
#include <QFile>
#include <QJsonArray>
#include <QStandardPaths>
#include <QTimer>

#ifdef Q_OS_WIN
#  include <QTcpSocket>
static constexpr quint16 IPC_TCP_PORT = 54321;
#else
#  include <sys/socket.h>
#  include <unistd.h>
// Must exactly mirror the logic in Daemon.cpp so both sides resolve the same path.
// Never falls back to /tmp — an attacker can pre-create a world-writable socket there.
static QString unixSocketPath() {
    const QString rt = QStandardPaths::writableLocation(QStandardPaths::RuntimeLocation);
    // Daemon uses the same formula; keep in sync.
    return rt.isEmpty()
        ? QStringLiteral("/run/user/") + QString::number(static_cast<quint32>(::getuid()))
              + QStringLiteral("/shadowcypher-daemon.sock")
        : rt + QStringLiteral("/shadowcypher-daemon.sock");
}
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
    sock->connectToServer(unixSocketPath());
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

#ifndef Q_OS_WIN
    // Before sending anything, verify the daemon process is owned by this user.
    // Prevents connecting to a spoofed socket left in the path by another user.
    auto* sock = qobject_cast<QLocalSocket*>(m_device);
    if (sock) {
        struct ucred cred{};
        socklen_t credLen = sizeof(cred);
        const int fd = static_cast<int>(sock->socketDescriptor());
        if (fd < 0 || ::getsockopt(fd, SOL_SOCKET, SO_PEERCRED, &cred, &credLen) != 0
                   || cred.uid != ::getuid()) {
            qWarning("[IpcClient] Daemon peer UID mismatch — disconnecting");
            sock->disconnectFromServer();
            return;  // onDisconnected() will schedule a reconnect
        }
    }
#else
    // Authenticate: read the per-session token written by the daemon at startup
    const QString tokenPath = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)
                              + QStringLiteral("/daemon.token");
    QFile tf(tokenPath);
    if (tf.open(QIODevice::ReadOnly)) {
        const QByteArray token = tf.readAll().trimmed();
        tf.close();
        QJsonObject authMsg{
            {QStringLiteral("jsonrpc"), QStringLiteral("2.0")},
            {QStringLiteral("method"),  QStringLiteral("auth")},
            {QStringLiteral("params"),  QJsonObject{{QStringLiteral("token"),
                                                     QString::fromUtf8(token)}}},
            {QStringLiteral("id"), 0}
        };
        m_device->write(QJsonDocument(authMsg).toJson(QJsonDocument::Compact) + '\n');
    } else {
        qWarning("[IpcClient] Cannot read daemon token — Windows auth will fail");
    }
#endif

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
