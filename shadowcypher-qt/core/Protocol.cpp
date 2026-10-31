#include "Protocol.h"
#include <QJsonDocument>

namespace shadow {
namespace {
QJsonObject error(const QJsonValue& id, int code, const QString& message) {
    return {{"jsonrpc", "2.0"}, {"id", id}, {"error", QJsonObject{{"code", code}, {"message", message}}}};
}
QJsonObject result(const QJsonValue& id, const QJsonObject& value) {
    return {{"jsonrpc", "2.0"}, {"id", id}, {"result", value}};
}
QJsonObject textContent(const QJsonObject& value, bool failed = false) {
    return {{"content", QJsonArray{QJsonObject{{"type", "text"}, {"text", QString::fromUtf8(QJsonDocument(value).toJson(QJsonDocument::Compact))}}}}, {"isError", failed}};
}
}

Protocol::Protocol(NativeTools tools, Cancel cancel) : m_tools(std::move(tools)), m_cancel(std::move(cancel)) {}

QJsonArray Protocol::tools() {
    const QJsonObject target{{"type", "string"}, {"description", "IP address or hostname"}};
    return {
        QJsonObject{{"name", "shadowcypher_network_scan"}, {"description", "Read the local neighbor table. Does not probe undiscovered hosts."},
            {"inputSchema", QJsonObject{{"type", "object"}, {"properties", QJsonObject{}}, {"additionalProperties", false}}}},
        QJsonObject{{"name", "shadowcypher_port_scan"}, {"description", "Check selected TCP ports on an authorized target."},
            {"inputSchema", QJsonObject{{"type", "object"}, {"properties", QJsonObject{{"target", target}, {"ports", QJsonObject{{"type", "string"}, {"default", "22,80,443,8080"}}}}},
                {"required", QJsonArray{"target"}}, {"additionalProperties", false}}}},
        QJsonObject{{"name", "shadowcypher_ai_query"}, {"description", "Ask the configured local Ollama model to analyze supplied evidence."},
            {"inputSchema", QJsonObject{{"type", "object"}, {"properties", QJsonObject{{"message", QJsonObject{{"type", "string"}}}}},
                {"required", QJsonArray{"message"}}, {"additionalProperties", false}}}}
    };
}

std::optional<QJsonObject> Protocol::handle(const QByteArray& line) const {
    QJsonParseError parseError;
    const auto document = QJsonDocument::fromJson(line, &parseError);
    if (parseError.error != QJsonParseError::NoError) return error(QJsonValue::Null, -32700, "Parse error");
    if (!document.isObject()) return error(QJsonValue::Null, -32600, "Expected a JSON-RPC object");
    const auto request = document.object();
    const auto id = request.value("id");
    const auto responseId = id.isUndefined() ? QJsonValue(QJsonValue::Null) : id;
    if ((!id.isUndefined() && !id.isNull() && !id.isString() && !id.isDouble()) ||
        request.value("jsonrpc") != "2.0" || !request.value("method").isString())
        return error(QJsonValue::Null, -32600, "Invalid JSON-RPC request");
    // Notifications never receive a response or execute tools.
    if (id.isUndefined()) return std::nullopt;
    if (request.contains("params") && !request.value("params").isObject()) return error(responseId, -32602, "params must be an object");
    const auto method = request.value("method").toString();
    const auto params = request.value("params").toObject();
    if (method == "initialize") {
        const QString requested = params.value("protocolVersion").toString();
        const QString version = QStringList{"2024-11-05", "2025-03-26", "2025-06-18"}.contains(requested) ? requested : "2024-11-05";
        return result(responseId, {{"protocolVersion", version}, {"capabilities", QJsonObject{{"tools", QJsonObject{}}}},
            {"serverInfo", QJsonObject{{"name", "shadowcypher-native"}, {"version", "0.1.0"}}}});
    }
    if (method == "ping") return result(responseId, {});
    if (method == "tools/list") return result(responseId, {{"tools", tools()}});
    if (method != "tools/call") return error(responseId, -32601, "Method not found");
    if (!params.value("name").isString() || (params.contains("arguments") && !params.value("arguments").isObject()))
        return error(responseId, -32602, "Expected tool name and arguments object");
    const auto name = params.value("name").toString();
    const auto args = params.value("arguments").toObject();
    QStringList allowed;
    if (name == "shadowcypher_port_scan") allowed = {"target", "ports"};
    else if (name == "shadowcypher_ai_query") allowed = {"message"};
    else if (name != "shadowcypher_network_scan") return error(responseId, -32602, "Tool not found");
    for (auto it = args.begin(); it != args.end(); ++it)
        if (!allowed.contains(it.key()) || !it.value().isString()) return error(responseId, -32602, "Invalid tool argument: " + it.key());
    if (name == "shadowcypher_port_scan" && args.value("target").toString().isEmpty()) return error(responseId, -32602, "target is required");
    if (name == "shadowcypher_ai_query" && args.value("message").toString().isEmpty()) return error(responseId, -32602, "message is required");
    try {
        QJsonObject value;
        if (name == "shadowcypher_network_scan") value = {{"devices", m_tools.discover(m_cancel)}};
        else if (name == "shadowcypher_port_scan") value = m_tools.portScan(args.value("target").toString(), args.value("ports").toString("22,80,443,8080"), m_cancel);
        else value = m_tools.chat(args.value("message").toString(), m_cancel);
        return result(responseId, textContent(value));
    } catch (const std::exception& exception) {
        return result(responseId, textContent({{"error", QString::fromUtf8(exception.what())}}, true));
    }
}
}
