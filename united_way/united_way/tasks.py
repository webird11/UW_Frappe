import frappe
from frappe.utils import add_days, nowdate, getdate


def daily_pledge_reminders():
    """Send reminders for pledges with outstanding balances past the reminder threshold."""
    settings = frappe.get_single("UW Settings")
    reminder_days = settings.pledge_reminder_days or 30

    cutoff_date = add_days(nowdate(), -reminder_days)

    overdue_pledges = frappe.get_all(
        "Pledge",
        filters={
            "docstatus": 1,
            "collection_status": ["in", ["Not Started", "In Progress"]],
            "pledge_date": ["<", cutoff_date],
        },
        fields=["name", "donor", "donor_name", "pledge_amount", "total_collected", "outstanding_balance", "campaign"],
    )

    for pledge in overdue_pledges:
        # Check if donor has email and is contactable
        contact = frappe.get_doc("Contact", pledge.donor)
        if contact.email and not contact.do_not_contact and not contact.do_not_email:
            # TODO: Send email notification
            frappe.logger().info(
                f"Pledge reminder due: {pledge.name} - {pledge.donor_name} "
                f"- Outstanding: ${pledge.outstanding_balance:,.2f}"
            )

    frappe.db.commit()


def mark_overdue_payment_schedules():
    """Mark payment schedule entries as overdue if past due date and still pending."""
    today = nowdate()

    overdue = frappe.db.sql("""
        SELECT pse.name, pse.parent
        FROM `tabPayment Schedule Entry` pse
        JOIN `tabPledge` p ON pse.parent = p.name
        WHERE pse.status = 'Pending'
        AND pse.due_date < %s
        AND p.docstatus = 1
    """, today, as_dict=True)

    for entry in overdue:
        frappe.db.set_value("Payment Schedule Entry", entry.name, "status", "Overdue")

    if overdue:
        frappe.logger().info(f"Marked {len(overdue)} payment schedule entries as overdue")
        frappe.db.commit()


def weekly_campaign_summary():
    """Generate weekly summary of active campaign progress."""
    active_campaigns = frappe.get_all(
        "Campaign",
        filters={"status": "Active", "docstatus": 1},
        fields=["name", "campaign_name", "fundraising_goal", "total_pledged", "total_collected"],
    )

    for campaign in active_campaigns:
        frappe.logger().info(
            f"Campaign '{campaign.campaign_name}': "
            f"Goal ${campaign.fundraising_goal:,.2f} | "
            f"Pledged ${campaign.total_pledged:,.2f} | "
            f"Collected ${campaign.total_collected:,.2f}"
        )

    # TODO: Send summary email to Campaign Managers and Executives


def monthly_agency_distribution():
    """Calculate and log monthly agency distribution summaries for active campaigns."""
    active_campaigns = frappe.get_all(
        "Campaign",
        filters={"status": "Active", "docstatus": 1},
        pluck="name",
    )

    for campaign_name in active_campaigns:
        distributions = frappe.db.sql("""
            SELECT
                pa.agency,
                o.organization_name,
                SUM(pa.allocated_amount) as total_allocated,
                COUNT(DISTINCT p.donor) as donor_count
            FROM `tabPledge Allocation` pa
            JOIN `tabPledge` p ON pa.parent = p.name
            JOIN `tabOrganization` o ON pa.agency = o.name
            WHERE p.campaign = %s AND p.docstatus = 1
            GROUP BY pa.agency, o.organization_name
            ORDER BY total_allocated DESC
        """, campaign_name, as_dict=True)

        for dist in distributions:
            frappe.logger().info(
                f"Distribution [{campaign_name}] {dist.organization_name}: "
                f"${dist.total_allocated:,.2f} from {dist.donor_count} donors"
            )

    frappe.db.commit()
