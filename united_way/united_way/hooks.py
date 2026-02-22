app_name = "united_way"
app_title = "United Way"
app_publisher = "Beyond the Horizon Technology"
app_description = "United Way CRM and Fundraising Platform"
app_email = "eric@bthtech.com"
app_license = "Proprietary"
app_version = "0.1.0"

# Required apps
required_apps = ["frappe"]

# Module registration
# Each module maps to a folder under united_way/
# --------------------------------------------------------------------------

# Document Events
# Hook into document lifecycle events (like Apex triggers)
# --------------------------------------------------------------------------
doc_events = {
    "Pledge": {
        "validate": "united_way.uw_core.doctype.pledge.pledge.validate_pledge",
        "on_submit": "united_way.uw_core.doctype.pledge.pledge.on_submit_pledge",
        "on_cancel": "united_way.uw_core.doctype.pledge.pledge.on_cancel_pledge",
    },
    "Donation": {
        "validate": "united_way.uw_core.doctype.donation.donation.validate_donation",
        "on_submit": "united_way.uw_core.doctype.donation.donation.on_submit_donation",
    },
}

# Scheduled Tasks (like Salesforce Scheduled Apex)
# --------------------------------------------------------------------------
scheduler_events = {
    "daily": [
        "united_way.tasks.daily_pledge_reminders",
        "united_way.tasks.mark_overdue_payment_schedules",
    ],
    "weekly": [
        "united_way.tasks.weekly_campaign_summary",
    ],
    "monthly": [
        "united_way.tasks.monthly_agency_distribution",
    ],
}

# Permissions - default roles created on install
# --------------------------------------------------------------------------
after_install = "united_way.setup.after_install"

# Website / Portal
# --------------------------------------------------------------------------
# website_generators = ["Campaign"]

# Jinja template filters
# --------------------------------------------------------------------------
jinja = {
    "methods": [
        "united_way.utils.format_currency_short",
    ],
}

# Fixtures - export these doctypes as JSON for version control
# --------------------------------------------------------------------------
fixtures = [
    {
        "dt": "Role",
        "filters": [["name", "in", [
            "Campaign Manager",
            "Agency Admin",
            "UW Finance",
            "UW Executive",
            "Donor Portal User",
        ]]],
    },
    {
        "dt": "Workflow",
        "filters": [["name", "in", [
            "Pledge Approval",
            "Donation Processing",
        ]]],
    },
    {
        "dt": "Custom Field",
        "filters": [["module", "=", "UW Core"]],
    },
    {
        "dt": "Email Template",
        "filters": [["name", "in", [
            "Pledge Confirmation",
            "Donation Thank You",
            "Pledge Reminder",
            "Campaign Update",
        ]]],
    },
]

# Override default Frappe desktop icons
# --------------------------------------------------------------------------
app_include_css = "/assets/united_way/css/united_way.css"
app_include_js = "/assets/united_way/js/united_way.js"

# Permission Query Conditions — filter list views for Agency Admins
# These add WHERE clauses so Agency Admins only see data for their agency.
# --------------------------------------------------------------------------
permission_query_conditions = {
	"Pledge Allocation": "united_way.permissions.get_pledge_allocation_permission_query",
	"Distribution Item": "united_way.permissions.get_distribution_item_permission_query",
	"Distribution Run": "united_way.permissions.get_distribution_run_permission_query",
}

# Has Permission — per-document permission checks for Agency Admins
# --------------------------------------------------------------------------
has_permission = {
	"Pledge Allocation": "united_way.permissions.has_pledge_allocation_permission",
	"Distribution Item": "united_way.permissions.has_distribution_item_permission",
	"Distribution Run": "united_way.permissions.has_distribution_run_permission",
}
