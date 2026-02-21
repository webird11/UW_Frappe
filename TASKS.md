# TASKS.md — Weekend Sprint Task List

## Instructions for Claude Code

Work through these tasks IN ORDER. Each task should be committed to git when complete.
Ask Eric before moving to the next task if anything is ambiguous.
Run `bench --site uw.localhost migrate` after every DocType JSON change.
Test each feature before moving on.

---

## TASK 1: Donor Giving History Report ⏱️ ~1 hour

**Location:** `united_way/united_way/uw_core/report/donor_giving_history/`

Create a Script Report that shows each donor's complete giving profile.

**Files to create:**
- `donor_giving_history.json` — report config with filters for campaign, date range, donor, organization
- `donor_giving_history.py` — report logic

**Columns:**
- Donor (Link to Contact)
- Organization (Link to Organization)
- Campaign (Link to Campaign)
- Pledge Amount (Currency)
- Total Donated (Currency)
- Outstanding (Currency)
- Collection % (Percent)
- Pledge Count (Int)
- Donor Since (Date)
- Lifetime Giving (Currency)

**Filters:**
- Campaign (Link to Campaign)
- From Date / To Date (Date)
- Organization (Link to Organization)
- Donor Level (Select — same options as Contact.donor_level)

**Chart:** Horizontal bar chart — top 10 donors by lifetime giving

**Summary cards:** Total donors, total pledged, total collected, average gift size

**Commit message:** `feat: Donor Giving History script report with chart and KPIs`

---

## TASK 2: Agency Allocation Detail Report ⏱️ ~1 hour

**Location:** `united_way/united_way/uw_core/report/agency_allocation_report/`

Create a Script Report showing exactly which donors pledged to each agency.

**Files to create:**
- `agency_allocation_report.json`
- `agency_allocation_report.py`

**Columns:**
- Agency (Link to Organization)
- Agency Code (Data)
- Donor (Link to Contact)
- Donor Organization (Link to Organization)
- Campaign (Link to Campaign)
- Designation Type (Data)
- Allocation % (Percent)
- Allocated Amount (Currency)
- Collected Against Pledge (Currency)
- Pledge Status (Data)

**Filters:**
- Agency (Link to Organization, filtered to org_type = "Member Agency")
- Campaign (Link to Campaign)
- Campaign Year (Int)
- Designation Type (Select: Donor Designated, Community Impact, Corporate)

**Chart:** Pie chart — allocation by agency for selected campaign

**Summary cards:** Total agencies, total allocated, total collected, number of designations

**Logic notes:**
- Join Pledge Allocation → Pledge → Campaign, and Pledge Allocation → Organization
- Only include submitted pledges (docstatus = 1)
- For "Collected Against Pledge" — pull from the Pledge's collection_percentage × allocation amount (proportional)

**Commit message:** `feat: Agency Allocation Detail report with pie chart`

---

## TASK 3: UW Core Workspace (Dashboard) ⏱️ ~1.5 hours

**Location:** `united_way/united_way/uw_core/workspace/uw_core/`

Create the main dashboard workspace.

**Files to create:**
- `uw_core.json` — workspace definition

**Number Cards (top row):**
1. Total Pledged (Sum of Pledge.pledge_amount where docstatus=1)
2. Total Collected (Sum of Donation.amount where docstatus=1)
3. Active Campaigns (Count of Campaign where status="Active" and docstatus=1)
4. Total Donors (Count distinct Contact where contact_type="Individual Donor")

**Charts:**
1. Pledged vs Collected by Agency (bar chart — from Campaign Summary report)
2. Monthly Donation Trend (line chart — donations grouped by month for current year)
3. Campaign Progress (bar chart — each active campaign's % of goal)
4. Donor Level Distribution (pie chart — count of donors by donor_level)

**Shortcuts:**
- New Pledge, New Donation, New Contact, New Organization
- Campaign Summary Report, Donor Giving History, Agency Allocation Report
- UW Settings

**Note:** You may need to create Number Card and Dashboard Chart doctypes in the system. These are standard Frappe DocTypes. You can create them via:
```python
# In bench console or via execute
frappe.get_doc({
    "doctype": "Number Card",
    "name": "Total Pledged",
    "document_type": "Pledge",
    "function": "Sum",
    "aggregate_function_based_on": "pledge_amount",
    "filters_json": '{"docstatus": 1}',
    "label": "Total Pledged",
    "module": "UW Core"
}).insert()
```

Alternatively, create the workspace through the Frappe UI and export the JSON.

**Commit message:** `feat: UW Core workspace with number cards, charts, and shortcuts`

---

## TASK 4: Pledge Approval Workflow ⏱️ ~45 min

Create a Frappe Workflow for the Pledge DocType.

**States:**
| State | Doc Status | Style |
|---|---|---|
| Draft | 0 | Red |
| Pending Review | 0 | Orange |
| Approved | 1 | Blue |
| Rejected | 0 | Red |
| Cancelled | 2 | Red |

**Transitions:**
| Action | From | To | Allowed Role |
|---|---|---|---|
| Submit for Review | Draft | Pending Review | Campaign Manager |
| Approve | Pending Review | Approved | UW Finance |
| Reject | Pending Review | Rejected | UW Finance |
| Revise | Rejected | Draft | Campaign Manager |
| Cancel | Approved | Cancelled | UW Finance |

**Implementation options:**
1. Create via Frappe UI (Workflow → New) and export as fixture
2. Create as a Python script that runs on install (in setup.py)
3. Create directly as fixture JSON

**Also add:** A `workflow_state` field to the Pledge DocType JSON if not already present (Frappe may auto-add this).

**Commit message:** `feat: Pledge approval workflow with role-based transitions`

---

## TASK 5: Print Format — Donation Receipt ⏱️ ~45 min

**Location:** `united_way/united_way/uw_core/print_format/donation_receipt/`

Create a professional donation receipt for tax purposes.

**Files to create:**
- `donation_receipt.json` — print format config
- `donation_receipt.html` — Jinja2 template

**Content:**
- Header: United Way logo/name (from UW Settings)
- Title: "Official Donation Receipt"
- Receipt number (donation name/ID)
- Date of donation
- Donor name and address (from linked Contact)
- Donation amount (formatted currency)
- Tax deductible amount (if applicable)
- Campaign name
- Payment method and reference number
- IRS disclaimer text: "No goods or services were provided in exchange for this contribution. [Organization Name] is a 501(c)(3) tax-exempt organization. EIN: [from org settings]"
- Footer: Thank you message

**Styling:** Clean, professional, suitable for printing. Use inline CSS.

**Commit message:** `feat: Donation receipt print format`

---

## TASK 6: Print Format — Pledge Confirmation ⏱️ ~45 min

**Location:** `united_way/united_way/uw_core/print_format/pledge_confirmation/`

Create a pledge confirmation letter showing the allocation breakdown.

**Content:**
- Header: United Way branding
- "Pledge Confirmation" title
- Pledge date and ID
- Donor name and address
- Campaign name and year
- Pledge amount
- Payment method and frequency
- If payroll deduction: deduction per period, start/end dates, employer name
- **Allocation table:** Agency name | Designation Type | Percentage | Dollar Amount
- If corporate match eligible: expected match amount and status
- Thank you message
- Contact information for questions

**Commit message:** `feat: Pledge confirmation print format with allocation table`

---

## TASK 7: Email Templates ⏱️ ~45 min

Create email templates for common communications.

**Templates to create** (as Email Template DocType fixtures or as Jinja files):

1. **Pledge Confirmation Email**
   - Subject: "Thank you for your pledge to {{ campaign }}"
   - Body: Pledge summary, allocation breakdown, payment schedule if applicable

2. **Donation Thank You Email**
   - Subject: "Thank you for your gift of {{ amount }}"
   - Body: Donation details, tax deductible info, link to receipt

3. **Pledge Reminder Email**
   - Subject: "Reminder: Outstanding pledge balance"
   - Body: Original pledge amount, collected so far, outstanding balance, how to pay

4. **Campaign Update Email**
   - Subject: "{{ campaign }} Progress Update"
   - Body: Campaign goal, progress %, donor count, thank you

**Implementation:** Create as fixtures in hooks.py or as files that the setup.py after_install creates.

**Commit message:** `feat: Email templates for pledge confirmation, donation thanks, reminders`

---

## TASK 8: Data Import Templates ⏱️ ~1 hour

Create CSV import templates and a data import helper for migrating from Salesforce.

**Location:** `united_way/united_way/import_templates/`

**Templates to create:**
1. `organizations_import.csv` — Headers matching Organization DocType fields
2. `contacts_import.csv` — Headers matching Contact DocType fields
3. `pledges_import.csv` — Headers matching Pledge fields (with allocation sub-rows)
4. `donations_import.csv` — Headers matching Donation fields

**Each CSV should have:**
- Header row with Frappe field names
- 2-3 example rows showing expected format
- Comments or a companion `.md` file explaining field mappings from Salesforce

**Also create:** `united_way/united_way/import_helpers.py` with utility functions:
- `import_organizations_from_csv(filepath)` — reads CSV, creates Organization docs
- `import_contacts_from_csv(filepath)` — reads CSV, links to orgs
- `validate_import_data(doctype, rows)` — pre-validates before import

**Commit message:** `feat: Data import templates and helper scripts for Salesforce migration`

---

## TASK 9: Dashboard Charts & Number Cards ⏱️ ~1 hour

If not already created as part of Task 3, create the actual Dashboard Chart and Number Card records.

**Create a setup script** at `united_way/united_way/setup_dashboard.py`:

```python
def create_dashboard_elements():
    """Create Number Cards and Dashboard Charts for the UW Core workspace."""
    create_number_cards()
    create_dashboard_charts()

def create_number_cards():
    # Total Pledged, Total Collected, Active Campaigns, Total Donors
    ...

def create_dashboard_charts():
    # Monthly Donation Trend, Campaign Progress, Donor Level Distribution
    ...
```

Wire it into `setup.py` after_install or make it callable via:
```bash
bench --site uw.localhost execute united_way.setup_dashboard.create_dashboard_elements
```

**Commit message:** `feat: Dashboard number cards and chart configurations`

---

## TASK 10: Contact DocType Enhancement ⏱️ ~30 min

The Contact DocType has a `update_donor_stats` method referenced in donation.py but it may not be fully implemented. Verify and complete:

**In contact.py, ensure these methods exist:**
```python
def update_donor_stats(self):
    """Recalculate lifetime giving, last donation, consecutive years, donor level."""
    # Sum all submitted donations for this contact
    # Update: lifetime_giving, last_donation_date, last_donation_amount
    # Calculate consecutive_years_giving
    # Auto-set donor_level based on lifetime_giving thresholds

def autoset_donor_level(self):
    """Set donor level based on lifetime giving thresholds.
    Bronze: < $500
    Silver: $500 - $2,499
    Gold: $2,500 - $9,999
    Platinum: $10,000+
    """
```

**Also verify:** The `full_name` field is auto-set from first_name + last_name in validate().

**Commit message:** `feat: Complete Contact donor stats calculation and auto-leveling`

---

## STRETCH GOALS (if time permits)

### S1: Donor Portal (Web View)
A simple web page where donors can see their pledge status and giving history. Uses Frappe's Web Page or Portal Page feature.

### S2: Bulk Pledge Entry
A custom page for processing workplace campaign pledge forms in bulk — paste a spreadsheet or upload CSV of pledges for a single campaign.

### S3: API Endpoints
Whitelist custom API endpoints for potential future integrations:
- `GET /api/method/united_way.api.get_campaign_summary`
- `GET /api/method/united_way.api.get_donor_profile`
- `POST /api/method/united_way.api.create_pledge`

### S4: Automated Tests
Create test files for the core business logic:
- `test_pledge.py` — allocation validation, corporate match calc
- `test_donation.py` — pledge linkage, overpayment warning
- `test_campaign.py` — rollup calculations

---

## DONE CHECKLIST

After completing all tasks, verify:
- [ ] All 3 reports load without errors
- [ ] Workspace dashboard shows number cards and charts
- [ ] Pledge workflow allows Draft → Pending Review → Approved flow
- [ ] Donation receipt print format renders correctly
- [ ] Pledge confirmation print format shows allocation table
- [ ] Seed data loads without errors: `bench execute united_way.seed.run`
- [ ] All changes committed and pushed to GitHub
- [ ] `bench --site uw.localhost migrate` runs clean with no errors
