# CLAUDE.md - Mission Briefing for Claude Code

## WHO YOU ARE AND WHAT THIS PROJECT IS

You are building a United Way CRM and Fundraising Platform on the **Frappe Framework (v15)** for Beyond the Horizon Technology (BTH). This replaces a Salesforce-based package for United Way organizations that want a vendor-independent solution. The project owner is Eric, a Salesforce architect with 12+ years of nonprofit CRM experience. He knows the business domain deeply but is new to Frappe. Your job is to be the Frappe expert.

## FIRST THINGS FIRST — ENVIRONMENT SETUP

Before writing ANY code, make sure the dev environment is running. Ask Eric what state he's in:

### If Frappe is NOT yet installed/running:

**Option A: Docker (Preferred)**
```bash
cd ~/UW_Frappe

# Clone frappe_docker if not present
git clone https://github.com/frappe/frappe_docker.git
cd frappe_docker
cp example.env .env

# Start containers
docker compose -f compose.yaml \
  -f overrides/compose.noproxy.yaml \
  -f overrides/compose.mariadb.yaml \
  -f overrides/compose.redis.yaml \
  up -d

# Wait for containers to be ready (check logs)
docker compose logs -f backend
# Wait for ready state, then Ctrl+C

# Create site
docker compose exec backend bench new-site uw.localhost \
  --mariadb-root-password 123 \
  --admin-password admin \
  --no-mariadb-socket

docker compose exec backend bench use uw.localhost

# Install the app — NOTE the app lives at ~/UW_Frappe/united_way/
# Inside the container, symlink or copy it:
docker compose exec backend bash -c "cd /workspace/development/frappe-bench && ln -s /path/to/mounted/united_way apps/united_way"
# OR clone from GitHub:
docker compose exec backend bash -c "cd /workspace/development/frappe-bench && bench get-app https://github.com/REPO_OWNER/UW_Frappe.git"

docker compose exec backend bench --site uw.localhost install-app united_way
docker compose exec backend bench --site uw.localhost migrate
docker compose exec backend bench --site uw.localhost execute united_way.seed.run
docker compose exec backend bench start
```

**Option B: Native Install (Ubuntu/WSL2)**
```bash
# Install system deps
sudo apt update && sudo apt install -y \
  python3-dev python3-pip python3-venv \
  redis-server mariadb-server mariadb-client \
  nodejs npm git curl

# MariaDB config
sudo tee /etc/mysql/mariadb.conf.d/50-custom.cnf << 'CONF'
[mysqld]
character-set-client-handshake = FALSE
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
[mysql]
default-character-set = utf8mb4
CONF
sudo systemctl restart mariadb

sudo npm install -g yarn
pip3 install frappe-bench

# Initialize bench
bench init uw-bench --frappe-branch version-15
cd uw-bench

# Create site
bench new-site uw.localhost --admin-password admin
bench use uw.localhost

# Get app from GitHub (or symlink local folder)
bench get-app https://github.com/REPO_OWNER/UW_Frappe.git
# If nested: ln -s ~/UW_Frappe/united_way apps/united_way

# Install and run
bench --site uw.localhost install-app united_way
bench --site uw.localhost migrate
bench --site uw.localhost execute united_way.seed.run
bench start
```

### If Frappe IS already running:
After any code changes, run:
```bash
bench --site uw.localhost migrate    # After DocType JSON changes
bench build                          # After CSS/JS changes
bench --site uw.localhost clear-cache  # If things look stale
```

Access: http://localhost:8000 — Login: Administrator / admin

---

## PROJECT STRUCTURE — KNOW THIS COLD

```
~/UW_Frappe/
├── CLAUDE.md                          ← YOU ARE HERE
├── README.md
├── TASKS.md                           ← WEEKEND SPRINT TASK LIST
├── .gitignore
├── scripts/
│   ├── docker-dev-setup.sh
│   ├── github-setup.sh
│   └── install-dependencies.sh
├── united_way/                        ← THE FRAPPE APP (this gets installed into bench)
│   ├── setup.py                       # Python package setup
│   ├── requirements.txt
│   └── united_way/                    ← App code lives here
│       ├── __init__.py
│       ├── hooks.py                   # App config, doc_events, scheduler, fixtures
│       ├── modules.txt                # Lists "UW Core"
│       ├── patches.txt                # Migration patches (empty for now)
│       ├── setup.py                   # Post-install: creates roles, defaults
│       ├── tasks.py                   # Scheduled background jobs
│       ├── utils.py                   # Shared helper functions
│       ├── seed.py                    # Test data generator
│       ├── public/
│       │   ├── css/united_way.css     # Global styles
│       │   └── js/united_way.js       # Global client scripts
│       └── uw_core/                   ← Main module
│           ├── __init__.py
│           ├── doctype/               ← Data models
│           │   ├── organization/      # 38 fields — agencies, corporates, partners
│           │   ├── contact/           # 34 fields — donors, staff, board members
│           │   ├── campaign/          # 23 fields — SUBMITTABLE
│           │   ├── pledge/            # 32 fields — SUBMITTABLE, has child allocations
│           │   ├── pledge_allocation/ # 6 fields — CHILD TABLE of Pledge
│           │   ├── donation/          # 22 fields — SUBMITTABLE
│           │   ├── agency_distribution/ # 5 fields — CHILD TABLE of Campaign
│           │   └── uw_settings/       # 17 fields — SINGLETON config
│           ├── report/
│           │   ├── campaign_summary/          # ✅ DONE — bar chart + KPIs
│           │   ├── donor_giving_history/      # 🔲 NEEDS BUILDING
│           │   └── agency_allocation_report/  # 🔲 NEEDS BUILDING
│           └── workspace/                     # 🔲 DASHBOARD NEEDS BUILDING
```

---

## FRAPPE FRAMEWORK ESSENTIALS — PATTERNS YOU MUST FOLLOW

### DocTypes = Data Models (like Salesforce Custom Objects)

Each DocType is defined by TWO files:
- `doctype_name.json` — Schema: fields, permissions, naming, layout, properties
- `doctype_name.py` — Controller: Python class with lifecycle event handlers

**JSON file is the source of truth for the schema.** When you add fields, modify the JSON directly. The field order in the JSON determines the form layout.

**Naming conventions:**
- DocType folder name: `snake_case` (e.g., `pledge_allocation`)
- DocType name in JSON: `Title Case` (e.g., `Pledge Allocation`)
- Python class: `PascalCase` (e.g., `PledgeAllocation`)
- Database table: `tabDocType Name` (e.g., `tabPledge Allocation`)

### Key DocType Properties
```json
{
  "name": "Pledge",
  "module": "UW Core",
  "is_submittable": 1,    // Enables Draft → Submitted → Cancelled workflow
  "istable": 0,           // Set to 1 for child tables (like Pledge Allocation)
  "issingle": 0,          // Set to 1 for settings/config singletons
  "autoname": "naming_series:", // Or "field:fieldname" or "format:PLG-{####}"
  "naming_series": "PLG-.YYYY.-.####"
}
```

### Field Types Reference
| Frappe Type | Salesforce Equivalent | Notes |
|---|---|---|
| `Data` | Text | Add `options: "Email"`, `"URL"`, `"Phone"` for validation |
| `Link` | Lookup | `options: "DocType Name"` — creates foreign key |
| `Table` | Master-Detail (child) | `options: "Child DocType Name"` — embeds rows |
| `Select` | Picklist | `options: "Option1\nOption2\nOption3"` (newline-separated) |
| `Currency` | Currency | |
| `Percent` | Percent | |
| `Int` / `Float` | Number | |
| `Date` / `Datetime` | Date / DateTime | |
| `Check` | Checkbox | Returns 0 or 1 |
| `Text Editor` | Rich Text Area | |
| `Small Text` | Long Text Area | |
| `Attach Image` | File field | |
| `Section Break` | — | Layout: starts new section |
| `Column Break` | — | Layout: starts new column within section |
| `Read Only` | Formula field | Use `fetch_from` or compute in Python |
| `MultiSelect` | Multi-Select Picklist | |

### Field Properties That Matter
```json
{
  "fieldname": "pledge_amount",
  "fieldtype": "Currency",
  "label": "Pledge Amount",
  "reqd": 1,                    // Required field
  "read_only": 1,               // Computed field
  "hidden": 1,                  // Hidden from UI
  "default": "Today",           // Default value
  "depends_on": "eval:doc.payment_method=='Payroll Deduction'",  // Conditional visibility
  "fetch_from": "donor.full_name",  // Auto-fetch from linked record
  "in_list_view": 1,            // Show in list view
  "in_standard_filter": 1,      // Show in filter sidebar
  "allow_on_submit": 1,         // Editable after submit
  "no_copy": 1,                 // Don't copy when duplicating
  "options": "Organization",     // For Link: target DocType. For Select: "opt1\nopt2"
  "permlevel": 0                // Permission level (0 = everyone with role access)
}
```

### Document Lifecycle Events (= Apex Triggers)
```python
import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate, add_days

class MyDocType(Document):
    def before_save(self):     # Before any save (insert or update)
    def validate(self):        # Validation — runs before insert AND update
    def before_insert(self):   # Before first save only
    def after_insert(self):    # After first save (record has a name now)
    def on_update(self):       # After any save
    def on_submit(self):       # When docstatus changes 0→1 (Draft→Submitted)
    def on_cancel(self):       # When docstatus changes 1→2 (Submitted→Cancelled)
    def on_trash(self):        # Before permanent deletion
    def before_naming(self):   # Before auto-name is generated
```

### Common Frappe APIs — USE THESE
```python
import frappe
from frappe.utils import flt, cint, nowdate, add_days, getdate, date_diff, fmt_money

# === CRUD ===
doc = frappe.get_doc("DocType", "record-name")       # Get by name
doc = frappe.get_doc("DocType", {"field": "value"})   # Get by filter (first match)
doc = frappe.new_doc("DocType")                        # New blank record
doc.field = "value"                                    # Set fields
doc.insert()                                           # Insert (creates name, runs validate)
doc.save()                                             # Update (runs validate)
doc.submit()                                           # Submit (docstatus 0→1)
doc.cancel()                                           # Cancel (docstatus 1→2)
doc.db_update()                                        # Direct DB write (SKIPS validation — use sparingly)
doc.reload()                                           # Refresh from DB

# === QUERIES (like SOQL) ===
frappe.get_all("Pledge",
    filters={"campaign": "2025 Annual Campaign", "docstatus": 1},
    fields=["name", "donor", "pledge_amount", "collection_status"],
    order_by="pledge_amount desc",
    limit_page_length=100
)

frappe.get_value("Organization", "Big Brothers Big Sisters", "agency_code")  # Single field
frappe.get_value("Donation", {"pledge": "PLG-001", "docstatus": 1}, "SUM(amount)")

frappe.db.exists("Organization", {"organization_name": "Meals on Wheels"})  # Boolean check
frappe.db.count("Pledge", {"campaign": campaign_name, "docstatus": 1})

# Raw SQL (for complex joins)
frappe.db.sql("""
    SELECT pa.agency, SUM(pa.allocated_amount) as total
    FROM `tabPledge Allocation` pa
    JOIN `tabPledge` p ON pa.parent = p.name
    WHERE p.campaign = %s AND p.docstatus = 1
    GROUP BY pa.agency
""", campaign_name, as_dict=True)

# === CONTEXT ===
frappe.session.user                         # Current logged-in user
frappe.throw("Error message")               # Stop execution, show error to user
frappe.msgprint("Info message")             # Show info popup (doesn't stop)
frappe.msgprint("Warning", indicator="orange", title="Watch Out")
frappe.logger().info("Log message")         # Server log
frappe.flags.ignore_permissions = True      # Bypass permissions (admin operations)

# === WHITELISTED APIs (callable from frontend JS) ===
@frappe.whitelist()
def my_api(param1, param2):
    """Frontend can call: frappe.call({method: 'united_way.utils.my_api', args: {...}})"""
    return {"result": "value"}

@frappe.whitelist(allow_guest=True)
def public_api():
    """No login required"""
    pass
```

### Permissions in DocType JSON
```json
"permissions": [
    {"role": "Campaign Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "submit": 1, "cancel": 1},
    {"role": "Agency Admin", "read": 1, "write": 0, "create": 0},
    {"role": "UW Finance", "read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
    {"role": "UW Executive", "read": 1},
    {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "submit": 1, "cancel": 1, "amend": 1}
]
```

---

## EXISTING BUSINESS LOGIC — DON'T BREAK THIS

### Pledge → Allocation Flow
1. Donor creates a Pledge linked to a Campaign
2. Pledge has child `Pledge Allocation` rows: agency + percentage + designation type
3. **Percentages MUST total exactly 100%** (validated in pledge.py)
4. **Dollar amounts auto-calculated**: pledge_amount × (percentage / 100)
5. **Duplicate agencies rejected** within same pledge
6. **Corporate match auto-calculated** if donor's org has matching program
7. On submit → Campaign totals recalculated

### Donation → Collection Flow
1. Donation links to a Pledge (optional — can be standalone)
2. If linked: validates campaign match and donor match
3. Warns on overpayment but doesn't block
4. On submit → Pledge collection fields update (total_collected, outstanding, status, %)
5. Campaign totals recalculate
6. Donor lifetime giving stats update on Contact record

### Campaign Rollups
- `total_pledged`: SUM of submitted pledge amounts
- `total_collected`: SUM of submitted donation amounts
- `pledge_count`, `donor_count`: distinct counts
- `percent_of_goal`: total_pledged / fundraising_goal × 100
- `collection_rate`: total_collected / total_pledged × 100

### Roles
| Role | Access Level |
|---|---|
| Campaign Manager | Full CRUD on campaigns, pledges, contacts, organizations |
| UW Finance | Full access to donations, financial reports, submit/cancel |
| Agency Admin | Read-only — sees allocations to their agency |
| UW Executive | Read-only dashboard view |
| System Manager | God mode |

---

## SCRIPT REPORTS — HOW TO BUILD THEM

Script Reports are the most powerful reporting option. Each report needs 3 files:

```
uw_core/report/report_name/
├── __init__.py              # Empty
├── report_name.json         # Report config
└── report_name.py           # Python: columns, data, chart, summary
```

**report_name.json:**
```json
{
  "name": "Report Name",
  "doctype": "Report",
  "ref_doctype": "Pledge",
  "report_type": "Script Report",
  "module": "UW Core",
  "is_standard": "Yes",
  "filters": [
    {
      "fieldname": "campaign",
      "label": "Campaign",
      "fieldtype": "Link",
      "options": "Campaign"
    },
    {
      "fieldname": "from_date",
      "label": "From Date",
      "fieldtype": "Date"
    }
  ]
}
```

**report_name.py:**
```python
import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)       # Optional — returns chart config
    summary = get_summary(data)   # Optional — returns KPI cards
    return columns, data, None, chart, summary

def get_columns():
    return [
        {"fieldname": "name", "label": "Name", "fieldtype": "Data", "width": 200},
        {"fieldname": "amount", "label": "Amount", "fieldtype": "Currency", "width": 140},
        # ...
    ]

def get_data(filters):
    # Return list of dicts matching column fieldnames
    return frappe.db.sql("""SELECT ...""", filters, as_dict=True)

def get_chart(data):
    return {
        "data": {
            "labels": [...],
            "datasets": [{"name": "Series", "values": [...]}]
        },
        "type": "bar",  # bar, line, pie, donut, percentage
        "colors": ["#5B8FF9", "#5AD8A6"]
    }

def get_summary(data):
    return [
        {"value": 1234, "label": "Total", "datatype": "Currency", "indicator": "green"},
    ]
```

---

## WORKSPACES — HOW TO BUILD DASHBOARDS

A Workspace is defined as a JSON file. Create it at:
```
uw_core/workspace/uw_core/uw_core.json
```

Structure:
```json
{
  "name": "UW Core",
  "module": "UW Core",
  "label": "United Way",
  "category": "Modules",
  "icon": "heart",
  "is_default": 0,
  "content": "[{\"type\":\"header\",\"data\":{\"text\":\"Your United Way\",...}}]",
  "charts": [
    {
      "chart_name": "Pledges by Campaign",
      "chart_type": "Report",
      "report_name": "Campaign Summary",
      "chart_height": 300
    }
  ],
  "shortcuts": [
    {"type": "DocType", "link_to": "Pledge", "label": "Pledges"},
    {"type": "DocType", "link_to": "Donation", "label": "Donations"},
    {"type": "Report", "link_to": "Campaign Summary", "label": "Campaign Report"}
  ],
  "number_cards": [
    {
      "number_card_name": "Total Pledged",
      "doctype": "Number Card",
      "document_type": "Pledge",
      "function": "Sum",
      "aggregate_function_based_on": "pledge_amount",
      "filters_json": "{\"docstatus\":1}"
    }
  ]
}
```

Note: Workspaces can also be created through the Frappe UI (Setup > Workspace) and exported. If you find it easier to build via UI and then export the JSON, that's fine.

---

## WORKFLOWS — HOW TO BUILD APPROVAL FLOWS

Workflows are typically created as fixture data (JSON) or through the UI. For the Pledge Approval workflow:

Create: `united_way/united_way/uw_core/doctype/pledge_workflow.json` or define it as a fixture.

The workflow needs:
- **States**: Draft, Pending Review, Approved, Rejected
- **Transitions**: Submit (Draft→Pending Review), Approve (Pending Review→Approved), Reject (Pending Review→Rejected)
- **Allowed roles**: Campaign Manager can submit, UW Finance can approve/reject

Alternatively, set this up through Frappe UI:
1. Go to Workflow list
2. Create new Workflow for document type "Pledge"
3. Define states and transitions
4. Save — it auto-applies

---

## PRINT FORMATS — HOW TO BUILD THEM

Print Formats use Jinja2 templates. Create at:
```
uw_core/print_format/donation_receipt/
├── __init__.py
├── donation_receipt.json
└── donation_receipt.html    # Jinja2 template
```

**donation_receipt.html:**
```html
<div class="print-format">
  <h2>Donation Receipt</h2>
  <p>Date: {{ doc.donation_date }}</p>
  <p>Donor: {{ doc.donor_name }}</p>
  <p>Amount: {{ frappe.utils.fmt_money(doc.amount) }}</p>
  {% if doc.tax_deductible %}
  <p>Tax Deductible Amount: {{ frappe.utils.fmt_money(doc.tax_deductible_amount) }}</p>
  {% endif %}
  <p>Campaign: {{ doc.campaign }}</p>
  <p>Thank you for your generous contribution!</p>
</div>
```

---

## DEVELOPMENT COMMANDS CHEAT SHEET

```bash
bench start                                      # Dev server (must be running)
bench --site uw.localhost migrate                 # Apply DocType/schema changes
bench --site uw.localhost clear-cache             # Clear server + Redis cache
bench build                                      # Rebuild JS/CSS assets
bench --site uw.localhost console                 # Python REPL with Frappe loaded
bench --site uw.localhost execute module.function  # Run any Python function
bench --site uw.localhost set-admin-password admin  # Reset admin password
bench --site uw.localhost execute united_way.seed.run  # Reload seed data
```

---

## GIT WORKFLOW

After completing each task:
```bash
cd ~/UW_Frappe
git add .
git commit -m "descriptive message of what was built"
git push origin main
```

Commit after each completed task, not at the end. This gives Eric restore points.

---

## CRITICAL RULES

1. **All code goes under `united_way/united_way/`** — never modify Frappe core files
2. **Module is always "UW Core"** — every DocType, Report, Workspace references this module
3. **Run `bench migrate` after ANY DocType JSON change** — or changes won't appear
4. **Submittable DocTypes** (Campaign, Pledge, Donation) use docstatus: 0=Draft, 1=Submitted, 2=Cancelled. Filter queries with `docstatus = 1` for active records
5. **Child tables** (Pledge Allocation, Agency Distribution) have `istable: 1` and are embedded in parent forms via a `Table` field
6. **Use `flt()` for all math** — `from frappe.utils import flt` — it handles None/empty gracefully
7. **Don't break existing business logic** — the pledge allocation validation, campaign rollups, and donation processing all work. Test after changes.
8. **Permissions matter** — every DocType JSON must have a permissions array. Use the 5 roles defined above.
9. **Naming matters** — DocType folder = `snake_case`, DocType name = `Title Case`, class = `PascalCase`
10. **Commit often** — after each completed task
