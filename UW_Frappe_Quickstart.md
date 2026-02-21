# United Way Frappe — Weekend Quickstart Guide

## Step 0: Prerequisites on Your Local Machine (Dallas box)

You need Docker Desktop and GitHub CLI. If you don't have them:

```bash
# Install Docker Desktop (Windows or Mac)
# Download from: https://docs.docker.com/desktop/

# Install GitHub CLI
# Mac:
brew install gh

# Windows (winget):
winget install --id GitHub.cli

# Linux:
sudo apt install gh

# Authenticate with GitHub
gh auth login
```

Verify everything:
```bash
docker --version          # Need 20+
docker compose version    # Need v2+
gh auth status            # Should show logged in
git --version             # Need 2.x
```

---

## Step 1: Create the GitHub Repo and Push

```bash
cd ~/UW_Frappe

# Create private repo on GitHub and push
gh repo create UW_Frappe --private --source=. --remote=origin \
  --description "United Way CRM and Fundraising Platform - Frappe Framework"

git push -u origin main
```

That's it. Your repo is live at `https://github.com/YOUR_USERNAME/UW_Frappe`.

---

## Step 2: Stand Up the Frappe Dev Environment (Docker)

The Docker approach is the fastest path. We'll use Frappe's official Docker setup with your custom app mounted in.

### 2a. Clone the Frappe Docker repo alongside your project

```bash
cd ~/UW_Frappe

# Clone frappe_docker into a subdirectory (already in .gitignore)
git clone https://github.com/frappe/frappe_docker.git
cd frappe_docker
```

### 2b. Set up the development environment

```bash
# Copy the example env
cp example.env .env

# Start the development containers
docker compose -f compose.yaml \
  -f overrides/compose.noproxy.yaml \
  -f overrides/compose.mariadb.yaml \
  -f overrides/compose.redis.yaml \
  up -d

# Wait for containers to fully start (check with)
docker compose logs -f backend
# Wait until you see "Werkzeug" or "bench" ready messages, then Ctrl+C
```

### 2c. Create a site and install the app

```bash
# Enter the backend container
docker compose exec backend bash

# Inside the container, you're in /workspace/development/frappe-bench
# Create a new site
bench new-site uw.localhost \
  --mariadb-root-password 123 \
  --admin-password admin \
  --no-mariadb-socket

# Set as default site
bench use uw.localhost

# Now get your custom app into the bench
# Option A: Clone from GitHub (recommended for Claude Code workflow)
bench get-app https://github.com/YOUR_USERNAME/UW_Frappe.git \
  --branch main \
  --resolve-deps

# If the app structure is nested (UW_Frappe/united_way/), you may need:
# cd apps && git clone https://github.com/YOUR_USERNAME/UW_Frappe.git
# Then symlink: ln -s UW_Frappe/united_way united_way

# Install the app
bench --site uw.localhost install-app united_way

# Run migrations to create all the tables
bench --site uw.localhost migrate

# Load seed data
bench --site uw.localhost execute united_way.seed.run

# Start the dev server
bench start
```

### 2d. Access Frappe

Open your browser to: **http://localhost:8000** (or http://uw.localhost:8000)

Login:
- Username: `Administrator`
- Password: `admin`

You should see the Frappe desk. Navigate to the search bar and type "Organization" or "Campaign" to see your DocTypes with seed data loaded.

---

## Step 3: Alternative — Native Install (No Docker)

If you'd rather run Frappe natively (useful if Docker is flaky on your machine):

### Ubuntu 22.04/24.04 or WSL2

```bash
# System dependencies
sudo apt update
sudo apt install -y python3-dev python3-pip python3-venv \
  redis-server mariadb-server mariadb-client \
  nodejs npm git curl

# Set up MariaDB
sudo mysql_secure_installation
# Set root password, answer Y to all

# Enable MariaDB character set
sudo tee /etc/mysql/mariadb.conf.d/50-custom.cnf << 'EOF'
[mysqld]
character-set-client-handshake = FALSE
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

[mysql]
default-character-set = utf8mb4
EOF
sudo systemctl restart mariadb

# Install yarn
sudo npm install -g yarn

# Install bench CLI
pip3 install frappe-bench

# Initialize a new bench
bench init uw-bench --frappe-branch version-15
cd uw-bench

# Create site
bench new-site uw.localhost --admin-password admin
bench use uw.localhost

# Get your app from GitHub
bench get-app https://github.com/YOUR_USERNAME/UW_Frappe.git

# Install app
bench --site uw.localhost install-app united_way

# Migrate
bench --site uw.localhost migrate

# Seed data
bench --site uw.localhost execute united_way.seed.run

# Run dev server
bench start
```

---

## Step 4: Claude Code Workflow

Once your dev environment is running, here's how to work with Claude Code:

### Point Claude Code at the project
```bash
cd ~/UW_Frappe
claude
```

Claude Code will read the `CLAUDE.md` file automatically and understand the full project context.

### The development loop
1. Tell Claude Code what to build (e.g., "Create a Donor Giving History script report")
2. Claude Code writes the files in the `united_way/` directory
3. In your Frappe terminal, run: `bench --site uw.localhost migrate`
4. Refresh the browser to see changes
5. Test, iterate, commit

### Key commands Claude Code should know
```bash
# After any DocType changes
bench --site uw.localhost migrate

# After CSS/JS changes
bench build

# Clear cache if things look stale
bench --site uw.localhost clear-cache

# Open Python console with Frappe context (great for testing)
bench --site uw.localhost console

# Run a specific function
bench --site uw.localhost execute united_way.seed.run
```

### Weekend POC Task List for Claude Code

Feed these to Claude Code roughly in order:

1. **Donor Giving History report** — Script report showing each donor's pledges, donations, lifetime total, and year-over-year trend
2. **Agency Allocation Detail report** — Drill-down showing exactly which donors pledged to each agency, amounts, and collection status
3. **UW Core Workspace** — Dashboard with number cards (total pledged, collected, donors, campaigns), charts (pledged vs collected by agency, monthly donation trend), and shortcut links
4. **Pledge Approval Workflow** — Frappe Workflow: Draft → Pending Review → Approved, with email notifications
5. **Print Format: Donation Receipt** — Jinja template for tax-deductible donation receipts
6. **Print Format: Pledge Confirmation** — Confirmation letter with allocation breakdown
7. **Data Import Templates** — CSV templates + import scripts for migrating from Salesforce exports
8. **Email Templates** — Pledge confirmation, donation thank-you, pledge reminder emails
9. **Dashboard Charts** — Number cards and trend charts for the workspace

---

## Project File Structure Reference

```
~/UW_Frappe/
├── CLAUDE.md                          # Claude Code instructions
├── README.md                          # Project documentation
├── .gitignore
├── scripts/
│   ├── docker-dev-setup.sh            # Automated Docker setup
│   ├── github-setup.sh                # GitHub repo creation
│   └── install-dependencies.sh        # Native install deps
├── united_way/                        # THE FRAPPE APP (this is what gets installed)
│   ├── setup.py
│   ├── requirements.txt
│   └── united_way/
│       ├── hooks.py                   # App configuration & event hooks
│       ├── modules.txt                # "UW Core"
│       ├── setup.py                   # Post-install setup (creates roles)
│       ├── seed.py                    # Test data generator
│       ├── tasks.py                   # Scheduled background jobs
│       ├── utils.py                   # Helper functions
│       ├── uw_core/
│       │   ├── doctype/
│       │   │   ├── organization/      # 38 fields — agencies, corporates
│       │   │   ├── contact/           # 34 fields — donors, staff
│       │   │   ├── campaign/          # 23 fields — submittable
│       │   │   ├── pledge/            # 32 fields — submittable, has allocations
│       │   │   ├── pledge_allocation/ # 6 fields — child table
│       │   │   ├── donation/          # 22 fields — submittable
│       │   │   ├── agency_distribution/ # 5 fields — child table
│       │   │   └── uw_settings/       # 17 fields — singleton config
│       │   ├── report/
│       │   │   ├── campaign_summary/  # ✅ Built — bar chart + KPIs
│       │   │   ├── donor_giving_history/  # 🔲 Needs building
│       │   │   └── agency_allocation_report/ # 🔲 Needs building
│       │   └── workspace/             # 🔲 Dashboard needs building
│       └── public/
│           ├── css/united_way.css
│           └── js/united_way.js
└── frappe_docker/                     # (cloned, gitignored)
```

---

## Quick Troubleshooting

| Problem | Fix |
|---|---|
| `bench start` fails with Redis error | `sudo systemctl start redis-server` |
| MariaDB connection refused | `sudo systemctl start mariadb` |
| "Site not found" errors | `bench use uw.localhost` |
| DocType changes not showing | `bench --site uw.localhost migrate` then clear cache |
| Frontend changes not showing | `bench build` then hard refresh browser |
| Permission denied on Docker | `sudo usermod -aG docker $USER` then restart terminal |
| Port 8000 already in use | `lsof -i :8000` then kill the process |

---

## What You'll Have After the Weekend

If Claude Code grinds through the task list above, by Sunday night you'll have:

- ✅ Full data model with 8 DocTypes
- ✅ Business logic for pledges, donations, allocations, corporate match
- ✅ 3 script reports with charts
- ✅ Dashboard workspace with KPI cards
- ✅ Pledge approval workflow
- ✅ Print formats for receipts and confirmations
- ✅ Seed data for demos
- ✅ Hosted on GitHub, deployable to Frappe Cloud

That's a credible demo-ready alternative you can show any United Way that doesn't want Salesforce.
