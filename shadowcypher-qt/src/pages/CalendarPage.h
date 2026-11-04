#pragma once
#include <QWidget>
#include <QCalendarWidget>
#include <QListWidget>
#include <QLineEdit>
#include <QPlainTextEdit>
#include <QDateTimeEdit>
#include <QCheckBox>
#include <QComboBox>
#include <QPushButton>
#include <QLabel>
#include <QJsonObject>
#include <QVector>

class CalendarPage : public QWidget {
    Q_OBJECT
public:
    explicit CalendarPage(QWidget* parent = nullptr);

protected:
    void showEvent(QShowEvent* e) override;

private slots:
    void loadMonth();
    void refreshDayList();
    void onEventPicked();
    void newEvent();
    void saveEvent();
    void removeEvent();
    void onAllDayToggled(bool on);

private:
    QCalendarWidget* m_cal;
    QListWidget*     m_dayList;
    QLabel*          m_dayTitle;
    QLabel*          m_formTitle;
    QLineEdit*       m_title;
    QDateTimeEdit*   m_start;
    QDateTimeEdit*   m_end;
    QCheckBox*       m_allDay;
    QComboBox*       m_color;
    QLineEdit*       m_location;
    QPlainTextEdit*  m_desc;
    QPushButton*     m_saveBtn;
    QPushButton*     m_deleteBtn;
    QLabel*          m_status;

    QVector<QJsonObject> m_events;
    QString m_editingId;
    bool    m_loadedOnce = false;

    void buildUi();
    void applyHighlights();
    void fillForm(const QJsonObject& ev);
    void clearForm(const QDate& day);
    void setStatus(const QString& msg, bool error = false);
    static QDateTime parseIso(const QString& s);
    static QString toIso(const QDateTime& dt);
};
