import frappe
from frappe.utils import flt


@frappe.whitelist(allow_guest=False)
def get_campaign_summary(campaign=None, campaign_year=None):
    """Get campaign summary with pledge and donation totals.

    GET /api/method/united_way.api.get_campaign_summary?campaign=CAMP-2025-0001
    GET /api/method/united_way.api.get_campaign_summary?campaign_year=2025
    """
    filters = {"docstatus": 1}
    if campaign:
        filters["name"] = campaign
    if campaign_year:
        filters["campaign_year"] = campaign_year

    campaigns = frappe.get_all(
        "Campaign",
        filters=filters,
        fields=[
            "name", "campaign_name", "campaign_type", "campaign_year",
            "status", "start_date", "end_date", "fundraising_goal",
            "total_pledged", "total_collected", "percent_of_goal",
            "donor_count", "pledge_count", "collection_rate",
        ],
        order_by="campaign_year desc, campaign_name",
    )

    for camp in campaigns:
        camp["outstanding"] = flt(camp["total_pledged"]) - flt(camp["total_collected"])

    return campaigns


@frappe.whitelist(allow_guest=False)
def get_donor_profile(donor=None, email=None):
    """Get donor profile with giving history.

    GET /api/method/united_way.api.get_donor_profile?donor=John-Smith-0001
    GET /api/method/united_way.api.get_donor_profile?email=john@example.com
    """
    if not donor and not email:
        frappe.throw("Either 'donor' (Contact name) or 'email' is required.")

    if email and not donor:
        donor = frappe.db.get_value("Contact", {"email": email}, "name")
        if not donor:
            frappe.throw(f"No contact found with email '{email}'.")

    contact = frappe.get_doc("Contact", donor)

    profile = {
        "name": contact.name,
        "full_name": contact.full_name,
        "email": contact.email,
        "organization": contact.organization,
        "contact_type": contact.contact_type,
        "donor_since": contact.donor_since,
        "lifetime_giving": flt(contact.lifetime_giving),
        "donor_level": contact.donor_level,
        "last_donation_date": contact.last_donation_date,
        "last_donation_amount": flt(contact.last_donation_amount),
        "consecutive_years_giving": contact.consecutive_years_giving,
    }

    # Get active pledges
    profile["pledges"] = frappe.get_all(
        "Pledge",
        filters={"donor": donor, "docstatus": 1},
        fields=[
            "name", "campaign", "pledge_date", "pledge_amount",
            "total_collected", "outstanding_balance", "collection_status",
        ],
        order_by="pledge_date desc",
    )

    # Get recent donations
    profile["recent_donations"] = frappe.get_all(
        "Donation",
        filters={"donor": donor, "docstatus": 1},
        fields=[
            "name", "donation_date", "campaign", "amount",
            "payment_method", "pledge",
        ],
        order_by="donation_date desc",
        limit_page_length=20,
    )

    return profile


@frappe.whitelist(allow_guest=False)
def create_pledge(campaign, donor, pledge_amount, allocations,
                  payment_method=None, payment_frequency="One-Time",
                  pledge_date=None, eligible_for_match=0):
    """Create and optionally submit a new pledge via API.

    POST /api/method/united_way.api.create_pledge
    Body (JSON):
    {
        "campaign": "CAMP-2025-0001",
        "donor": "John-Smith-0001",
        "pledge_amount": 5000,
        "payment_method": "Payroll Deduction",
        "payment_frequency": "Monthly",
        "allocations": [
            {"agency": "Big Brothers Big Sisters", "designation_type": "Donor Designated", "percentage": 60},
            {"agency": "Meals on Wheels", "designation_type": "Community Impact Fund", "percentage": 40}
        ]
    }
    """
    import json

    if isinstance(allocations, str):
        allocations = json.loads(allocations)

    if not allocations:
        frappe.throw("At least one allocation is required.")

    # Validate totals
    total_pct = sum(flt(a.get("percentage", 0)) for a in allocations)
    if abs(total_pct - 100) > 0.01:
        frappe.throw(f"Allocation percentages total {total_pct}%, must equal 100%.")

    pledge = frappe.new_doc("Pledge")
    pledge.campaign = campaign
    pledge.donor = donor
    pledge.pledge_amount = flt(pledge_amount)
    pledge.pledge_date = pledge_date or frappe.utils.nowdate()
    pledge.payment_method = payment_method
    pledge.payment_frequency = payment_frequency
    pledge.eligible_for_match = int(eligible_for_match)

    for alloc in allocations:
        pledge.append("allocations", {
            "agency": alloc["agency"],
            "designation_type": alloc.get("designation_type", "Undesignated"),
            "percentage": flt(alloc["percentage"]),
        })

    pledge.insert()

    return {
        "pledge": pledge.name,
        "status": "Draft",
        "pledge_amount": pledge.pledge_amount,
        "match_amount": flt(pledge.match_amount),
        "message": f"Pledge {pledge.name} created successfully.",
    }
