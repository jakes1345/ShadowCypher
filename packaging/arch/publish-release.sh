#!/usr/bin/env bash
# Publish a repository built by build-repo.sh as the assets of a GitHub release.
#
#   packaging/arch/publish-release.sh <repo-dir> <release-tag>
#
# Needs the gh CLI, with GH_REPO naming the repository and a token that may
# write to its releases. The publish-arch workflow is the only thing meant to
# run this.
#
# Only what changed is uploaded. A package file that the published database
# lists is never replaced: its name carries its version, pacman keeps
# downloaded packages by name, and build-repo.sh gives changed contents a new
# version. Being asked to replace one means something upstream went wrong, so
# the script stops instead.
set -euo pipefail

[[ $# -eq 2 ]] || { echo "usage: ${0##*/} <repo-dir> <release-tag>" >&2; exit 2; }
tag=$2
cd "$1"
REPO_NAME=shadowos
[[ -f $REPO_NAME.db ]] || { echo "$1 holds no $REPO_NAME.db" >&2; exit 2; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

if ! gh release view "$tag" > /dev/null 2>&1; then
    # --latest=false: "latest" stays with the product releases.
    gh release create "$tag" --target "${GITHUB_SHA:-main}" --latest=false \
        --title "ShadowOS pacman repository" \
        --notes "The signed \`[$REPO_NAME]\` pacman repository. The \`publish-arch\` workflow adds each new package version here and removes the ones it replaces; the tag itself does not move. To use the repository, see [packaging/arch/README.md](https://github.com/$GH_REPO/blob/main/packaging/arch/README.md)."
fi

# What the release holds now: asset name and sha256 (empty for assets uploaded
# before GitHub recorded one).
gh api "repos/$GH_REPO/releases/tags/$tag" \
    --jq '.assets[] | [.name, (.digest // "")] | @tsv' > "$tmp/assets.tsv"

# The package files the published database lists. The files database carries
# the same entries, in case the other one is missing.
: > "$tmp/listed"
for db in "$REPO_NAME.db" "$REPO_NAME.files"; do
    if cut -f1 "$tmp/assets.tsv" | grep -qxF "$db"; then
        gh release download "$tag" --pattern "$db" --dir "$tmp/published"
        tar -xOf "$tmp/published/$db" --wildcards '*/desc' |
            awk '/^%FILENAME%$/ { getline; print }' > "$tmp/listed"
        break
    fi
done

published_sha() {
    local name=$1 digest
    digest=$(awk -F'\t' -v n="$name" '$1 == n { print $2 }' "$tmp/assets.tsv")
    if [[ -z $digest ]]; then
        gh release download "$tag" --pattern "$name" --dir "$tmp/have" --clobber
        digest="sha256:$(sha256sum "$tmp/have/$name" | cut -d' ' -f1)"
    fi
    echo "$digest"
}

new=() leftover=() kept=0
for f in *.pkg.tar.zst *.pkg.tar.zst.sig; do
    [[ -e $f ]] || continue
    if ! cut -f1 "$tmp/assets.tsv" | grep -qxF "$f"; then
        new+=("$f")
    elif [[ $(published_sha "$f") == "sha256:$(sha256sum "$f" | cut -d' ' -f1)" ]]; then
        kept=$((kept + 1))
    elif grep -qxF "${f%.sig}" "$tmp/listed"; then
        echo "::error title=Refusing to replace a published package::$f is listed by the published database and differs from the file to publish"
        exit 1
    else
        # On the release but not in its database: left by a run that stopped
        # before its database went up. Nobody can have installed it.
        leftover+=("$f")
    fi
done

echo "Already published and unchanged: $kept files."
if (( ${#new[@]} )); then
    echo "New: ${new[*]}"
    gh release upload "$tag" "${new[@]}"
fi
if (( ${#leftover[@]} )); then
    echo "Replacing files left by an unfinished run: ${leftover[*]}"
    gh release upload "$tag" --clobber "${leftover[@]}"
fi

# The databases last, so they never list a package that is not there yet.
for f in "$REPO_NAME.files" "$REPO_NAME.files.sig" "$REPO_NAME.db" "$REPO_NAME.db.sig"; do
    [[ ! -e $f ]] || gh release upload "$tag" --clobber "$f"
done

# Then drop whatever the new database no longer lists.
gh release view "$tag" --json assets --jq '.assets[].name' |
    while read -r name; do
        if [[ ! -e $name ]]; then
            echo "Removing $name"
            gh release delete-asset "$tag" "$name" --yes
        fi
    done
