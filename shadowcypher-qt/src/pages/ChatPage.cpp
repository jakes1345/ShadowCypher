#include "ChatPage.h"
#include "../theme.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QScrollBar>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSettings>
#include <QUrl>
#include <QNetworkProxy>
#include <QNetworkRequest>
#include <QResizeEvent>
#include <QTimer>

#include <openssl/evp.h>
#include <openssl/rand.h>
#include <cstring>

// ── Crypto constants ─────────────────────────────────────────────────────────

static constexpr int AES_KEY_LEN   = 32;
static constexpr int GCM_NONCE_LEN = 12;
static constexpr int GCM_TAG_LEN   = 16;
static constexpr int PBKDF2_ITERS  = 100000;
static const char*   PBKDF2_SALT   = "shadowcypher-e2e-v1";

static bool deriveKey(const QByteArray& keyMaterial, unsigned char* out32) {
    return PKCS5_PBKDF2_HMAC(
        keyMaterial.constData(), keyMaterial.size(),
        reinterpret_cast<const unsigned char*>(PBKDF2_SALT),
        static_cast<int>(strlen(PBKDF2_SALT)),
        PBKDF2_ITERS, EVP_sha256(), AES_KEY_LEN, out32) == 1;
}

// ── AES-256-GCM encrypt ──────────────────────────────────────────────────────

QString ChatPage::encryptMessage(const QString& plaintext) {
    if (m_apiKey.isEmpty()) return plaintext;

    unsigned char key[AES_KEY_LEN];
    if (!deriveKey(m_apiKey.toUtf8(), key)) return plaintext;

    unsigned char nonce[GCM_NONCE_LEN];
    if (RAND_bytes(nonce, GCM_NONCE_LEN) != 1) return plaintext;

    QByteArray pt = plaintext.toUtf8();
    QByteArray ct(pt.size(), '\0');
    unsigned char tag[GCM_TAG_LEN];

    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (!ctx) return plaintext;

    bool ok = false;
    int outLen = 0;
    if (EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr) == 1 &&
        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, GCM_NONCE_LEN, nullptr) == 1 &&
        EVP_EncryptInit_ex(ctx, nullptr, nullptr, key, nonce) == 1 &&
        EVP_EncryptUpdate(ctx, reinterpret_cast<unsigned char*>(ct.data()), &outLen,
                          reinterpret_cast<const unsigned char*>(pt.constData()), pt.size()) == 1 &&
        EVP_EncryptFinal_ex(ctx, reinterpret_cast<unsigned char*>(ct.data()) + outLen, &outLen) == 1 &&
        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, GCM_TAG_LEN, tag) == 1) {
        ok = true;
    }
    EVP_CIPHER_CTX_free(ctx);
    if (!ok) return plaintext;

    QByteArray wire;
    wire.append(reinterpret_cast<const char*>(nonce), GCM_NONCE_LEN);
    wire.append(ct);
    wire.append(reinterpret_cast<const char*>(tag), GCM_TAG_LEN);
    return QString::fromUtf8(wire.toBase64());
}

// ── AES-256-GCM decrypt ──────────────────────────────────────────────────────

QString ChatPage::decryptMessage(const QString& ciphertext) {
    if (m_apiKey.isEmpty()) return ciphertext;

    QByteArray wire = QByteArray::fromBase64(ciphertext.toUtf8());
    int minLen = GCM_NONCE_LEN + GCM_TAG_LEN;
    if (wire.size() < minLen) {
        // Legacy ENC: fallback
        if (ciphertext.startsWith("ENC:"))
            return QString::fromUtf8(QByteArray::fromBase64(ciphertext.mid(4).toUtf8()));
        return ciphertext;
    }

    unsigned char key[AES_KEY_LEN];
    if (!deriveKey(m_apiKey.toUtf8(), key)) return ciphertext;

    const unsigned char* nonce = reinterpret_cast<const unsigned char*>(wire.constData());
    const unsigned char* ct    = nonce + GCM_NONCE_LEN;
    int ctLen = wire.size() - GCM_NONCE_LEN - GCM_TAG_LEN;
    unsigned char tag[GCM_TAG_LEN];
    memcpy(tag, wire.constData() + GCM_NONCE_LEN + ctLen, GCM_TAG_LEN);

    QByteArray pt(ctLen, '\0');
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (!ctx) return ciphertext;

    bool ok = false;
    int outLen = 0;
    if (EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr) == 1 &&
        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, GCM_NONCE_LEN, nullptr) == 1 &&
        EVP_DecryptInit_ex(ctx, nullptr, nullptr, key, nonce) == 1 &&
        EVP_DecryptUpdate(ctx, reinterpret_cast<unsigned char*>(pt.data()), &outLen, ct, ctLen) == 1 &&
        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, GCM_TAG_LEN, tag) == 1 &&
        EVP_DecryptFinal_ex(ctx, reinterpret_cast<unsigned char*>(pt.data()) + outLen, &outLen) == 1) {
        ok = true;
    }
    EVP_CIPHER_CTX_free(ctx);

    // Auth tag mismatch → tampered or wrong key, return empty
    return ok ? QString::fromUtf8(pt) : QString();
}

// ── Constructor ──────────────────────────────────────────────────────────────

ChatPage::ChatPage(IpcClient* ipc, QWidget* parent)
    : QWidget(parent), m_ipc(ipc),
      m_socket(new QWebSocket(QString(), QWebSocketProtocol::VersionLatest, this))
{
    QSettings settings;
    m_serverUrl   = settings.value("chat/server_url",
                                   "wss://api.shadowcypher.site/v1/chat/ws").toString();
    m_apiKey      = settings.value("api/key").toString();
    m_torEnabled  = settings.value("chat/tor_enabled", false).toBool();
    m_currentRoom = "general";

    buildUi();

    connect(m_socket, &QWebSocket::connected,           this, &ChatPage::onWsConnected);
    connect(m_socket, &QWebSocket::disconnected,        this, &ChatPage::onWsDisconnected);
    connect(m_socket, &QWebSocket::textMessageReceived, this, &ChatPage::onTextMessageReceived);
    connect(m_socket, &QWebSocket::errorOccurred,       this, &ChatPage::onWsError);

    if (m_ipc) {
        connect(m_ipc, &IpcClient::resultReady, this, &ChatPage::onIpcResult);
        connect(m_ipc, &IpcClient::connected, this, [this]() {
            // Probe Ghost Mode state to auto-enable Tor if already active
            m_statusReqId = m_ipc->call("ghost_mode_status");
        });
    }

    // Apply proxy and connect after event loop starts to avoid signal ordering issues
    QTimer::singleShot(0, this, [this]() { joinRoom(); });
}

// ── UI ───────────────────────────────────────────────────────────────────────

void ChatPage::buildUi() {
    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(20, 14, 20, 14);
    lay->setSpacing(10);

    // ── Header ──
    auto* header = new QHBoxLayout;
    auto* title = new QLabel;
    title->setText("<span style='font-weight:900;font-size:16px;color:#b44aff;"
                   "letter-spacing:2px;'>ENCRYPTED CHAT</span>");
    title->setTextFormat(Qt::RichText);
    header->addWidget(title);
    header->addStretch();

    m_encLabel = new QLabel("AES-256-GCM");
    m_encLabel->setStyleSheet(
        "color: #00ff9d; font-family: 'JetBrains Mono'; font-size: 9px; "
        "letter-spacing: 1.5px; border: 1px solid rgba(0,255,157,0.25); "
        "border-radius: 3px; padding: 2px 6px;"
    );
    header->addWidget(m_encLabel);
    lay->addLayout(header);

    // ── Top bar ──
    auto* topBar = new QHBoxLayout;

    auto* roomLabel = new QLabel("ROOM");
    roomLabel->setStyleSheet(
        "color: #475569; font-family: 'JetBrains Mono'; font-size: 10px; letter-spacing: 1.5px;"
    );
    topBar->addWidget(roomLabel);

    m_roomInput = new QLineEdit(m_currentRoom);
    m_roomInput->setFixedWidth(160);
    m_roomInput->setStyleSheet(R"(
        QLineEdit {
            background: #111827; color: #e2e8f0;
            border: 1px solid rgba(180,74,255,0.25); border-radius: 6px;
            font-family: 'JetBrains Mono'; font-size: 12px; padding: 6px 10px;
        }
        QLineEdit:focus { border-color: rgba(180,74,255,0.55); }
    )");
    topBar->addWidget(m_roomInput);

    m_joinBtn = new QPushButton("JOIN");
    m_joinBtn->setStyleSheet(R"(
        QPushButton {
            background: rgba(180,74,255,0.12); border: 1px solid rgba(180,74,255,0.35);
            color: #b44aff; font-family: 'JetBrains Mono'; font-size: 10px;
            letter-spacing: 1px; padding: 6px 16px; border-radius: 6px; font-weight: 700;
        }
        QPushButton:hover { background: rgba(180,74,255,0.22); }
    )");
    connect(m_joinBtn, &QPushButton::clicked, this, &ChatPage::joinRoom);
    topBar->addWidget(m_joinBtn);

    topBar->addStretch();

    // Tor toggle
    m_torBtn = new QPushButton(m_torEnabled ? "🧅 TOR ON" : "🧅 TOR");
    m_torBtn->setCheckable(true);
    m_torBtn->setChecked(m_torEnabled);
    auto torStyle = [](bool on) -> QString {
        return on
            ? "QPushButton { background: rgba(0,255,157,0.12); border: 1px solid rgba(0,255,157,0.4); "
              "color: #00ff9d; font-family: 'JetBrains Mono'; font-size: 9px; "
              "letter-spacing: 1px; padding: 6px 10px; border-radius: 6px; font-weight: 700; }"
            : "QPushButton { background: transparent; border: 1px solid rgba(255,255,255,0.1); "
              "color: #334155; font-family: 'JetBrains Mono'; font-size: 9px; "
              "letter-spacing: 1px; padding: 6px 10px; border-radius: 6px; }";
    };
    m_torBtn->setStyleSheet(torStyle(m_torEnabled));
    connect(m_torBtn, &QPushButton::toggled, this, [this, torStyle](bool on) {
        m_torEnabled = on;
        m_torBtn->setText(on ? "🧅 TOR ON" : "🧅 TOR");
        m_torBtn->setStyleSheet(torStyle(on));
        QSettings().setValue("chat/tor_enabled", on);
        toggleTor();
    });
    topBar->addWidget(m_torBtn);

    // Connection dot
    m_connDot = new QLabel("●");
    m_connDot->setStyleSheet("color: #334155; font-size: 14px; margin-left: 6px;");
    m_connDot->setToolTip("WebSocket: disconnected");
    topBar->addWidget(m_connDot);

    lay->addLayout(topBar);

    // Separator
    auto* sep = new QFrame;
    sep->setFrameShape(QFrame::HLine);
    sep->setStyleSheet("color: rgba(255,255,255,0.06);");
    lay->addWidget(sep);

    // ── Message area ──
    m_scrollArea = new QScrollArea;
    m_scrollArea->setWidgetResizable(true);
    m_scrollArea->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    m_scrollArea->setStyleSheet(R"(
        QScrollArea {
            background: #060810;
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 10px;
        }
        QScrollArea > QWidget > QWidget { background: #060810; }
    )");

    m_bubblesWidget = new QWidget;
    m_bubblesWidget->setStyleSheet("background: #060810;");
    m_bubblesLayout = new QVBoxLayout(m_bubblesWidget);
    m_bubblesLayout->setContentsMargins(12, 12, 12, 12);
    m_bubblesLayout->setSpacing(8);
    m_bubblesLayout->addStretch();

    m_scrollArea->setWidget(m_bubblesWidget);
    lay->addWidget(m_scrollArea, 1);

    // ── Bottom bar ──
    auto* bottomBar = new QHBoxLayout;

    m_msgInput = new QLineEdit;
    m_msgInput->setPlaceholderText("Type a message… (AES-256-GCM)");
    m_msgInput->setStyleSheet(R"(
        QLineEdit {
            background: #111827; color: #e2e8f0;
            border: 1px solid rgba(180,74,255,0.25); border-radius: 8px;
            font-size: 13px; padding: 10px 14px;
        }
        QLineEdit:focus { border-color: rgba(180,74,255,0.6); }
    )");
    connect(m_msgInput, &QLineEdit::returnPressed, this, &ChatPage::sendMessage);
    bottomBar->addWidget(m_msgInput, 1);

    m_sendBtn = new QPushButton("SEND");
    m_sendBtn->setStyleSheet(R"(
        QPushButton {
            background: rgba(180,74,255,0.18); border: 1px solid rgba(180,74,255,0.45);
            color: #b44aff; font-family: 'JetBrains Mono'; font-size: 11px;
            letter-spacing: 1px; padding: 10px 22px; border-radius: 8px; font-weight: 700;
        }
        QPushButton:hover { background: rgba(180,74,255,0.30); }
        QPushButton:disabled { color: #334155; border-color: #1e293b; background: transparent; }
    )");
    connect(m_sendBtn, &QPushButton::clicked, this, &ChatPage::sendMessage);
    bottomBar->addWidget(m_sendBtn);

    lay->addLayout(bottomBar);
}

// ── Resize — update bubble max widths ────────────────────────────────────────

void ChatPage::resizeEvent(QResizeEvent* event) {
    QWidget::resizeEvent(event);
    updateBubbleWidths();
}

void ChatPage::updateBubbleWidths() {
    int maxW = static_cast<int>(m_scrollArea->width() * 0.70);
    if (maxW < 100) return;
    for (int i = 0; i < m_bubblesLayout->count(); ++i) {
        auto* item = m_bubblesLayout->itemAt(i);
        if (item && item->widget())
            item->widget()->setMaximumWidth(maxW);
    }
}

// ── WebSocket management ─────────────────────────────────────────────────────

void ChatPage::applyProxy() {
    if (m_torEnabled) {
        QNetworkProxy proxy(QNetworkProxy::Socks5Proxy, "127.0.0.1", 9050);
        m_socket->setProxy(proxy);
    } else {
        m_socket->setProxy(QNetworkProxy::NoProxy);
    }
}

void ChatPage::connectWebSocket() {
    if (m_socket->state() != QAbstractSocket::UnconnectedState)
        m_socket->close();

    // Re-read API key in case it was updated in Settings
    m_apiKey = QSettings().value("api/key").toString();

    applyProxy();

    QNetworkRequest req(QUrl(m_serverUrl + "?room=" + QUrl::toPercentEncoding(m_currentRoom)));
    if (!m_apiKey.isEmpty())
        req.setRawHeader("Authorization", ("Bearer " + m_apiKey).toUtf8());

    m_socket->open(req);
}

void ChatPage::joinRoom() {
    m_reconnecting = false;
    QString room = m_roomInput->text().trimmed();
    if (room.isEmpty()) room = "general";
    m_currentRoom = room;
    m_roomInput->setText(room);
    clearBubbles();
    connectWebSocket();
}

void ChatPage::toggleTor() {
    // Reconnect with new proxy setting
    appendBubble("SYSTEM",
        m_torEnabled
            ? "Tor routing enabled — reconnecting via SOCKS5 127.0.0.1:9050"
            : "Tor routing disabled — reconnecting directly",
        false);
    joinRoom();
}

void ChatPage::scheduleReconnect() {
    if (m_reconnecting) return;
    m_reconnecting = true;
    appendBubble("SYSTEM", "Connection lost — reconnecting in 5s…", false);
    QTimer::singleShot(5000, this, [this]() {
        if (m_socket->state() == QAbstractSocket::UnconnectedState)
            connectWebSocket();
        m_reconnecting = false;
    });
}

// ── WebSocket callbacks ───────────────────────────────────────────────────────

void ChatPage::onWsConnected() {
    m_reconnecting = false;
    m_connDot->setStyleSheet("color: #00ff9d; font-size: 14px; margin-left: 6px;");
    m_connDot->setToolTip("WebSocket: connected to #" + m_currentRoom
                         + (m_torEnabled ? " via Tor" : ""));
    appendBubble("SYSTEM",
        "Connected to #" + m_currentRoom
        + " — AES-256-GCM encrypted"
        + (m_torEnabled ? " · Tor routing active" : ""),
        false);
}

void ChatPage::onWsDisconnected() {
    m_connDot->setStyleSheet("color: #334155; font-size: 14px; margin-left: 6px;");
    m_connDot->setToolTip("WebSocket: disconnected");
    scheduleReconnect();
}

void ChatPage::onWsError(QAbstractSocket::SocketError) {
    QString errMsg = m_socket->errorString();
    if (m_torEnabled && errMsg.contains("refused", Qt::CaseInsensitive))
        appendBubble("SYSTEM", "Tor SOCKS5 refused — is Tor running? (systemctl start tor)", false);
    scheduleReconnect();
}

// ── IPC — auto-sync Ghost Mode state ─────────────────────────────────────────

void ChatPage::onIpcResult(int id, QJsonObject result) {
    if (id != m_statusReqId) return;
    bool ghostActive = result.value("active").toBool();
    if (ghostActive && !m_torEnabled) {
        m_torEnabled = true;
        m_torBtn->setChecked(true);
        appendBubble("SYSTEM", "Ghost Mode detected — Tor routing auto-enabled", false);
    }
}

// ── Send / receive ────────────────────────────────────────────────────────────

void ChatPage::sendMessage() {
    QString text = m_msgInput->text().trimmed();
    if (text.isEmpty()) return;
    if (m_socket->state() != QAbstractSocket::ConnectedState) {
        appendBubble("SYSTEM", "Not connected — click JOIN to reconnect.", false);
        return;
    }

    m_msgInput->clear();

    QJsonObject msg;
    msg["type"]    = "message";
    msg["room"]    = m_currentRoom;
    msg["content"] = encryptMessage(text);
    msg["sender"]  = "user";

    m_socket->sendTextMessage(
        QString::fromUtf8(QJsonDocument(msg).toJson(QJsonDocument::Compact)));

    appendBubble("you", text, true);
}

void ChatPage::onTextMessageReceived(const QString& raw) {
    QJsonParseError err;
    QJsonDocument doc = QJsonDocument::fromJson(raw.toUtf8(), &err);
    if (err.error != QJsonParseError::NoError || !doc.isObject()) return;

    QJsonObject obj = doc.object();
    if (obj.value("type").toString() != "message") return;

    QString sender    = obj.value("sender").toString("unknown");
    QString encrypted = obj.value("content").toString();

    if (sender == "user") return;  // don't echo own messages

    QString plaintext = decryptMessage(encrypted);
    if (plaintext.isEmpty()) {
        appendBubble("SYSTEM", "[message could not be decrypted — wrong key or tampered]", false);
        return;
    }

    appendBubble(sender, plaintext, false);
}

// ── Bubble helpers ────────────────────────────────────────────────────────────

void ChatPage::clearBubbles() {
    while (m_bubblesLayout->count() > 1) {
        QLayoutItem* item = m_bubblesLayout->takeAt(0);
        if (item) {
            delete item->widget();
            delete item;
        }
    }
}

void ChatPage::appendBubble(const QString& sender, const QString& content, bool isSelf) {
    auto* row    = new QWidget;
    auto* rowLay = new QHBoxLayout(row);
    rowLay->setContentsMargins(0, 0, 0, 0);
    rowLay->setSpacing(0);
    row->setStyleSheet("background: transparent;");

    auto* col    = new QWidget;
    auto* colLay = new QVBoxLayout(col);
    colLay->setContentsMargins(0, 0, 0, 0);
    colLay->setSpacing(3);
    col->setStyleSheet("background: transparent;");

    // Set max width from current scroll area size, not widget()->width() which may be 0
    int maxW = static_cast<int>(m_scrollArea->width() * 0.70);
    if (maxW > 100) col->setMaximumWidth(maxW);

    if (!isSelf) {
        auto* senderLbl = new QLabel(sender.toUpper());
        senderLbl->setStyleSheet(
            "color: #334155; font-family: 'JetBrains Mono'; font-size: 9px; "
            "letter-spacing: 1.5px; background: transparent;"
        );
        colLay->addWidget(senderLbl, 0, Qt::AlignLeft);
    }

    auto* bubble = new QLabel(content.toHtmlEscaped().replace("\n", "<br>"));
    bubble->setTextFormat(Qt::RichText);
    bubble->setWordWrap(true);

    if (isSelf) {
        bubble->setStyleSheet(R"(
            QLabel {
                background: rgba(180,74,255,0.15); color: #e2e8f0;
                border-radius: 12px; padding: 8px 12px;
                font-size: 13px; line-height: 1.5;
            }
        )");
    } else {
        bool isSystem = (sender == "SYSTEM");
        bubble->setStyleSheet(isSystem
            ? R"(QLabel {
                background: rgba(255,255,255,0.02); color: #334155;
                border-radius: 12px; padding: 8px 12px;
                font-family: 'JetBrains Mono'; font-size: 10px; font-style: italic;
              })"
            : R"(QLabel {
                background: rgba(255,255,255,0.05); color: #94a3b8;
                border-radius: 12px; padding: 8px 12px;
                font-size: 13px; line-height: 1.5;
              })"
        );
    }

    colLay->addWidget(bubble);

    if (isSelf) {
        rowLay->addStretch();
        rowLay->addWidget(col);
    } else {
        rowLay->addWidget(col);
        rowLay->addStretch();
    }

    // Insert before the trailing stretch
    int insertPos = m_bubblesLayout->count() - 1;
    m_bubblesLayout->insertWidget(insertPos, row);

    scrollToBottom();
}

void ChatPage::scrollToBottom() {
    QScrollBar* vsb = m_scrollArea->verticalScrollBar();
    vsb->setValue(vsb->maximum());
}
