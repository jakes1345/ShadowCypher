#include "InstallPage.h"
#include "../theme.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QFrame>
#include <QScrollBar>
#include <QFile>
#include <QTextStream>
#include <QDir>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>

InstallPage::InstallPage(InstallState* state, QWidget* parent)
    : QWidget(parent), m_state(state), m_proc(nullptr)
{
    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(48, 40, 48, 40);
    lay->setSpacing(16);

    auto* tag = new QLabel("STEP 06 — INSTALLING");
    tag->setStyleSheet(QString("font-size:9px;font-weight:800;letter-spacing:5px;"
                               "color:%1;font-family:'JetBrains Mono',monospace;").arg(Theme::ACCENT));
    auto* title = new QLabel("Installing ShadowOS…");
    title->setStyleSheet("font-size:28px;font-weight:900;color:#E6EDF3;");

    m_status = new QLabel("Preparing installation script…");
    m_status->setStyleSheet(QString("font-size:13px;color:%1;").arg(Theme::ACCENT));

    m_progress = new QProgressBar;
    m_progress->setRange(0, 0);
    m_progress->setTextVisible(false);
    m_progress->setFixedHeight(4);
    m_progress->setStyleSheet(QString(
        "QProgressBar { background:%1; border-radius:2px; border:none; }"
        "QProgressBar::chunk { background:%2; border-radius:2px; }"
    ).arg(Theme::BG_SURFACE, Theme::ACCENT));

    auto* divider = new QFrame;
    divider->setFrameShape(QFrame::HLine);
    divider->setStyleSheet("border: none; border-top: 1px solid rgba(0,224,164,0.12);");

    m_log = new QTextEdit;
    m_log->setReadOnly(true);
    m_log->setStyleSheet(QString(
        "QTextEdit { background:%1; color:%2; border:1px solid %3;"
        " border-radius:8px; padding:12px;"
        " font-family:'JetBrains Mono',monospace; font-size:11px; }"
    ).arg(Theme::BG_SURFACE, Theme::TEXT_SEC, Theme::BORDER_DIM));

    lay->addWidget(tag);
    lay->addWidget(title);
    lay->addWidget(m_status);
    lay->addWidget(m_progress);
    lay->addWidget(divider);
    lay->addWidget(m_log, 1);
}

namespace {

// One shell word, whatever the text holds: wrapped in single quotes, with each
// single quote closed, escaped and reopened.
QString shq(const QString& v) {
    QString out = v;
    out.replace('\'', "'\\''");
    return '\'' + out + '\'';
}

QJsonObject btrfsRoot(bool encrypted) {
    QJsonObject subvols{
        {"@", "/"}, {"@home", "/home"}, {"@snapshots", "/.snapshots"},
        {"@log", "/var/log"}, {"@pkg", "/var/cache/pacman/pkg"},
    };
    QJsonObject part{
        {"type", "primary"}, {"start", "513MiB"}, {"size", "100%"},
        {"fs_type", "btrfs"}, {"mountpoint", "/"},
        {"btrfs", QJsonObject{{"subvolumes", subvols}}},
    };
    if (encrypted) part.insert("encrypt", true);
    return part;
}

// Writes [doc] to [path] readable by root only, before any byte of it lands.
bool writePrivate(const QString& path, const QByteArray& data) {
    QFile f(path);
    f.remove();
    if (!f.open(QIODevice::WriteOnly | QIODevice::NewOnly)) return false;
    f.setPermissions(QFile::ReadOwner | QFile::WriteOwner);
    const bool ok = f.write(data) == data.size();
    f.close();
    return ok;
}

} // namespace

// The archinstall configuration, built as JSON so nothing the user typed can
// change its structure. Secrets are not in it: see credentialsJson().
QByteArray InstallPage::configJson() const {
    QJsonArray partitions{
        QJsonObject{
            {"type", "primary"}, {"start", "1MiB"}, {"size", "512MiB"},
            {"fs_type", "fat32"}, {"mount_options", QJsonArray{"umask=0077"}},
            {"mountpoint", "/boot/efi"}, {"flags", QJsonArray{"boot", "esp"}},
        },
        btrfsRoot(m_state->luks),
    };
    QJsonObject root{
        {"disk_config", QJsonObject{
            {"config_type", "default_layout"},
            {"device_modifications", QJsonArray{QJsonObject{
                {"device", m_state->disk}, {"wipe", true}, {"partitions", partitions},
            }}},
        }},
        {"bootloader", "systemd-bootctl"},
        {"hostname", m_state->hostname},
        {"locale_config", QJsonObject{{"sys_lang", m_state->locale}, {"sys_enc", "UTF-8"}}},
        {"timezone", m_state->timezone},
        {"kernels", QJsonArray{"linux-hardened"}},
        {"swap", false},
        {"packages", QJsonArray{"hyprland", "waybar", "kitty", "networkmanager",
                                "base-devel", "git", "sudo", "pipewire", "wireplumber",
                                "xdg-portal-hyprland", "polkit-kde-agent",
                                "noto-fonts", "ttf-jetbrains-mono"}},
        {"services", QJsonArray{"NetworkManager", "systemd-timesyncd"}},
    };
    return QJsonDocument(root).toJson();
}

// The user's password and the disk passphrase, for archinstall's --creds file.
QByteArray InstallPage::credentialsJson() const {
    QJsonObject creds{
        {"!users", QJsonArray{QJsonObject{
            {"username", m_state->username},
            {"!password", m_state->password},
            {"groups", QJsonArray{"wheel", "video", "audio", "network"}},
            {"sudo", true},
        }}},
    };
    if (m_state->luks) creds.insert("!encryption-password", m_state->luksPass);
    return QJsonDocument(creds).toJson();
}

QString InstallPage::buildScript() {
    QString s;
    QTextStream ts(&s);

    ts << "#!/bin/bash\n";
    ts << "set -euo pipefail\n\n";

    // Every value is one quoted word; the script never expands user text.
    ts << "DISK=" << shq(m_state->disk) << "\n";
    ts << "USERNAME=" << shq(m_state->username) << "\n";
    ts << "HOSTNAME=" << shq(m_state->hostname) << "\n";
    ts << "PROFILE=" << shq(m_state->profile) << "\n";
    ts << "LOCALE=" << shq(m_state->locale) << "\n";
    ts << "TIMEZONE=" << shq(m_state->timezone) << "\n";
    ts << "CONFIG=" << shq(kConfigPath) << "\n";
    ts << "CREDS=" << shq(kCredsPath) << "\n\n";

    ts << "cleanup() { shred -u \"$CREDS\" 2>/dev/null || rm -f \"$CREDS\"; rm -f \"$CONFIG\"; }\n";
    ts << "trap cleanup EXIT\n\n";

    ts << "echo '>>> Starting archinstall…'\n";
    ts << "archinstall --config \"$CONFIG\" --creds \"$CREDS\" --silent 2>&1\n\n";

    ts << "echo \">>> Applying ShadowOS profile: $PROFILE\"\n";
    ts << "CHROOT=(arch-chroot /mnt)\n\n";

    ts << "case \"$PROFILE\" in\n";
    ts << "  pentest)\n";
    ts << "    \"${CHROOT[@]}\" pacman -Sy --noconfirm nmap metasploit aircrack-ng wireshark-qt \\\n";
    ts << "      john hashcat sqlmap hydra nikto gobuster 2>&1\n";
    ts << "    ;;\n";
    ts << "  privacy)\n";
    ts << "    \"${CHROOT[@]}\" pacman -Sy --noconfirm tor torbrowser-launcher firejail apparmor 2>&1\n";
    ts << "    \"${CHROOT[@]}\" systemctl enable tor apparmor 2>&1\n";
    ts << "    ;;\n";
    ts << "  gaming)\n";
    ts << "    \"${CHROOT[@]}\" pacman -Sy --noconfirm steam gamescope gamemode \\\n";
    ts << "      mangohud lib32-mesa vulkan-radeon lib32-vulkan-radeon lib32-vulkan-intel 2>&1\n";
    ts << "    \"${CHROOT[@]}\" systemctl enable gamemode 2>&1\n";
    ts << "    ;;\n";
    ts << "  *) ;;\n";
    ts << "esac\n\n";

    ts << "\"${CHROOT[@]}\" pacman -Sy --noconfirm ghostty yazi atuin zoxide fzf anonsurf-parrot shadowcypher-qt 2>&1 || true\n\n";
    ts << "echo '>>> ShadowOS installation complete!'\n";
    return s;
}

void InstallPage::begin() {
    appendLog("Generating installation script…");

    const QString scriptPath = "/tmp/shadowos-installer.sh";
    if (!writePrivate(kConfigPath, configJson())
        || !writePrivate(kCredsPath, credentialsJson())
        || !writePrivate(scriptPath, buildScript().toUtf8())) {
        QFile::remove(kCredsPath);
        appendLog("ERROR: Cannot write the installation files to /tmp", true);
        emit finished(false);
        return;
    }

    appendLog("Launching installer…");
    m_status->setText("Installing — this will take 5–20 minutes…");

    m_proc = new QProcess(this);
    m_proc->setProcessChannelMode(QProcess::MergedChannels);
    connect(m_proc, &QProcess::readyRead, this, &InstallPage::onReadyRead);
    connect(m_proc, QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished),
            this, &InstallPage::onFinished);

    m_proc->start("bash", {scriptPath});
    if (!m_proc->waitForStarted(5000)) {
        appendLog("ERROR: Failed to start installation script", true);
        emit finished(false);
    }
}

void InstallPage::onReadyRead() {
    while (m_proc->canReadLine()) {
        appendLog(QString::fromUtf8(m_proc->readLine()).trimmed());
    }
}

void InstallPage::onFinished(int exitCode, QProcess::ExitStatus) {
    // Drain remaining output
    const QByteArray rem = m_proc->readAll();
    if (!rem.isEmpty()) {
        for (const auto& line : rem.split('\n')) {
            if (!line.trimmed().isEmpty())
                appendLog(QString::fromUtf8(line.trimmed()));
        }
    }

    m_progress->setRange(0, 1);
    m_progress->setValue(1);

    if (exitCode == 0) {
        m_status->setText("Installation complete!");
        m_status->setStyleSheet(QString("font-size:13px;color:%1;").arg(Theme::ACCENT));
        appendLog("=== ShadowOS installed successfully ===");
        emit finished(true);
    } else {
        m_status->setText(QString("Installation failed (exit code %1)").arg(exitCode));
        m_status->setStyleSheet(QString("font-size:13px;color:%1;").arg(Theme::DANGER));
        appendLog(QString("=== Installation exited with code %1 ===").arg(exitCode), true);
        emit finished(false);
    }
}

void InstallPage::appendLog(const QString& line, bool error) {
    const QString color = error ? Theme::DANGER : Theme::TEXT_SEC;
    m_log->append(QString("<span style='color:%1;'>%2</span>").arg(color, line.toHtmlEscaped()));
    m_log->verticalScrollBar()->setValue(m_log->verticalScrollBar()->maximum());
}
