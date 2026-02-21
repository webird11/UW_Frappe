import frappe


def after_install():
    """Run after app installation to set up roles and defaults."""
    create_roles()
    create_default_settings()
    create_pledge_workflow()
    create_email_templates()
    setup_dashboard()
    frappe.db.commit()
    print("United Way app setup complete.")


def create_email_templates():
    """Create standard email templates."""
    from united_way.email_templates import create_email_templates as _create
    _create()


def setup_dashboard():
    """Create dashboard number cards and charts."""
    from united_way.setup_dashboard import create_dashboard_elements
    create_dashboard_elements()


def create_roles():
    """Create custom roles for the United Way app."""
    roles = [
        {"role_name": "Campaign Manager", "desk_access": 1},
        {"role_name": "Agency Admin", "desk_access": 1},
        {"role_name": "UW Finance", "desk_access": 1},
        {"role_name": "UW Executive", "desk_access": 1},
        {"role_name": "Donor Portal User", "desk_access": 0},
    ]

    for role_data in roles:
        if not frappe.db.exists("Role", role_data["role_name"]):
            role = frappe.get_doc({
                "doctype": "Role",
                "role_name": role_data["role_name"],
                "desk_access": role_data["desk_access"],
                "is_custom": 1,
            })
            role.insert(ignore_permissions=True)
            print(f"  Created role: {role_data['role_name']}")


def create_default_settings():
    """Initialize UW Settings with defaults."""
    if not frappe.db.exists("UW Settings"):
        settings = frappe.get_doc({
            "doctype": "UW Settings",
            "united_way_name": "United Way",
            "fiscal_year_start_month": "January",
            "default_currency": "USD",
            "pledge_reminder_days": 30,
            "send_pledge_confirmations": 1,
            "send_donation_receipts": 1,
        })
        settings.insert(ignore_permissions=True)
        print("  Created default UW Settings")


def create_pledge_workflow():
    """Create the Pledge Approval workflow with role-based transitions."""
    if frappe.db.exists("Workflow", "Pledge Approval"):
        print("  Pledge Approval workflow already exists, skipping")
        return

    workflow = frappe.get_doc({
        "doctype": "Workflow",
        "workflow_name": "Pledge Approval",
        "document_type": "Pledge",
        "is_active": 1,
        "send_email_alert": 0,
        "states": [
            {
                "state": "Draft",
                "doc_status": "0",
                "style": "Red",
                "allow_edit": "Campaign Manager",
            },
            {
                "state": "Pending Review",
                "doc_status": "0",
                "style": "Orange",
                "allow_edit": "UW Finance",
            },
            {
                "state": "Approved",
                "doc_status": "1",
                "style": "Blue",
                "allow_edit": "UW Finance",
            },
            {
                "state": "Rejected",
                "doc_status": "0",
                "style": "Red",
                "allow_edit": "Campaign Manager",
            },
            {
                "state": "Cancelled",
                "doc_status": "2",
                "style": "Red",
                "allow_edit": "UW Finance",
            },
        ],
        "transitions": [
            {
                "state": "Draft",
                "action": "Submit for Review",
                "next_state": "Pending Review",
                "allowed": "Campaign Manager",
                "allow_self_approval": 1,
            },
            {
                "state": "Pending Review",
                "action": "Approve",
                "next_state": "Approved",
                "allowed": "UW Finance",
                "allow_self_approval": 1,
            },
            {
                "state": "Pending Review",
                "action": "Reject",
                "next_state": "Rejected",
                "allowed": "UW Finance",
                "allow_self_approval": 1,
            },
            {
                "state": "Rejected",
                "action": "Revise",
                "next_state": "Draft",
                "allowed": "Campaign Manager",
                "allow_self_approval": 1,
            },
            {
                "state": "Approved",
                "action": "Cancel",
                "next_state": "Cancelled",
                "allowed": "UW Finance",
                "allow_self_approval": 1,
            },
        ],
    })
    workflow.insert(ignore_permissions=True)
    print("  Created Pledge Approval workflow")
