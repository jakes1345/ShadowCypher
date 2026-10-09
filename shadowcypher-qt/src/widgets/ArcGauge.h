#pragma once
#include <QWidget>
#include <QColor>

// QPainter-drawn arc gauge — direct Qt6 port of the Cairo ArcGauge in dashboard.py
class ArcGauge : public QWidget {
    Q_OBJECT
    Q_PROPERTY(double value READ value WRITE setValue NOTIFY valueChanged)

public:
    explicit ArcGauge(const QString& title, const QString& unit = "%",
                      const QColor& accent = QColor("#00ff9d"),
                      int size = 130, QWidget* parent = nullptr);

    double value() const { return m_value; }
    void setValue(double v, const QString& subtitle = {});

    QSize sizeHint() const override { return {m_size, m_size + 36}; }

signals:
    void valueChanged(double);

protected:
    void paintEvent(QPaintEvent*) override;

private:
    QString m_title;
    QString m_unit;
    QColor  m_accent;
    int     m_size;
    double  m_value = 0.0;
    QString m_subtitle;

    QColor escalatedColor() const;
};
