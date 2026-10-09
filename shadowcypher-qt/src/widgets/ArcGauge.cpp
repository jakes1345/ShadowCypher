#include "ArcGauge.h"
#include <QPainter>
#include <QPainterPath>
#include <QtMath>

ArcGauge::ArcGauge(const QString& title, const QString& unit,
                   const QColor& accent, int size, QWidget* parent)
    : QWidget(parent), m_title(title), m_unit(unit), m_accent(accent), m_size(size)
{
    setMinimumSize(size, size + 36);
    setAttribute(Qt::WA_TranslucentBackground);
}

void ArcGauge::setValue(double v, const QString& subtitle) {
    m_value = qBound(0.0, v, 100.0);
    if (!subtitle.isNull()) m_subtitle = subtitle;
    emit valueChanged(m_value);
    update();
}

QColor ArcGauge::escalatedColor() const {
    if (m_value > 85) return QColor("#f43f5e");
    if (m_value > 65) return QColor("#ffb84d");
    return m_accent;
}

void ArcGauge::paintEvent(QPaintEvent*) {
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing);

    const int w = width();
    const double cx = w / 2.0;
    const double cy = m_size / 2.0 + 5;
    const double radius = (m_size / 2.0) - 14;

    // Arc geometry: starts at 225° (7 o'clock), sweeps 270° clockwise
    // Qt angles: 0° = 3 o'clock, positive = counter-clockwise
    // Start angle in Qt: 225° → 225 * 16 (Qt uses 1/16th degree units)
    const int startAngle = 225 * 16;
    const int fullSpan   = 270 * 16;

    QRectF arcRect(cx - radius, cy - radius, radius * 2, radius * 2);

    // 1. Background ring
    QPen bgPen(QColor(20, 30, 51, 153), 8, Qt::SolidLine, Qt::RoundCap);
    p.setPen(bgPen);
    p.drawArc(arcRect, startAngle, -fullSpan);

    // 2. Progress arc
    if (m_value > 0) {
        QColor col = escalatedColor();
        int span = static_cast<int>((m_value / 100.0) * fullSpan);

        QPen fgPen(col, 10, Qt::SolidLine, Qt::RoundCap);
        p.setPen(fgPen);
        p.drawArc(arcRect, startAngle, -span);

        // Glow ring
        QColor glow = col;
        glow.setAlphaF(0.25);
        QRectF glowRect(cx - radius - 4, cy - radius - 4, (radius + 4) * 2, (radius + 4) * 2);
        QPen glowPen(glow, 3, Qt::SolidLine, Qt::RoundCap);
        p.setPen(glowPen);
        p.drawArc(glowRect, startAngle, -span);
    }

    // 3. Value text (center)
    p.setPen(QColor("#e2e8f0"));
    QFont valFont("Inter", -1, QFont::Bold);
    valFont.setPixelSize(22);
    p.setFont(valFont);
    QString valStr = QString::number(static_cast<int>(m_value)) + m_unit;
    QFontMetrics fm(valFont);
    QRect valBounds = fm.boundingRect(valStr);
    p.drawText(
        static_cast<int>(cx - valBounds.width() / 2.0),
        static_cast<int>(cy + valBounds.height() / 2.0 - 3),
        valStr
    );

    // 4. Title (top center)
    p.setPen(QColor("#94a3b8"));
    QFont titleFont("JetBrains Mono", -1);
    titleFont.setPixelSize(9);
    p.setFont(titleFont);
    QFontMetrics tfm(titleFont);
    QRect titleBounds = tfm.boundingRect(m_title);
    p.drawText(
        static_cast<int>(cx - titleBounds.width() / 2.0),
        12,
        m_title
    );

    // 5. Subtitle (bottom)
    if (!m_subtitle.isEmpty()) {
        p.setPen(QColor("#64748b"));
        QFontMetrics sfm(titleFont);
        QRect subBounds = sfm.boundingRect(m_subtitle);
        p.drawText(
            static_cast<int>(cx - subBounds.width() / 2.0),
            m_size + 22,
            m_subtitle
        );
    }
}
