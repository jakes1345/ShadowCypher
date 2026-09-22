#include "AiPage.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QScrollBar>
#include <QKeyEvent>
#include <QDateTime>

// Maps display name → Python team key
static const QVector<QPair<QString,QString>> TEAMS = {
    {"Shadow AI",        "shadowai"},
    {"Red Phantom",      "adversary"},
    {"Blue Sentinel",    "blue_team"},
    {"Purple Phantom",   "purple_team"},
    {"Ghost Recon",      "osint"},
    {"Zero · Exploit",   "exploit_dev"},
    {"Specter · Malware","malware_analyst"},
    {"Wrath · Web",      "web_security"},
    {"Nebula · Cloud",   "cloud_security"},
    {"Spectre · Net",    "network_security"},
    {"Chronicle · DFIR", "forensics"},
    {"Forge · DevSecOps","devops"},
    {"Shadow Commander", "commander"},
    {"Shadow Oracle",    "general"},
};

AiPage::AiPage(IpcClient* ipc, QWidget* parent) : QWidget(parent), m_ipc(ipc) {
    buildUi();
    if (m_ipc) {
        connect(m_ipc, &IpcClient::resultReady, this, &AiPage::onIpcResult);
        connect(m_ipc, &IpcClient::connected, this, [this]() {
            m_ipc->call("get_ai_model");
        });
    }
}

void AiPage::buildUi() {
    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(20, 14, 20, 14);
    lay->setSpacing(10);

    // ── Header row ──────────────────────────────────────────────────
    auto* header = new QHBoxLayout;
    auto* title = new QLabel;
    title->setText("<span style='font-weight:900;font-size:16px;color:#8b5cf6;"
                   "letter-spacing:2px;'>AI ASSISTANT</span>");
    title->setTextFormat(Qt::RichText);
    header->addWidget(title);

    // Team selector
    m_teamSelector = new QComboBox;
    for (const auto& pair : TEAMS)
        m_teamSelector->addItem(pair.first, pair.second);
    m_teamSelector->setStyleSheet(R"(
        QComboBox {
            background: #111827; color: #8b5cf6;
            border: 1px solid rgba(139,92,246,0.35); border-radius: 6px;
            font-family: 'JetBrains Mono'; font-size: 10px;
            padding: 4px 10px; min-width: 150px;
        }
        QComboBox::drop-down { border: none; width: 18px; }
        QComboBox QAbstractItemView {
            background: #111827; color: #cbd5e1;
            border: 1px solid rgba(139,92,246,0.25);
            selection-background-color: rgba(139,92,246,0.2);
        }
    )");
    header->addWidget(m_teamSelector);
    header->addStretch();

    m_modelLabel = new QLabel("Model: connecting…");
    m_modelLabel->setStyleSheet("color: #475569; font-family: 'JetBrains Mono'; "
                                "font-size: 10px; letter-spacing: 1px;");
    header->addWidget(m_modelLabel);
    lay->addLayout(header);

    // ── Chat view ────────────────────────────────────────────────────
    m_chatView = new QTextEdit;
    m_chatView->setReadOnly(true);
    m_chatView->setStyleSheet(R"(
        QTextEdit {
            background: #060810; color: #cbd5e1;
            border: 1px solid rgba(255,255,255,0.06); border-radius: 10px;
            font-family: "Inter", sans-serif; font-size: 13px;
            padding: 12px;
        }
    )");
    lay->addWidget(m_chatView, 1);

    // ── Input row ────────────────────────────────────────────────────
    auto* inputRow = new QHBoxLayout;
    m_input = new QLineEdit;
    m_input->setPlaceholderText("Ask about network anomalies, CVEs, counter-intel findings…");
    m_input->setStyleSheet(R"(
        QLineEdit {
            background: #111827; color: #e2e8f0;
            border: 1px solid rgba(139,92,246,0.25); border-radius: 8px;
            font-size: 13px; padding: 10px 14px;
        }
        QLineEdit:focus { border-color: rgba(139,92,246,0.6); }
    )");
    connect(m_input, &QLineEdit::returnPressed, this, &AiPage::sendMessage);
    inputRow->addWidget(m_input, 1);

    m_sendBtn = new QPushButton("SEND");
    m_sendBtn->setStyleSheet(R"(
        QPushButton {
            background: rgba(139,92,246,0.15); border: 1px solid rgba(139,92,246,0.4);
            color: #8b5cf6; font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing: 1px;
            padding: 10px 20px; border-radius: 8px; font-weight: 700;
        }
        QPushButton:hover { background: rgba(139,92,246,0.25); }
        QPushButton:disabled { color: #334155; border-color: #1e293b; }
    )");
    connect(m_sendBtn, &QPushButton::clicked, this, &AiPage::sendMessage);
    inputRow->addWidget(m_sendBtn);
    lay->addLayout(inputRow);

    // Welcome message
    m_chatView->setHtml(
        "<div style='color:#334155;font-family:JetBrains Mono;font-size:11px;"
        "text-align:center;padding:40px 20px;'>"
        "SHADOW AI ASSISTANT<br><br>"
        "<span style='font-size:10px;color:#1e293b;'>"
        "Security-aware · Offline-capable via Ollama<br>"
        "Live network state injected into every query"
        "</span>"
        "</div>"
    );
}

QString AiPage::currentTeam() const {
    return m_teamSelector->currentData().toString();
}

void AiPage::sendMessage() {
    QString text = m_input->text().trimmed();
    if (text.isEmpty() || m_waiting) return;
    if (!m_ipc || !m_ipc->isConnected()) {
        appendMessage("SYSTEM", "Daemon not connected — AI requires daemon connection or direct Ollama setup.");
        return;
    }

    m_input->clear();
    appendMessage("YOU", text);
    setWaiting(true);
    m_chatReqId = m_ipc->call("ai_chat", {{"message", text}, {"team", currentTeam()}});
}

void AiPage::onIpcResult(int id, QJsonObject result) {
    if (id == m_chatReqId) {
        setWaiting(false);
        QString response = result.value("response").toString();
        if (response.isEmpty()) response = result.value("error").toString("No response from AI");
        appendMessage("SHADOW", response);
    }
    if (result.contains("model")) {
        m_modelLabel->setText("Model: " + result.value("model").toString());
    }
}

void AiPage::appendMessage(const QString& role, const QString& content) {
    QString ts   = QDateTime::currentDateTime().toString("HH:mm");
    QString roleColor = (role == "YOU") ? "#00d4ff"
                      : (role == "SHADOW") ? "#8b5cf6"
                      : "#334155";
    QString bg   = (role == "YOU") ? "rgba(0,212,255,0.04)" : "rgba(139,92,246,0.04)";

    QString teamBadge;
    if (role == "SHADOW") {
        teamBadge = QString(" <span style='color:#334155;font-size:9px;'>%1</span>")
                        .arg(m_teamSelector->currentText());
    }

    QString html = QString(
        "<div style='margin:6px 0;padding:10px 14px;background:%1;"
        "border-radius:8px;border-left:3px solid %2;'>"
        "<span style='color:%2;font-family:JetBrains Mono;font-size:10px;"
        "letter-spacing:1px;font-weight:700;'>%3</span>"
        "%6"
        "<span style='color:#334155;font-size:10px;margin-left:8px;'>%4</span>"
        "<div style='color:#cbd5e1;margin-top:6px;line-height:1.6;'>%5</div>"
        "</div>"
    ).arg(bg, roleColor, role, ts,
          content.toHtmlEscaped().replace("\n", "<br>"),
          teamBadge);

    m_chatView->append(html);
    m_chatView->verticalScrollBar()->setValue(m_chatView->verticalScrollBar()->maximum());
}

void AiPage::setWaiting(bool waiting) {
    m_waiting = waiting;
    m_sendBtn->setEnabled(!waiting);
    m_sendBtn->setText(waiting ? "…" : "SEND");
    m_input->setEnabled(!waiting);
    m_teamSelector->setEnabled(!waiting);
    if (waiting)
        appendMessage("SHADOW", "<span style='color:#334155;font-style:italic;'>Thinking…</span>");
}
