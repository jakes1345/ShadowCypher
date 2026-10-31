#pragma once
#include "Process.h"
#include <QJsonObject>
#include <QMap>
#include <QVector>

namespace shadow {
struct Statement {
    QString command;
    QStringList args;
    QVector<Statement> body;
    QVector<Statement> otherwise;
    int line = 1;
};
using Directive = std::function<QString(const QString&, const QStringList&, const Cancel&)>;

class ShadowScript {
public:
    explicit ShadowScript(Output output = {}, Directive directive = {}, Cancel cancel = {});
    static QVector<Statement> parse(const QString& source);
    QJsonObject run(const QString& source, const QString& sourceDirectory = {});
    const QMap<QString, QString>& variables() const { return m_variables; }
private:
    Output m_output;
    Directive m_directive;
    Cancel m_cancel;
    QMap<QString, QString> m_variables;
    QMap<QString, Statement> m_native;
    QString m_directory;
    int m_steps = 0;
    int m_loadDepth = 0;
    void execute(const QVector<Statement>& statements, bool unsafe = false, int loopDepth = 0);
    void call(const Statement& statement, bool unsafe);
    QString resolve(const QString& value) const;
    bool condition(const QStringList& args) const;
    void output(const QString& value);
    QString invokeNative(const Statement& definition, const QStringList& args);
};
}
