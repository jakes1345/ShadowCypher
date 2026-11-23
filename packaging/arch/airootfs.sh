# Sourced inside package() by the PKGBUILDs that install ShadowOS's scripts or
# files that call them:
#
#     . "$startdir/../airootfs.sh"
#
# The files are the ISO's own, read straight from shadowos/profile/airootfs in
# this checkout, so a package and the ISO cannot drift apart. A path that moves
# there fails the build instead of silently dropping out of the package.
AIROOTFS="$startdir/../../../shadowos/profile/airootfs"

# install_script <name>...
#
# The ISO keeps its scripts in /usr/local/bin, which is where an image puts
# what it lays over the packaged system. A package must not install there: on
# an installed system /usr/local is the local admin's. So they go to /usr/bin.
install_script() {
    local name
    for name in "$@"; do
        install -Dm755 "$AIROOTFS/usr/local/bin/$name" "$pkgdir/usr/bin/$name"
    done
}

# use_packaged_script_paths
#
# Call it last in package(). The ISO's configuration, units and scripts name
# those scripts by their /usr/local/bin path; this rewrites the references in
# everything the package ships to /usr/bin, where install_script puts them.
#
# Only ShadowOS's own scripts (shadow-*, shadowos-*, shadowcypher-*) are
# rewritten. Privacy mode writes firejail wrappers for the browsers into
# /usr/local/bin on purpose, ahead of /usr/bin in PATH, and that path has to
# stay as it is. build-repo.sh checks afterwards that every reference is to a
# file one of the packages installs.
use_packaged_script_paths() {
    grep -rlIZ '/usr/local/bin/shadow' "$pkgdir" |
        xargs -0r sed -i -E 's|/usr/local/bin/(shadow[a-z0-9-]+)|/usr/bin/\1|g'
}
