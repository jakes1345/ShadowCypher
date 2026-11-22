#!/usr/bin/env bash
# Build the [shadowos] pacman repository: every package in PACKAGES below, then
# the repository database, into <output-dir>.
#
#   packaging/arch/build-repo.sh <output-dir>
#
# Run it on Arch as a normal user who can `sudo pacman` (makepkg refuses to run
# as root). The checkout is only read; all build output goes to a scratch
# directory and, once everything has passed, to <output-dir>.
#
#   SIGN_KEY=<fingerprint>   sign the packages and the database with this key.
#                            Unset builds an unsigned repository, which is what
#                            pull-request checks and local test builds want.
#
# One broken package does not stop the others, so a single run names every
# package that fails. <output-dir> is only written when all packages built and
# the repository passed the checks at the end of this script. Publishing
# replaces the previous repository, so a partial one must never get that far.
set -euo pipefail

PACKAGES=(
    shadowos-keyring
    shadowos-mirrorlist
    shadowos-base
    shadowos-branding
    shadowos-tools
    shadowos-hyprland-config
    shadowos-firefox-config
    shadowos-fastfetch
    shadowos-meta
    shadowcypher
)
REPO_NAME=shadowos

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ $# -eq 1 ]] || { echo "usage: ${0##*/} <output-dir>" >&2; exit 2; }
[[ $EUID -ne 0 ]] || { echo "Run as a normal user: makepkg refuses to run as root." >&2; exit 2; }

mkdir -p "$1"
out="$(cd "$1" && pwd)"
# The output directory is emptied before the repository is written, so only
# accept an empty one or one that already holds this repository.
if [[ -n $(ls -A "$out") && ! -e $out/$REPO_NAME.db ]]; then
    echo "$out is not empty and is not a $REPO_NAME repository; refusing to overwrite it." >&2
    exit 2
fi

work="$(mktemp -d "${TMPDIR:-/tmp}/shadowos-repo.XXXXXX")"
trap 'rm -rf "$work"' EXIT
repo="$work/repo"
mkdir -p "$work"/{build,pkgs,src,logs} "$repo"

# GitHub Actions folds each step's log and shows failures as annotations;
# anywhere else these print plain headings.
if [[ -n ${GITHUB_ACTIONS:-} ]]; then
    group()    { echo "::group::$*"; }
    endgroup() { echo "::endgroup::"; }
    fail()     { echo "::error title=$1::$2"; }
else
    group()    { printf '\n==> %s\n' "$*"; }
    endgroup() { :; }
    fail()     { printf 'ERROR: %s: %s\n' "$1" "$2" >&2; }
fi

# Run one named check, folded in the log. A check that fails stops the script.
check() {
    local title=$1 problem=$2 fn=$3
    group "$title"
    if "$fn" 2>&1 | tee "$work/logs/check.log"; then
        endgroup
    else
        endgroup
        fail "$problem" "$(tail -n 5 "$work/logs/check.log" | paste -sd' ')"
        printf '\n%s. No repository was written.\n' "$problem" >&2
        exit 1
    fi
}

# ── Packages ─────────────────────────────────────────────────────────────────
sign_args=(--nosign)
[[ -z ${SIGN_KEY:-} ]] || sign_args=(--sign --key "$SIGN_KEY")

# makepkg writes into the PKGBUILD's directory unless told otherwise.
export BUILDDIR="$work/build" PKGDEST="$work/pkgs" SRCDEST="$work/src" \
       SRCPKGDEST="$work/src" LOGDEST="$work/logs"

# The files makepkg will produce for a package, without the -debug split.
package_files() {
    (cd "$here/$1" && makepkg --packagelist) | grep -v -- '-debug-' || true
}

build_package() {
    local pkg=$1 args=(--force --clean --noconfirm "${sign_args[@]}") f
    # A package that compiles gets its dependencies installed by makepkg. The
    # others only copy files, and installing hyprland or linux-hardened to
    # package a config file would add gigabytes to every run, so their
    # dependencies are resolved against the real repositories below instead.
    if grep -qE '^(build|check)\(\)' "$here/$pkg/PKGBUILD"; then
        args+=(--syncdeps)
    else
        args+=(--nodeps)
    fi
    (cd "$here/$pkg" && makepkg "${args[@]}") || return 1

    while read -r f; do
        [[ -f $f ]] || { echo "makepkg succeeded but did not produce $f"; return 1; }
        [[ -z ${SIGN_KEY:-} || -f $f.sig ]] || { echo "missing signature $f.sig"; return 1; }
    done < <(package_files "$pkg")
}

failed=()
for pkg in "${PACKAGES[@]}"; do
    group "Build $pkg"
    build_package "$pkg" 2>&1 | tee "$work/logs/$pkg.log" || failed+=("$pkg")
    endgroup
done

if (( ${#failed[@]} )); then
    for pkg in "${failed[@]}"; do
        printf '\n==> %s failed to build. Last lines of its log:\n' "$pkg"
        tail -n 40 "$work/logs/$pkg.log" | sed 's/^/    /'
        fail "Package failed to build" "$pkg (packaging/arch/$pkg/PKGBUILD)"
    done
    printf '\n%d of %d packages failed to build: %s\nNo repository was written.\n' \
        "${#failed[@]}" "${#PACKAGES[@]}" "${failed[*]}" >&2
    exit 1
fi

# ── Repository database ──────────────────────────────────────────────────────
build_database() {
    cp "$work"/pkgs/*.pkg.tar.zst "$repo/" || return 1
    if [[ -n ${SIGN_KEY:-} ]]; then
        cp "$work"/pkgs/*.pkg.tar.zst.sig "$repo/" || return 1
    fi
    cd "$repo" || return 1
    repo-add ${SIGN_KEY:+--sign --key "$SIGN_KEY"} "$REPO_NAME.db.tar.gz" ./*.pkg.tar.zst || return 1
    # repo-add leaves shadowos.db and shadowos.files as symlinks to the
    # archives. Static hosts and release assets do not keep symlinks, and
    # pacman only ever asks for the short names, so publish those as files.
    local kind ext
    for kind in db files; do
        for ext in "" .sig; do
            [[ -e $REPO_NAME.$kind.tar.gz$ext ]] || continue
            rm -f "$REPO_NAME.$kind$ext"
            mv "$REPO_NAME.$kind.tar.gz$ext" "$REPO_NAME.$kind$ext" || return 1
        done
    done
    rm -f ./*.old ./*.old.sig
}
check "Build the $REPO_NAME database" "Could not build the repository database" build_database

# ── Checks against what a user's pacman will do ──────────────────────────────
# A private pacman root: this machine's official repositories plus the
# repository just built, an empty local database (so dependencies are resolved
# as on a system with nothing installed) and its own keyring. Nothing here
# touches the machine's own pacman state, hence fakeroot rather than sudo.
pm_root="$work/pacman"
mkdir -p "$pm_root"/{db,cache,gnupg}
{
    cat /etc/pacman.conf
    printf '\n[%s]\nSigLevel = %s\nServer = file://%s\n' "$REPO_NAME" \
        "$([[ -n ${SIGN_KEY:-} ]] && echo 'Required DatabaseOptional' || echo 'Never')" "$repo"
} > "$pm_root/pacman.conf"
pm() {
    fakeroot -- pacman --config "$pm_root/pacman.conf" --dbpath "$pm_root/db" \
        --cachedir "$pm_root/cache" --gpgdir "$pm_root/gnupg" --logfile /dev/null \
        --noconfirm "$@"
}

sync_repositories() {
    if [[ -n ${SIGN_KEY:-} ]]; then
        # Trust only the key shadowos-keyring ships, as a user's pacman does.
        # A signing key that no longer matches the published one fails here.
        local fpr
        fpr=$(awk -F: 'NR==1 {print $1}' "$here/shadowos-keyring/shadowos-trusted")
        fakeroot -- pacman-key --gpgdir "$pm_root/gnupg" --init || return 1
        fakeroot -- pacman-key --gpgdir "$pm_root/gnupg" --add "$here/shadowos-keyring/shadowos.gpg" || return 1
        fakeroot -- pacman-key --gpgdir "$pm_root/gnupg" --lsign-key "$fpr" || return 1
    fi
    pm -Sy || return 1
    pm -Fy || return 1
}

check_dependencies() {
    # --print prepares the whole transaction (every dependency, down to the
    # official repositories) and stops before downloading anything.
    pm -S --print --print-format '%r/%n %v' "${PACKAGES[@]}" > "$work/logs/resolved.txt" || return 1
    printf '%d packages resolve, pulling in %d from the official repositories.\n' \
        "${#PACKAGES[@]}" "$(grep -vc "^$REPO_NAME/" "$work/logs/resolved.txt")"
}

check_file_conflicts() {
    # pacman aborts a transaction when a package brings a file that another
    # package owns, unless the two are declared to conflict. Resolving
    # dependencies does not notice that, so look every packaged path up in the
    # official repositories' file lists, and check that no two of our own
    # packages ship the same path.
    local list="$work/logs/files.tsv" declared="$work/logs/conflicts.tsv" pkgfile name
    : > "$list"; : > "$declared"
    for pkgfile in "$repo"/*.pkg.tar.zst; do
        name=$(bsdtar -xOqf "$pkgfile" .PKGINFO | sed -n 's/^pkgname = //p') || return 1
        bsdtar -tf "$pkgfile" | grep -v -e '/$' -e '^\.' | sed "s|^|$name\t|" >> "$list" || return 1
        bsdtar -xOqf "$pkgfile" .PKGINFO |
            sed -n "s/^\(conflict\|replaces\) = \([^<>=]*\).*/$name\t\2/p" >> "$declared"
    done

    local clashes="$work/logs/clashes.txt" paths path
    cut -f2- "$list" | sort | uniq -d | while read -r path; do
        printf '/%s is in more than one package: %s\n' "$path" \
            "$(awk -F'\t' -v p="$path" '$2 == p {print $1}' "$list" | paste -sd' ')"
    done > "$clashes"

    mapfile -t paths < <(cut -f2- "$list")
    # One line per owner: repo NUL package NUL version NUL path. pacman exits
    # non-zero for paths nobody owns, which is the good case here.
    { pm -F --machinereadable "${paths[@]}" || true; } | tr '\0' '\t' |
        awk -F'\t' -v ours="$REPO_NAME" -v list="$list" -v declared="$declared" '
            BEGIN {
                while ((getline line < list) > 0) { split(line, f, "\t"); mine[f[2]] = f[1] }
                while ((getline line < declared) > 0) { split(line, f, "\t"); ok[f[1], f[2]] = 1 }
            }
            $1 != ours && !((mine[$4], $2) in ok) {
                printf "%s: /%s is owned by %s (%s)\n", mine[$4], $4, $2, $1
            }
        ' >> "$clashes"

    if [[ -s $clashes ]]; then
        cat "$clashes"
        return 1
    fi
    printf '%d packaged files, none owned by another package without a declared conflict.\n' "${#paths[@]}"
}

check_signatures() {
    # Have pacman fetch every package from the repository and verify it.
    pm -Sw --nodeps --nodeps "${PACKAGES[@]}" || return 1
}

check "Read the repository with pacman" \
    "pacman could not read the repository${SIGN_KEY:+ (signed with a key other than the one in shadowos-keyring?)}" \
    sync_repositories
check "Resolve dependencies" "Dependencies do not resolve" check_dependencies
check "Check for file conflicts" "A package ships a file another package owns" check_file_conflicts
if [[ -n ${SIGN_KEY:-} ]]; then
    check "Verify package signatures" "pacman rejected a package signature" check_signatures
fi

# ── Output ───────────────────────────────────────────────────────────────────
find "$out" -mindepth 1 -delete
cp "$repo"/* "$out/"
printf '\nRepository written to %s:\n' "$out"
ls -l "$out"
