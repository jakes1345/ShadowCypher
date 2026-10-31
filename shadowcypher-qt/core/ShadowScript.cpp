#include "ShadowScript.h"
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QRegularExpression>
#include <QTemporaryDir>
#include <QThread>
#include <QElapsedTimer>
#include <cmath>

namespace shadow {
namespace {
struct Token { QString text; int line; bool literal = false; };
class Parser {
public:
    explicit Parser(const QString& source) { tokenize(source); }
    QVector<Statement> program(bool block = false) {
        if (++nesting > 128) fail("Block nesting exceeded 128 levels");
        QVector<Statement> result;
        while (pos < tokens.size()) {
            if (take("\n") || take(";") || take("->")) continue;
            if (is("}")) {
                if (!block) fail("Unexpected closing brace");
                ++pos;
                --nesting;
                return result;
            }
            Statement s;
            const auto command = next();
            s.command = command.text;
            s.line = command.line;
            if (command.literal) fail("Expected a directive");
            if (s.command == "VAR" || s.command == "SET") {
                const auto name = next().text;
                if (!QRegularExpression("^[A-Za-z_][A-Za-z0-9_]*$").match(name).hasMatch()) fail("Invalid variable name");
                require("=");
                s.args = {name, value().text};
            } else if (s.command == "IF" || s.command == "WHILE" || s.command == "FOR") {
                while (!is("{")) {
                    if (pos >= tokens.size() || is("}")) fail("Expected a block");
                    if (!take("\n")) s.args.append(next().text);
                }
                require("{");
                s.body = program(true);
                if (s.command == "FOR") {
                    if (s.args.size() < 3 || s.args[1] != "IN") fail("Expected FOR name IN values");
                } else if (s.args.size() != 1 && s.args.size() != 3) fail("Invalid condition");
                if (s.command == "IF") {
                    while (take("\n")) {}
                    if (take("ELSE")) { require("{"); s.otherwise = program(true); }
                }
            } else if (s.command == "FILTER") {
                require("{");
                while (!is("}")) {
                    if (pos >= tokens.size() || is("{")) fail("Expected FILTER condition");
                    if (!take("\n")) s.args.append(next().text);
                }
                require("}");
                if (s.args.size() != 1 && s.args.size() != 3) fail("Invalid FILTER condition");
            } else if (s.command == "UNSAFE" || s.command == "MAP") {
                while (take("\n")) {}
                require("{");
                s.body = program(true);
            } else if (s.command == "rust" || s.command == "go" || s.command == "cpp") {
                s.args.append(next().text);
                if (pos >= tokens.size() || !tokens[pos].literal) fail("Expected native source block");
                s.args.append(next().text);
            } else if (s.command == "RETURN" || s.command == "YIELD") {
                if (pos < tokens.size() && !is("\n") && !is("}")) s.args.append(value().text);
            } else if (s.command == "BREAK") {
                // No arguments.
            } else if (take("(")) {
                QString argument;
                bool present = false;
                while (!is(")")) {
                    if (pos >= tokens.size() || is("{") || is("}")) fail("Unclosed argument list");
                    if (take(",")) {
                        if (!present) fail("Empty argument");
                        s.args.append(argument); argument.clear(); present = false;
                    } else if (!take("\n")) {
                        const auto token = next();
                        argument += token.text;
                        present = true;
                    }
                }
                require(")");
                if (present) s.args.append(argument);
            } else {
                // Native function calls and TARGET also accept bare arguments.
                while (pos < tokens.size() && !is("\n") && !is("}") && !is(";") && !is("->"))
                    s.args.append(value().text);
            }
            result.append(s);
        }
        if (block) fail("Unclosed block");
        --nesting;
        return result;
    }
private:
    QVector<Token> tokens;
    qsizetype pos = 0;
    int nesting = 0;
    [[noreturn]] void fail(const QString& message) const {
        const int line = pos < tokens.size() ? tokens[pos].line : (tokens.isEmpty() ? 1 : tokens.last().line);
        throw Error(QString("Line %1: %2").arg(line).arg(message));
    }
    bool is(const QString& value) const { return pos < tokens.size() && !tokens[pos].literal && tokens[pos].text == value; }
    bool take(const QString& value) { if (!is(value)) return false; ++pos; return true; }
    void require(const QString& value) { if (!take(value)) fail("Expected '" + value + "'"); }
    Token next() { if (pos >= tokens.size()) fail("Unexpected end of script"); return tokens[pos++]; }
    Token value() {
        if (is("\n") || is("}") || is("{") || is(";") || is(")")) fail("Expected a value");
        return next();
    }
    void tokenize(const QString& source) {
        if (source.size() > 1024 * 1024) throw Error("Script exceeds 1 MiB");
        int line = 1;
        qsizetype i = 0;
        while (i < source.size()) {
            QChar c = source[i];
            if (c == '\n') { tokens.append({"\n", line++}); ++i; continue; }
            if (c.isSpace()) { ++i; continue; }
            if (c == '#') { while (i < source.size() && source[i] != '\n') ++i; continue; }
            const int startLine = line;
            if (c == '{' && tokens.size() >= 2 &&
                (tokens[tokens.size()-2].text == "cpp" || tokens[tokens.size()-2].text == "go" || tokens[tokens.size()-2].text == "rust")) {
                const auto start = ++i;
                int depth = 1;
                QChar quote;
                bool escape = false, lineComment = false, blockComment = false;
                for (; i < source.size(); ++i) {
                    c = source[i];
                    QChar following = i + 1 < source.size() ? source[i+1] : QChar();
                    if (c == '\n') { ++line; lineComment = false; }
                    if (lineComment) continue;
                    if (blockComment) { if (c == '*' && following == '/') { blockComment = false; ++i; } continue; }
                    if (!quote.isNull()) {
                        if (escape) escape = false;
                        else if (c == '\\' && quote != '`') escape = true;
                        else if (c == quote) quote = {};
                        continue;
                    }
                    if (c == 'R' && following == '"') {
                        const auto open = source.indexOf('(', i+2);
                        if (open < 0 || open-i > 18) throw Error("Invalid C++ raw string delimiter");
                        const auto closing = ")" + source.mid(i+2, open-i-2) + "\"";
                        const auto end = source.indexOf(closing, open+1);
                        if (end < 0) throw Error("Unclosed C++ raw string");
                        line += source.mid(i, end+closing.size()-i).count('\n');
                        i = end+closing.size()-1;
                        continue;
                    }
                    if (c == '/' && following == '/') { lineComment = true; ++i; }
                    else if (c == '/' && following == '*') { blockComment = true; ++i; }
                    else if (c == '"' || c == '`' || (c == '\'' &&
                             (following == '\\' || (i+2 < source.size() && source[i+2] == '\'')))) quote = c;
                    else if (c == '{') ++depth;
                    else if (c == '}' && --depth == 0) break;
                }
                if (depth != 0) throw Error(QString("Line %1: Unclosed native block").arg(startLine));
                tokens.append({source.mid(start, i-start), startLine, true});
                ++i;
                continue;
            }
            if (c == '\'' || c == '"') {
                const QChar quote = c;
                QString text;
                ++i;
                while (i < source.size() && source[i] != quote) {
                    c = source[i++];
                    if (c == '\n') ++line;
                    if (c == '\\' && i < source.size()) {
                        const auto escaped = source[i++];
                        if (escaped == 'n') c = '\n';
                        else if (escaped == 't') c = '\t';
                        else if (escaped == quote || escaped == '\\') c = escaped;
                        else { text += c; c = escaped; }
                    }
                    text += c;
                }
                if (i >= source.size()) throw Error(QString("Line %1: Unterminated string").arg(startLine));
                ++i;
                tokens.append({text, startLine, true});
                continue;
            }
            const QString pair = source.mid(i, 2);
            if (QStringList{"==", "!=", ">=", "<=", "->"}.contains(pair)) {
                tokens.append({pair, line}); i += 2; continue;
            }
            if (QString("{}(),;=><").contains(c)) { tokens.append({QString(c), line}); ++i; continue; }
            const auto start = i++;
            while (i < source.size() && !source[i].isSpace() && !QString("{}(),;=><\"'#").contains(source[i]) && source.mid(i,2) != "->" && source.mid(i,2) != "!=") ++i;
            tokens.append({source.mid(start, i-start), startLine});
        }
    }
};
struct Return { QString value; };
struct Break {};
void writeFile(const QString& path, const QByteArray& data) {
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly) || file.write(data) != data.size()) throw Error("Cannot write " + path);
}
}

ShadowScript::ShadowScript(Output output, Directive directive, Cancel cancel)
    : m_output(std::move(output)), m_directive(std::move(directive)), m_cancel(std::move(cancel)) {}

QVector<Statement> ShadowScript::parse(const QString& source) { return Parser(source).program(); }

QString ShadowScript::resolve(const QString& value) const {
    static const QRegularExpression reference("\\$([A-Za-z_][A-Za-z0-9_]*)");
    auto matches = reference.globalMatch(value);
    QString result;
    qsizetype offset = 0;
    while (matches.hasNext()) {
        const auto match = matches.next();
        result += value.mid(offset, match.capturedStart()-offset) + m_variables.value(match.captured(1));
        offset = match.capturedEnd();
    }
    return result + value.mid(offset);
}

bool ShadowScript::condition(const QStringList& args) const {
    if (args.isEmpty()) return false;
    const auto left = resolve(args[0]);
    if (args.size() == 1) return !QStringList{"", "0", "false", "none"}.contains(left.toLower());
    const auto right = resolve(args[2]);
    const auto op = args[1];
    if (op == "==") return left == right;
    if (op == "!=") return left != right;
    bool aOk, bOk;
    const auto a = left.toDouble(&aOk), b = right.toDouble(&bOk);
    if (!aOk || !bOk) throw Error("Numeric comparison requires numbers");
    if (op == ">") return a > b;
    if (op == "<") return a < b;
    if (op == ">=") return a >= b;
    if (op == "<=") return a <= b;
    throw Error("Unknown condition operator: " + op);
}

void ShadowScript::output(const QString& value) {
    m_variables["LAST"] = value;
    if (m_output) m_output(value);
}

QJsonObject ShadowScript::run(const QString& source, const QString& sourceDirectory) {
    m_variables.clear(); m_native.clear(); m_steps = 0; m_loadDepth = 0;
    m_directory = sourceDirectory.isEmpty() ? QDir::currentPath() : sourceDirectory;
    const auto statements = parse(source); // Parse the entire script before executing anything.
    try { execute(statements); }
    catch (const Return& result) { m_variables["RESULT"] = result.value; }
    QJsonObject result;
    for (auto it = m_variables.cbegin(); it != m_variables.cend(); ++it) result.insert(it.key(), it.value());
    return result;
}

void ShadowScript::execute(const QVector<Statement>& statements, bool unsafe, int loopDepth) {
    for (const auto& s : statements) {
        checkCancelled(m_cancel);
        if (++m_steps > 100000) throw Error("Mission exceeded its instruction limit");
        const auto command = s.command;
        if (command == "VAR" || command == "SET") m_variables[s.args[0]] = resolve(s.args[1]);
        else if (command == "IF") execute(condition(s.args) ? s.body : s.otherwise, unsafe, loopDepth);
        else if (command == "FOR") {
            try {
                for (qsizetype i = 2; i < s.args.size(); ++i) {
                    if (s.args[i] == ",") continue;
                    m_variables[s.args[0]] = resolve(s.args[i]);
                    execute(s.body, unsafe, loopDepth+1);
                }
            } catch (const Break&) {}
        } else if (command == "WHILE") {
            int iterations = 0;
            try {
                while (condition(s.args)) {
                    if (++iterations > 1000) throw Error("WHILE exceeded 1000 iterations");
                    execute(s.body, unsafe, loopDepth+1);
                }
            } catch (const Break&) {}
        } else if (command == "BREAK") {
            if (!loopDepth) throw Error("BREAK requires a loop");
            throw Break{};
        } else if (command == "RETURN") throw Return{resolve(s.args.value(0))};
        else if (command == "YIELD") { m_variables["YIELD"] = resolve(s.args.value(0)); output("YIELD: " + m_variables["YIELD"]); }
        else if (command == "UNSAFE") execute(s.body, true, loopDepth);
        else if (command == "MAP" || command == "FILTER") {
            const auto items = m_variables.value("LAST").split('\n', Qt::SkipEmptyParts);
            QStringList kept;
            try {
                for (const auto& item : items) {
                    m_variables["ITEM"] = item;
                    if (command == "FILTER") {
                        if (condition(s.args)) kept.append(item);
                    } else execute(s.body, unsafe, loopDepth+1);
                }
            } catch (const Break&) {}
            if (command == "FILTER") {
                m_variables["FILTERED"] = kept.join('\n');
                output(QString("FILTER: %1 items matched").arg(kept.size()));
            }
        } else if (command == "cpp" || command == "go" || command == "rust") {
            m_native[s.args[0]] = s;
        } else {
            try { call(s, unsafe); }
            catch (const Error& error) { throw Error(QString("Line %1: %2").arg(s.line).arg(error.what())); }
        }
    }
}

void ShadowScript::call(const Statement& s, bool unsafe) {
    QStringList args;
    for (const auto& arg : s.args) args.append(resolve(arg));
    if (s.command == "!echo") { output(args.join(' ')); return; }
    if (s.command == "TARGET") {
        if (args.size() != 1 || args[0].isEmpty()) throw Error("TARGET requires one target");
        m_variables["CURRENT_TARGET"] = args[0];
        output("Target locked → " + args[0]);
        return;
    }
    if (s.command == "!sleep") {
        bool ok;
        const double seconds = args.value(0, "1").toDouble(&ok);
        if (!ok || !std::isfinite(seconds) || seconds < 0 || seconds > 120) throw Error("Sleep must be between 0 and 120 seconds");
        QElapsedTimer timer; timer.start();
        while (timer.elapsed() < seconds * 1000) { checkCancelled(m_cancel); QThread::msleep(10); }
        return;
    }
    if (s.command == "!sys" || s.command == "!pipe") {
        if (!unsafe) throw Error(s.command + " requires UNSAFE { }");
        auto command = splitCommand(args.join(' '));
        const auto program = command.takeFirst();
        const auto result = runProcess(program, command, m_cancel);
        m_variables["EXIT_CODE"] = QString::number(result.exitCode);
        const auto text = QString::fromUtf8(s.command == "!pipe" ? result.out : result.out + result.err).trimmed();
        if (s.command == "!pipe") m_variables["PIPE_OUT"] = text;
        output(text);
        return;
    }
    if (s.command == "LOAD") {
        if (args.size() != 1 || args[0].isEmpty()) throw Error("LOAD requires a file");
        if (m_loadDepth >= 16) throw Error("LOAD nesting exceeded 16 files");
        const auto path = QDir(m_directory).absoluteFilePath(args[0]);
        QFile file(path);
        if (!file.open(QIODevice::ReadOnly)) throw Error("Cannot read " + path);
        const auto body = parse(QString::fromUtf8(file.read(1024 * 1024 + 1)));
        const auto previousDirectory = m_directory;
        m_directory = QFileInfo(path).absolutePath();
        ++m_loadDepth;
        try { execute(body, unsafe); }
        catch (...) { --m_loadDepth; m_directory = previousDirectory; throw; }
        --m_loadDepth; m_directory = previousDirectory;
        return;
    }
    if (m_native.contains(s.command)) {
        if (!unsafe) throw Error("Native functions require UNSAFE { }");
        output(invokeNative(m_native[s.command], args));
        return;
    }
    QString method;
    QStringList callArgs;
    if (s.command == "SCAN") {
        method = "network.port_scan";
        callArgs = {m_variables.value("CURRENT_TARGET"), args.isEmpty() ? "1-1000" : args.join(',')};
    } else if (s.command == "STRIKE" || s.command == "!module") {
        if (args.size() < 2) throw Error("Module and method are required");
        method = args[0] + "." + args[1];
        callArgs = args.mid(2);
        if (s.command == "STRIKE" && !m_variables.value("CURRENT_TARGET").isEmpty()) callArgs.prepend(m_variables["CURRENT_TARGET"]);
    } else if (s.command == "AI") { method = "ai.chat"; callArgs = {args.join(' ')}; }
    else throw Error("Unsupported directive: " + s.command);
    if (!m_directive) throw Error("No native handler for " + method);
    const auto text = m_directive(method, callArgs, m_cancel);
    if (s.command == "AI") m_variables["AI_RESULT"] = text;
    output(text);
}

QString ShadowScript::invokeNative(const Statement& definition, const QStringList& args) {
    // Private per-invocation files avoid stale or writable shared compiler caches.
    QTemporaryDir directory;
    if (!directory.isValid()) throw Error("Cannot create native build directory");
    const auto language = definition.command;
    const auto binary = directory.filePath("shadow_native");
    QString program;
    QStringList compilerArgs;
    const auto source = resolve(definition.args[1]).toUtf8();
    if (language == "cpp") {
        const auto path = directory.filePath("main.cpp"); writeFile(path, source);
        program = "c++"; compilerArgs = {"-std=c++17", "-O2", path, "-o", binary};
    } else if (language == "go") {
        const auto path = directory.filePath("main.go"); writeFile(path, source);
        program = "go"; compilerArgs = {"build", "-o", binary, path};
    } else {
        QDir(directory.path()).mkdir("src");
        writeFile(directory.filePath("src/main.rs"), source);
        writeFile(directory.filePath("Cargo.toml"), "[package]\nname = \"shadow_native\"\nversion = \"0.1.0\"\nedition = \"2021\"\n[dependencies]\nserde_json = \"1\"\n");
        program = "cargo"; compilerArgs = {"build", "--release", "--manifest-path", directory.filePath("Cargo.toml")};
    }
    const auto compiled = runProcess(program, compilerArgs, m_cancel, 120000, {}, directory.path());
    if (compiled.exitCode) throw Error("Native compilation failed: " + QString::fromUtf8(compiled.err).right(4000));
    const auto executable = language == "rust" ? directory.filePath("target/release/shadow_native") : binary;
    QJsonObject payload;
    for (auto it = m_variables.cbegin(); it != m_variables.cend(); ++it) payload.insert(it.key(), it.value());
    for (qsizetype i = 0; i < args.size(); ++i) payload.insert("arg" + QString::number(i), args[i]);
    const auto result = runProcess(executable, {}, m_cancel, 60000, QJsonDocument(payload).toJson(QJsonDocument::Compact));
    if (result.exitCode) throw Error("Native function failed: " + QString::fromUtf8(result.err).right(4000));
    QStringList lines;
    for (const auto& line : QString::fromUtf8(result.out).split('\n', Qt::SkipEmptyParts)) {
        if (line.startsWith("SHADOWVAR:")) {
            const auto equals = line.indexOf('=', 10);
            if (equals >= 0) m_variables[line.mid(10, equals-10).trimmed()] = line.mid(equals+1).trimmed();
        } else lines.append(line);
    }
    const auto text = lines.join('\n');
    m_variables["NATIVE_RESULT"] = text;
    return text;
}
}
