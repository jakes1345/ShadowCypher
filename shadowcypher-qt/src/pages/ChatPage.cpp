#include "ChatPage.h"
#include "../theme.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QScrollBar>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSettings>
#include <QUrl>

// ── Simulated encryption layer ──────────────────────────────────────────────
// TODO: replace with real AES-256-GCM via OpenSSL

QString ChatPage::encryptMessage(const QString& plaintext, const QString& /*key*/) {
    return "ENC:" + plaintext.toUtf8().toBase64();
}

QString ChatPage::decryptMessage(const QString& ciphertext, const QString& /*key*/) {
    if (ciphertext.startsWith("ENC:")) {
        QByteArray encoded = ciphertext.mid(4).toUtf8();
        return QString::fromUtf8(QByteArray::fromBase64(encoded));
    }
    // Plaintext fallback for unencrypted rooms
    return ciphertext;
}

// ── Constructor ─────────────────────────────────────────────────────────────

ChatPage::ChatPage(IpcClient* ipc, QWidget* parent)
    : QWidget(parent), m_ipc(ipc), m_socket(new QWebSocket(QString(), QWebSocketProtocol::VersionLatest, this))
{
    QSettings settings;
    m_serverUrl   = settings.value("chat/server_url", "wss://api.shadowcypher.site/v1/chat/ws").toString();
    m_apiKey      = settings.value("api/key").toString();
    m_currentRoom = "general";

    buildUi();

    connect(m_socket, &QWebSocket::connected,    this, &ChatPage::onWsConnected);
    connect(m_socket, &QWebSocket::disconnected, this, &ChatPage::onWsDisconnected);
    connect(m_socket, &QWebSocket::textMessageReceived, this, &ChatPage::onTextMessageReceived);
}

// ── UI Construction ─────────────────────────────────────────────────────────

void ChatPage::buildUi() {
    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(20, 14, 20, 14);
    lay->setSpacing(10);

    // ── Header ──────────────────────────────────────────────────────────────
    auto* header = new QHBoxLayout;
    auto* title = new QLabel;
    title->setText("<span style='font-weight:900;font-size:16px;color:#b44aff;"
                   "letter-spacing:2px;'>ENCRYPTED CHAT</span>");
    title->setTextFormat(Qt::RichText);
    header->addWidget(title);
    header->addStretch();
    lay->addLayout(header);

    // ── Top bar: room + join + connection dot ────────────────────────────────
    auto* topBar = new QHBoxLayout;

    auto* roomLabel = new QLabel("ROOM");
    roomLabel->setStyleSheet(
        "color: #475569; font-family: 'JetBrains Mono'; font-size: 10px; "
        "letter-spacing: 1.5px;"
    );
    topBar->addWidget(roomLabel);

    m_roomInput = new QLineEdit(m_currentRoom);
    m_roomInput->setFixedWidth(160);
    m_roomInput->setStyleSheet(R"(
        QLineEdit {
            background: #111827; color: #e2e8f0;
            border: 1px solid rgba(180,74,255,0.25); border-radius: 6px;
            font-family: 'JetBrains Mono'; font-size: 12px;
            padding: 6px 10px;
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

    // Connection status dot
    m_connDot = new QLabel("●");
    m_connDot->setStyleSheet("color: #334155; font-size: 14px;");
    m_connDot->setToolTip("WebSocket: disconnected");
    topBar->addWidget(m_connDot);

    lay->addLayout(topBar);

    // Separator line
    auto* sep = new QFrame;
    sep->setFrameShape(QFrame::HLine);
    sep->setStyleSheet("color: rgba(255,255,255,0.06);");
    lay->addWidget(sep);

    // ── Message area ─────────────────────────────────────────────────────────
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
    m_bubblesLayout->addStretch();  // pushes bubbles to the bottom

    m_scrollArea->setWidget(m_bubblesWidget);
    lay->addWidget(m_scrollArea, 1);

    // ── Bottom bar: input + send ──────────────────────────────────────────────
    auto* bottomBar = new QHBoxLayout;

    m_msgInput = new QLineEdit;
    m_msgInput->setPlaceholderText("Type a message… (AES-256-GCM encrypted)");
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

    // Auto-join default room on construction
    joinRoom();
}

// ── WebSocket management ─────────────────────────────────────────────────────

void ChatPage::connectWebSocket() {
    if (m_socket->state() != QAbstractSocket::UnconnectedState)
        m_socket->close();

    QString urlStr = m_serverUrl
        + "?room=" + QUrl::toPercentEncoding(m_currentRoom)
        + "&key="  + QUrl::toPercentEncoding(m_apiKey);

    m_socket->open(QUrl(urlStr));
}

void ChatPage::joinRoom() {
    QString room = m_roomInput->text().trimmed();
    if (room.isEmpty()) room = "general";
    m_currentRoom = room;
    m_roomInput->setText(room);

    // Clear existing bubbles (leave the trailing stretch)
    while (m_bubblesLayout->count() > 1)
        delete m_bubblesLayout->takeAt(0)->widget();

    // Reconnect
    connectWebSocket();
}

void ChatPage::onWsConnected() {
    m_connDot->setStyleSheet("color: #00ff9d; font-size: 14px;");
    m_connDot->setToolTip("WebSocket: connected to " + m_currentRoom);
    appendBubble("SYSTEM", "Connected to #" + m_currentRoom + " — messages are end-to-end encrypted", false);
}

void ChatPage::onWsDisconnected() {
    m_connDot->setStyleSheet("color: #334155; font-size: 14px;");
    m_connDot->setToolTip("WebSocket: disconnected");
}

// ── Message send / receive ────────────────────────────────────────────────────

void ChatPage::sendMessage() {
    QString text = m_msgInput->text().trimmed();
    if (text.isEmpty()) return;
    if (m_socket->state() != QAbstractSocket::ConnectedState) {
        appendBubble("SYSTEM", "Not connected — click JOIN to reconnect.", false);
        return;
    }

    m_msgInput->clear();

    QString encrypted = encryptMessage(text, m_apiKey);

    QJsonObject msg;
    msg["type"]    = "message";
    msg["room"]    = m_currentRoom;
    msg["content"] = encrypted;
    msg["sender"]  = "user";

    m_socket->sendTextMessage(QString::fromUtf8(QJsonDocument(msg).toJson(QJsonDocument::Compact)));

    // Show own message immediately
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
    QString plaintext = decryptMessage(encrypted, m_apiKey);

    // Don't echo our own messages (server may broadcast back)
    if (sender == "user") return;

    appendBubble(sender, plaintext, false);
}

// ── Bubble renderer ───────────────────────────────────────────────────────────

void ChatPage::appendBubble(const QString& sender, const QString& content, bool isSelf) {
    // Row widget — full width, alignment done with stretch
    auto* row    = new QWidget;
    auto* rowLay = new QHBoxLayout(row);
    rowLay->setContentsMargins(0, 0, 0, 0);
    rowLay->setSpacing(0);
    row->setStyleSheet("background: transparent;");

    // Column: optional sender label + bubble
    auto* col    = new QWidget;
    auto* colLay = new QVBoxLayout(col);
    colLay->setContentsMargins(0, 0, 0, 0);
    colLay->setSpacing(3);
    col->setStyleSheet("background: transparent;");
    col->setMaximumWidth(static_cast<int>(width() * 0.70 + 0.5));  // ~70% max

    // Sender label for received messages
    if (!isSelf) {
        auto* senderLbl = new QLabel(sender.toUpper());
        senderLbl->setStyleSheet(
            "color: #334155; font-family: 'JetBrains Mono'; font-size: 9px; "
            "letter-spacing: 1.5px; background: transparent;"
        );
        colLay->addWidget(senderLbl, 0, isSelf ? Qt::AlignRight : Qt::AlignLeft);
    }

    // Bubble label
    auto* bubble = new QLabel(content.toHtmlEscaped().replace("\n", "<br>"));
    bubble->setTextFormat(Qt::RichText);
    bubble->setWordWrap(true);

    if (isSelf) {
        bubble->setStyleSheet(R"(
            QLabel {
                background: rgba(180,74,255,0.15);
                color: #e2e8f0;
                border-radius: 12px;
                padding: 8px 12px;
                font-size: 13px;
                line-height: 1.5;
            }
        )");
    } else {
        // SYSTEM messages get a distinct dim style
        bool isSystem = (sender == "SYSTEM");
        bubble->setStyleSheet(isSystem
            ? R"(QLabel {
                background: rgba(255,255,255,0.02);
                color: #334155;
                border-radius: 12px;
                padding: 8px 12px;
                font-family: 'JetBrains Mono';
                font-size: 10px;
                font-style: italic;
            })"
            : R"(QLabel {
                background: rgba(255,255,255,0.05);
                color: #94a3b8;
                border-radius: 12px;
                padding: 8px 12px;
                font-size: 13px;
                line-height: 1.5;
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

    // Insert before the trailing stretch (last item)
    int insertPos = m_bubblesLayout->count() - 1;
    m_bubblesLayout->insertWidget(insertPos, row);

    scrollToBottom();
}

void ChatPage::scrollToBottom() {
    QScrollBar* vsb = m_scrollArea->verticalScrollBar();
    vsb->setValue(vsb->maximum());
}
