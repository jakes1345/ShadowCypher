#pragma once
#include <QObject>
#include <QString>
#include <QJsonObject>

class Config : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString apiKey       READ apiKey       WRITE setApiKey       NOTIFY changed)
    Q_PROPERTY(QString apiBase      READ apiBase      WRITE setApiBase      NOTIFY changed)
    Q_PROPERTY(int     scanInterval READ scanInterval WRITE setScanInterval NOTIFY changed)

public:
    explicit Config(QObject* parent = nullptr);

    QString apiKey()      const;
    QString apiBase()     const;
    int     scanInterval() const;

    void setApiKey(const QString&);
    void setApiBase(const QString&);
    void setScanInterval(int seconds);

    Q_INVOKABLE void save();
    Q_INVOKABLE void reload();

signals:
    void changed();

private:
    QString     m_path;
    // Whole file contents; config.json is shared with the Python agent, so keys we
    // don't own must survive a save.
    QJsonObject m_raw;
    QString     m_apiKey;
    QString     m_apiBase   = "https://api.shadowcypher.site";
    int         m_scanInterval = 600;

    void load();
};
