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
#   PUBLISHED_URL=<url>      where the repository is published now. Each package
#                            is compared with the published one: unchanged
#                            contents keep the published file, changed contents
#                            get the next release number (see "Versions" below).
#                            Unset builds every package at the PKGBUILD's own
#                            version, for a quick local test.
#   SIGN_KEY=<fingerprint>   sign the packages and the database with this key.
#                            Unset builds an unsigned repository, which is what
#                            pull-request checks and local test builds want.
#   SUMMARY=<file>           also write the version table there, as Markdown.
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
published="$work/published"
mkdir -p "$work"/{build,pkgs,src,logs} "$repo" "$published"

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

# Run one named step, folded in the log. A step that fails stops the script.
# The step runs in a subshell, so steps hand their results on in files.
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
# makepkg writes into the PKGBUILD's directory unless told otherwise.
export BUILDDIR="$work/build" PKGDEST="$work/pkgs" SRCDEST="$work/src" \
       SRCPKGDEST="$work/src" LOGDEST="$work/logs"

# The file makepkg produces for a package (at release $2, if given), without
# the -debug split.
package_file() {
    (
        [[ -z ${2:-} ]] || export SHADOWOS_PKGREL=$2
        cd "$here/$1" && makepkg --packagelist
    ) | grep -v -- '-debug-' || true
}

build_package() {
    local pkg=$1 args=(--force --noconfirm --nosign) files
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

    mapfile -t files < <(package_file "$pkg")
    if [[ ${#files[@]} -ne 1 ]]; then
        echo "$pkg: expected one package from this PKGBUILD, makepkg lists ${#files[@]}"
        return 1
    fi
    [[ -f ${files[0]} ]] || { echo "makepkg succeeded but did not produce ${files[0]}"; return 1; }
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

# ── Versions ─────────────────────────────────────────────────────────────────
# pacman upgrades a package only when its version goes up, and it expects a
# file it has already downloaded to still be the file the repository lists.
# So against what is published at PUBLISHED_URL:
#   - contents unchanged: the published file (and its signature) is kept, not
#     the rebuild, which differs in timestamps only;
#   - contents changed: the package is repackaged one release higher;
#   - pkgver raised in the PKGBUILD: that version is used as it is.
# The release number therefore lives in the published repository, not in git.

# A digest of what a package installs and declares, leaving out everything
# that only records when or where it was built.
payload_digest() {
    {
        bsdtar -cf - --format=mtree --options='!all,type,uid,gid,mode,link,sha256' \
            --exclude=.BUILDINFO --exclude=.MTREE --exclude=.PKGINFO "@$1" |
            grep -v '^#' | LC_ALL=C sort
        bsdtar -xOqf "$1" .PKGINFO | grep -Ev '^(#|pkgver = |builddate = |packager = |size = )'
    } | sha256sum | cut -d' ' -f1
}

package_version() { bsdtar -xOqf "$1" .PKGINFO | sed -n 's/^pkgver = //p'; }

# fetch <url> <file>: 0 = saved, 4 = the server says it is not there, 1 = failed.
fetch() {
    local code
    code=$(curl -sSL --retry 3 --retry-delay 5 -o "$2" -w '%{http_code}' "$1") || { rm -f "$2"; return 1; }
    case $code in
        200) return 0 ;;
        404) rm -f "$2"; return 4 ;;
        *)   rm -f "$2"; echo "HTTP $code from $1"; return 1 ;;
    esac
}

settle_versions() {
    local index="$published/index.tsv" name cand cver pver pfile psum rel rc db
    : > "$index"; : > "$work/final.list"; : > "$work/versions.tsv"

    if [[ -n ${PUBLISHED_URL:-} ]]; then
        # The files database carries the same package entries. Publishing
        # replaces the two one after the other, so if a run died in between,
        # one of them is still there to read.
        rc=4
        for db in "$REPO_NAME.db" "$REPO_NAME.files"; do
            rc=0; fetch "$PUBLISHED_URL/$db" "$published/$db" || rc=$?
            [[ $rc -eq 4 ]] || break
            echo "$PUBLISHED_URL/$db is not there"
        done
        if [[ $rc -eq 4 ]]; then
            # Without it nothing says which versions users already have, and
            # starting again from the PKGBUILD versions would hand them
            # packages older than the ones they installed.
            echo "No database at $PUBLISHED_URL. To build a repository from nothing, run without PUBLISHED_URL."
            return 1
        elif [[ $rc -ne 0 ]]; then
            echo "Could not read $PUBLISHED_URL/$db"
            return 1
        fi
        # name, version, file name and checksum of every published package
        bsdtar -xOf "$published/$db" --include='*/desc' | awk '
            /^%FILENAME%$/  { getline file }
            /^%NAME%$/      { getline name }
            /^%VERSION%$/   { getline version }
            /^%SHA256SUM%$/ { getline sum; print name "\t" version "\t" file "\t" sum }
        ' > "$index" || return 1
        [[ -s $index ]] || { echo "$PUBLISHED_URL/$db lists no packages"; return 1; }
    else
        echo "PUBLISHED_URL is not set: building every package at its PKGBUILD version."
    fi

    for name in "${PACKAGES[@]}"; do
        cand=$(package_file "$name")
        cver=$(package_version "$cand") || return 1
        pver=""; pfile=""; psum=""
        IFS=$'\t' read -r pver pfile psum < <(awk -F'\t' -v n="$name" '$1 == n {print $2 "\t" $3 "\t" $4}' "$index") || true

        if [[ -z $pver ]]; then
            printf '%s\t%s\t%s\t%s\n' "$name" "-" "$cver" "new package" >> "$work/versions.tsv"
            echo "$cand" >> "$work/final.list"
            continue
        fi
        if (( $(vercmp "$cver" "$pver") > 0 )); then
            printf '%s\t%s\t%s\t%s\n' "$name" "$pver" "$cver" "new version" >> "$work/versions.tsv"
            echo "$cand" >> "$work/final.list"
            continue
        fi
        if [[ ${cver%-*} != "${pver%-*}" ]]; then
            echo "$name: the PKGBUILD says ${cver%-*} but $pver is published. A version cannot go down; raise pkgver."
            return 1
        fi
        if [[ ! ${pver##*-} =~ ^[0-9]+$ ]]; then
            echo "$name: cannot count on from the published release in $pver"
            return 1
        fi

        fetch "$PUBLISHED_URL/$pfile" "$published/$pfile" || { echo "Could not download the published $pfile"; return 1; }
        echo "$psum  $published/$pfile" | sha256sum --check --quiet || {
            echo "$pfile at $PUBLISHED_URL is not the file its database lists"; return 1; }

        if [[ $(payload_digest "$cand") == "$(payload_digest "$published/$pfile")" ]]; then
            rc=0; fetch "$PUBLISHED_URL/$pfile.sig" "$published/$pfile.sig" > /dev/null || rc=$?
            [[ $rc -eq 0 || $rc -eq 4 ]] || { echo "Could not download the published $pfile.sig"; return 1; }
            printf '%s\t%s\t%s\t%s\n' "$name" "$pver" "$pver" "unchanged" >> "$work/versions.tsv"
            echo "$published/$pfile" >> "$work/final.list"
        else
            rel=$(( ${pver##*-} + 1 ))
            echo "$name: contents differ from the published $pver, repackaging as ${pver%-*}-$rel"
            (
                export SHADOWOS_PKGREL=$rel
                cd "$here/$name" && makepkg --repackage --force --noconfirm --nodeps --nosign
            ) || return 1
            cand=$(package_file "$name" "$rel")
            [[ -f $cand ]] || { echo "makepkg did not produce $cand"; return 1; }
            printf '%s\t%s\t%s\t%s\n' "$name" "$pver" "${pver%-*}-$rel" "changed" >> "$work/versions.tsv"
            echo "$cand" >> "$work/final.list"
        fi
    done

    printf '\n'
    column -t -s $'\t' -N 'PACKAGE,PUBLISHED,THIS BUILD,CHANGE' "$work/versions.tsv"
}
check "Settle versions" "Could not settle the package versions" settle_versions

# ── Repository database ──────────────────────────────────────────────────────
build_database() {
    local f kind ext
    while read -r f; do
        cp "$f" "$repo/" || return 1
        [[ -n ${SIGN_KEY:-} ]] || continue
        # A kept package keeps the signature it was published with.
        if [[ ! -f $f.sig ]]; then
            gpg --batch --detach-sign --use-agent --local-user "$SIGN_KEY" --no-armor "$f" || return 1
        fi
        cp "$f.sig" "$repo/" || return 1
    done < "$work/final.list"

    cd "$repo" || return 1
    repo-add ${SIGN_KEY:+--sign --key "$SIGN_KEY"} "$REPO_NAME.db.tar.gz" ./*.pkg.tar.zst || return 1
    # repo-add leaves shadowos.db and shadowos.files as symlinks to the
    # archives. Static hosts and release assets do not keep symlinks, and
    # pacman only ever asks for the short names, so publish those as files.
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

check_desktop_config() {
    # Hyprland reads its configuration at login. A file it rejects leaves the
    # user with an error banner in place of the desktop, and a new Hyprland
    # release can make a file that used to be fine into one of those. So ask
    # Hyprland itself, about the files as packaged: hyprland.lua together with
    # every hardware profile and every mode colour that shadowos-session-start
    # and shadowos-theme-apply can put beside it. --verify-config only parses,
    # so it needs no display.
    if ! command -v Hyprland > /dev/null; then
        sudo pacman -S --needed --noconfirm hyprland || { echo "This check needs Hyprland (pacman -S hyprland)."; return 1; }
    fi

    local root="$work/desktop" config hypr modes profile mode output version
    version=$(Hyprland --version | sed -n '1s/ built from.*//p')
    mkdir -p "$root/runtime" && chmod 700 "$root/runtime"
    bsdtar -xf "$repo"/shadowos-hyprland-config-[0-9]*.pkg.tar.zst -C "$root" \
        etc/skel/.config/hypr etc/shadowos/desktop || return 1
    bsdtar -xf "$repo"/shadowos-tools-[0-9]*.pkg.tar.zst -C "$root" \
        usr/local/bin/shadowos-theme-apply || return 1
    mapfile -t modes < <(bsdtar -tf "$repo"/shadowos-base-[0-9]*.pkg.tar.zst |
        sed -n 's|^etc/shadowos/modes/\([^/]*\)/$|\1|p')
    (( ${#modes[@]} )) || { echo "shadowos-base ships no modes in /etc/shadowos/modes"; return 1; }
    config="$root/etc/skel/.config"
    hypr="$config/hypr"

    for profile in "$root"/etc/shadowos/desktop/hardware/*.lua; do
        for mode in "${modes[@]}"; do
            # The two files a login writes next to hyprland.lua.
            cp "$profile" "$hypr/hardware-adjustments.lua" || return 1
            XDG_CONFIG_HOME="$config" bash "$root/usr/local/bin/shadowos-theme-apply" "$mode" --no-reload || return 1
            output=$(XDG_CONFIG_HOME="$config" XDG_RUNTIME_DIR="$root/runtime" \
                Hyprland --verify-config -c "$hypr/hyprland.lua" 2>&1) || true
            if [[ $(tail -n 1 <<< "$output") != "config ok" ]]; then
                printf '%s rejects hyprland.lua with the %s hardware profile in %s mode:\n' \
                    "$version" "$(basename "$profile" .lua)" "$mode"
                sed -n '/Config parsing result/,$p' <<< "$output" | tail -n +2 | sed "s|$root||g"
                return 1
            fi
        done
    done
    printf '%s accepts hyprland.lua with each of %d hardware profiles in each of %d modes (%s).\n' \
        "$version" "$(ls "$root"/etc/shadowos/desktop/hardware/*.lua | wc -l)" \
        "${#modes[@]}" "${modes[*]}"
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
check "Check the desktop configuration with Hyprland" "Hyprland rejects the packaged desktop configuration" check_desktop_config
if [[ -n ${SIGN_KEY:-} ]]; then
    check "Verify package signatures" "pacman rejected a package signature" check_signatures
fi

# ── Output ───────────────────────────────────────────────────────────────────
find "$out" -mindepth 1 -delete
cp "$repo"/* "$out/"
if [[ -n ${SUMMARY:-} ]]; then
    {
        printf '### [%s] repository\n\n' "$REPO_NAME"
        if [[ -n ${PUBLISHED_URL:-} ]]; then
            printf '| Package | Published | This build | |\n|---|---|---|---|\n'
            awk -F'\t' '{ printf "| `%s` | %s | %s | %s |\n", $1, $2, ($4 == "unchanged" ? $3 : "**" $3 "**"), $4 }' "$work/versions.tsv"
        else
            printf '| Package | Version |\n|---|---|\n'
            awk -F'\t' '{ printf "| `%s` | %s |\n", $1, $3 }' "$work/versions.tsv"
        fi
    } > "$SUMMARY"
fi
printf '\nRepository written to %s:\n' "$out"
ls -l "$out"
