#pragma once
#include <QWidget>
#include <QLabel>

class MiniStat : public QWidget {
    Q_OBJECT
public:
    explicit MiniStat(const QString& title, const QString& value = "—",
                      const QString& accent = "#00d4ff", QWidget* parent = nullptr);

    void setValue(const QString& val);

private:
    QLabel*  m_valLabel;
    QString  m_accent;
};
