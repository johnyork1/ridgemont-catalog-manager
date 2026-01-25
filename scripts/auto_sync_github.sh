#!/bin/bash
# Auto-sync Ridgemont Catalog Manager to GitHub
# This script commits and pushes any changes to GitHub daily

# Set the path to your repository
REPO_PATH="/Users/johnyork/My Drive/Ridgemont Studio/Claude Cowork/Ridgemont Catalog Manager"

# Navigate to the repository
cd "$REPO_PATH" || exit 1

# Check if there are any changes
if [[ -n $(git status --porcelain) ]]; then
    # Add all changes
    git add .

    # Create a commit with timestamp
    TIMESTAMP=$(date "+%Y-%m-%d %H:%M")
    git commit -m "Auto-sync: $TIMESTAMP"

    # Push to GitHub
    git push origin main

    echo "✅ Changes pushed to GitHub at $TIMESTAMP"
else
    echo "ℹ️ No changes to sync at $(date "+%Y-%m-%d %H:%M")"
fi
