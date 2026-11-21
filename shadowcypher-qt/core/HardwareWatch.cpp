#include "HardwareWatch.h"
#include <QDir>
#include <QFile>
#include <QRegularExpression>

namespace shadow {

namespace {

constexpr int kMaxName  = 48;    // a USB device chooses its own names; keep them short
constexpr int kMaxKnown = 2048;  // past this, new devices keep being reported instead of remembered

// The kernel's name for a USB device: bus, then the chain of ports to reach it.
const QRegularExpression& usbDeviceName() {
    static const QRegularExpression re(QStringLiteral("^\\d+-\\d+(\\.\\d+)*$"));
    return re;
}

// Device names end up in incident text, so only plain characters get through.
QString cleanName(const QByteArray& raw) {
    QString out;
    for (const QChar c : QString::fromUtf8(raw).simplified()) {
        if (c.isLetterOrNumber() || c == ' ' || QStringLiteral("-_.,:/()+#'").contains(c))
            out.append(c);
        if (out.size() == kMaxName) break;
    }
    return out.trimmed();
}

QByteArray readAttr(const QString& dir, const char* name) {
    QFile f(dir + '/' + QLatin1String(name));
    if (!f.open(QIODevice::ReadOnly)) return {};
    return f.read(512).trimmed();
}

QString where(const HardwareDevice& d) {
    return d.bus == HardwareDevice::Bus::Usb ? QStringLiteral("USB ") + d.port
                                             : QStringLiteral("Bluetooth");
}

HardwareFinding finding(const HardwareDevice& d, const char* type, const char* severity,
                        const QString& description) {
    return {QLatin1String(type), QLatin1String(severity), where(d), description};
}

HardwareFinding newKeyboard(const HardwareDevice& d) {
    if (d.bus == HardwareDevice::Bus::Bluetooth)
        return finding(d, "new_keyboard", "medium", QStringLiteral(
            "A Bluetooth keyboard this computer has not used before connected: %1. If you did "
            "not pair a keyboard, remove it from your Bluetooth devices: some computers can be "
            "made to accept one without asking.").arg(d.label()));
    if (d.storage || d.network) {
        const QString other = d.storage ? QStringLiteral("storage drive")
                                        : QStringLiteral("network adapter");
        return finding(d, "new_keyboard", "high", QStringLiteral(
            "A device that is both a keyboard and a %1 was plugged in: %2. Ordinary keyboards "
            "are not %1s, and an ordinary %1 cannot type. Unless you know what it is, unplug it "
            "and check what was typed: new terminal windows, your shell history, new startup "
            "entries.").arg(other, d.label()));
    }
    return finding(d, "new_keyboard", "medium", QStringLiteral(
        "A keyboard this computer has not used before was plugged in: %1. If you did not plug "
        "in a keyboard, unplug whatever you just connected: a USB stick or a charging cable can "
        "hide a keyboard that types commands.").arg(d.label()));
}

HardwareFinding newNetwork(const HardwareDevice& d) {
    return finding(d, "new_usb_network", "medium", QStringLiteral(
        "A network adapter this computer has not used before was plugged in: %1. Your traffic "
        "can be sent through it. A phone sharing its connection looks the same; if you "
        "connected nothing like that, unplug it.").arg(d.label()));
}

}  // namespace

// ── Devices ───────────────────────────────────────────────────────────────────

QString HardwareDevice::id() const {
    return QStringLiteral("%1:%2").arg(vendorId, 4, 16, QLatin1Char('0'))
                                  .arg(productId, 4, 16, QLatin1Char('0'));
}

QString HardwareDevice::label() const {
    QString named = product;
    if (!manufacturer.isEmpty() && !product.startsWith(manufacturer, Qt::CaseInsensitive))
        named = (manufacturer + ' ' + product).trimmed();
    return named.isEmpty() ? QStringLiteral("no name (%1)").arg(id())
                           : QStringLiteral("%1 (%2)").arg(named, id());
}

QString HardwareDevice::identity() const {
    QStringList does;
    if (keyboard) does << QStringLiteral("keyboard");
    if (storage)  does << QStringLiteral("storage");
    if (network)  does << QStringLiteral("network");
    const bool usb = bus == Bus::Usb;
    // cleanName never lets '|' through, so the parts cannot run into each other
    return QStringList{usb ? QStringLiteral("usb") : QStringLiteral("bluetooth"), id(),
                       manufacturer, product, usb ? serial : port, does.join('+')}
        .join('|');
}

// ── Reading what the kernel reports ───────────────────────────────────────────

QList<InputDevice> parseInputDevices(const QByteArray& text) {
    QList<InputDevice> out;
    InputDevice cur;
    bool any = false;
    const auto flush = [&] {
        if (any) out.append(cur);
        cur = InputDevice();
        any = false;
    };
    const auto unquoted = [](QByteArray v) {
        if (v.size() >= 2 && v.startsWith('"') && v.endsWith('"')) v = v.mid(1, v.size() - 2);
        return v;
    };
    for (const QByteArray& raw : text.split('\n')) {
        const QByteArray line = raw.trimmed();
        if (line.isEmpty()) { flush(); continue; }
        any = true;
        if (line.startsWith("I:")) {
            for (const QByteArray& field : line.mid(2).simplified().split(' ')) {
                const int eq = field.indexOf('=');
                if (eq < 0) continue;
                const QByteArray key = field.left(eq);
                const uint value = field.mid(eq + 1).toUInt(nullptr, 16);
                if (key == "Bus")          cur.bus = static_cast<int>(value);
                else if (key == "Vendor")  cur.vendorId = static_cast<quint16>(value);
                else if (key == "Product") cur.productId = static_cast<quint16>(value);
            }
        } else if (line.startsWith("N: Name=")) {
            cur.name = cleanName(unquoted(line.mid(8)));
        } else if (line.startsWith("S: Sysfs=")) {
            cur.sysfs = QString::fromUtf8(line.mid(9));
        } else if (line.startsWith("U: Uniq=")) {
            cur.uniq = cleanName(line.mid(8)).toLower();
        } else if (line.startsWith("B: KEY=")) {
            // The key bitmap is printed highest word first, so the last word
            // holds keys 0 to 31: Esc, the digits and Q through D. udev calls a
            // device a keyboard when it has all of them (bit 0 is unused), and
            // so does this.
            const quint64 low = line.mid(7).simplified().split(' ').last().toULongLong(nullptr, 16);
            cur.keyboard = (low & 0xFFFFFFFEull) == 0xFFFFFFFEull;
        }
    }
    flush();
    return out;
}

QString usbPortOf(const QString& sysfsPath) {
    QString port;
    // A device behind a hub has the hub earlier in its path; the last match is the device.
    for (const QString& part : sysfsPath.split('/', Qt::SkipEmptyParts))
        if (usbDeviceName().match(part).hasMatch()) port = part;
    return port;
}

QList<HardwareDevice> readHardware(const QString& usbSysfsDir, const QByteArray& inputDevices) {
    QList<HardwareDevice> out;
    QSet<QString> typingPorts;
    QSet<QString> bluetoothSeen;
    for (const InputDevice& in : parseInputDevices(inputDevices)) {
        if (!in.keyboard) continue;
        if (in.bus == InputDevice::kBusUsb) {
            // Empty for a keyboard a program made up (it has no USB device behind it).
            const QString port = usbPortOf(in.sysfs);
            if (!port.isEmpty()) typingPorts.insert(port);
        } else if (in.bus == InputDevice::kBusBluetooth) {
            HardwareDevice d;
            d.bus       = HardwareDevice::Bus::Bluetooth;
            d.port      = in.uniq;
            d.vendorId  = in.vendorId;
            d.productId = in.productId;
            d.product   = in.name;
            d.keyboard  = true;
            // One keyboard can register several input devices
            const QString identity = d.identity();
            if (bluetoothSeen.contains(identity)) continue;
            bluetoothSeen.insert(identity);
            out.append(d);
        }
    }

    const QDir root(usbSysfsDir);
    const QStringList entries = root.entryList(QDir::Dirs | QDir::NoDotAndDotDot, QDir::Name);
    for (const QString& name : entries) {
        if (!usbDeviceName().match(name).hasMatch()) continue;  // skips root hubs and interfaces
        const QString dir = root.filePath(name);
        HardwareDevice d;
        d.port         = name;
        d.vendorId     = static_cast<quint16>(readAttr(dir, "idVendor").toUInt(nullptr, 16));
        d.productId    = static_cast<quint16>(readAttr(dir, "idProduct").toUInt(nullptr, 16));
        d.manufacturer = cleanName(readAttr(dir, "manufacturer"));
        d.product      = cleanName(readAttr(dir, "product"));
        d.serial       = cleanName(readAttr(dir, "serial"));
        d.keyboard     = typingPorts.contains(name);
        const QString prefix = name + ':';
        for (const QString& iface : entries) {
            if (!iface.startsWith(prefix)) continue;
            const QString ifaceDir = root.filePath(iface);
            if (readAttr(ifaceDir, "bInterfaceClass").toUInt(nullptr, 16) == 0x08) d.storage = true;
            // The kernel lists the network interface it made for this one here
            if (!QDir(ifaceDir + QStringLiteral("/net"))
                     .entryList(QDir::Dirs | QDir::NoDotAndDotDot).isEmpty())
                d.network = true;
        }
        out.append(d);
    }
    return out;
}

// ── Known attack hardware ─────────────────────────────────────────────────────

std::optional<HardwareFinding> matchAttackHardware(const HardwareDevice& d) {
    if (d.bus == HardwareDevice::Bus::Bluetooth) {
        // Flipper Zero typing over Bluetooth. flipperzero-firmware,
        // applications/main/bad_usb/helpers/bad_usb_hid.c:
        //   const char* badusb_device_name_prefix = "BadUSB";
        // followed by a space and the Flipper's own name.
        if (d.keyboard && d.product.startsWith(QStringLiteral("BadUSB ")))
            return finding(d, "attack_hardware", "high", QStringLiteral(
                "A Bluetooth keyboard that calls itself \"%1\" connected. A Flipper Zero gives "
                "itself that name when it types commands over Bluetooth, unless its owner "
                "changed it. If it is not yours, remove it from your Bluetooth devices and "
                "check what was typed.").arg(d.product));
        return std::nullopt;
    }

    // Flipper Zero under its own name. flipperzero-firmware,
    // targets/f7/furi_hal/furi_hal_usb_cdc.c:
    //   USB_STRING_DESC("Flipper Devices Inc."), .idVendor = 0x0483, .idProduct = 0x5740
    // 0483:5740 alone is the ID every STM32 serial port shares, so the maker's
    // name is what identifies it.
    if (d.manufacturer == QStringLiteral("Flipper Devices Inc.")) {
        if (d.keyboard)
            return finding(d, "attack_hardware", "high", QStringLiteral(
                "A Flipper Zero is plugged into this computer as a keyboard (%1). It can type "
                "commands by itself. If it is not yours, unplug it and check what was typed.")
                .arg(d.label()));
        return finding(d, "attack_hardware", "medium", QStringLiteral(
            "A Flipper Zero is plugged into this computer (%1). Connected like this it charges "
            "and talks to its own app; it cannot type. If it is not yours, unplug it.")
            .arg(d.label()));
    }

    // Flipper Zero typing as a keyboard. targets/furi_hal_include/furi_hal_usb_hid.h:
    //   #define HID_VID_DEFAULT 0x046D
    //   #define HID_PID_DEFAULT 0xC529
    // and furi_hal_usb_hid.c sets iManufacturer and iProduct to 0 unless the
    // script being run supplies names. So: Logitech's vendor ID, and no names.
    if (d.keyboard && d.vendorId == 0x046D && d.productId == 0xC529
        && d.manufacturer.isEmpty() && d.product.isEmpty())
        return finding(d, "attack_hardware", "high", QStringLiteral(
            "A keyboard was plugged in that uses a Logitech ID (046d:c529) but gives no maker "
            "or product name. A Flipper Zero looks exactly like this when it types commands, "
            "unless its owner changed it. If you did not expect it, unplug it and check what "
            "was typed: new terminal windows, your shell history, new startup entries."));

    // Digispark, the small ATtiny85 board sold as a cheap keystroke injector.
    // DigistumpArduino, libraries/DigisparkKeyboard/usbconfig.h:
    //   #define USB_CFG_VENDOR_ID 0xc0, 0x16
    //   #define USB_CFG_DEVICE_ID 0xdb, 0x27
    //   #define USB_CFG_VENDOR_NAME 'd','i','g','i','s','t','u','m','p','.','c','o','m'
    // 16c0:27db is shared by other hobby keyboards, so the name is required.
    if (d.vendorId == 0x16C0 && d.productId == 0x27DB
        && d.manufacturer == QStringLiteral("digistump.com"))
        return finding(d, "attack_hardware", "high", QStringLiteral(
            "A Digispark board set up as a keyboard was plugged in (%1). It is a bare circuit "
            "board with no keys: it types whatever it was programmed to. If you did not "
            "program it yourself, unplug it and check what was typed.").arg(d.label()));

    return std::nullopt;
}

// ── Watching ──────────────────────────────────────────────────────────────────

HardwareWatch::HardwareWatch(const QStringList& known, bool baselined)
    : m_known(known.begin(), known.end()), m_baselined(baselined) {}

QStringList HardwareWatch::known() const {
    QStringList list(m_known.begin(), m_known.end());
    list.sort();
    return list;
}

QList<HardwareFinding> HardwareWatch::observe(const QList<HardwareDevice>& now) {
    QList<HardwareFinding> findings;
    QSet<QString> present;
    const bool firstLook = !m_baselined;
    for (const HardwareDevice& d : now) {
        const auto tool = matchAttackHardware(d);
        if (!tool && !d.keyboard && !d.network) continue;  // a drive, a mouse, a webcam
        const QString identity = d.identity();
        const QString plug = d.port + '|' + identity;
        present.insert(plug);
        if (m_present.contains(plug)) continue;  // still plugged in since the last look
        if (tool) {
            findings.append(*tool);
            continue;
        }
        if (m_known.contains(identity)) continue;
        const bool remembered = m_known.size() < kMaxKnown;
        if (remembered) m_known.insert(identity);
        if (firstLook && remembered) continue;
        findings.append(d.keyboard ? newKeyboard(d) : newNetwork(d));
    }
    m_present = present;
    m_baselined = true;
    return findings;
}

}  // namespace shadow
