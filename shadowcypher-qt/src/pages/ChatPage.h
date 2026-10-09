#pragma once
#include <QWidget>
#include <QWebSocket>
#include <QLineEdit>
#include <QPushButton>
#include <QLabel>
#include <QScrollArea>
#include <QVBoxLayout>
#include <QFrame>
#include "../ipc/IpcClient.h"

// AES-256-GCM via OpenSSL EVP.
// Key: PBKDF2-SHA256(api_key, salt, 100k iters) — 32 bytes.
// Wire format: base64(nonce[12] || ciphertext || tag[16])
class ChatPage : public QWidget {
    Q_OBJECT
public:
    explicit ChatPage(IpcClient* ipc, QWidget* parent = nullptr);

protected:
    void resizeEvent(QResizeEvent* event) override;

private slots:
    void joinRoom();
    void sendMessage();
    void onWsConnected();
    void onWsDisconnected();
    void onWsError(QAbstractSocket::SocketError error);
    void onTextMessageReceived(const QString& message);
    void onIpcResult(int id, QJsonObject result);
    void toggleTor();
    void scheduleReconnect();

private:
    IpcClient*   m_ipc;
    QWebSocket*  m_socket;

    // Top bar
    QLineEdit*   m_roomInput;
    QPushButton* m_joinBtn;
    QPushButton* m_torBtn;
    QLabel*      m_connDot;
    QLabel*      m_encLabel;

    // Message area
    QScrollArea* m_scrollArea;
    QWidget*     m_bubblesWidget;
    QVBoxLayout* m_bubblesLayout;

    // Bottom bar
    QLineEdit*   m_msgInput;
    QPushButton* m_sendBtn;

    QString m_currentRoom;
    QString m_apiKey;
    QString m_serverUrl;
    bool    m_torEnabled  = false;
    bool    m_reconnecting = false;
    int     m_statusReqId = -1;

    void buildUi();
    void connectWebSocket();
    void clearBubbles();
    void appendBubble(const QString& sender, const QString& content, bool isSelf);
    void scrollToBottom();
    void updateBubbleWidths();
    void applyProxy();

    // AES-256-GCM via OpenSSL EVP
    QString encryptMessage(const QString& plaintext);
    QString decryptMessage(const QString& ciphertext);
};
