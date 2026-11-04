#include "CalendarPage.h"
#include "../api/ApiClient.h"
#include "../theme.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFormLayout>
#include <QSplitter>
#include <QMessageBox>
#include <QJsonArray>
#include <QTextCharFormat>
#include <QBrush>

namespace {
struct ColorOpt { const char* name; const char* hex; };
const ColorOpt kColors[] = {
    {"Violet", "#b44aff"}, {"Red", "#ef4444"}, {"Orange", "#f97316"},
    {"Green", "#22c55e"},  {"Blue", "#3b82f6"}, {"Teal", "#14b8a6"},
};

QString btnStyle(const QString& color) {
    return QString(
        "QPushButton { background:transparent; color:%1; border:1px solid %1; border-radius:6px;"
        " padding:6px 14px; font-weight:600; letter-spacing:1px; }"
        "QPushButton:hover { background:%1; color:#0d0f1a; }"
        "QPushButton:disabled { color:#475569; border-color:#475569; background:transparent; }").arg(color);
}

QString fieldStyle() {
    return QString("background:%1; color:%2; border:1px solid %3; border-radius:6px; padding:6px;")
        .arg(Theme::BG_BASE, Theme::TEXT_PRIMARY, Theme::BORDER);
}
}

CalendarPage::CalendarPage(QWidget* parent) : QWidget(parent) { buildUi(); }

QDateTime CalendarPage::parseIso(const QString& s) {
    return QDateTime::fromString(s, Qt::ISODate).toLocalTime();
}

QString CalendarPage::toIso(const QDateTime& dt) {
    return dt.toUTC().toString(Qt::ISODate);
}

void CalendarPage::buildUi() {
    auto* root = new QHBoxLayout(this);
    root->setContentsMargins(24, 20, 24, 20);
    root->setSpacing(18);

    // Left: month grid + day list
    auto* left = new QVBoxLayout;
    auto* title = new QLabel("SHADOW CALENDAR");
    title->setStyleSheet(QString("color:%1; font-size:18px; font-weight:700; letter-spacing:3px;")
                             .arg(Theme::TEXT_PRIMARY));
    left->addWidget(title);

    m_cal = new QCalendarWidget;
    m_cal->setGridVisible(false);
    m_cal->setVerticalHeaderFormat(QCalendarWidget::NoVerticalHeader);
    m_cal->setStyleSheet(QString(
        "QCalendarWidget QWidget { background:%1; color:%2; }"
        "QCalendarWidget QAbstractItemView:enabled { background:%1; color:%2;"
        " selection-background-color:%3; selection-color:#ffffff; }"
        "QCalendarWidget QAbstractItemView:disabled { color:%4; }"
        "QCalendarWidget QToolButton { color:%2; background:transparent; font-weight:600; }"
        "QCalendarWidget QToolButton:hover { color:%3; }")
        .arg(Theme::BG_SURFACE, Theme::TEXT_PRIMARY, Theme::ACCENT, Theme::TEXT_DIM));
    QTextCharFormat head;
    head.setForeground(QColor(Theme::TEXT_SECONDARY));
    head.setBackground(QColor(Theme::BG_BASE));
    m_cal->setHeaderTextFormat(head);
    QTextCharFormat weekend;
    weekend.setForeground(QColor(Theme::CRITICAL));
    m_cal->setWeekdayTextFormat(Qt::Saturday, weekend);
    m_cal->setWeekdayTextFormat(Qt::Sunday, weekend);
    left->addWidget(m_cal, 3);

    m_dayTitle = new QLabel;
    m_dayTitle->setStyleSheet(QString("color:%1; font-size:12px; letter-spacing:2px; font-weight:600;")
                                  .arg(Theme::TEXT_SECONDARY));
    left->addWidget(m_dayTitle);

    m_dayList = new QListWidget;
    m_dayList->setStyleSheet(QString(
        "QListWidget { background:%1; color:%2; border:1px solid %3; border-radius:8px; }"
        "QListWidget::item { padding:8px; }"
        "QListWidget::item:selected { background:rgba(180,74,255,0.18); }")
        .arg(Theme::BG_SURFACE, Theme::TEXT_PRIMARY, Theme::BORDER));
    left->addWidget(m_dayList, 2);
    root->addLayout(left, 3);

    // Right: editor
    auto* right = new QVBoxLayout;
    m_formTitle = new QLabel("NEW EVENT");
    m_formTitle->setStyleSheet(QString("color:%1; font-size:12px; letter-spacing:2px; font-weight:600;")
                                   .arg(Theme::TEXT_SECONDARY));
    right->addWidget(m_formTitle);

    auto* form = new QFormLayout;
    form->setLabelAlignment(Qt::AlignLeft);
    form->setSpacing(10);
    const QString lbl = QString("color:%1; font-size:11px; letter-spacing:1px;").arg(Theme::TEXT_SECONDARY);

    m_title = new QLineEdit;
    m_title->setMaxLength(200);
    m_title->setPlaceholderText("Title");
    m_title->setStyleSheet(fieldStyle());

    m_allDay = new QCheckBox("All day");
    m_allDay->setStyleSheet(QString(
        "QCheckBox { color:%1; }"
        "QCheckBox::indicator { width:16px; height:16px; border:1px solid %2; border-radius:4px; background:%3; }"
        "QCheckBox::indicator:checked { background:%4; border-color:%4; }")
        .arg(Theme::TEXT_PRIMARY, Theme::TEXT_SECONDARY, Theme::BG_BASE, Theme::ACCENT));

    m_start = new QDateTimeEdit;
    m_end = new QDateTimeEdit;
    for (auto* e : {m_start, m_end}) {
        e->setCalendarPopup(true);
        e->setDisplayFormat("yyyy-MM-dd HH:mm");
        e->setStyleSheet(fieldStyle());
    }

    m_color = new QComboBox;
    for (const auto& c : kColors) m_color->addItem(c.name, QString(c.hex));
    m_color->setStyleSheet(fieldStyle());

    m_location = new QLineEdit;
    m_location->setMaxLength(500);
    m_location->setStyleSheet(fieldStyle());

    m_desc = new QPlainTextEdit;
    m_desc->setStyleSheet(fieldStyle());
    m_desc->setFixedHeight(90);

    auto addRow = [&](const QString& name, QWidget* w) {
        auto* l = new QLabel(name);
        l->setStyleSheet(lbl);
        form->addRow(l, w);
    };
    addRow("TITLE", m_title);
    addRow("", m_allDay);
    addRow("STARTS", m_start);
    addRow("ENDS", m_end);
    addRow("COLOR", m_color);
    addRow("LOCATION", m_location);
    addRow("NOTES", m_desc);
    right->addLayout(form);

    auto* btns = new QHBoxLayout;
    auto* newBtn = new QPushButton("NEW");
    newBtn->setStyleSheet(btnStyle(Theme::CYAN));
    m_saveBtn = new QPushButton("SAVE");
    m_saveBtn->setStyleSheet(btnStyle(Theme::ACCENT));
    m_deleteBtn = new QPushButton("DELETE");
    m_deleteBtn->setStyleSheet(btnStyle(Theme::CRITICAL));
    btns->addWidget(newBtn);
    btns->addWidget(m_saveBtn);
    btns->addWidget(m_deleteBtn);
    btns->addStretch();
    right->addLayout(btns);

    m_status = new QLabel;
    m_status->setWordWrap(true);
    m_status->setStyleSheet(QString("color:%1; font-size:12px;").arg(Theme::TEXT_SECONDARY));
    right->addWidget(m_status);
    right->addStretch();
    root->addLayout(right, 2);

    connect(m_cal, &QCalendarWidget::selectionChanged, this, [this]() {
        refreshDayList();
        if (m_editingId.isEmpty()) clearForm(m_cal->selectedDate());
    });
    connect(m_cal, &QCalendarWidget::currentPageChanged, this, &CalendarPage::loadMonth);
    connect(m_dayList, &QListWidget::itemSelectionChanged, this, &CalendarPage::onEventPicked);
    connect(newBtn, &QPushButton::clicked, this, &CalendarPage::newEvent);
    connect(m_saveBtn, &QPushButton::clicked, this, &CalendarPage::saveEvent);
    connect(m_deleteBtn, &QPushButton::clicked, this, &CalendarPage::removeEvent);
    connect(m_allDay, &QCheckBox::toggled, this, &CalendarPage::onAllDayToggled);

    clearForm(m_cal->selectedDate());
    refreshDayList();
}

void CalendarPage::showEvent(QShowEvent* e) {
    QWidget::showEvent(e);
    if (!m_loadedOnce) {
        m_loadedOnce = true;
        loadMonth();
    }
}

void CalendarPage::setStatus(const QString& msg, bool error) {
    m_status->setStyleSheet(QString("color:%1; font-size:12px;")
                                .arg(error ? Theme::CRITICAL : Theme::TEXT_SECONDARY));
    m_status->setText(msg);
}

void CalendarPage::onAllDayToggled(bool on) {
    const QString fmt = on ? "yyyy-MM-dd" : "yyyy-MM-dd HH:mm";
    m_start->setDisplayFormat(fmt);
    m_end->setDisplayFormat(fmt);
}

void CalendarPage::loadMonth() {
    auto* api = ApiClient::instance();
    if (!api || !api->isAuthenticated()) {
        setStatus("Sign in to use Shadow Calendar.", true);
        return;
    }
    const QDate first(m_cal->yearShown(), m_cal->monthShown(), 1);
    const QDateTime from(first.addDays(-7), QTime(0, 0));
    const QDateTime to(first.addMonths(1).addDays(7), QTime(0, 0));
    const QString path = QString("/v1/calendar/events?from=%1&to=%2").arg(toIso(from), toIso(to));

    api->get(path, this, [this](bool ok, QJsonDocument doc, int status) {
        if (!ok) {
            setStatus(QString("Could not load events (HTTP %1)").arg(status), true);
            return;
        }
        m_events.clear();
        for (const auto& v : doc.object().value("events").toArray())
            m_events.append(v.toObject());
        applyHighlights();
        refreshDayList();
    });
}

void CalendarPage::applyHighlights() {
    m_cal->setDateTextFormat(QDate(), QTextCharFormat());
    QTextCharFormat fmt;
    fmt.setBackground(QColor(180, 74, 255, 70));
    fmt.setFontWeight(QFont::Bold);
    for (const auto& ev : m_events) {
        const QDate s = parseIso(ev.value("start_at").toString()).date();
        QDate e = parseIso(ev.value("end_at").toString()).date();
        if (e < s) e = s;
        if (s.daysTo(e) > 62) e = s.addDays(62);
        for (QDate d = s; d <= e; d = d.addDays(1))
            m_cal->setDateTextFormat(d, fmt);
    }
}

void CalendarPage::refreshDayList() {
    const QDate day = m_cal->selectedDate();
    m_dayTitle->setText(day.toString("dddd, d MMMM yyyy").toUpper());
    const QDateTime dayStart(day, QTime(0, 0));
    const QDateTime dayEnd = dayStart.addDays(1);

    QSignalBlocker block(m_dayList);
    m_dayList->clear();
    for (int i = 0; i < m_events.size(); ++i) {
        const QJsonObject& ev = m_events[i];
        const QDateTime s = parseIso(ev.value("start_at").toString());
        const QDateTime e = parseIso(ev.value("end_at").toString());
        if (!(s < dayEnd && e > dayStart)) continue;
        const QString when = ev.value("all_day").toBool() ? QString("All day") : s.toString("HH:mm");
        auto* item = new QListWidgetItem(when + "   " + ev.value("title").toString());
        item->setData(Qt::UserRole, i);
        item->setForeground(QColor(ev.value("color").toString("#b44aff")));
        m_dayList->addItem(item);
        if (ev.value("id").toString() == m_editingId) item->setSelected(true);
    }
}

void CalendarPage::onEventPicked() {
    const auto items = m_dayList->selectedItems();
    if (items.isEmpty()) return;
    const int idx = items.first()->data(Qt::UserRole).toInt();
    if (idx >= 0 && idx < m_events.size()) fillForm(m_events[idx]);
}

void CalendarPage::fillForm(const QJsonObject& ev) {
    m_editingId = ev.value("id").toString();
    m_formTitle->setText("EDIT EVENT");
    m_title->setText(ev.value("title").toString());
    const bool allDay = ev.value("all_day").toBool();
    m_allDay->setChecked(allDay);
    m_start->setDateTime(parseIso(ev.value("start_at").toString()));
    m_end->setDateTime(parseIso(ev.value("end_at").toString()));
    const int ci = m_color->findData(ev.value("color").toString());
    m_color->setCurrentIndex(ci >= 0 ? ci : 0);
    m_location->setText(ev.value("location").toString());
    m_desc->setPlainText(ev.value("description").toString());
    m_deleteBtn->setEnabled(true);
    setStatus({});
}

void CalendarPage::clearForm(const QDate& day) {
    m_editingId.clear();
    m_formTitle->setText("NEW EVENT");
    m_title->clear();
    m_allDay->setChecked(false);
    m_start->setDateTime(QDateTime(day, QTime(9, 0)));
    m_end->setDateTime(QDateTime(day, QTime(10, 0)));
    m_color->setCurrentIndex(0);
    m_location->clear();
    m_desc->clear();
    m_deleteBtn->setEnabled(false);
}

void CalendarPage::newEvent() {
    m_dayList->clearSelection();
    clearForm(m_cal->selectedDate());
    m_title->setFocus();
    setStatus({});
}

void CalendarPage::saveEvent() {
    auto* api = ApiClient::instance();
    if (!api || !api->isAuthenticated()) { setStatus("Sign in to use Shadow Calendar.", true); return; }

    const QString title = m_title->text().trimmed();
    if (title.isEmpty()) { setStatus("Give the event a title.", true); return; }

    QDateTime s = m_start->dateTime();
    QDateTime e = m_end->dateTime();
    if (m_allDay->isChecked()) {
        s = QDateTime(s.date(), QTime(0, 0, 0));
        e = QDateTime(e.date(), QTime(23, 59, 59));
    }
    if (e < s) { setStatus("The event can't end before it starts.", true); return; }

    QJsonObject body{
        {"title", title},
        {"start_at", toIso(s)},
        {"end_at", toIso(e)},
        {"all_day", m_allDay->isChecked()},
        {"color", m_color->currentData().toString()},
        {"location", m_location->text().trimmed()},
        {"description", m_desc->toPlainText().trimmed()},
    };

    auto done = [this](bool ok, QJsonDocument doc, int status) {
        if (!ok) {
            setStatus("Save failed: " + doc.object().value("error").toString(QString("HTTP %1").arg(status)), true);
            return;
        }
        const QDate d = m_cal->selectedDate();
        m_editingId.clear();
        clearForm(d);
        setStatus("Saved.");
        loadMonth();
    };

    if (m_editingId.isEmpty()) {
        api->post("/v1/calendar/events", body, this, done);
    } else {
        api->patch("/v1/calendar/events/" + m_editingId, body, this, done);
    }
}

void CalendarPage::removeEvent() {
    if (m_editingId.isEmpty()) return;
    if (QMessageBox::question(this, "Delete event",
            QString("Delete \"%1\"?").arg(m_title->text())) != QMessageBox::Yes) return;

    ApiClient::instance()->del("/v1/calendar/events/" + m_editingId, this,
        [this](bool ok, QJsonDocument, int status) {
        if (!ok) { setStatus(QString("Delete failed (HTTP %1)").arg(status), true); return; }
        clearForm(m_cal->selectedDate());
        setStatus("Deleted.");
        loadMonth();
    });
}
