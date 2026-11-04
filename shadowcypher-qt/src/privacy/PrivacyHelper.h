#pragma once
#include <QObject>
#include <QString>

// Turns Ghost mode's kill-switch on and off by running shadowcypher-privacy-helper
// through pkexec (Linux). The helper installs its own SHADOW_KS chains, so the
// user's other firewall rules are never touched, and it rolls back on failure.
class PrivacyHelper : public QObject
{
    Q_OBJECT
public:
    explicit PrivacyHelper(QObject* parent = nullptr);

    // The helper writes this marker only once the kill-switch is confirmed in
    // place, and removes it when it's taken down. It outlives the app.
    static bool killSwitchActive();

    bool busy() const { return m_busy; }
    void engage()    { run(QStringLiteral("engage")); }
    void disengage() { run(QStringLiteral("disengage")); }

signals:
    // active: the kill-switch state afterwards. message: what to show the user.
    void finished(bool ok, bool active, const QString& message);

private:
    void run(const QString& verb);
    void done(const QString& verb, int exitCode, const QString& output);

    bool m_busy = false;
};
