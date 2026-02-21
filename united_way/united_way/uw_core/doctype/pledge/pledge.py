import frappe
from frappe.model.document import Document
from frappe.utils import flt


class Pledge(Document):
    def validate(self):
        self.validate_allocations()
        self.calculate_allocation_amounts()
        self.calculate_corporate_match()
        self.update_collection_fields()

    def validate_allocations(self):
        """Ensure allocation percentages total exactly 100%."""
        if not self.allocations:
            frappe.throw("At least one allocation is required. Please designate funds to one or more agencies.")

        total_pct = sum(flt(a.percentage) for a in self.allocations)

        if abs(total_pct - 100) > 0.01:
            frappe.throw(
                f"Allocation percentages must total 100%. "
                f"Current total: {total_pct:.2f}%"
            )

        # Check for duplicate agencies
        agencies = [a.agency for a in self.allocations]
        duplicates = set(a for a in agencies if agencies.count(a) > 1)
        if duplicates:
            frappe.throw(
                f"Duplicate agency allocations found: {', '.join(duplicates)}. "
                "Please combine allocations for the same agency."
            )

    def calculate_allocation_amounts(self):
        """Calculate dollar amounts from percentages."""
        for allocation in self.allocations:
            allocation.allocated_amount = flt(self.pledge_amount) * flt(allocation.percentage) / 100

    def calculate_corporate_match(self):
        """Auto-calculate expected corporate match amount."""
        if self.eligible_for_match and self.donor_organization:
            org = frappe.get_doc("Organization", self.donor_organization)
            if org.corporate_match and org.match_ratio:
                self.match_amount = min(
                    flt(self.pledge_amount) * flt(org.match_ratio),
                    flt(org.match_cap) if org.match_cap else float("inf"),
                )
            else:
                self.match_amount = 0
        elif not self.eligible_for_match:
            self.match_amount = 0

    def update_collection_fields(self):
        """Recalculate collection status from linked donations."""
        total_collected = frappe.db.get_value(
            "Donation",
            {"pledge": self.name, "docstatus": 1},
            "SUM(amount)",
        ) or 0

        self.total_collected = total_collected
        self.outstanding_balance = flt(self.pledge_amount) - flt(total_collected)

        if self.pledge_amount:
            self.collection_percentage = (flt(total_collected) / flt(self.pledge_amount)) * 100
        else:
            self.collection_percentage = 0

        # Auto-set collection status
        if total_collected == 0:
            self.collection_status = "Not Started"
        elif flt(total_collected) >= flt(self.pledge_amount):
            self.collection_status = "Fully Collected"
        else:
            self.collection_status = "In Progress"

        # Last payment date
        last_payment = frappe.db.get_value(
            "Donation",
            {"pledge": self.name, "docstatus": 1},
            "MAX(donation_date)",
        )
        if last_payment:
            self.last_payment_date = last_payment

    def on_submit(self):
        """After pledge is submitted, update campaign totals."""
        self.update_campaign_totals()

    def on_cancel(self):
        """After pledge is cancelled, update campaign totals."""
        self.update_campaign_totals()

    def update_campaign_totals(self):
        """Trigger campaign recalculation."""
        if self.campaign:
            from united_way.uw_core.doctype.campaign.campaign import recalculate_campaign
            recalculate_campaign(self.campaign)


# Hook functions referenced in hooks.py
def validate_pledge(doc, method):
    """Called by doc_events hook."""
    pass  # Validation handled by class method


def on_submit_pledge(doc, method):
    """Called by doc_events hook."""
    pass  # Handled by class method


def on_cancel_pledge(doc, method):
    """Called by doc_events hook."""
    pass  # Handled by class method
