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

QString InstallPage::buildScript() {
    QString s;
    QTextStream ts(&s);

    ts << "#!/bin/bash\n";
    ts << "set -euo pipefail\n\n";

    ts << "DISK=" << m_state->disk << "\n";
    ts << "USERNAME=" << m_state->username << "\n";
    ts << "HOSTNAME=" << m_state->hostname << "\n";
    ts << "PROFILE=" << m_state->profile << "\n";
    ts << "LOCALE=" << m_state->locale << "\n";
    ts << "TIMEZONE=" << m_state->timezone << "\n";
    ts << "LUKS=" << (m_state->luks ? "1" : "0") << "\n\n";

    // Write archinstall config JSON
    ts << "cat > /tmp/shadowos-install.json << 'ARCHINSTALL_EOF'\n";
    ts << "{\n";
    ts << "  \"disk_config\": {\n";
    ts << "    \"config_type\": \"default_layout\",\n";
    ts << "    \"device_modifications\": [\n";
    ts << "      {\n";
    ts << "        \"device\": \"" << m_state->disk << "\",\n";
    ts << "        \"wipe\": true,\n";
    ts << "        \"partitions\": [\n";
    ts << "          { \"type\": \"primary\", \"start\": \"1MiB\", \"size\": \"512MiB\","
          " \"fs_type\": \"fat32\", \"mount_options\": [\"umask=0077\"],"
          " \"mountpoint\": \"/boot/efi\", \"flags\": [\"boot\", \"esp\"] },\n";
    if (m_state->luks) {
        ts << "          { \"type\": \"primary\", \"start\": \"513MiB\", \"size\": \"100%\","
              " \"fs_type\": \"btrfs\", \"mountpoint\": \"/\","
              " \"btrfs\": { \"subvolumes\": {\""
              "@\": \"/\", \"@home\": \"/home\", \"@snapshots\": \"/.snapshots\","
              "\"@log\": \"/var/log\", \"@pkg\": \"/var/cache/pacman/pkg\" } },"
              " \"encrypt\": true }\n";
    } else {
        ts << "          { \"type\": \"primary\", \"start\": \"513MiB\", \"size\": \"100%\","
              " \"fs_type\": \"btrfs\", \"mountpoint\": \"/\","
              " \"btrfs\": { \"subvolumes\": {\""
              "@\": \"/\", \"@home\": \"/home\", \"@snapshots\": \"/.snapshots\","
              "\"@log\": \"/var/log\", \"@pkg\": \"/var/cache/pacman/pkg\" } } }\n";
    }
    ts << "        ]\n";
    ts << "      }\n";
    ts << "    ]\n";
    ts << "  },\n";
    ts << "  \"bootloader\": \"systemd-bootctl\",\n";
    ts << "  \"hostname\": \"" << m_state->hostname << "\",\n";
    ts << "  \"locale_config\": { \"sys_lang\": \"" << m_state->locale << "\","
          " \"sys_enc\": \"UTF-8\" },\n";
    ts << "  \"timezone\": \"" << m_state->timezone << "\",\n";
    ts << "  \"kernels\": [\"linux-hardened\"],\n";
    ts << "  \"swap\": false,\n";
    ts << "  \"packages\": [\"hyprland\",\"waybar\",\"kitty\",\"networkmanager\","
          "\"base-devel\",\"git\",\"sudo\",\"pipewire\",\"wireplumber\","
          "\"xdg-portal-hyprland\",\"polkit-kde-agent\","
          "\"noto-fonts\",\"ttf-jetbrains-mono\"],\n";
    ts << "  \"services\": [\"NetworkManager\",\"systemd-timesyncd\"],\n";
    ts << "  \"user_config\": {\n";
    ts << "    \"!users\": [\n";
    ts << "      {\n";
    ts << "        \"username\": \"" << m_state->username << "\",\n";
    ts << "        \"!password\": \"" << m_state->password << "\",\n";
    ts << "        \"groups\": [\"wheel\", \"video\", \"audio\", \"network\"],\n";
    ts << "        \"sudo\": \"WITH_PASSWORD\"\n";
    ts << "      }\n";
    ts << "    ]\n";
    ts << "  }\n";
    ts << "}\n";
    ts << "ARCHINSTALL_EOF\n\n";

    if (m_state->luks) {
        ts << "echo '" << m_state->luksPass << "' > /tmp/.luks_pass\n";
        ts << "export LUKS_PASSPHRASE=$(cat /tmp/.luks_pass)\n";
    }

    ts << "echo '>>> Starting archinstall…'\n";
    ts << "archinstall --config /tmp/shadowos-install.json --silent 2>&1\n\n";

    ts << "echo '>>> Applying ShadowOS profile: $PROFILE'\n";
    ts << "CHROOT=\"arch-chroot /mnt\"\n\n";

    ts << "# Install profile-specific packages\n";
    ts << "case \"$PROFILE\" in\n";
    ts << "  pentest)\n";
    ts << "    $CHROOT pacman -Sy --noconfirm nmap metasploit aircrack-ng wireshark-qt \\\n";
    ts << "      john hashcat sqlmap hydra nikto gobuster 2>&1\n";
    ts << "    ;;\n";
    ts << "  privacy)\n";
    ts << "    $CHROOT pacman -Sy --noconfirm tor torbrowser-launcher \\\n";
    ts << "      firejail apparmor 2>&1\n";
    ts << "    $CHROOT systemctl enable tor apparmor 2>&1\n";
    ts << "    ;;\n";
    ts << "  gaming)\n";
    ts << "    $CHROOT pacman -Sy --noconfirm steam gamescope gamemode \\\n";
    ts << "      mangohud lib32-mesa vulkan-radeon lib32-vulkan-radeon \\\n";
    ts << "      lib32-vulkan-intel 2>&1\n";
    ts << "    $CHROOT systemctl enable gamemode 2>&1\n";
    ts << "    ;;\n";
    ts << "  *)\n";
    ts << "    # standard — nothing extra beyond base\n";
    ts << "    ;;\n";
    ts << "esac\n\n";

    ts << "# Install ShadowOS base tools\n";
    ts << "$CHROOT pacman -Sy --noconfirm \\\n";
    ts << "  ghostty yazi atuin zoxide fzf \\\n";
    ts << "  anonsurf-parrot \\\n";
    ts << "  shadowcypher-qt 2>&1 || true\n\n";

    ts << "echo '>>> Cleaning up'\n";
    ts << "rm -f /tmp/shadowos-install.json /tmp/.luks_pass\n\n";

    ts << "echo '>>> ShadowOS installation complete!'\n";

    return s;
}

void InstallPage::begin() {
    appendLog("Generating installation script…");

    const QString scriptPath = "/tmp/shadowos-installer.sh";
    QFile f(scriptPath);
    if (!f.open(QIODevice::WriteOnly | QIODevice::Text)) {
        appendLog("ERROR: Cannot write install script to /tmp", true);
        emit finished(false);
        return;
    }
    f.write(buildScript().toUtf8());
    f.setPermissions(QFile::ReadOwner | QFile::WriteOwner | QFile::ExeOwner);
    f.close();

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
