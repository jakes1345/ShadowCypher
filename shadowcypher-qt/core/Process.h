#pragma once
#include <QByteArray>
#include <QStringList>
#include <atomic>
#include <functional>
#include <memory>
#include <stdexcept>

namespace shadow {
using Cancel = std::shared_ptr<std::atomic_bool>;
using Output = std::function<void(const QString&)>;
class Error : public std::runtime_error {
public:
    explicit Error(const QString& message) : std::runtime_error(message.toUtf8().constData()) {}
};
struct ProcessResult {
    int exitCode = -1;
    QByteArray out;
    QByteArray err;
};
void checkCancelled(const Cancel& cancel);
ProcessResult runProcess(const QString& program, const QStringList& args = {},
                         const Cancel& cancel = {}, int timeoutMs = 120000,
                         const QByteArray& input = {}, const QString& directory = {});
QStringList splitCommand(const QString& command);
}
