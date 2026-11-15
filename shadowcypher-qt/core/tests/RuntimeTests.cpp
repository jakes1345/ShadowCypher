#include "CveEnrichment.h"
#include "NativeTools.h"
#include "MissionRunner.h"
#include "Process.h"
#include "Protocol.h"
#include "ShadowScript.h"
#include <QCoreApplication>
#include <QElapsedTimer>
#include <QFile>
#include <QDirIterator>
#include <QJsonDocument>
#include <QSignalSpy>
#include <QStandardPaths>
#include <QTcpServer>
#include <QTcpSocket>
#include <QTemporaryDir>
#include <QTest>
#include <QUrlQuery>
#include <QThread>
#include <thread>
#include <cstdio>

using namespace shadow;

struct EnrichFixture {
    QList<QUrl> calls;
    bool kevFails = false, epssFails = false;
    qint64 now = 1'000'000'000'000LL;
    CveEnricher make() {
        return CveEnricher(
            [this](const QUrl& url) -> QJsonObject {
                calls.append(url);
                if (url.host() == "www.cisa.gov") {
                    if (kevFails) throw Error("kev down");
                    return QJsonObject{{"vulnerabilities", QJsonArray{
                        QJsonObject{{"cveID", "CVE-2021-44228"}, {"dueDate", "2021-12-24"}}}}};
                }
                if (epssFails) throw Error("epss down");
                QJsonArray data;
                for (const QString& id : QUrlQuery(url).queryItemValue("cve").split(','))
                    data.append(QJsonObject{{"cve", id}, {"epss", "0.97500"}});
                return QJsonObject{{"data", data}};
            },
            [this] { return now; });
    }
    int count(const char* host) const {
        int n = 0;
        for (const QUrl& u : calls) if (u.host() == host) ++n;
        return n;
    }
};
static QJsonArray cveRows(const QStringList& ids) {
    QJsonArray rows;
    for (const QString& id : ids)
        rows.append(QJsonObject{{"cve_id", id}, {"epss_score", 0.0}, {"kev_exploited", false}});
    return rows;
}

class RuntimeTests : public QObject {
    Q_OBJECT
private slots:
    void variablesAndBranches() {
        QStringList lines;
        ShadowScript script([&](const auto& line) { lines.append(line); });
        auto vars = script.run("VAR target = '127.0.0.1'\nTARGET($target)\nIF $target == '127.0.0.1' { !echo('ok') } ELSE { !echo('bad') }\nRETURN '$target'\n!echo('unreachable')");
        QCOMPARE(lines, QStringList({"Target locked → 127.0.0.1", "ok"}));
        QCOMPARE(vars["RESULT"].toString(), "127.0.0.1");
    }
    void loopsAndReturn() {
        QStringList lines;
        ShadowScript script([&](const auto& line) { lines.append(line); });
        auto result = script.run("FOR item IN a b c { IF $item == b { BREAK } !echo($item) }\nVAR stop = 0\nWHILE $stop == 0 { SET stop = 1 }\nRETURN $stop");
        QCOMPARE(lines, QStringList{"a"});
        QCOMPARE(result["RESULT"].toString(), "1");
    }
    void preservesPortsAndPaths() {
        QStringList captured;
        QString called;
        ShadowScript script({}, [&](const QString& method, const QStringList& args, const Cancel&) {
            called = method;
            captured = args;
            return QString("done");
        });
        script.run("TARGET(127.0.0.1) -> SCAN(22,80,1000-1002)");
        QCOMPARE(called, QString("network.port_scan"));
        QCOMPARE(captured, QStringList({"127.0.0.1", "22,80,1000-1002"}));
    }
    void parsingPrecedesSideEffects() {
        int calls = 0;
        ShadowScript script([&](const auto&) { ++calls; });
        QVERIFY_EXCEPTION_THROWN(script.run("!echo('first')\nIF true {"), Error);
        QCOMPARE(calls, 0);
        QVERIFY_EXCEPTION_THROWN(ShadowScript::parse("!echo('unclosed)"), Error);
        QVERIFY_EXCEPTION_THROWN(ShadowScript::parse("}"), Error);
    }
    void unsupportedOperationsFail() {
        ShadowScript script;
        QVERIFY_EXCEPTION_THROWN(script.run("SWARM()"), Error);
        QVERIFY_EXCEPTION_THROWN(script.run("BREAK"), Error);
        QVERIFY_EXCEPTION_THROWN(NativeTools().invoke("missing.method", {}), Error);
    }
    void unsafeScopeDoesNotLeak() {
        ShadowScript script;
        QVERIFY_EXCEPTION_THROWN(script.run("!sys('echo forbidden')"), Error);
        QVERIFY_EXCEPTION_THROWN(script.run("UNSAFE { !echo('allowed') }\n!pipe('echo forbidden')"), Error);
    }
    void iterationLimit() {
        ShadowScript script;
        QVERIFY_EXCEPTION_THROWN(script.run("WHILE true { VAR x = 1 }"), Error);
    }
    void filterRetainsLanguageContract() {
        ShadowScript script;
        const auto vars = script.run("VAR LAST = 'ssh\\ntelnet\\nhttps'\nFILTER { $ITEM == 'telnet' }\n");
        QCOMPARE(vars["FILTERED"].toString(), "telnet");
    }
    void cancellation() {
        auto cancel = std::make_shared<std::atomic_bool>(false);
        std::thread worker([cancel] { QThread::msleep(40); cancel->store(true); });
        ShadowScript script({}, {}, cancel);
        QElapsedTimer timer; timer.start();
        QVERIFY_EXCEPTION_THROWN(script.run("!sleep(120)"), Error);
        worker.join();
        QVERIFY(timer.elapsed() < 1000);
    }
    void loadRelativeToSource() {
        QTemporaryDir dir;
        QFile file(dir.filePath("child.shadow"));
        QVERIFY(file.open(QIODevice::WriteOnly));
        file.write("VAR child = 'loaded'\n"); file.close();
        ShadowScript script;
        QCOMPARE(script.run("LOAD('child.shadow')", dir.path())["child"].toString(), "loaded");
        file.open(QIODevice::WriteOnly); file.write("LOAD('child.shadow')"); file.close();
        QVERIFY_EXCEPTION_THROWN(script.run("LOAD('child.shadow')", dir.path()), Error);
    }
    void quotedNativeBraces() {
        auto parsed = ShadowScript::parse("cpp hello {\n#include <cstdio>\nint main() { /* } */ puts(\"}\"); }\n}\nUNSAFE { hello }\n");
        QCOMPARE(parsed.size(), 2);
        QVERIFY(parsed[0].args[1].contains("puts(\"}\")"));
        const auto raw = ShadowScript::parse("cpp raw { int main() { auto s = R\"tag(\"'}{)tag\"; } }\n");
        QCOMPARE(raw.size(), 1);
    }
    void bundledMissionAndLessonSyntax() {
        QDirIterator iterator(SHADOW_SCRIPT_DIR, {"*.shadow"}, QDir::Files, QDirIterator::Subdirectories);
        int checked = 0;
        while (iterator.hasNext()) {
            QFile file(iterator.next());
            QVERIFY(file.open(QIODevice::ReadOnly));
            try { ShadowScript::parse(QString::fromUtf8(file.readAll())); }
            catch (const Error& error) { QFAIL(qPrintable(file.fileName() + ": " + error.what())); }
            ++checked;
        }
        QVERIFY(checked > 0);
    }
    void nativeExecutionAndWriteback() {
        if (QStandardPaths::findExecutable("c++").isEmpty()) QSKIP("C++ compiler unavailable");
        ShadowScript script;
        const auto vars = script.run("cpp hello {\n#include <cstdio>\nint main() { puts(\"SHADOWVAR:answer=42\"); puts(\"native\"); }\n}\nUNSAFE { hello }\n");
        QCOMPARE(vars["answer"].toString(), "42");
        QCOMPARE(vars["NATIVE_RESULT"].toString(), "native");
    }
    void splitCommandPreservesBoundaries() {
        QCOMPARE(splitCommand("tool 'two words' \"\" a\\ b ';'"), QStringList({"tool", "two words", "", "a b", ";"}));
        QVERIFY_EXCEPTION_THROWN(splitCommand("tool 'unclosed"), Error);
    }
    void processExitAndMissingProgram() {
        auto result = runProcess(QCoreApplication::applicationFilePath(), {"--helper-exit"});
        QCOMPARE(result.exitCode, 7);
        QCOMPARE(QString::fromUtf8(result.out), "output\n");
        QVERIFY_EXCEPTION_THROWN(runProcess("/nonexistent/shadowcypher-program"), Error);
    }
    void processTimeoutAndCancellation() {
        QElapsedTimer timer; timer.start();
        QVERIFY_EXCEPTION_THROWN(runProcess(QCoreApplication::applicationFilePath(), {"--helper-sleep"}, {}, 50), Error);
        QVERIFY(timer.elapsed() < 1500);
        auto cancel = std::make_shared<std::atomic_bool>(true);
        QVERIFY_EXCEPTION_THROWN(runProcess(QCoreApplication::applicationFilePath(), {"--helper-exit"}, cancel), Error);
    }
    void validatePortRanges() {
        QCOMPARE(NativeTools::parsePorts("22,80,22,100-102"), QList<quint16>({22,80,100,101,102}));
        for (const auto& invalid : {"", "0", "65536", "10-2", "1-65535", "80;touch /tmp/x"})
            QVERIFY_EXCEPTION_THROWN(NativeTools::parsePorts(invalid), Error);
        QVERIFY_EXCEPTION_THROWN(NativeTools::validateTarget("--script=bad"), Error);
    }
    void tcpScanLoopback() {
        QTcpServer server;
        QVERIFY(server.listen(QHostAddress::LocalHost));
        const auto result = NativeTools().portScan("127.0.0.1", QString::number(server.serverPort()));
        QCOMPARE(result["open_ports"].toArray(), QJsonArray{server.serverPort()});
    }
    void neighborParsing() {
        const QByteArray data = R"([{"dst":"192.0.2.1","lladdr":"AA:BB:CC:DD:EE:FF","dev":"eth0","state":["STALE"]},{"dst":"192.0.2.2","state":["INCOMPLETE"]}])";
        auto devices = NativeTools::parseNeighbors(data);
        QCOMPARE(devices.size(), 1);
        QCOMPARE(devices[0].toObject()["mac"].toString(), "aa:bb:cc:dd:ee:ff");
        QVERIFY_EXCEPTION_THROWN(NativeTools::parseNeighbors("not json"), Error);
    }
    void httpSuccessAndFailure() {
        QTcpServer server;
        QVERIFY(server.listen(QHostAddress::LocalHost));
        int status = 200;
        QByteArray response = "{\"ok\":true}";
        connect(&server, &QTcpServer::newConnection, &server, [&] {
            auto* socket = server.nextPendingConnection();
            connect(socket, &QTcpSocket::readyRead, socket, [&, socket] {
                socket->readAll();
                socket->write("HTTP/1.1 " + QByteArray::number(status) + " Result\r\nContent-Type: application/json\r\nContent-Length: " + QByteArray::number(response.size()) + "\r\nConnection: close\r\n\r\n" + response);
                socket->disconnectFromHost();
            });
            connect(socket, &QTcpSocket::disconnected, socket, &QObject::deleteLater);
        });
        const QUrl url("http://127.0.0.1:" + QString::number(server.serverPort()));
        QVERIFY(NativeTools::request(url)["ok"].toBool());
        status = 500;
        QVERIFY_EXCEPTION_THROWN(NativeTools::request(url), Error);
        status = 200; response = "not JSON";
        QVERIFY_EXCEPTION_THROWN(NativeTools::request(url), Error);
        QVERIFY_EXCEPTION_THROWN(NativeTools::request(QUrl("http://example.com"), {}, false, "secret"), Error);
    }
    // ── CVE enrichment (EPSS + CISA KEV) ────────────────────────────────────
    void cveEnrichmentAppliesEpssAndKev() {
        EnrichFixture f; auto e = f.make();
        auto rows = cveRows({"CVE-2021-44228", "CVE-2020-0001"});
        e.enrich(rows);
        const auto kev = rows[0].toObject(), other = rows[1].toObject();
        QVERIFY(kev["kev_exploited"].toBool());
        QCOMPARE(kev["kev_due_date"].toString(), "2021-12-24");
        QCOMPARE(kev["epss_score"].toDouble(), 0.975);
        QVERIFY(!other["kev_exploited"].toBool());
        QVERIFY(!other.contains("kev_due_date"));
        QCOMPARE(other["epss_score"].toDouble(), 0.975);
    }
    void cveEnrichmentCachesWithinTtlAndRefetchesAfter() {
        EnrichFixture f; auto e = f.make();
        auto a = cveRows({"CVE-2021-44228"}); e.enrich(a);
        auto b = cveRows({"CVE-2021-44228"}); e.enrich(b);
        QCOMPARE(f.count("www.cisa.gov"), 1);
        QCOMPARE(f.count("api.first.org"), 1);
        QCOMPARE(b[0].toObject()["epss_score"].toDouble(), 0.975);
        f.now += CveEnricher::kKevTtlMs + 1;
        auto c = cveRows({"CVE-2021-44228"}); e.enrich(c);
        QCOMPARE(f.count("www.cisa.gov"), 2);
        QCOMPARE(f.count("api.first.org"), 2);
    }
    void cveEnrichmentBatchesEpssLookups() {
        EnrichFixture f; auto e = f.make();
        QStringList ids;
        for (int i = 0; i < CveEnricher::kEpssBatch + 1; ++i) ids << QString("CVE-2024-%1").arg(1000 + i);
        ids << ids.first();  // duplicate ids are looked up once
        auto rows = cveRows(ids); e.enrich(rows);
        QCOMPARE(f.count("api.first.org"), 2);
        QCOMPARE(QUrlQuery(f.calls.last()).queryItemValue("cve"), QString("CVE-2024-%1").arg(1000 + CveEnricher::kEpssBatch));
    }
    void cveEnrichmentFailuresAreNonFatal() {
        EnrichFixture f; f.kevFails = true; f.epssFails = true;
        auto e = f.make();
        auto rows = cveRows({"CVE-2021-44228"});
        e.enrich(rows);  // must not throw
        const auto row = rows[0].toObject();
        QCOMPARE(row["epss_score"].toDouble(), 0.0);
        QVERIFY(!row["kev_exploited"].toBool());
    }
    void cveEnrichmentBacksOffAfterFailedKevFetch() {
        EnrichFixture f; f.kevFails = true;
        auto e = f.make();
        auto a = cveRows({"CVE-2021-44228"}); e.enrich(a);
        f.now += CveEnricher::kRetryMs - 1000;  // inside the back-off window
        auto b = cveRows({"CVE-2021-44228"}); e.enrich(b);
        QCOMPARE(f.count("www.cisa.gov"), 1);
        f.kevFails = false;
        f.now += 2000;                           // past it
        auto c = cveRows({"CVE-2021-44228"}); e.enrich(c);
        QCOMPARE(f.count("www.cisa.gov"), 2);
        QVERIFY(c[0].toObject()["kev_exploited"].toBool());
    }
    void cveEnrichmentIgnoresEpssFailureForCachedRows() {
        EnrichFixture f; auto e = f.make();
        auto a = cveRows({"CVE-2021-44228"}); e.enrich(a);
        f.epssFails = true;
        auto b = cveRows({"CVE-2021-44228"}); e.enrich(b);
        QCOMPARE(b[0].toObject()["epss_score"].toDouble(), 0.975);
    }
    void mcpProtocol() {
        Protocol protocol{NativeTools{}};
        QCOMPARE(protocol.handle("not JSON")->value("error").toObject()["code"].toInt(), -32700);
        QVERIFY(!protocol.handle(R"({"jsonrpc":"2.0","method":"notifications/initialized"})").has_value());
        const auto initialized = protocol.handle(R"({"jsonrpc":"2.0","id":"abc","method":"initialize","params":{"protocolVersion":"2025-03-26"}})").value();
        QCOMPARE(initialized["id"].toString(), "abc");
        QCOMPARE(initialized["result"].toObject()["protocolVersion"].toString(), "2025-03-26");
        QCOMPARE(protocol.handle(R"({"jsonrpc":"2.0","id":2,"method":"tools/list"})")->value("result").toObject()["tools"].toArray().size(), 3);
        QCOMPARE(protocol.handle(R"({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"shadowcypher_port_scan","arguments":{}}})")->value("error").toObject()["code"].toInt(), -32602);
        const auto badScan = protocol.handle(R"({"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"shadowcypher_port_scan","arguments":{"target":"--invalid"}}})").value();
        QVERIFY(badScan["result"].toObject()["isError"].toBool());
    }
    void desktopRunnerSuccessFailureAndStop() {
        MissionRunner runner(nullptr, SHADOW_RUNTIME_PATH);
        QSignalSpy output(&runner, &MissionRunner::output);
        QSignalSpy finished(&runner, &MissionRunner::finished);
        QVERIFY(runner.start("!echo('native desktop')", QDir::tempPath()));
        QTRY_COMPARE_WITH_TIMEOUT(finished.count(), 1, 3000);
        QVERIFY(finished.last()[0].toBool());
        QCOMPARE(output.first()[0].toString(), "native desktop");
        QVERIFY(runner.start("INVALID()", QDir::tempPath()));
        QTRY_COMPARE_WITH_TIMEOUT(finished.count(), 2, 3000);
        QVERIFY(!finished.last()[0].toBool());
        QVERIFY(runner.start("!sleep(120)", QDir::tempPath()));
        QTest::qWait(60);
        runner.stop();
        QTRY_COMPARE_WITH_TIMEOUT(finished.count(), 3, 3000);
        QVERIFY(!finished.last()[0].toBool());
        QVERIFY(!runner.running());
    }
    void desktopRunnerMissingBinary() {
        MissionRunner runner(nullptr, "/nonexistent/shadowcypher-runtime");
        QSignalSpy finished(&runner, &MissionRunner::finished);
        QVERIFY(runner.start("!echo('hello')", QDir::tempPath()));
        QTRY_COMPARE_WITH_TIMEOUT(finished.count(), 1, 3000);
        QVERIFY(!finished.first()[0].toBool());
    }
    void nativeAgentApiContract() {
        QTemporaryDir dir;
        QTcpServer server;
        QVERIFY(server.listen(QHostAddress::LocalHost));
        QStringList paths;
        QMap<QString, QJsonObject> posted;
        connect(&server, &QTcpServer::newConnection, &server, [&] {
            auto* socket = server.nextPendingConnection();
            auto buffer = std::make_shared<QByteArray>();
            connect(socket, &QTcpSocket::readyRead, socket, [&, socket, buffer] {
                *buffer += socket->readAll();
                const auto split = buffer->indexOf("\r\n\r\n");
                if (split < 0) return;
                const auto headers = buffer->left(split);
                int length = 0;
                for (const auto& line : headers.split('\n'))
                    if (line.toLower().startsWith("content-length:")) length = line.mid(15).trimmed().toInt();
                if (buffer->size() < split+4+length) return;
                const auto path = QString::fromUtf8(headers.split(' ').value(1));
                paths.append(path);
                posted.insert(path, QJsonDocument::fromJson(buffer->mid(split+4, length)).object());
                QJsonObject response;
                if (path == "/v1/agents/register") response.insert("agent_id", "test-agent");
                else if (path.endsWith("/missions/pending")) response.insert("missions", QJsonArray{QJsonObject{{"id", "mission-1"}, {"script_content", "!echo('native mission')"}}});
                const auto bytes = QJsonDocument(response).toJson(QJsonDocument::Compact);
                socket->write("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: " + QByteArray::number(bytes.size()) + "\r\nConnection: close\r\n\r\n" + bytes);
                socket->disconnectFromHost();
            });
            connect(socket, &QTcpSocket::disconnected, socket, &QObject::deleteLater);
        });
        NativeTools tools({{"api_base", "http://127.0.0.1:" + QString::number(server.serverPort())}, {"api_key", "test-only"}},
            [](const Cancel&) { return QJsonArray{QJsonObject{{"ip", "192.0.2.1"}, {"mac", "aa:bb:cc:dd:ee:ff"}}}; });
        const auto state = dir.filePath("state.json");
        auto first = tools.agentCycle(state, false, {});
        QCOMPARE(first["device_count"].toInt(), 1);
        QCOMPARE(paths, QStringList({"/v1/agents/register", "/v1/agents/heartbeat", "/v1/scans"}));
        QVERIFY(!posted["/v1/agents/register"]["hostname"].toString().isEmpty());
        QCOMPARE(posted["/v1/scans"]["agent_id"].toString(), "test-agent");
        paths.clear();
        QCOMPARE(tools.agentCycle(state, true, {})["missions_executed"].toInt(), 1);
        QVERIFY(!paths.contains("/v1/agents/register"));
        QCOMPARE(posted["/v1/missions/mission-1/result"]["exit_code"].toInt(-1), 0);
        QCOMPARE(posted["/v1/missions/mission-1/result"]["output"].toString(), "native mission");
    }
};

int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);
    const auto args = app.arguments();
    if (args.contains("--helper-exit")) { std::fputs("output\n", stdout); return 7; }
    if (args.contains("--helper-sleep")) { QThread::sleep(10); return 0; }
    RuntimeTests tests;
    return QTest::qExec(&tests, argc, argv);
}
#include "RuntimeTests.moc"
