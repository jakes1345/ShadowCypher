#include "NativeTools.h"
#include "Protocol.h"
#include "ShadowScript.h"
#include <QCommandLineParser>
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QSettings>
#include <QTextStream>
#include <QThread>
#include <csignal>
#include <cstdio>

namespace {
std::atomic_bool interrupted{false};
static_assert(std::atomic_bool::is_always_lock_free, "Signal cancellation requires lock-free atomics");
void interrupt(int) { interrupted.store(true); }
void printJson(const QJsonObject& object) {
    QTextStream out(stdout);
    out << QJsonDocument(object).toJson(QJsonDocument::Compact) << '\n'; out.flush();
}
}

int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);
    QCoreApplication::setApplicationName("shadowcypher-runtime");
    QCoreApplication::setApplicationVersion("0.1.0");
    std::signal(SIGINT, interrupt);
    std::signal(SIGTERM, interrupt);
    const shadow::Cancel cancel(&interrupted, [](std::atomic_bool*) {});
    QCommandLineParser parser;
    parser.setApplicationDescription("Native Qt6/C++ ShadowScript, Guardian and MCP runtime");
    parser.addHelpOption(); parser.addVersionOption();
    parser.addPositionalArgument("mode", "script, check, mcp, agent-once, agent-run, or capabilities");
    parser.addPositionalArgument("file", "ShadowScript source file (script/check modes)", "[file]");
    parser.addOptions({
        {{"c", "config"}, "Read an agent JSON configuration file", "file"},
        {"config-ini", "Read desktop INI configuration", "file"},
        {"source-directory", "Resolve script LOAD paths relative to this directory", "directory"},
        {"state", "Agent state file", "file", QDir::homePath()+"/.shadowcypher/native-agent-state.json"},
        {"missions", "Allow the native agent to claim and execute remote missions"},
        {"interval", "Seconds between native agent cycles", "seconds", "600"},
        {"json-lines", "Emit structured script output, result and error records"}
    });
    parser.process(app);
    auto positional = parser.positionalArguments();
    if (positional.isEmpty()) parser.showHelp(2);
    try {
        QJsonObject config;
        if (parser.isSet("config")) {
            QFile file(parser.value("config"));
            if (!file.open(QIODevice::ReadOnly)) throw shadow::Error("Cannot read configuration");
            QJsonParseError error;
            auto document = QJsonDocument::fromJson(file.readAll(), &error);
            if (error.error != QJsonParseError::NoError || !document.isObject()) throw shadow::Error("Invalid configuration JSON");
            config = document.object();
        }
        if (parser.isSet("config-ini")) {
            QSettings settings(parser.value("config-ini"), QSettings::IniFormat);
            config.insert("api_key", settings.value("api_key").toString());
            config.insert("ollama_url", settings.value("ollama/endpoint", "http://127.0.0.1:11434").toString());
            config.insert("ollama_model", settings.value("ollama/model").toString());
        }
        shadow::NativeTools tools(config);
        const QString mode = positional[0];
        auto output = [&](const QString& line) {
            if (parser.isSet("json-lines")) printJson({{"type", "output"}, {"text", line}});
            else { QTextStream stream(stdout); stream << line << '\n'; stream.flush(); }
        };
        if (mode == "check" || mode == "script") {
            if (positional.size() != 2) throw shadow::Error("Provide a .shadow source file");
            QFile file(positional[1]);
            if (!file.open(QIODevice::ReadOnly)) throw shadow::Error("Cannot read script");
            const auto source = QString::fromUtf8(file.read(1024*1024+1));
            if (mode == "check") {
                shadow::ShadowScript::parse(source);
                printJson({{"syntax_valid", true}});
            } else {
                shadow::ShadowScript script(output, [&](const QString& method, const QStringList& args, const shadow::Cancel& token) {
                    return tools.invoke(method, args, token);
                }, cancel);
                const auto variables = script.run(source, parser.isSet("source-directory") ? parser.value("source-directory") : QFileInfo(file).absolutePath());
                if (parser.isSet("json-lines")) printJson({{"type", "complete"}, {"variables", variables}});
            }
        } else if (mode == "mcp") {
            shadow::Protocol protocol(tools, cancel);
            QByteArray line;
            bool oversized = false;
            int c;
            while ((c = std::getchar()) != EOF) {
                shadow::checkCancelled(cancel);
                if (c == '\n') {
                    if (oversized) throw shadow::Error("MCP request exceeded 1 MiB");
                    if (!line.trimmed().isEmpty()) {
                        const auto response = protocol.handle(line);
                        if (response) printJson(*response);
                    }
                    line.clear(); oversized = false;
                } else if (line.size() < 1024*1024) line.append(static_cast<char>(c));
                else oversized = true;
            }
            if (oversized) throw shadow::Error("MCP request exceeded 1 MiB");
            if (!line.trimmed().isEmpty()) { const auto response = protocol.handle(line); if (response) printJson(*response); }
        } else if (mode == "agent-once" || mode == "agent-run") {
            bool ok;
            const int seconds = parser.value("interval").toInt(&ok);
            if (!ok || seconds < 10 || seconds > 86400) throw shadow::Error("interval must be 10–86400 seconds");
            do {
                QString agentId;
                try {
                    const auto result = tools.agentCycle(parser.value("state"), parser.isSet("missions"), output, cancel);
                    agentId = result.value("agent_id").toString();
                    printJson(result);
                } catch (const std::exception& error) {
                    if (mode == "agent-once" || interrupted.load()) throw;
                    QTextStream(stderr) << "Agent cycle failed: " << error.what() << '\n';
                }
                if (mode == "agent-once") break;
                for (int elapsed = 0; elapsed < seconds*10; ++elapsed) {
                    shadow::checkCancelled(cancel); QThread::msleep(100);
                    if (!agentId.isEmpty() && elapsed > 0 && elapsed % 600 == 0) {
                        try { tools.api("/v1/agents/heartbeat", {{"agent_id", agentId}}, true, cancel); }
                        catch (const std::exception& error) { QTextStream(stderr) << "Heartbeat failed: " << error.what() << '\n'; }
                    }
                }
            } while (!interrupted.load());
        } else if (mode == "capabilities") {
            printJson({{"runtime", "Qt6/C++"}, {"python_required", false}, {"version", "0.1.0"},
                {"modes", QJsonArray{"script", "check", "mcp", "agent-once", "agent-run"}}, {"mcp_tools", shadow::Protocol::tools()},
                {"migration_complete", false}});
        } else throw shadow::Error("Unknown mode: " + mode);
        return 0;
    } catch (const std::exception& error) {
        if (parser.isSet("json-lines")) printJson({{"type", "error"}, {"message", QString::fromUtf8(error.what())}});
        else QTextStream(stderr) << error.what() << '\n';
        return interrupted.load() ? 130 : 1;
    }
}
