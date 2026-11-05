#!/usr/bin/env bash
# Print a CHANGELOG.md entry for VERSION from the commits since the last tag,
# grouped by conventional-commit type. Used by .github/workflows/changelog.yml.
set -euo pipefail

version="${1:-Unreleased}"
last_tag="$(git describe --tags --abbrev=0 2>/dev/null || true)"
range="${last_tag:+${last_tag}..}HEAD"

declare -A groups=()
while IFS='|' read -r hash subject; do
    [[ -z "$hash" ]] && continue
    case "$subject" in
        security*) cat=security ;;
        feat*)     cat=features ;;
        fix*)      cat=bugfixes ;;
        perf*)     cat=performance ;;
        *)         cat=other ;;
    esac
    groups[$cat]+="- ${subject} (${hash:0:7})"$'\n'
done < <(git log "$range" --pretty=format:'%H|%s' 2>/dev/null; echo)

echo "## [${version}] - $(date +%Y-%m-%d)"
for cat in security features bugfixes performance other; do
    [[ -n "${groups[$cat]:-}" ]] || continue
    printf '\n### %s\n\n%s' "${cat^}" "${groups[$cat]}"
done
