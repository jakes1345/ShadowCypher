// shadowcypher-privacy-helper: the only part of ShadowCypher that runs as root.
// Launched through pkexec with a single fixed verb and no other input, so the
// surface exposed to an unprivileged caller is "turn the kill-switch on/off".
//
// Exit codes (126/127 are left to pkexec):
//   0 ok, 2 usage, 3 not root, 4 Tor missing, 5 firewall failure (rolled back),
//   6 Tor failed to start (rolled back), 7 iptables not installed.

#include <cerrno>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <fcntl.h>
#include <pwd.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

namespace {

constexpr const char* kRunDir = "/run/shadowcypher";
constexpr const char* kMarker = "/run/shadowcypher/privacy-active";

struct Tools {
    std::string ipt, ip6t, systemctl;
};

std::string findBin(const char* name)
{
    for (const char* dir : {"/usr/sbin/", "/usr/bin/", "/sbin/", "/bin/"}) {
        std::string path = std::string(dir) + name;
        if (access(path.c_str(), X_OK) == 0) return path;
    }
    return {};
}

int run(const std::string& bin, const std::vector<std::string>& args)
{
    if (bin.empty()) return -1;
    const pid_t pid = fork();
    if (pid < 0) return -1;
    if (pid == 0) {
        const int devnull = open("/dev/null", O_WRONLY);
        if (devnull >= 0) { dup2(devnull, STDOUT_FILENO); dup2(devnull, STDERR_FILENO); }
        std::vector<char*> argv;
        argv.push_back(const_cast<char*>(bin.c_str()));
        for (const auto& a : args) argv.push_back(const_cast<char*>(a.c_str()));
        argv.push_back(nullptr);
        char* envp[] = {const_cast<char*>("PATH=/usr/sbin:/usr/bin:/sbin:/bin"),
                        const_cast<char*>("LC_ALL=C"), nullptr};
        execve(bin.c_str(), argv.data(), envp);
        _exit(127);
    }
    int status = 0;
    while (waitpid(pid, &status, 0) < 0 && errno == EINTR) {}
    return WIFEXITED(status) ? WEXITSTATUS(status) : -1;
}

std::string torUser()
{
    for (const char* name : {"debian-tor", "tor", "_tor"})
        if (getpwnam(name)) return name;
    return {};
}

bool markerSaysStartedTor()
{
    FILE* f = std::fopen(kMarker, "re");
    if (!f) return false;
    char buf[64] = {};
    const size_t n = std::fread(buf, 1, sizeof(buf) - 1, f);
    std::fclose(f);
    return std::strstr(std::string(buf, n).c_str(), "started_tor=1") != nullptr;
}

bool writeMarker(bool startedTor)
{
    if (mkdir(kRunDir, 0755) < 0 && errno != EEXIST) return false;
    const int fd = open(kMarker, O_WRONLY | O_CREAT | O_TRUNC | O_NOFOLLOW | O_CLOEXEC, 0644);
    if (fd < 0) return false;
    const char* body = startedTor ? "started_tor=1\n" : "started_tor=0\n";
    const bool ok = write(fd, body, std::strlen(body)) == ssize_t(std::strlen(body));
    close(fd);
    return ok;
}

void removeChains(const Tools& t)
{
    run(t.ipt,  {"-D", "OUTPUT", "-j", "SHADOW_KS"});
    run(t.ipt,  {"-F", "SHADOW_KS"});
    run(t.ipt,  {"-X", "SHADOW_KS"});
    run(t.ip6t, {"-D", "OUTPUT", "-j", "SHADOW_KS6"});
    run(t.ip6t, {"-F", "SHADOW_KS6"});
    run(t.ip6t, {"-X", "SHADOW_KS6"});
}

bool chainsInstalled(const Tools& t)
{
    return run(t.ipt,  {"-C", "OUTPUT", "-j", "SHADOW_KS"})  == 0
        && run(t.ip6t, {"-C", "OUTPUT", "-j", "SHADOW_KS6"}) == 0;
}

bool buildChains(const Tools& t, const std::string& tor)
{
    run(t.ipt, {"-N", "SHADOW_KS"});   // may already exist
    if (run(t.ipt, {"-F", "SHADOW_KS"}) != 0
     || run(t.ipt, {"-A", "SHADOW_KS", "-m", "owner", "--uid-owner", tor, "-j", "ACCEPT"}) != 0
     || run(t.ipt, {"-A", "SHADOW_KS", "-o", "lo", "-j", "ACCEPT"}) != 0
     || run(t.ipt, {"-A", "SHADOW_KS", "-j", "DROP"}) != 0)
        return false;
    if (run(t.ipt, {"-C", "OUTPUT", "-j", "SHADOW_KS"}) != 0
     && run(t.ipt, {"-I", "OUTPUT", "1", "-j", "SHADOW_KS"}) != 0)
        return false;

    run(t.ip6t, {"-N", "SHADOW_KS6"});
    if (run(t.ip6t, {"-F", "SHADOW_KS6"}) != 0
     || run(t.ip6t, {"-A", "SHADOW_KS6", "-o", "lo", "-j", "ACCEPT"}) != 0
     || run(t.ip6t, {"-A", "SHADOW_KS6", "-j", "DROP"}) != 0)
        return false;
    if (run(t.ip6t, {"-C", "OUTPUT", "-j", "SHADOW_KS6"}) != 0
     && run(t.ip6t, {"-I", "OUTPUT", "1", "-j", "SHADOW_KS6"}) != 0)
        return false;
    return true;
}

int engage(const Tools& t)
{
    const std::string tor = torUser();
    if (tor.empty()) {
        std::puts("error: Tor is not installed (no tor system user found)");
        return 4;
    }

    // Already on: rebuilding would briefly empty the chain and let traffic through.
    if (access(kMarker, F_OK) == 0 && chainsInstalled(t)) {
        std::puts("active");
        return 0;
    }

    // Remember whether Tor was already running so disengage only stops it if we started it.
    const bool startedEarlier = markerSaysStartedTor();
    const bool torActive = run(t.systemctl, {"is-active", "--quiet", "tor"}) == 0;

    if (!buildChains(t, tor)) {
        removeChains(t);
        std::puts("error: failed to install the kill-switch firewall rules");
        return 5;
    }

    bool startedTor = startedEarlier;
    if (!torActive) {
        if (run(t.systemctl, {"start", "tor"}) != 0) {
            removeChains(t);
            std::puts("error: Tor failed to start");
            return 6;
        }
        startedTor = true;
    }

    if (!chainsInstalled(t) || !writeMarker(startedTor)) {
        removeChains(t);
        if (startedTor && !startedEarlier) run(t.systemctl, {"stop", "tor"});
        unlink(kMarker);
        std::puts("error: kill-switch could not be confirmed after setup");
        return 5;
    }

    std::puts("active");
    return 0;
}

int disengage(const Tools& t)
{
    const bool startedTor = markerSaysStartedTor();
    removeChains(t);
    if (startedTor) run(t.systemctl, {"stop", "tor"});
    unlink(kMarker);

    if (run(t.ipt,  {"-C", "OUTPUT", "-j", "SHADOW_KS"})  == 0
     || run(t.ip6t, {"-C", "OUTPUT", "-j", "SHADOW_KS6"}) == 0) {
        std::puts("error: kill-switch rules are still present");
        return 5;
    }
    std::puts("off");
    return 0;
}

} // namespace

int main(int argc, char** argv)
{
    if (argc != 2) {
        std::puts("usage: shadowcypher-privacy-helper engage|disengage");
        return 2;
    }
    if (geteuid() != 0) {
        std::puts("error: must run as root");
        return 3;
    }

    umask(022);
    const Tools t{findBin("iptables"), findBin("ip6tables"), findBin("systemctl")};
    if (t.ipt.empty() || t.ip6t.empty()) {
        std::puts("error: iptables is not installed");
        return 7;
    }

    const std::string verb = argv[1];
    if (verb == "engage")    return engage(t);
    if (verb == "disengage") return disengage(t);
    std::puts("usage: shadowcypher-privacy-helper engage|disengage");
    return 2;
}
