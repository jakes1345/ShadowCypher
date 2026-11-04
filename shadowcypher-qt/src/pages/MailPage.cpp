#include "MailPage.h"
#include "../theme.h"
#include "../api/ApiClient.h"

#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QSplitter>
#include <QFrame>
#include <QListWidgetItem>
#include <QJsonDocument>
#include <QDateTime>
#include <QUrl>
#include <QTextDocumentFragment>
#include <QTimer>

// ── Style helpers ─────────────────────────────────────────────────────────────

static QString accentBtnStyle()
{
    return QStringLiteral(R"(
        QPushButton {
            background: rgba(180,74,255,0.12);
            border: 1px solid rgba(180,74,255,0.35);
            color: #b44aff;
            font-family: 'JetBrains Mono';
            font-size: 10px;
            letter-spacing: 1px;
            padding: 6px 16px;
            border-radius: 6px;
            font-weight: 700;
        }
        QPushButton:hover  { background: rgba(180,74,255,0.22); }
        QPushButton:pressed { background: rgba(180,74,255,0.30); }
        QPushButton:disabled { color: #334155; border-color: #1e293b; background: transparent; }
    )");
}

static QString ghostBtnStyle()
{
    return QStringLiteral(R"(
        QPushButton {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.10);
            color: #475569;
            font-family: 'JetBrains Mono';
            font-size: 10px;
            letter-spacing: 1px;
            padding: 6px 16px;
            border-radius: 6px;
            font-weight: 700;
        }
        QPushButton:hover { background: rgba(255,255,255,0.09); color: #94a3b8; }
        QPushButton:disabled { color: #1e293b; border-color: #1e293b; background: transparent; }
    )");
}

static QString fieldStyle()
{
    return QStringLiteral(R"(
        QLineEdit, QPlainTextEdit {
            background: #0d0f1a;
            color: #e2e8f0;
            border: 1px solid rgba(180,74,255,0.25);
            border-radius: 6px;
            font-size: 12px;
            padding: 6px 10px;
            selection-background-color: rgba(180,74,255,0.35);
        }
        QLineEdit:focus, QPlainTextEdit:focus {
            border-color: rgba(180,74,255,0.55);
        }
        QLineEdit:disabled, QPlainTextEdit:disabled {
            color: #334155;
            border-color: #1e293b;
        }
    )");
}

// ── Constructor ───────────────────────────────────────────────────────────────

// Mail lives on the API (Shadow Mail), not in the local daemon, so every call
// goes through ApiClient with the signed-in account's key.
MailPage::MailPage(QWidget* parent)
    : QWidget(parent)
{
    buildUi();

    m_timer = new QTimer(this);
    m_timer->setInterval(60'000);
    connect(m_timer, &QTimer::timeout, this, &MailPage::refresh);
    m_timer->start();

    refresh();
}

// ── UI Construction ───────────────────────────────────────────────────────────

void MailPage::buildUi()
{
    auto* rootLay = new QVBoxLayout(this);
    rootLay->setContentsMargins(0, 0, 0, 0);
    rootLay->setSpacing(0);

    auto* splitter = new QSplitter(Qt::Horizontal, this);
    splitter->setHandleWidth(1);
    splitter->setChildrenCollapsible(false);
    splitter->setStyleSheet("QSplitter::handle { background: rgba(255,255,255,0.06); }");
    rootLay->addWidget(splitter);

    // ═══════════════════════════════════════════════════════════════════════
    //  LEFT PANEL
    // ═══════════════════════════════════════════════════════════════════════
    auto* leftPanel = new QWidget;
    leftPanel->setMinimumWidth(240);
    leftPanel->setMaximumWidth(360);
    leftPanel->setStyleSheet("background: #111827;");

    auto* leftLay = new QVBoxLayout(leftPanel);
    leftLay->setContentsMargins(0, 0, 0, 0);
    leftLay->setSpacing(0);

    // ── Left header ─────────────────────────────────────────────────────────
    auto* leftHeader = new QWidget;
    leftHeader->setFixedHeight(48);
    leftHeader->setStyleSheet(
        "background: #111827; border-bottom: 1px solid rgba(255,255,255,0.06);"
    );

    auto* leftHeaderLay = new QHBoxLayout(leftHeader);
    leftHeaderLay->setContentsMargins(14, 0, 10, 0);
    leftHeaderLay->setSpacing(6);

    auto* titleLbl = new QLabel;
    titleLbl->setText(
        "<span style='font-weight:900;font-size:12px;color:#b44aff;"
        "letter-spacing:3px;font-family:\"JetBrains Mono\",monospace;'>"
        "SHADOW MAIL</span>"
    );
    titleLbl->setTextFormat(Qt::RichText);
    leftHeaderLay->addWidget(titleLbl);
    leftHeaderLay->addStretch();

    m_syncLabel = new QLabel;
    m_syncLabel->setText(
        "<span style='font-family:\"JetBrains Mono\",monospace;font-size:9px;"
        "color:#ffb84d;letter-spacing:1px;'>SYNCING…</span>"
    );
    m_syncLabel->setTextFormat(Qt::RichText);
    m_syncLabel->hide();
    leftHeaderLay->addWidget(m_syncLabel);

    // Refresh button
    auto* refreshBtn = new QPushButton("⟳");
    refreshBtn->setFixedSize(28, 28);
    refreshBtn->setToolTip("Refresh inbox");
    refreshBtn->setStyleSheet(R"(
        QPushButton {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.10);
            color: #94a3b8;
            font-size: 15px;
            border-radius: 6px;
            padding: 0;
        }
        QPushButton:hover { background: rgba(255,255,255,0.11); color: #e2e8f0; }
        QPushButton:pressed { background: rgba(255,255,255,0.18); }
    )");
    connect(refreshBtn, &QPushButton::clicked, this, &MailPage::refresh);
    leftHeaderLay->addWidget(refreshBtn);

    m_composeBtn = new QPushButton("✉ COMPOSE");
    m_composeBtn->setStyleSheet(accentBtnStyle());
    connect(m_composeBtn, &QPushButton::clicked, this, &MailPage::toggleCompose);
    leftHeaderLay->addWidget(m_composeBtn);

    leftLay->addWidget(leftHeader);

    // ── Message list ────────────────────────────────────────────────────────
    m_msgList = new QListWidget;
    m_msgList->setStyleSheet(R"(
        QListWidget {
            background: #0d0f1a;
            border: none;
            outline: none;
        }
        QListWidget::item {
            border: none;
            border-bottom: 1px solid rgba(255,255,255,0.04);
            padding: 0px;
        }
        QListWidget::item:selected {
            background: rgba(180,74,255,0.10);
        }
        QListWidget::item:hover:!selected {
            background: rgba(255,255,255,0.03);
        }
        QScrollBar:vertical {
            background: #0d0f1a;
            width: 5px;
            border-radius: 2px;
        }
        QScrollBar::handle:vertical {
            background: #1e293b;
            border-radius: 2px;
            min-height: 20px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    )");
    m_msgList->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    m_msgList->setVerticalScrollMode(QAbstractItemView::ScrollPerPixel);
    m_msgList->setSpacing(0);
    connect(m_msgList, &QListWidget::itemClicked, this, &MailPage::onMessageClicked);
    leftLay->addWidget(m_msgList, 1);

    splitter->addWidget(leftPanel);

    // ═══════════════════════════════════════════════════════════════════════
    //  RIGHT PANEL
    // ═══════════════════════════════════════════════════════════════════════
    auto* rightPanel = new QWidget;
    rightPanel->setStyleSheet("background: #0d0f1a;");

    auto* rightLay = new QVBoxLayout(rightPanel);
    rightLay->setContentsMargins(0, 0, 0, 0);
    rightLay->setSpacing(0);

    // ── Body view ───────────────────────────────────────────────────────────
    m_bodyView = new QTextEdit;
    m_bodyView->setReadOnly(true);
    m_bodyView->setFrameShape(QFrame::NoFrame);
    m_bodyView->setStyleSheet(R"(
        QTextEdit {
            background: #060810;
            border: none;
            color: #e2e8f0;
            font-size: 13px;
            selection-background-color: rgba(180,74,255,0.30);
        }
        QScrollBar:vertical {
            background: #0d0f1a;
            width: 5px;
            border-radius: 2px;
        }
        QScrollBar::handle:vertical {
            background: #1e293b;
            border-radius: 2px;
            min-height: 20px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    )");
    // Empty state
    m_bodyView->setHtml(
        "<div style='padding:80px 40px;text-align:center;'>"
        "<p style='color:#334155;font-family:\"JetBrains Mono\",monospace;"
        "font-size:11px;letter-spacing:2px;margin:0;'>"
        "SELECT A MESSAGE TO READ</p></div>"
    );
    rightLay->addWidget(m_bodyView, 1);

    // ── Compose panel (hidden by default) ───────────────────────────────────
    m_composePanel = new QWidget;
    m_composePanel->setStyleSheet(
        "QWidget { background: #111827; border-top: 1px solid rgba(180,74,255,0.22); }"
    );
    m_composePanel->hide();

    auto* composeLay = new QVBoxLayout(m_composePanel);
    composeLay->setContentsMargins(20, 12, 20, 14);
    composeLay->setSpacing(8);

    // Compose title
    auto* composeTitleRow = new QHBoxLayout;
    auto* composeTitleLbl = new QLabel;
    composeTitleLbl->setText(
        "<span style='font-family:\"JetBrains Mono\",monospace;font-size:10px;"
        "font-weight:700;color:#b44aff;letter-spacing:2px;'>✉ COMPOSE MESSAGE</span>"
    );
    composeTitleLbl->setTextFormat(Qt::RichText);
    composeTitleRow->addWidget(composeTitleLbl);
    composeTitleRow->addStretch();
    composeLay->addLayout(composeTitleRow);

    // To row
    auto* toRow = new QHBoxLayout;
    toRow->setSpacing(10);
    auto* toLbl = new QLabel("TO");
    toLbl->setFixedWidth(58);
    toLbl->setStyleSheet(
        "color:#475569;font-family:'JetBrains Mono',monospace;font-size:10px;"
        "letter-spacing:1.5px;background:transparent;"
    );
    toRow->addWidget(toLbl);
    m_toField = new QLineEdit;
    m_toField->setPlaceholderText("recipient@example.com");
    m_toField->setStyleSheet(fieldStyle());
    toRow->addWidget(m_toField, 1);
    composeLay->addLayout(toRow);

    // Subject row
    auto* subjectRow = new QHBoxLayout;
    subjectRow->setSpacing(10);
    auto* subjectLbl = new QLabel("SUBJECT");
    subjectLbl->setFixedWidth(58);
    subjectLbl->setStyleSheet(
        "color:#475569;font-family:'JetBrains Mono',monospace;font-size:10px;"
        "letter-spacing:1.5px;background:transparent;"
    );
    subjectRow->addWidget(subjectLbl);
    m_subjectField = new QLineEdit;
    m_subjectField->setPlaceholderText("Message subject");
    m_subjectField->setStyleSheet(fieldStyle());
    subjectRow->addWidget(m_subjectField, 1);
    composeLay->addLayout(subjectRow);

    // Body field
    m_bodyField = new QPlainTextEdit;
    m_bodyField->setPlaceholderText("Write your message…");
    m_bodyField->setFixedHeight(110);
    m_bodyField->setStyleSheet(fieldStyle());
    composeLay->addWidget(m_bodyField);

    // Buttons + status row
    auto* btnRow = new QHBoxLayout;
    btnRow->setSpacing(8);

    m_sendBtn = new QPushButton("SEND");
    m_sendBtn->setStyleSheet(accentBtnStyle());
    connect(m_sendBtn, &QPushButton::clicked, this, &MailPage::sendMail);
    btnRow->addWidget(m_sendBtn);

    auto* cancelBtn = new QPushButton("CANCEL");
    cancelBtn->setStyleSheet(ghostBtnStyle());
    connect(cancelBtn, &QPushButton::clicked, this, [this]() {
        m_composePanel->hide();
        m_composeBtn->setText("✉ COMPOSE");
        m_toField->clear();
        m_subjectField->clear();
        m_bodyField->clear();
        m_sendStatusLabel->hide();
    });
    btnRow->addWidget(cancelBtn);

    btnRow->addStretch();

    m_sendStatusLabel = new QLabel;
    m_sendStatusLabel->setStyleSheet(
        "font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:1px;"
        "background:transparent;"
    );
    m_sendStatusLabel->hide();
    btnRow->addWidget(m_sendStatusLabel);

    composeLay->addLayout(btnRow);

    rightLay->addWidget(m_composePanel);

    splitter->addWidget(rightPanel);

    // Initial split: 280 for left, rest for right
    splitter->setSizes({280, 700});
    splitter->setStretchFactor(0, 0);
    splitter->setStretchFactor(1, 1);
}

// ── Message list helpers ──────────────────────────────────────────────────────

QWidget* MailPage::createMessageWidget(const QJsonObject& msg)
{
    const bool   isRead   = msg.value("read").toBool(true);
    const QString from    = msg.value("from").toString();
    const QString subject = msg.value("subject").toString();
    const QString preview = msg.value("preview").toString();
    const QString date    = msg.value("short_date").toString(msg.value("date").toString());

    auto* container = new QWidget;
    container->setAttribute(Qt::WA_TranslucentBackground);

    auto* outerLay = new QHBoxLayout(container);
    outerLay->setContentsMargins(0, 0, 0, 0);
    outerLay->setSpacing(0);

    // Accent left bar for unread messages
    if (!isRead) {
        auto* bar = new QWidget;
        bar->setFixedWidth(3);
        bar->setStyleSheet("background: #b44aff;");
        outerLay->addWidget(bar);
    }

    auto* inner = new QWidget;
    inner->setStyleSheet("background: transparent;");
    auto* innerLay = new QVBoxLayout(inner);
    innerLay->setContentsMargins(isRead ? 14 : 11, 9, 10, 9);
    innerLay->setSpacing(3);

    // Row 1: sender + date
    auto* topRow = new QHBoxLayout;
    topRow->setSpacing(6);

    auto* fromLbl = new QLabel;
    {
        // Elide long addresses
        QString display = from.length() > 28 ? from.left(25) + "…" : from;
        fromLbl->setText(display.toHtmlEscaped());
    }
    fromLbl->setStyleSheet(
        isRead
        ? "color:#475569;font-size:12px;font-weight:600;background:transparent;"
        : "color:#e2e8f0;font-size:12px;font-weight:700;background:transparent;"
    );
    topRow->addWidget(fromLbl, 1);

    auto* dateLbl = new QLabel;
    {
        // Show first 10 chars (YYYY-MM-DD portion) or raw if short
        QString display = date.length() > 10 ? date.left(10) : date;
        dateLbl->setText(display);
    }
    dateLbl->setStyleSheet(
        "color:#334155;font-family:'JetBrains Mono',monospace;font-size:9px;"
        "background:transparent;"
    );
    dateLbl->setAlignment(Qt::AlignRight | Qt::AlignVCenter);
    topRow->addWidget(dateLbl);

    innerLay->addLayout(topRow);

    // Row 2: subject
    auto* subjectLbl = new QLabel;
    {
        QString display = subject.length() > 42 ? subject.left(39) + "…" : subject;
        subjectLbl->setText(display.toHtmlEscaped());
    }
    subjectLbl->setStyleSheet(
        isRead
        ? "color:#475569;font-size:11px;background:transparent;"
        : "color:#cbd5e1;font-size:11px;font-weight:600;background:transparent;"
    );
    innerLay->addWidget(subjectLbl);

    // Row 3: preview
    auto* previewLbl = new QLabel;
    {
        QString display = preview.length() > 55 ? preview.left(52) + "…" : preview;
        previewLbl->setText(display.toHtmlEscaped());
    }
    previewLbl->setStyleSheet(
        "color:#334155;font-size:10px;background:transparent;"
    );
    innerLay->addWidget(previewLbl);

    outerLay->addWidget(inner, 1);

    return container;
}

void MailPage::loadMessages(const QJsonArray& messages)
{
    m_msgList->clear();

    if (messages.isEmpty()) {
        // Empty-state placeholder item
        auto* item = new QListWidgetItem(m_msgList);
        item->setFlags(Qt::NoItemFlags);
        item->setSizeHint(QSize(0, 80));

        auto* emptyW = new QWidget;
        emptyW->setStyleSheet("background: transparent;");
        auto* emptyLay = new QVBoxLayout(emptyW);
        emptyLay->setAlignment(Qt::AlignCenter);
        auto* emptyLbl = new QLabel("NO MESSAGES");
        emptyLbl->setStyleSheet(
            "color:#334155;font-family:'JetBrains Mono',monospace;"
            "font-size:10px;letter-spacing:2px;background:transparent;"
        );
        emptyLbl->setAlignment(Qt::AlignCenter);
        emptyLay->addWidget(emptyLbl);
        m_msgList->setItemWidget(item, emptyW);
        return;
    }

    for (const QJsonValue& val : messages) {
        const QJsonObject row = val.toObject();
        const QDateTime when = QDateTime::fromString(row.value("received_at").toString(), Qt::ISODate);
        QJsonObject msg{
            {"id",      row.value("id")},
            {"from",    row.value("from_addr")},
            {"to",      row.value("to_addr")},
            {"subject", row.value("subject").toString().isEmpty()
                            ? QStringLiteral("(no subject)") : row.value("subject").toString()},
            {"date",    when.isValid() ? when.toLocalTime().toString("MMM d, hh:mm") : QString()},
            // The list column is narrow: time for today's mail, otherwise just the day.
            {"short_date", !when.isValid() ? QString()
                           : when.toLocalTime().date() == QDate::currentDate()
                               ? when.toLocalTime().toString("hh:mm")
                               : when.toLocalTime().toString("MMM d")},
            {"read",    row.value("is_read").toBool(true)},
        };

        auto* item = new QListWidgetItem(m_msgList);
        item->setData(Qt::UserRole, QVariant::fromValue(msg));
        item->setSizeHint(QSize(0, 74));
        item->setFlags(Qt::ItemIsSelectable | Qt::ItemIsEnabled);

        m_msgList->setItemWidget(item, createMessageWidget(msg));
    }

    m_syncLabel->hide();
}

// ── Slots ─────────────────────────────────────────────────────────────────────

void MailPage::refresh()
{
    auto* api = ApiClient::instance();
    if (!api || !api->isAuthenticated()) return;
    m_syncLabel->show();
    api->get("/v1/mail/inbox?limit=50", this, [this](bool ok, QJsonDocument doc, int status) {
        m_syncLabel->hide();
        if (!ok) {
            m_bodyView->setHtml(QString("<div style='padding:24px;color:#f43f5e;font-family:\"JetBrains Mono\";"
                                        "font-size:11px;'>Couldn't load mail (HTTP %1).</div>").arg(status));
            return;
        }
        loadMessages(doc.object().value("messages").toArray());
    });
}

void MailPage::onMessageClicked(QListWidgetItem* item)
{
    if (!item) return;

    const QJsonObject msg = item->data(Qt::UserRole).value<QJsonObject>();
    const QString id = msg.value("id").toString();
    if (id.isEmpty()) return;

    auto* api = ApiClient::instance();
    if (!api) return;
    m_openId = id;
    showMessage(msg, QStringLiteral("Loading…"));
    // Opening a message also marks it read on the server.
    api->get("/v1/mail/" + QUrl::toPercentEncoding(id), this,
             [this, msg, id](bool ok, QJsonDocument doc, int status) {
        if (id != m_openId) return;   // the user opened another message meanwhile
        if (!ok) { showMessage(msg, QString("Couldn't load this message (HTTP %1).").arg(status)); return; }
        const QJsonObject full = doc.object();
        QString text = full.value("body_text").toString();
        if (text.isEmpty() && !full.value("body_html").toString().isEmpty())
            text = QTextDocumentFragment::fromHtml(full.value("body_html").toString()).toPlainText();
        showMessage(msg, text.isEmpty() ? QStringLiteral("(empty message)") : text);
    });
}

void MailPage::showMessage(const QJsonObject& msg, const QString& body)
{
    const QString from    = msg.value("from").toString().toHtmlEscaped();
    const QString date    = msg.value("date").toString().toHtmlEscaped();
    const QString subject = msg.value("subject").toString().toHtmlEscaped();
    const QString bodyHtml = body
                               .toHtmlEscaped()
                               .replace(QChar('\n'), QLatin1String("<br>"));

    QString html;
    html += "<div style='padding:24px 28px;background:#060810;'>";

    // Header table
    html += "<table style='border-collapse:collapse;margin-bottom:18px;'>";

    auto row = [](const QString& label, const QString& value, const QString& color) -> QString {
        return QString(
            "<tr>"
            "<td style='color:#475569;font-family:\"JetBrains Mono\",monospace;"
            "font-size:9px;letter-spacing:2px;padding:3px 20px 3px 0;"
            "vertical-align:top;white-space:nowrap;'>%1</td>"
            "<td style='color:%2;font-size:12px;padding:3px 0;'>%3</td>"
            "</tr>"
        ).arg(label, color, value);
    };

    html += row("FROM",    from,    "#e2e8f0");
    html += row("DATE",    date,    "#94a3b8");
    html += row("SUBJECT", subject, "#e2e8f0");

    html += "</table>";

    // Divider
    html += "<div style='height:1px;background:rgba(255,255,255,0.06);margin-bottom:20px;'></div>";

    // Body
    html += "<div style='color:#cbd5e1;font-size:13px;line-height:1.75;"
            "font-family:Inter,Outfit,sans-serif;'>" + bodyHtml + "</div>";

    html += "</div>";

    m_bodyView->setHtml(html);
}

void MailPage::toggleCompose()
{
    if (m_composePanel->isVisible()) {
        m_composePanel->hide();
        m_composeBtn->setText("✉ COMPOSE");
        m_sendStatusLabel->hide();
    } else {
        m_composePanel->show();
        m_composeBtn->setText("✕ CLOSE");
        m_toField->setFocus();
    }
}

void MailPage::sendMail()
{
    if (m_sending) return;

    const QString to      = m_toField->text().trimmed();
    const QString subject = m_subjectField->text().trimmed();
    const QString body    = m_bodyField->toPlainText().trimmed();

    if (to.isEmpty() || subject.isEmpty() || body.isEmpty()) {
        showSendStatus("Fill in all fields", false);
        return;
    }

    m_sending = true;
    setComposeEnabled(false);
    showSendStatus("SENDING…", true);  // accent-colored while in-flight

    auto* api = ApiClient::instance();
    if (!api) { finishSend(false, "Not signed in"); return; }
    api->post("/v1/mail/send", QJsonObject{{"to", to}, {"subject", subject}, {"text", body}}, this,
              [this](bool ok, QJsonDocument doc, int status) {
        const QString err = doc.object().value("error").toString();
        finishSend(ok, err.isEmpty() ? QString("HTTP %1").arg(status) : err);
    });
}

void MailPage::finishSend(bool ok, const QString& error)
{
    m_sending = false;
    setComposeEnabled(true);
    if (!ok) { showSendStatus("ERROR: " + error, false); return; }
    showSendStatus("✓ MESSAGE SENT", true);
    m_toField->clear();
    m_subjectField->clear();
    m_bodyField->clear();
    QTimer::singleShot(1200, this, [this]() {
        m_composePanel->hide();
        m_composeBtn->setText("✉ COMPOSE");
        m_sendStatusLabel->hide();
    });
    refresh();
}

// ── Private helpers ───────────────────────────────────────────────────────────

void MailPage::setComposeEnabled(bool on)
{
    m_toField->setEnabled(on);
    m_subjectField->setEnabled(on);
    m_bodyField->setEnabled(on);
    m_sendBtn->setEnabled(on);
    m_sendBtn->setText(on ? "SEND" : "SENDING…");
}

void MailPage::showSendStatus(const QString& text, bool success)
{
    const QString color = success ? "#00ff9d" : "#f43f5e";
    m_sendStatusLabel->setText(
        QString("<span style='color:%1;font-family:\"JetBrains Mono\",monospace;"
                "font-size:10px;letter-spacing:1px;font-weight:700;'>%2</span>")
            .arg(color, text.toHtmlEscaped())
    );
    m_sendStatusLabel->setTextFormat(Qt::RichText);
    m_sendStatusLabel->show();
}
