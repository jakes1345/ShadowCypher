#pragma once
#include <QByteArray>
#include <QList>
#include <QSet>
#include <QString>
#include <QStringList>
#include <optional>

namespace shadow {

// Watches what is plugged into this computer for hardware that can type on its
// own: a "USB stick" or cable that is really a keyboard, a Flipper Zero, a
// drive that also types. It works from what the kernel says about each device
// (its IDs, its names, what it can do) and never reads a keystroke.
//
// What this cannot do: stop the typing. The keys are sent the moment the
// device is plugged in, so a finding says what happened; it does not prevent
// it. A device that copies the IDs and names of a keyboard already used on
// this computer is not noticed either.

// One entry of /proc/bus/input/devices.
struct InputDevice {
    static constexpr int kBusUsb       = 0x03;
    static constexpr int kBusBluetooth = 0x05;

    int     bus = 0;
    quint16 vendorId = 0;
    quint16 productId = 0;
    QString name;
    QString sysfs;            // path below /sys
    QString uniq;             // Bluetooth: the device's own address
    bool    keyboard = false; // has every key from Esc to D, the test udev uses
};

// A device that can type, hold files or carry network traffic.
struct HardwareDevice {
    enum class Bus { Usb, Bluetooth };

    Bus     bus = Bus::Usb;
    QString port;          // USB: the kernel's name for the socket, e.g. "1-2.3". Bluetooth: the device's address.
    quint16 vendorId = 0;
    quint16 productId = 0;
    QString manufacturer;  // empty when the device gives none
    QString product;
    QString serial;
    bool    keyboard = false;
    bool    storage  = false;  // has a USB mass storage interface
    bool    network  = false;  // the kernel attached a network driver to it

    QString id() const;        // "046d:c31c"
    QString label() const;     // for people: names if it has any, then the ID
    QString identity() const;  // the same for the same model doing the same things
};

struct HardwareFinding {
    QString type;         // "attack_hardware" | "new_keyboard" | "new_usb_network"
    QString severity;     // "low" | "medium" | "high"
    QString device;       // short: "USB 1-2" or "Bluetooth"
    QString description;
};

QList<InputDevice> parseInputDevices(const QByteArray& text);

// The USB device ("1-2.3") an input device's sysfs path hangs off, or empty.
QString usbPortOf(const QString& sysfsPath);

// usbSysfsDir is /sys/bus/usb/devices; inputDevices the contents of
// /proc/bus/input/devices. Both are parameters so tests can supply their own.
QList<HardwareDevice> readHardware(const QString& usbSysfsDir, const QByteArray& inputDevices);

// A device whose identity is one an attack tool uses unless its owner changed
// it. Each rule is taken from that tool's own source, quoted in the .cpp.
std::optional<HardwareFinding> matchAttackHardware(const HardwareDevice& device);

class HardwareWatch {
public:
    // known: identities recorded by an earlier run. baselined: whether an
    // earlier run already recorded what was plugged in when it first looked.
    explicit HardwareWatch(const QStringList& known = {}, bool baselined = false);

    // Call with everything present now. The first call of the first run
    // records the keyboards and network adapters already there without
    // reporting them: they were here before anyone was watching. After that
    // each one is reported the first time it is seen and then remembered.
    // Attack hardware is reported every time it is plugged in.
    QList<HardwareFinding> observe(const QList<HardwareDevice>& now);

    QStringList known() const;
    bool        baselined() const { return m_baselined; }

private:
    QSet<QString> m_known;
    bool          m_baselined;
    QSet<QString> m_present;  // already handled and still plugged in
};

}  // namespace shadow
