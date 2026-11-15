#pragma once
#include <QHash>
#include <QJsonArray>
#include <QJsonObject>
#include <QMutex>
#include <QPair>
#include <QString>
#include <QUrl>
#include <functional>

namespace shadow {

// Adds EPSS scores (FIRST.org) and CISA KEV status to CVE rows. Best effort:
// a failed fetch leaves a row's epss_score/kev_exploited at their defaults.
// The fetcher and clock are injectable so tests need no network.
class CveEnricher {
public:
    using Fetch = std::function<QJsonObject(const QUrl&)>;  // throws on failure
    using Clock = std::function<qint64()>;                  // ms since epoch

    static constexpr qint64 kKevTtlMs   = 12LL * 3600 * 1000;
    static constexpr qint64 kEpssTtlMs  = 12LL * 3600 * 1000;
    static constexpr qint64 kRetryMs    = 10LL * 60 * 1000;  // wait after a failed KEV fetch
    static constexpr int    kEpssBatch  = 100;

    CveEnricher(Fetch fetch, Clock clock);

    // Rows need a "cve_id". Sets epss_score, kev_exploited and kev_due_date.
    void enrich(QJsonArray& cves);

private:
    Fetch  m_fetch;
    Clock  m_clock;
    QMutex m_mutex;  // guards the caches only; never held during a fetch
    QHash<QString, QString>               m_kev;   // CVE id -> CISA due date
    qint64                                m_kevFetchedMs = 0;
    QHash<QString, QPair<double, qint64>> m_epss;  // CVE id -> (score, fetched ms)
};

}  // namespace shadow
