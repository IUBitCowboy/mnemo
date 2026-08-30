#!/usr/bin/env bash
# Push tools/icex_checker to the TA tools repo (github.iu.edu:mnemo-course-dev/ta-tools)
#
# Usage: ./scripts/push-ta-tools.sh [--force]
#
# This script uses git subtree to push the tools/icex_checker directory
# to the standalone TA tools repository. TAs pull updates with:
#
#   git pull
#
# Run this from the mnemo repo root after committing changes to tools/icex_checker/.

set -euo pipefail

REMOTE_NAME="ta-tools"
REMOTE_URL="git@github.iu.edu:mnemo-course-dev/ta-tools.git"
PREFIX="tools/icex_checker"
BRANCH="main"

# Ensure the remote exists
if ! git remote get-url "$REMOTE_NAME" >/dev/null 2>&1; then
    git remote add "$REMOTE_NAME" "$REMOTE_URL"
fi

echo "Pushing $PREFIX to $REMOTE_NAME (branch: $BRANCH)..."

# subtree split creates a temporary branch with just the icex_checker history
SPLIT_BRANCH="ta-tools-split-$(date +%s)"
git subtree split --prefix="$PREFIX" -b "$SPLIT_BRANCH"

# Push to the TA repo
if [[ "${1:-}" == "--force" ]]; then
    git push --force "$REMOTE_NAME" "$SPLIT_BRANCH:$BRANCH"
else
    git push "$REMOTE_NAME" "$SPLIT_BRANCH:$BRANCH"
fi

# Clean up the temporary branch
git branch -D "$SPLIT_BRANCH"

echo "Done. TAs can update with: git pull"