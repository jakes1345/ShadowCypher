#pragma once
#include <QObject>
#include <QString>
#include <QJsonObject>

class Config : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString apiKey    READ apiKey    NOTIFY changed)
    Q_PROPERTY(QString apiBase   READ apiBase   NOTIFY changed)
    Q_PROPERTY(int     scanInterval READ scanInterval NOTIFY changed)

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
    QString     m_apiKey;
    QString     m_apiBase   = "https://api.shadowcypher.site";
    int         m_scanInterval = 600;

    void load();
};
