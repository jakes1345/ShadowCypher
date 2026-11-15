#include "CveEnrichment.h"
#include <QMutexLocker>
#include <QStringList>
#include <QUrlQuery>

namespace shadow {

CveEnricher::CveEnricher(Fetch fetch, Clock clock)
    : m_fetch(std::move(fetch)), m_clock(std::move(clock)) {}

void CveEnricher::enrich(QJsonArray& cves) {
    const qint64 now = m_clock();

    // CISA KEV catalog: one file, cached.
    bool needKev;
    {
        QMutexLocker l(&m_mutex);
        needKev = now - m_kevFetchedMs > kKevTtlMs;
        if (needKev) m_kevFetchedMs = now - kKevTtlMs + kRetryMs;  // claim the retry slot
    }
    if (needKev) {
        try {
            const QJsonObject cat = m_fetch(QUrl(QStringLiteral(
                "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json")));
            QHash<QString, QString> fresh;
            for (const QJsonValue& v : cat.value(QStringLiteral("vulnerabilities")).toArray()) {
                const QJsonObject o = v.toObject();
                fresh.insert(o.value(QStringLiteral("cveID")).toString(),
                             o.value(QStringLiteral("dueDate")).toString());
            }
            if (!fresh.isEmpty()) {
                QMutexLocker l(&m_mutex);
                m_kev = fresh;
                m_kevFetchedMs = m_clock();
            }
        } catch (...) {}
    }

    // EPSS: FIRST.org API, batched, cached per CVE.
    QStringList missing;
    {
        QMutexLocker l(&m_mutex);
        for (const QJsonValue& v : cves) {
            const QString id = v.toObject().value(QStringLiteral("cve_id")).toString();
            const auto it = m_epss.constFind(id);
            if (!id.isEmpty() && (it == m_epss.constEnd() || now - it->second > kEpssTtlMs))
                missing.append(id);
        }
    }
    missing.removeDuplicates();
    for (int i = 0; i < missing.size(); i += kEpssBatch) {
        const QStringList batch = missing.mid(i, kEpssBatch);
        try {
            QUrl url(QStringLiteral("https://api.first.org/data/v1/epss"));
            QUrlQuery q;
            q.addQueryItem(QStringLiteral("cve"), batch.join(','));
            url.setQuery(q);
            const QJsonObject resp = m_fetch(url);
            QMutexLocker l(&m_mutex);
            const qint64 t = m_clock();
            for (const QJsonValue& v : resp.value(QStringLiteral("data")).toArray()) {
                const QJsonObject o = v.toObject();
                // FIRST returns scores as strings
                m_epss.insert(o.value(QStringLiteral("cve")).toString(),
                              {o.value(QStringLiteral("epss")).toString().toDouble(), t});
            }
        } catch (...) {}
    }

    QMutexLocker l(&m_mutex);
    for (int i = 0; i < cves.size(); ++i) {
        QJsonObject row = cves.at(i).toObject();
        const QString id = row.value(QStringLiteral("cve_id")).toString();
        if (const auto e = m_epss.constFind(id); e != m_epss.constEnd())
            row[QStringLiteral("epss_score")] = e->first;
        if (const auto k = m_kev.constFind(id); k != m_kev.constEnd()) {
            row[QStringLiteral("kev_exploited")] = true;
            row[QStringLiteral("kev_due_date")]  = k.value();
        }
        cves[i] = row;
    }
}

}  // namespace shadow
