import frappe

no_cache = 1


def get_context(context):
    """Build context for bulk pledge entry page."""
    if frappe.session.user == "Guest":
        frappe.throw("Please log in to access bulk pledge entry.", frappe.AuthenticationError)

    context.no_cache = 1
    context.show_sidebar = False
    context.title = "Bulk Pledge Entry"

    # Get active campaigns for the dropdown
    context.campaigns = frappe.get_all(
        "Campaign",
        filters={"status": ["in", ["Active", "Planning"]], "docstatus": 1},
        fields=["name", "campaign_name", "campaign_year"],
        order_by="campaign_year desc, campaign_name",
    )
