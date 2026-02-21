# United Way Platform - Frappe Edition

A vendor-independent CRM and fundraising platform for United Way organizations, built on the [Frappe Framework](https://frappeframework.com/).

## Overview

This application provides United Way organizations with:
- Organization and Contact management
- Campaign and Pledge tracking with multi-agency allocation
- Donation processing and reconciliation
- Agency distribution reporting
- Role-based access for Campaign Managers, Agency Admins, and Finance staff

## Quick Start (Local Development)

### Prerequisites
- Ubuntu 22.04/24.04 (or macOS with Homebrew)
- Python 3.10+
- Node.js 18+
- MariaDB 10.6+
- Redis 6+
- Git

### Option A: Docker Development Environment (Recommended)

```bash
# 1. Run the Docker setup script
chmod +x scripts/docker-dev-setup.sh
./scripts/docker-dev-setup.sh

# 2. Access the site at http://localhost:8080
#    Login: Administrator / admin
```

### Option B: Native Installation

```bash
# 1. Install system dependencies (Ubuntu)
chmod +x scripts/install-dependencies.sh
./scripts/install-dependencies.sh

# 2. Install Frappe Bench
pip3 install frappe-bench

# 3. Initialize bench
bench init --frappe-branch version-15 uw-bench
cd uw-bench

# 4. Create a new site
bench new-site uw.localhost --mariadb-root-password YOUR_MYSQL_ROOT_PW --admin-password admin

# 5. Clone this app into the bench
# Option: symlink from your repo location
ln -s /path/to/UW_Frappe/united_way apps/united_way
# Or: copy the app
# cp -r /path/to/UW_Frappe/united_way apps/

# 6. Install the app on your site
bench --site uw.localhost install-app united_way

# 7. Run database migrations
bench --site uw.localhost migrate

# 8. Start development server
bench start

# 9. Access at http://uw.localhost:8000
#    Login: Administrator / admin
```

### Load Sample Data

```bash
bench --site uw.localhost execute united_way.seed.run
```

## Project Structure

```
united_way/                    # Frappe custom app
├── united_way/
│   ├── hooks.py               # App hooks (event handlers, schedulers)
│   ├── modules.txt            # Registered modules
│   ├── uw_core/               # Main module
│   │   ├── doctype/           # Data models (DocTypes)
│   │   │   ├── organization/  # Member agencies, corporate donors
│   │   │   ├── contact/       # Individual contacts
│   │   │   ├── campaign/      # Annual campaigns
│   │   │   ├── pledge/        # Pledges with allocations
│   │   │   ├── donation/      # Payments received
│   │   │   └── ...
│   │   ├── report/            # Custom reports
│   │   └── workspace/         # Dashboard configurations
│   └── seed.py                # Sample data generator
├── setup.py
└── requirements.txt
```

## Salesforce Concept Mapping

| Salesforce | Frappe | Notes |
|---|---|---|
| Custom Object | DocType | JSON-defined, auto-generates DB + API |
| Fields | DocType Fields | Same types: Link, Currency, Date, Select |
| Lookup | Link field | Foreign key to another DocType |
| Master-Detail | Child Table | Embedded table (like Pledge Allocations) |
| Record Type | Select field or separate DocType | Depends on complexity |
| Sharing Rules | User Permissions | Role + user-level access |
| Apex Trigger | hooks.py / DocType controller | Python, no governor limits |
| Flow | Workflow | Built-in state machine engine |
| Lightning Component | Page / Web Template | JS + Jinja templates |
| Report | Report Builder / Script Report | No-code or Python |
| Permission Set | Role | Assignable permission bundles |

## License

Proprietary - Beyond the Horizon Technology, LLC
