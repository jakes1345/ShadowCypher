#!/bin/bash
# Sync all worktrees (nxp, quf, vej) with main/master
# Run from: /home/jack/ShadowCypher
# Usage: ./scripts/sync-worktrees.sh [--commit] [--force]

set -e
MAIN="${MAIN:-/home/jack/ShadowCypher}"
WORKTREES="${WORKTREES:-/home/jack/.cursor/worktrees/ShadowCypher}"
COMMIT=false
FORCE=false

for arg in "$@"; do
  case "$arg" in
    --commit) COMMIT=true ;;
    --force)  FORCE=true ;;
  esac
done

cd "$MAIN"

# 1. Commit in main if there are changes
if [[ "$COMMIT" == "true" && -n $(git status -s 2>/dev/null) ]]; then
  git add -A
  git commit -m "Sync: $(date +%Y-%m-%d\ %H:%M:%S)" || true
fi

# 2. Sync each worktree
for wt in nxp quf vej; do
  wtdir="$WORKTREES/$wt"
  [[ ! -d "$wtdir" ]] && continue

  cd "$wtdir"
  echo -n "Syncing $wt... "

  if [[ "$FORCE" == "true" ]]; then
git reset --hard master 2>/dev/null && echo "OK (forced)" || echo "FAILED"
  else
    if git merge master --no-edit 2>/dev/null; then
      echo "OK (merged)"
    else
      echo "CONFLICT - run with --force to overwrite, or resolve manually"
      git merge --abort 2>/dev/null || true
    fi
  fi
done

echo "Done."

# === USAGE ===
# ./scripts/sync-worktrees.sh           # Merge master into each worktree
# ./scripts/sync-worktrees.sh --commit # Commit main changes first, then sync
# ./scripts/sync-worktrees.sh --force  # Force reset each worktree to master (discards local changes)
#
# Post-commit hook: After every commit in main, worktrees auto-merge master.
# To keep worktrees updated: commit in main, or run this script.
