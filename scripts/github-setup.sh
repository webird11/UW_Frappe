#!/bin/bash
# Setup GitHub repo for UW_Frappe project
# Run from the UW_Frappe directory

set -e

echo "============================================"
echo "GitHub Repository Setup"
echo "============================================"

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo ""
    echo "GitHub CLI (gh) not found."
    echo "Install it: https://cli.github.com/"
    echo ""
    echo "Or set up manually:"
    echo "  1. Create a new repo at https://github.com/new"
    echo "     Name: UW_Frappe (private)"
    echo "  2. Then run:"
    echo "     git init"
    echo "     git add ."
    echo "     git commit -m 'Initial commit: United Way Frappe app scaffold'"
    echo "     git branch -M main"
    echo "     git remote add origin git@github.com:YOUR_USERNAME/UW_Frappe.git"
    echo "     git push -u origin main"
    exit 1
fi

# Check auth
if ! gh auth status &> /dev/null 2>&1; then
    echo "Not authenticated with GitHub. Running gh auth login..."
    gh auth login
fi

REPO_NAME="UW_Frappe"

echo ""
echo "Creating private repository: $REPO_NAME"

# Create repo (private by default)
gh repo create "$REPO_NAME" --private --source=. --remote=origin --description "United Way CRM and Fundraising Platform - Built on Frappe Framework"

# Initialize git if needed
if [ ! -d .git ]; then
    git init
fi

# Initial commit
git add .
git commit -m "Initial commit: United Way Frappe app scaffold

- Core DocTypes: Organization, Contact, Campaign, Pledge, Donation
- Pledge allocation engine with multi-agency distribution
- Campaign rollup calculations
- Seed data generator with realistic test data
- Campaign Summary report with charts
- Role-based permissions (Campaign Manager, Agency Admin, Finance, Executive)
- Docker and native setup scripts
- Built on Frappe Framework v15"

git branch -M main
git push -u origin main

echo ""
echo "============================================"
echo "Repository created and pushed!"
echo "  https://github.com/$(gh api user --jq .login)/$REPO_NAME"
echo "============================================"
