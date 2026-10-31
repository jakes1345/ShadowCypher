#pragma once
#include "NativeTools.h"
#include <optional>

namespace shadow {
class Protocol {
public:
    explicit Protocol(NativeTools tools, Cancel cancel = {});
    std::optional<QJsonObject> handle(const QByteArray& line) const;
    static QJsonArray tools();
private:
    NativeTools m_tools;
    Cancel m_cancel;
};
}
