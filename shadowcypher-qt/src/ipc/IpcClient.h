#pragma once
#include <QObject>
#include <QIODevice>
#include <QJsonDocument>
#include <QJsonObject>

#ifdef Q_OS_WIN
#  include <QTcpSocket>
#else
#  include <QLocalSocket>
#endif

class IpcClient : public QObject {
    Q_OBJECT
public:
    explicit IpcClient(QObject* parent = nullptr);
    void connectToDaemon();
    bool isConnected() const;
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
    void onSocketError();

private:
    QIODevice* m_device;
    QByteArray m_buffer;
    int m_nextId = 1;
    void reconnectAfter(int ms);
};
