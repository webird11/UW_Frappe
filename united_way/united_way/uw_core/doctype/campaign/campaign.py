import frappe
from frappe.model.document import Document


class Campaign(Document):
    def validate(self):
        if self.end_date and self.start_date and self.end_date < self.start_date:
            frappe.throw("End Date cannot be before Start Date.")

    def update_totals(self):
        """Recalculate campaign totals from pledges and donations.
        Called by Pledge and Donation hooks after submit/cancel."""

        # Total pledged
        pledged = frappe.db.sql("""
            SELECT
                COALESCE(SUM(pledge_amount), 0) as total_pledged,
                COUNT(DISTINCT name) as pledge_count,
                COUNT(DISTINCT donor) as donor_count
            FROM `tabPledge`
            WHERE campaign = %s AND docstatus = 1
        """, self.name, as_dict=True)[0]

        self.total_pledged = pledged.total_pledged
        self.pledge_count = pledged.pledge_count
        self.donor_count = pledged.donor_count

        # Total collected
        collected = frappe.db.get_value(
            "Donation",
            {"campaign": self.name, "docstatus": 1},
            "SUM(amount)"
        ) or 0
        self.total_collected = collected

        # Calculated fields
        if self.fundraising_goal:
            self.percent_of_goal = (self.total_pledged / self.fundraising_goal) * 100

        if self.total_pledged:
            self.collection_rate = (self.total_collected / self.total_pledged) * 100
        else:
            self.collection_rate = 0

        self.db_update()
        frappe.db.commit()


def recalculate_campaign(campaign_name):
    """Utility function to trigger campaign recalculation."""
    if campaign_name:
        campaign = frappe.get_doc("Campaign", campaign_name)
        campaign.update_totals()
