import frappe
from frappe.model.document import Document
from frappe.utils import flt


class BatchDeposit(Document):
    def validate(self):
        self.set_item_campaigns()
        self.validate_items()
        self.calculate_totals()

    def set_item_campaigns(self):
        """Set item campaign from default_campaign if item.campaign is empty."""
        for item in self.items:
            if not item.campaign and self.default_campaign:
                item.campaign = self.default_campaign

    def validate_items(self):
        """Validate each item has donor and amount."""
        for idx, item in enumerate(self.items, start=1):
            if not item.donor:
                frappe.throw(f"Row {idx}: Donor is required.")
            if flt(item.amount) <= 0:
                frappe.throw(f"Row {idx}: Amount must be greater than zero.")

    def calculate_totals(self):
        """Calculate items_total, variance, and item_count."""
        self.items_total = flt(sum(flt(item.amount) for item in self.items))
        self.variance = flt(flt(self.total_amount) - flt(self.items_total))
        self.item_count = len(self.items)

    def on_submit(self):
        """Create a Donation for each item."""
        count = 0
        for item in self.items:
            donation = frappe.new_doc("Donation")
            donation.donation_date = self.deposit_date
            donation.donor = item.donor
            donation.campaign = item.campaign or self.default_campaign
            donation.amount = flt(item.amount)
            donation.pledge = item.pledge
            donation.payment_method = item.payment_method
            donation.reference_number = item.check_number
            donation.batch_number = self.name
            donation.insert()
            donation.submit()

            item.donation = donation.name
            item.db_update()
            count += 1

        self.donations_created = count
        self.db_update()

    def on_cancel(self):
        """Cancel each linked donation, clear item.donation, reset donations_created."""
        for item in self.items:
            if item.donation:
                try:
                    donation = frappe.get_doc("Donation", item.donation)
                    if donation.docstatus == 1:
                        donation.cancel()
                except Exception:
                    frappe.log_error(
                        f"Failed to cancel Donation {item.donation} from Batch Deposit {self.name}",
                        "Batch Deposit Cancel Error"
                    )

                item.donation = None
                item.db_update()

        self.donations_created = 0
        self.db_update()
