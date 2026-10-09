#include "ArsenalPage.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QScrollArea>
#include <QLabel>
#include <QProcess>
#include <QThread>
#include <QtConcurrent/QtConcurrent>

static const QList<std::tuple<QString,QString,QString,QString>> TOOLS = {
    {"nmap",        "Nmap",         "RECON",       "pacman -S nmap"},
    {"nuclei",      "Nuclei",       "VULN",        "go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"},
    {"ffuf",        "FFuF",         "WEB",         "go install github.com/ffuf/ffuf/v2@latest"},
    {"nikto",       "Nikto",        "WEB",         "pacman -S nikto"},
    {"sqlmap",      "SQLMap",       "WEB",         "pacman -S sqlmap"},
    {"hydra",       "Hydra",        "CREDS",       "pacman -S hydra"},
    {"john",        "John",         "CREDS",       "pacman -S john"},
    {"hashcat",     "Hashcat",      "CREDS",       "pacman -S hashcat"},
    {"aircrack-ng", "Aircrack",     "WIRELESS",    "pacman -S aircrack-ng"},
    {"tcpdump",     "tcpdump",      "NETWORK",     "pacman -S tcpdump"},
    {"responder",   "Responder",    "NETWORK",     "pacman -S responder"},
    {"tor",         "Tor",          "OPSEC",       "pacman -S tor"},
    {"proxychains", "Proxychains",  "OPSEC",       "pacman -S proxychains-ng"},
    {"wireshark",   "Wireshark",    "NETWORK",     "pacman -S wireshark-qt"},
    {"metasploit",  "Metasploit",   "EXPLOIT",     "pacman -S metasploit"},
    {"burpsuite",   "Burp Suite",   "WEB",         "download from portswigger.net"},
    {"feroxbuster", "Feroxbuster",  "WEB",         "cargo install feroxbuster"},
    {"gobuster",    "GoBuster",     "WEB",         "go install github.com/OJ/gobuster/v3@latest"},
    {"crackmapexec","CrackMapExec", "AD",          "pipx install crackmapexec"},
    {"impacket-scripts","Impacket", "AD",          "pipx install impacket"},
    {"volatility3", "Volatility3",  "FORENSICS",   "pip install volatility3"},
    {"binwalk",     "Binwalk",      "FORENSICS",   "pacman -S binwalk"},
    {"stegseek",    "Stegseek",     "FORENSICS",   "pacman -S stegseek"},
    {"ollama",      "Ollama",       "AI",          "curl -fsSL https://ollama.ai/install.sh | sh"},
};

ArsenalPage::ArsenalPage(QWidget* parent) : QWidget(parent) {
    buildUi();
    // Async audit so UI doesn't block
    QtConcurrent::run([this]() { audit(); });
}

void ArsenalPage::buildUi() {
    auto* scroll = new QScrollArea(this);
    scroll->setWidgetResizable(true);
    scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    scroll->setStyleSheet("QScrollArea { border: none; background: transparent; }");

    auto* root = new QWidget;
    auto* lay  = new QVBoxLayout(root);
    lay->setContentsMargins(20, 14, 20, 20);
    lay->setSpacing(12);

    auto* title = new QLabel;
    title->setText("<span style='font-weight:900;font-size:16px;color:#fbbf24;letter-spacing:2px;'>ARSENAL STATUS</span>");
    title->setTextFormat(Qt::RichText);
    lay->addWidget(title);

    auto* sub = new QLabel("Tools installed on this system — live check");
    sub->setStyleSheet("color: #475569; font-size: 12px;");
    lay->addWidget(sub);

    // Group by category
    QMap<QString, QList<int>> catMap;
    for (int i = 0; i < TOOLS.size(); ++i) {
        const auto& [cmd, label, cat, hint] = TOOLS[i];
        m_tools.append({cmd, label, cat, hint, nullptr, nullptr});
        catMap[cat].append(i);
    }

    for (const QString& cat : catMap.keys()) {
        auto* catLbl = new QLabel;
        catLbl->setText(QString("<span style='font-weight:800;color:#94a3b8;font-size:10px;letter-spacing:3px;'>// %1</span>").arg(cat));
        catLbl->setTextFormat(Qt::RichText);
        catLbl->setContentsMargins(0, 8, 0, 4);
        lay->addWidget(catLbl);

        auto* grid = new QGridLayout;
        grid->setSpacing(6);
        int col = 0, row = 0;
        for (int idx : catMap[cat]) {
            grid->addWidget(makeCard(m_tools[idx]), row, col);
            if (++col >= 4) { col = 0; row++; }
        }
        lay->addLayout(grid);
    }

    scroll->setWidget(root);
    auto* outer = new QVBoxLayout(this);
    outer->setContentsMargins(0, 0, 0, 0);
    outer->addWidget(scroll);
}

QWidget* ArsenalPage::makeCard(ToolCard& tool) {
    auto* card = new QWidget;
    card->setStyleSheet(
        "QWidget { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); "
        "border-radius: 6px; }"
        "QWidget:hover { border-color: rgba(255,255,255,0.1); background: rgba(255,255,255,0.03); }"
    );
    card->setToolTip("Install: " + tool.installHint);

    auto* hlay = new QHBoxLayout(card);
    hlay->setContentsMargins(10, 8, 10, 8);
    hlay->setSpacing(8);

    tool.dot = new QLabel("●");
    tool.dot->setStyleSheet("color: #1e293b; font-size: 10px; background: transparent; border: none;");
    hlay->addWidget(tool.dot);

    auto* lbl = new QLabel(tool.label);
    lbl->setStyleSheet("color: #64748b; font-size: 12px; background: transparent; border: none;");
    hlay->addWidget(lbl, 1);

    tool.statusLabel = new QLabel("…");
    tool.statusLabel->setStyleSheet("color: #334155; font-family: 'JetBrains Mono'; font-size: 9px; background: transparent; border: none;");
    hlay->addWidget(tool.statusLabel);

    return card;
}

void ArsenalPage::audit() {
    for (auto& tool : m_tools) {
        // Check PATH
        QProcess which;
        which.start("which", {tool.cmd});
        which.waitForFinished(2000);
        bool found = (which.exitCode() == 0);

        // Get version if found
        QString ver;
        if (found) {
            QProcess vp;
            vp.start(tool.cmd, {"--version"});
            vp.waitForFinished(1000);
            QString out = vp.readAllStandardOutput() + vp.readAllStandardError();
            QStringList lines = out.split('\n', Qt::SkipEmptyParts);
            if (!lines.isEmpty()) {
                ver = lines.first().simplified().left(20);
            }
        }

        auto* dot = tool.dot;
        auto* sl  = tool.statusLabel;
        QString dotStyle, lblStyle, lblText;

        if (found) {
            dotStyle = "color: #10b981; font-size: 10px; background: transparent; border: none;";
            lblStyle = "color: #10b981; font-family: 'JetBrains Mono'; font-size: 9px; background: transparent; border: none;";
            lblText  = ver.isEmpty() ? "INSTALLED" : ver.left(16);
        } else {
            dotStyle = "color: #334155; font-size: 10px; background: transparent; border: none;";
            lblStyle = "color: #334155; font-family: 'JetBrains Mono'; font-size: 9px; background: transparent; border: none;";
            lblText  = "NOT FOUND";
        }

        // Must update UI on main thread
        QMetaObject::invokeMethod(dot, [dot, dotStyle]() { dot->setStyleSheet(dotStyle); }, Qt::QueuedConnection);
        QMetaObject::invokeMethod(sl, [sl, lblStyle, lblText]() {
            sl->setStyleSheet(lblStyle);
            sl->setText(lblText);
        }, Qt::QueuedConnection);

        QThread::msleep(15); // tiny yield
    }
}
