#include "DiskPage.h"
#include "../theme.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QFrame>
#include <QRadioButton>
#include <QScrollArea>
#include <QPushButton>
#include <QMessageBox>

DiskPage::DiskPage(InstallState* state, QWidget* parent)
    : QWidget(parent), m_state(state)
{
    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(48, 40, 48, 40);
    lay->setSpacing(16);

    auto* tag = new QLabel("STEP 01 — DISK");
    tag->setStyleSheet(QString("font-size:9px;font-weight:800;letter-spacing:5px;"
                               "color:%1;font-family:'JetBrains Mono',monospace;").arg(Theme::ACCENT));
    auto* title = new QLabel("Select Installation Disk");
    title->setStyleSheet("font-size:28px;font-weight:900;color:#E6EDF3;");
    auto* sub = new QLabel("The entire disk will be erased and reformatted with a new partition layout.");
    sub->setStyleSheet(QString("font-size:13px;color:%1;").arg(Theme::TEXT_SEC));
    sub->setWordWrap(true);

    auto* danger = new QLabel(
        "  ◬  ALL DATA on the selected disk will be permanently destroyed."
    );
    danger->setStyleSheet(QString(
        "font-size:12px;color:%1;"
        "background:rgba(248,113,113,0.07);"
        "border:1px solid rgba(248,113,113,0.32);"
        "border-radius:7px;padding:10px 14px;"
    ).arg(Theme::DANGER));

    auto* divider = new QFrame;
    divider->setFrameShape(QFrame::HLine);
    divider->setStyleSheet("border: none; border-top: 1px solid rgba(0,224,164,0.12);");

    m_group    = new QButtonGroup(this);
    m_diskList = new QVBoxLayout;
    m_diskList->setSpacing(8);

    auto* scroll = new QScrollArea;
    scroll->setWidgetResizable(true);
    scroll->setFrameShape(QFrame::NoFrame);
    auto* inner = new QWidget;
    inner->setLayout(m_diskList);
    scroll->setWidget(inner);

    auto* refresh_btn = new QPushButton("⟳  Refresh disk list");
    refresh_btn->setStyleSheet(QString(
        "QPushButton { background:transparent; border:1px solid %1;"
        " border-radius:6px; padding:6px 16px; color:%1; font-size:11px; }"
        "QPushButton:hover { background:rgba(0,224,164,0.08); }"
    ).arg(Theme::TEXT_SEC));
    connect(refresh_btn, &QPushButton::clicked, this, &DiskPage::refresh);

    auto* layout_note = new QLabel(
        "Partition layout: 512 MiB FAT32 (EFI) + Btrfs root with subvolumes @, @home, @snapshots"
    );
    layout_note->setStyleSheet(QString("font-size:11px;color:%1;").arg(Theme::TEXT_DIM));

    lay->addWidget(tag);
    lay->addWidget(title);
    lay->addWidget(sub);
    lay->addWidget(danger);
    lay->addWidget(divider);
    lay->addWidget(scroll, 1);
    lay->addWidget(refresh_btn);
    lay->addWidget(layout_note);

    refresh();
}

void DiskPage::refresh() {
    // Clear existing buttons
    QLayoutItem* item;
    while ((item = m_diskList->takeAt(0)) != nullptr) {
        delete item->widget();
        delete item;
    }
    m_group->buttons().isEmpty(); // force group update

    const auto disks = DiskUtil::listDisks();
    if (disks.isEmpty()) {
        auto* empty = new QLabel("No disks found. Check lsblk in a terminal.");
        empty->setStyleSheet(QString("color:%1;").arg(Theme::TEXT_SEC));
        m_diskList->addWidget(empty);
        return;
    }

    for (const auto& d : disks) {
        auto* card = new QWidget;
        card->setStyleSheet(QString(
            "QWidget { background:%1; border:1px solid %2;"
            " border-radius:10px; padding:12px 16px; }"
        ).arg(Theme::BG_SURFACE, Theme::BORDER_DIM));

        auto* cl   = new QHBoxLayout(card);
        cl->setContentsMargins(12, 10, 12, 10);

        auto* rb = new QRadioButton;
        rb->setStyleSheet(QString(
            "QRadioButton::indicator { width:16px; height:16px; border-radius:8px;"
            " border:2px solid %1; background:transparent; }"
            "QRadioButton::indicator:checked { background:%2; border-color:%2; }"
        ).arg(Theme::TEXT_DIM, Theme::ACCENT));
        m_group->addButton(rb);

        QString icon = d.isNvme ? "⚡" : "🖴";
        auto* name = new QLabel(QString("%1 <b>%2</b>").arg(icon, d.path));
        name->setTextFormat(Qt::RichText);
        name->setStyleSheet("font-size:14px;color:#E6EDF3;");

        auto* size = new QLabel(d.size);
        size->setStyleSheet(QString("font-size:13px;color:%1;font-weight:600;").arg(Theme::ACCENT));

        auto* model = new QLabel(d.model);
        model->setStyleSheet(QString("font-size:11px;color:%1;").arg(Theme::TEXT_SEC));

        QString tran = d.transport.isEmpty() ? "" : QString(" [%1]").arg(d.transport);
        auto* trlbl = new QLabel(tran);
        trlbl->setStyleSheet(QString("font-size:10px;color:%1;").arg(Theme::TEXT_DIM));

        cl->addWidget(rb);
        cl->addWidget(name);
        cl->addWidget(model);
        cl->addStretch();
        cl->addWidget(trlbl);
        cl->addWidget(size);

        const QString path = d.path;
        connect(rb, &QRadioButton::toggled, this, [this, path, card](bool checked) {
            if (checked) {
                m_state->disk = path;
                card->setStyleSheet(QString(
                    "QWidget { background:%1; border:1px solid %2;"
                    " border-radius:10px; padding:12px 16px; }"
                ).arg(Theme::BG_CARD, Theme::ACCENT));
            }
        });

        if (m_state->disk == d.path) {
            rb->setChecked(true);
        }

        m_diskList->addWidget(card);
    }
    m_diskList->addStretch();
}

bool DiskPage::validate() {
    if (m_state->disk.isEmpty()) {
        QMessageBox::warning(this, "No Disk Selected",
                             "Please select a disk before continuing.");
        return false;
    }
    return true;
}
