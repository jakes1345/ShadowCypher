#include "DrivePage.h"
#include "../api/ApiClient.h"
#include "../theme.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QHeaderView>
#include <QFileDialog>
#include <QFileInfo>
#include <QFile>
#include <QDir>
#include <QMessageBox>
#include <QJsonObject>
#include <QDateTime>
#include <QStandardPaths>

namespace {
constexpr qint64 kMaxUploadBytes = 10 * 1024 * 1024;

QString btnStyle(const QString& color) {
    return QString(
        "QPushButton { background:transparent; color:%1; border:1px solid %1; border-radius:6px;"
        " padding:6px 14px; font-weight:600; letter-spacing:1px; }"
        "QPushButton:hover { background:%1; color:#0d0f1a; }"
        "QPushButton:disabled { color:#475569; border-color:#475569; background:transparent; }").arg(color);
}
}

DrivePage::DrivePage(QWidget* parent) : QWidget(parent) { buildUi(); }

void DrivePage::buildUi() {
    auto* root = new QVBoxLayout(this);
    root->setContentsMargins(24, 20, 24, 20);
    root->setSpacing(14);

    auto* head = new QHBoxLayout;
    auto* title = new QLabel("SHADOW DRIVE");
    title->setStyleSheet(QString("color:%1; font-size:18px; font-weight:700; letter-spacing:3px;")
                             .arg(Theme::TEXT_PRIMARY));
    m_usage = new QLabel;
    m_usage->setStyleSheet(QString("color:%1; font-size:12px;").arg(Theme::TEXT_SECONDARY));
    head->addWidget(title);
    head->addSpacing(12);
    head->addWidget(m_usage);
    head->addStretch();

    auto* refreshBtn = new QPushButton("REFRESH");
    refreshBtn->setStyleSheet(btnStyle(Theme::CYAN));
    auto* uploadBtn = new QPushButton("UPLOAD");
    uploadBtn->setStyleSheet(btnStyle(Theme::ACCENT));
    m_downloadBtn = new QPushButton("DOWNLOAD");
    m_downloadBtn->setStyleSheet(btnStyle(Theme::SUCCESS));
    m_deleteBtn = new QPushButton("DELETE");
    m_deleteBtn->setStyleSheet(btnStyle(Theme::CRITICAL));
    head->addWidget(refreshBtn);
    head->addWidget(uploadBtn);
    head->addWidget(m_downloadBtn);
    head->addWidget(m_deleteBtn);
    root->addLayout(head);

    m_table = new QTableWidget(0, 4);
    m_table->setHorizontalHeaderLabels({"NAME", "TYPE", "SIZE", "UPLOADED"});
    m_table->setSelectionBehavior(QAbstractItemView::SelectRows);
    m_table->setSelectionMode(QAbstractItemView::SingleSelection);
    m_table->setEditTriggers(QAbstractItemView::NoEditTriggers);
    m_table->setShowGrid(false);
    m_table->verticalHeader()->hide();
    m_table->horizontalHeader()->setSectionResizeMode(0, QHeaderView::Stretch);
    m_table->horizontalHeader()->setSectionResizeMode(1, QHeaderView::ResizeToContents);
    m_table->horizontalHeader()->setSectionResizeMode(2, QHeaderView::ResizeToContents);
    m_table->horizontalHeader()->setSectionResizeMode(3, QHeaderView::ResizeToContents);
    m_table->setStyleSheet(QString(
        "QTableWidget { background:%1; color:%2; border:1px solid %3; border-radius:8px; }"
        "QTableWidget::item { padding:8px; }"
        "QTableWidget::item:selected { background:rgba(180,74,255,0.18); color:%2; }"
        "QHeaderView::section { background:%4; color:%5; border:none; padding:8px;"
        " font-size:11px; letter-spacing:2px; }")
        .arg(Theme::BG_SURFACE, Theme::TEXT_PRIMARY, Theme::BORDER, Theme::BG_BASE, Theme::TEXT_SECONDARY));
    root->addWidget(m_table, 1);

    m_status = new QLabel;
    m_status->setStyleSheet(QString("color:%1; font-size:12px;").arg(Theme::TEXT_SECONDARY));
    root->addWidget(m_status);

    connect(refreshBtn, &QPushButton::clicked, this, &DrivePage::refresh);
    connect(uploadBtn, &QPushButton::clicked, this, &DrivePage::uploadFiles);
    connect(m_downloadBtn, &QPushButton::clicked, this, &DrivePage::downloadSelected);
    connect(m_deleteBtn, &QPushButton::clicked, this, &DrivePage::deleteSelected);
    connect(m_table, &QTableWidget::itemSelectionChanged, this, &DrivePage::updateButtons);
    connect(m_table, &QTableWidget::cellDoubleClicked, this, &DrivePage::downloadSelected);
    updateButtons();
}

void DrivePage::showEvent(QShowEvent* e) {
    QWidget::showEvent(e);
    if (!m_loadedOnce) {
        m_loadedOnce = true;
        refresh();
    }
}

void DrivePage::setStatus(const QString& msg, bool error) {
    m_status->setStyleSheet(QString("color:%1; font-size:12px;")
                                .arg(error ? Theme::CRITICAL : Theme::TEXT_SECONDARY));
    m_status->setText(msg);
}

void DrivePage::updateButtons() {
    bool has = !selectedKey().isEmpty();
    m_downloadBtn->setEnabled(has);
    m_deleteBtn->setEnabled(has);
}

QString DrivePage::selectedKey() const {
    auto rows = m_table->selectionModel()->selectedRows();
    if (rows.isEmpty()) return {};
    return m_table->item(rows.first().row(), 0)->data(Qt::UserRole).toString();
}

QString DrivePage::selectedName() const {
    auto rows = m_table->selectionModel()->selectedRows();
    if (rows.isEmpty()) return {};
    return m_table->item(rows.first().row(), 0)->text();
}

QString DrivePage::humanSize(qint64 b) {
    if (b < 1024) return QString::number(b) + " B";
    if (b < 1024 * 1024) return QString::number(b / 1024.0, 'f', 1) + " KB";
    return QString::number(b / (1024.0 * 1024.0), 'f', 1) + " MB";
}

QString DrivePage::mimeFor(const QString& fileName) {
    static const QHash<QString, QString> map = {
        {"jpg", "image/jpeg"}, {"jpeg", "image/jpeg"}, {"png", "image/png"},
        {"gif", "image/gif"}, {"webp", "image/webp"}, {"svg", "image/svg+xml"},
        {"pdf", "application/pdf"}, {"txt", "text/plain"}, {"md", "text/markdown"},
        {"zip", "application/zip"}, {"mp3", "audio/mpeg"}, {"ogg", "audio/ogg"},
        {"wav", "audio/wav"}, {"mp4", "video/mp4"}, {"webm", "video/webm"},
    };
    return map.value(QFileInfo(fileName).suffix().toLower());
}

void DrivePage::refresh() {
    auto* api = ApiClient::instance();
    if (!api || !api->isAuthenticated()) {
        setStatus("Sign in to use Shadow Drive.", true);
        return;
    }
    setStatus("Loading...");
    api->get("/v1/files", this, [this](bool ok, QJsonDocument doc, int status) {
        if (!ok) {
            setStatus(QString("Could not load files (HTTP %1)").arg(status), true);
            return;
        }
        QJsonObject o = doc.object();
        populate(o.value("files").toArray());
        m_usage->setText(QString("%1 used").arg(humanSize(qint64(o.value("total_bytes").toDouble()))));
        setStatus(o.value("truncated").toBool() ? "Showing the first 200 files." : QString());
    });
}

void DrivePage::populate(const QJsonArray& files) {
    m_table->setRowCount(0);
    for (const auto& v : files) {
        QJsonObject f = v.toObject();
        int r = m_table->rowCount();
        m_table->insertRow(r);
        auto* name = new QTableWidgetItem(f.value("name").toString());
        name->setData(Qt::UserRole, f.value("key").toString());
        auto* type = new QTableWidgetItem(f.value("type").toString());
        auto* size = new QTableWidgetItem(humanSize(qint64(f.value("size").toDouble())));
        QDateTime dt = QDateTime::fromString(f.value("uploaded_at").toString(), Qt::ISODate);
        auto* when = new QTableWidgetItem(dt.isValid() ? dt.toLocalTime().toString("yyyy-MM-dd HH:mm") : QString());
        type->setForeground(QColor(Theme::TEXT_SECONDARY));
        size->setForeground(QColor(Theme::TEXT_SECONDARY));
        when->setForeground(QColor(Theme::TEXT_SECONDARY));
        m_table->setItem(r, 0, name);
        m_table->setItem(r, 1, type);
        m_table->setItem(r, 2, size);
        m_table->setItem(r, 3, when);
    }
    updateButtons();
}

void DrivePage::uploadFiles() {
    auto* api = ApiClient::instance();
    if (!api || !api->isAuthenticated()) { setStatus("Sign in to use Shadow Drive.", true); return; }

    const QStringList paths = QFileDialog::getOpenFileNames(this, "Upload to Shadow Drive");
    if (paths.isEmpty()) return;

    auto pending = std::make_shared<int>(paths.size());
    auto failures = std::make_shared<QStringList>();
    auto finishOne = [this, pending, failures]() {
        if (--(*pending) > 0) return;
        if (failures->isEmpty()) setStatus("Upload complete.");
        else setStatus("Not uploaded: " + failures->join("; "), true);
        refresh();
    };

    setStatus("Uploading...");
    for (const QString& path : paths) {
        QFileInfo info(path);
        const QString mime = mimeFor(info.fileName());
        if (mime.isEmpty()) {
            failures->append(info.fileName() + " (type not supported)");
            finishOne();
            continue;
        }
        if (info.size() > kMaxUploadBytes) {
            failures->append(info.fileName() + " (over 10 MB)");
            finishOne();
            continue;
        }
        QFile f(path);
        if (!f.open(QIODevice::ReadOnly)) {
            failures->append(info.fileName() + " (unreadable)");
            finishOne();
            continue;
        }
        const QByteArray data = f.readAll();
        api->upload("/v1/files/upload", data, info.fileName(), mime, this,
                    [failures, name = info.fileName(), finishOne](bool ok, QJsonDocument doc, int status) {
            if (!ok) {
                QString why = doc.object().value("error").toString(QString("HTTP %1").arg(status));
                failures->append(name + " (" + why + ")");
            }
            finishOne();
        });
    }
}

void DrivePage::downloadSelected() {
    const QString key = selectedKey();
    if (key.isEmpty()) return;
    const QString name = selectedName();

    const QString dest = QFileDialog::getSaveFileName(
        this, "Save file",
        QDir(QStandardPaths::writableLocation(QStandardPaths::DownloadLocation)).filePath(name));
    if (dest.isEmpty()) return;

    setStatus("Downloading " + name + "...");
    ApiClient::instance()->getBytes("/v1/files/" + key, this,
        [this, dest, name](bool ok, QByteArray data, int status) {
        if (!ok) { setStatus(QString("Download failed (HTTP %1)").arg(status), true); return; }
        QFile out(dest);
        if (!out.open(QIODevice::WriteOnly) || out.write(data) != data.size()) {
            setStatus("Could not write " + dest, true);
            return;
        }
        setStatus("Saved " + name + " to " + dest);
    });
}

void DrivePage::deleteSelected() {
    const QString key = selectedKey();
    if (key.isEmpty()) return;
    const QString name = selectedName();
    if (QMessageBox::question(this, "Delete file",
            QString("Permanently delete \"%1\"?").arg(name)) != QMessageBox::Yes) return;

    ApiClient::instance()->del("/v1/files/" + key, this, [this](bool ok, QJsonDocument, int status) {
        if (!ok) { setStatus(QString("Delete failed (HTTP %1)").arg(status), true); return; }
        refresh();
    });
}
