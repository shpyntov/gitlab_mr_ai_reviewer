#!/bin/bash
# Release script - updates version, commits, creates tag and pushes

set -e

# Get current version
CURRENT_VERSION=$(grep '__version__' reviewbot/__init__.py | cut -d'"' -f2)
echo "Current version: $CURRENT_VERSION"

# Parse version parts
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Calculate new version (increment patch)
NEW_PATCH=$((PATCH + 1))
NEW_VERSION="$MAJOR.$MINOR.$NEW_PATCH"

echo "New version: $NEW_VERSION"

# Update version in __init__.py
sed -i "s/__version__ = \"$CURRENT_VERSION\"/__version__ = \"$NEW_VERSION\"/" reviewbot/__init__.py

# Commit version update
git add reviewbot/__init__.py
git commit -m "chore: обновить версию до $NEW_VERSION" || echo "No changes to commit"

# Push commit
git push

# Create and push tag
git tag "$NEW_VERSION"
git push origin "$NEW_VERSION"

echo "✓ Release $NEW_VERSION completed!"
