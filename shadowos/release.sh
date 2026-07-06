#!/bin/bash
set -e

VERSION="${1:-}"
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 3.0.0"
    exit 1
fi

echo "🚀 ShadowOS Release Helper v$VERSION"
echo "===================================="

# Check prerequisites
if ! command -v gpg &> /dev/null; then
    echo "✗ GPG not installed"
    exit 1
fi

if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "✗ Not in a git repository"
    exit 1
fi

# Create release branch
echo "Creating release branch..."
git checkout -b release/shadowos-v$VERSION

# Update version in files
echo "Updating version to $VERSION..."
sed -i "s/VERSION=.*/VERSION=$VERSION/" shadowos/build.sh
sed -i "s/version:.*/version: $VERSION/" shadowos/profile/profiledef.sh

# Commit version bump
git add shadowos/build.sh shadowos/profile/profiledef.sh
git commit -m "chore(release): bump version to $VERSION"

# Create release tag
echo "Creating release tag..."
git tag -s "shadowos-v$VERSION" -m "ShadowOS Enterprise $VERSION"

# Push to remote
echo "Pushing to remote..."
git push origin release/shadowos-v$VERSION
git push origin "shadowos-v$VERSION"

echo ""
echo "✓ Release prepared:"
echo "  - Branch: release/shadowos-v$VERSION"
echo "  - Tag: shadowos-v$VERSION"
echo ""
echo "Next steps:"
echo "  1. GitHub Actions will build and sign the ISO"
echo "  2. Verify artifacts with: ./verify-download.sh"
echo "  3. Sync to mirrors once verified"
echo "  4. Announce release on shadowcypher.site"
