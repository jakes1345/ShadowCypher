#include "ShadowScriptPage.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QSplitter>
#include <QDir>
#include <QFile>
#include <QTextStream>
#include <QListWidgetItem>
#include <QJsonObject>
#include <QStandardPaths>
#include <QCoreApplication>

QString ShadowScriptPage::missionDir() {
    // Check common locations
    for (const QString& d : {
            "/opt/shadowcypher/shadowscript/missions",
            QDir::homePath() + "/.local/share/shadowcypher/missions",
            QString(QCoreApplication::applicationDirPath()) + "/../shadowscript/missions",
        }) {
        if (QDir(d).exists()) return d;
    }
    return {};
}

ShadowScriptPage::ShadowScriptPage(IpcClient* ipc, QWidget* parent)
    : QWidget(parent), m_ipc(ipc)
{
    buildUi();
    scanLocalMissions();
    if (m_ipc) {
        connect(m_ipc, &IpcClient::resultReady, this, &ShadowScriptPage::onIpcResult);
        connect(m_ipc, &IpcClient::connected, this, &ShadowScriptPage::loadMissions);
    }
}

void ShadowScriptPage::buildUi() {
    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(20, 14, 20, 14);
    lay->setSpacing(10);

    // ── Header ──
    auto* header = new QHBoxLayout;
    auto* title = new QLabel;
    title->setText("<span style='font-weight:900;font-size:16px;color:#10b981;letter-spacing:2px;'>SHADOWSCRIPT</span>");
    title->setTextFormat(Qt::RichText);
    header->addWidget(title);
    header->addStretch();

    m_statusLabel = new QLabel("IDLE");
    m_statusLabel->setStyleSheet("color: #334155; font-family: 'JetBrains Mono'; font-size: 10px; letter-spacing: 2px;");
    header->addWidget(m_statusLabel);
    lay->addLayout(header);

    // ── Main splitter ──
    auto* splitter = new QSplitter(Qt::Horizontal);
    splitter->setStyleSheet("QSplitter::handle { background: rgba(255,255,255,0.05); width: 1px; }");

    // Left: mission list
    auto* leftPanel = new QWidget;
    auto* leftLay   = new QVBoxLayout(leftPanel);
    leftLay->setContentsMargins(0, 0, 8, 0);
    leftLay->setSpacing(6);
    auto* listLbl = new QLabel("<span style='font-weight:800;color:#94a3b8;font-size:11px;letter-spacing:2px;'>MISSIONS</span>");
    listLbl->setTextFormat(Qt::RichText);
    leftLay->addWidget(listLbl);

    m_missionList = new QListWidget;
    m_missionList->setStyleSheet(R"(
        QListWidget {
            background: #060810; border: 1px solid rgba(255,255,255,0.06);
            border-radius: 8px; color: #94a3b8; font-family: 'JetBrains Mono'; font-size: 12px;
        }
        QListWidget::item { padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.03); }
        QListWidget::item:selected { background: rgba(16,185,129,0.1); color: #10b981; }
        QListWidget::item:hover { background: rgba(255,255,255,0.03); }
    )");
    connect(m_missionList, &QListWidget::itemClicked, this, &ShadowScriptPage::onMissionSelected);
    leftLay->addWidget(m_missionList, 1);

    // Run/Stop buttons
    auto* btnRow = new QHBoxLayout;
    m_runBtn = new QPushButton("▶ RUN");
    m_runBtn->setEnabled(false);
    m_runBtn->setStyleSheet(R"(
        QPushButton {
            background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.35);
            color: #10b981; font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing: 1px;
            padding: 7px 16px; border-radius: 4px; font-weight: 700;
        }
        QPushButton:hover { background: rgba(16,185,129,0.2); }
        QPushButton:disabled { color: #334155; border-color: #1e293b; }
    )");
    connect(m_runBtn, &QPushButton::clicked, this, &ShadowScriptPage::runMission);
    btnRow->addWidget(m_runBtn);

    m_stopBtn = new QPushButton("■ STOP");
    m_stopBtn->setEnabled(false);
    m_stopBtn->setStyleSheet(R"(
        QPushButton {
            background: rgba(244,63,94,0.1); border: 1px solid rgba(244,63,94,0.35);
            color: #f43f5e; font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing: 1px;
            padding: 7px 16px; border-radius: 4px;
        }
        QPushButton:hover { background: rgba(244,63,94,0.2); }
        QPushButton:disabled { color: #334155; border-color: #1e293b; }
    )");
    connect(m_stopBtn, &QPushButton::clicked, this, &ShadowScriptPage::stopMission);
    btnRow->addWidget(m_stopBtn);
    leftLay->addLayout(btnRow);
    splitter->addWidget(leftPanel);

    // Right: editor + output
    auto* rightPanel = new QWidget;
    auto* rightLay   = new QVBoxLayout(rightPanel);
    rightLay->setContentsMargins(8, 0, 0, 0);
    rightLay->setSpacing(6);

    auto* edLbl = new QLabel("<span style='font-weight:800;color:#94a3b8;font-size:11px;letter-spacing:2px;'>MISSION SOURCE</span>");
    edLbl->setTextFormat(Qt::RichText);
    rightLay->addWidget(edLbl);

    m_editor = new QPlainTextEdit;
    m_editor->setStyleSheet(R"(
        QPlainTextEdit {
            background: #060810; color: #10b981; border: 1px solid rgba(16,185,129,0.15);
            border-radius: 8px; font-family: 'JetBrains Mono'; font-size: 12px; padding: 8px;
        }
    )");
    m_editor->setPlaceholderText("# Select a mission from the list, or write custom ShadowScript here…\n\nVAR target = \"192.168.1.1\"\nSCAN(1-1024)\nAI(\"Triage these ports: $LAST\")");
    rightLay->addWidget(m_editor, 1);

    auto* outLbl = new QLabel("<span style='font-weight:800;color:#94a3b8;font-size:11px;letter-spacing:2px;'>OUTPUT</span>");
    outLbl->setTextFormat(Qt::RichText);
    rightLay->addWidget(outLbl);

    m_output = new TacticalTerminal(this);
    m_output->setMinimumHeight(180);
    rightLay->addWidget(m_output);

    splitter->addWidget(rightPanel);
    splitter->setSizes({240, 760});
    lay->addWidget(splitter, 1);
}

void ShadowScriptPage::scanLocalMissions() {
    m_missionList->clear();
    QString dir = missionDir();
    if (dir.isEmpty()) {
        m_output->log("Mission directory not found — run shadowcypher from source or ShadowOS", "WARNING");
        return;
    }
    QDir d(dir);
    for (const QString& f : d.entryList({"*.shadow"}, QDir::Files, QDir::Name)) {
        auto* item = new QListWidgetItem("  " + f.chopped(7)); // strip .shadow
        item->setData(Qt::UserRole, dir + "/" + f);
        m_missionList->addItem(item);
    }
    m_output->log(QString("Found %1 mission(s) in %2").arg(m_missionList->count()).arg(dir), "SYSTEM");
}

void ShadowScriptPage::loadMissions() {
    if (m_ipc && m_ipc->isConnected())
        m_ipc->call("list_missions");
}

void ShadowScriptPage::onMissionSelected(QListWidgetItem* item) {
    QString path = item->data(Qt::UserRole).toString();
    if (path.isEmpty()) return;

    QFile f(path);
    if (f.open(QIODevice::ReadOnly | QIODevice::Text)) {
        m_editor->setPlainText(QTextStream(&f).readAll());
        f.close();
    }
    m_currentMission = item->text().trimmed();
    m_runBtn->setEnabled(!m_running);
    m_output->log("Loaded: " + m_currentMission, "INFO");
}

void ShadowScriptPage::runMission() {
    if (m_running || m_currentMission.isEmpty()) return;
    if (!m_ipc || !m_ipc->isConnected()) {
        m_output->log("Daemon not connected — cannot run mission", "WARNING");
        return;
    }
    setRunningState(true);
    m_output->log("▶ Running: " + m_currentMission, "SYSTEM");
    m_runReqId = m_ipc->call("run_mission", {
        {"name", m_currentMission},
        {"source", m_editor->toPlainText()}
    });
}

void ShadowScriptPage::stopMission() {
    if (!m_running) return;
    if (m_ipc && m_ipc->isConnected())
        m_stopReqId = m_ipc->call("stop_mission", {{"name", m_currentMission}});
    setRunningState(false);
    m_output->log("■ Mission stopped: " + m_currentMission, "WARNING");
}

void ShadowScriptPage::setRunningState(bool running) {
    m_running = running;
    m_runBtn->setEnabled(!running && !m_currentMission.isEmpty());
    m_stopBtn->setEnabled(running);
    m_statusLabel->setText(running ? "● RUNNING" : "IDLE");
    m_statusLabel->setStyleSheet(running
        ? "color: #10b981; font-family: 'JetBrains Mono'; font-size: 10px; letter-spacing: 2px;"
        : "color: #334155; font-family: 'JetBrains Mono'; font-size: 10px; letter-spacing: 2px;");
}

void ShadowScriptPage::onIpcResult(int id, QJsonObject result) {
    if (id == m_runReqId) {
        QString line = result.value("output").toString();
        QString level = result.value("level").toString("INFO");
        if (!line.isEmpty()) m_output->log(line, level);
        if (result.value("complete").toBool()) {
            setRunningState(false);
            m_output->log("Mission complete: " + m_currentMission, "SUCCESS");
        }
    }
}
