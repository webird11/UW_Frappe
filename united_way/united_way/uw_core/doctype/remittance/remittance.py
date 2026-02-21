import frappe
from frappe.model.document import Document
from frappe.utils import flt


class Remittance(Document):
    def validate(self):
        self.validate_items()
        self.calculate_totals()

    def validate_items(self):
        """Ensure all items have required fields and no empty rows."""
        if not self.items:
            frappe.throw("Remittance must have at least one item.")

        for idx, item in enumerate(self.items, start=1):
            if not item.donor:
                frappe.throw(f"Row {idx}: Donor is required for every remittance item.")
            if flt(item.amount) <= 0:
                frappe.throw(f"Row {idx}: Amount must be greater than zero.")

    def calculate_totals(self):
        """Calculate items total and variance."""
        self.items_total = flt(sum(flt(item.amount) for item in self.items))
        self.variance = flt(flt(self.total_amount) - flt(self.items_total))

    def on_submit(self):
        """Create individual Donation records for each remittance item."""
        donation_count = 0

        for item in self.items:
            donation = frappe.new_doc("Donation")
            donation.donation_date = self.remittance_date
            donation.donor = item.donor
            donation.campaign = self.campaign
            donation.amount = item.amount
            donation.pledge = item.pledge
            donation.payment_method = "Payroll Deduction"
            donation.reference_number = self.reference_number
            donation.batch_number = self.name
            donation.insert()
            donation.submit()

            # Write the created donation name back to the item row
            frappe.db.set_value("Remittance Item", item.name, "donation", donation.name)
            donation_count += 1

        # Update the donations created count
        self.db_set("donations_created", donation_count)

    def on_cancel(self):
        """Cancel all Donation records created by this remittance."""
        for item in self.items:
            if item.donation:
                donation = frappe.get_doc("Donation", item.donation)
                donation.cancel()
                frappe.db.set_value("Remittance Item", item.name, "donation", "")

        self.db_set("donations_created", 0)
