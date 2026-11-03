#pragma once
#include <QObject>
#include <QString>
#include <QNetworkAccessManager>

// Talks to a local Ollama instance (http://localhost:11434) for on-device AI.
// Falls back to the ShadowCypher API Guardian endpoint if Ollama is unavailable.
class OllamaClient : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool    available READ available NOTIFY availableChanged)
    Q_PROPERTY(bool    busy      READ busy      NOTIFY busyChanged)
    Q_PROPERTY(QString model     READ model     WRITE setModel NOTIFY modelChanged)

public:
    explicit OllamaClient(QObject* parent = nullptr);

    bool    available() const { return m_available; }
    bool    busy()      const { return m_busy; }
    QString model()     const { return m_model; }
    void    setModel(const QString& m) { m_model = m; emit modelChanged(); }

    Q_INVOKABLE void checkAvailability();
    Q_INVOKABLE void query(const QString& prompt, const QString& requestId = {});
    Q_INVOKABLE void listModels();

signals:
    void availableChanged();
    void busyChanged();
    void modelChanged();
    void queryResult(const QString& requestId, const QString& text);
    void modelsListed(const QStringList& models);
    void error(const QString& message);

private:
    void setBusy(bool b) { if (b == m_busy) return; m_busy = b; emit busyChanged(); }

    QNetworkAccessManager m_nam;
    QString               m_model     = "mistral:latest";
    QString               m_baseUrl   = "http://localhost:11434";
    bool                  m_available = false;
    bool                  m_busy      = false;
};
