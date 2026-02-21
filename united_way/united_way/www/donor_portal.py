import frappe

no_cache = 1


def get_context(context):
    """Build context for the donor portal page."""
    if frappe.session.user == "Guest":
        frappe.throw("Please log in to view your donor portal.", frappe.AuthenticationError)

    context.no_cache = 1
    context.show_sidebar = False
    context.title = "My Giving Dashboard"

    # Find the Contact record linked to this user's email
    contact_name = frappe.db.get_value(
        "Contact", {"email": frappe.session.user, "status": "Active"}, "name"
    )

    if not contact_name:
        context.donor = None
        context.pledges = []
        context.donations = []
        context.no_contact = True
        return

    context.no_contact = False
    context.donor = frappe.get_doc("Contact", contact_name)

    # Get pledges for this donor
    context.pledges = frappe.get_all(
        "Pledge",
        filters={"donor": contact_name, "docstatus": 1},
        fields=[
            "name", "campaign", "pledge_date", "pledge_amount",
            "payment_method", "payment_frequency", "total_collected",
            "outstanding_balance", "collection_percentage", "collection_status",
        ],
        order_by="pledge_date desc",
        limit_page_length=50,
    )

    # Get donations for this donor
    context.donations = frappe.get_all(
        "Donation",
        filters={"donor": contact_name, "docstatus": 1},
        fields=[
            "name", "donation_date", "campaign", "amount",
            "payment_method", "pledge", "tax_deductible_amount",
        ],
        order_by="donation_date desc",
        limit_page_length=50,
    )

    # Summary stats
    context.total_pledged = sum(p.pledge_amount or 0 for p in context.pledges)
    context.total_donated = sum(d.amount or 0 for d in context.donations)
    context.total_outstanding = sum(p.outstanding_balance or 0 for p in context.pledges)
    context.pledge_count = len(context.pledges)
