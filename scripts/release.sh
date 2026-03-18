#!/bin/bash
# Release script - updates version, commits, creates tag and pushes

set -e

# Get current version
CURRENT_VERSION=$(grep '__version__' reviewbot/__init__.py | cut -d'"' -f2)
echo "Current version: $CURRENT_VERSION"

# Parse version parts
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Get release type from argument (patch, minor, major)
RELEASE_TYPE=$1

if [[ -z "$RELEASE_TYPE" ]]; then
    echo "Error: Release type is required."
    echo "Usage: $0 <patch|minor|major>"
    echo ""
    echo "Examples:"
    echo "  $0 patch   # 1.0.8 → 1.0.9"
    echo "  $0 minor   # 1.0.8 → 1.1.0"
    echo "  $0 major   # 1.0.8 → 2.0.0"
    exit 1
fi

case $RELEASE_TYPE in
    major)
        NEW_MAJOR=$((MAJOR + 1))
        NEW_VERSION="$NEW_MAJOR.0.0"
        ;;
    minor)
        NEW_MINOR=$((MINOR + 1))
        NEW_VERSION="$MAJOR.$NEW_MINOR.0"
        ;;
    patch)
        NEW_PATCH=$((PATCH + 1))
        NEW_VERSION="$MAJOR.$MINOR.$NEW_PATCH"
        ;;
    *)
        echo "Error: Invalid release type '$RELEASE_TYPE'"
        echo "Valid types: patch, minor, major"
        exit 1
        ;;
esac

echo "Release type: $RELEASE_TYPE"
echo "New version: $NEW_VERSION"

# Update version in __init__.py
sed -i "s/__version__ = \"$CURRENT_VERSION\"/__version__ = \"$NEW_VERSION\"/" reviewbot/__init__.py

# Commit version update
git add reviewbot/__init__.py
git commit -m "chore: обновить версию до $NEW_VERSION" || echo "No changes to commit"

# Push commit
git push

# Create and push tag with 'v' prefix
GIT_TAG="v$NEW_VERSION"
git tag "$GIT_TAG"
git push origin "$GIT_TAG"

echo "✓ Release $GIT_TAG completed!"
