import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate, add_days, add_months, getdate


class PledgeWriteoff(Document):
    def validate(self):
        self.validate_pledge_submitted()
        self.validate_writeoff_amount()

    def validate_pledge_submitted(self):
        """Ensure the linked pledge is in Submitted state."""
        if self.pledge:
            pledge_docstatus = frappe.db.get_value("Pledge", self.pledge, "docstatus")
            if pledge_docstatus != 1:
                frappe.throw(
                    f"Pledge {self.pledge} must be submitted (docstatus=1) before it can be written off. "
                    f"Current docstatus: {pledge_docstatus}"
                )

    def validate_writeoff_amount(self):
        """Ensure write-off amount does not exceed outstanding balance."""
        if flt(self.writeoff_amount) <= 0:
            frappe.throw("Write-off Amount must be greater than zero.")

        if flt(self.writeoff_amount) > flt(self.outstanding_balance):
            frappe.throw(
                f"Write-off Amount ({frappe.format_value(self.writeoff_amount, {'fieldtype': 'Currency'})}) "
                f"cannot exceed the Outstanding Balance "
                f"({frappe.format_value(self.outstanding_balance, {'fieldtype': 'Currency'})})."
            )

    def on_submit(self):
        """On submission: record approver, update pledge status, mark schedule entries."""
        self.db_set("approved_by", frappe.session.user)

        pledge = frappe.get_doc("Pledge", self.pledge)

        # Determine new collection status based on whether write-off covers full outstanding
        if flt(self.writeoff_amount) >= flt(pledge.outstanding_balance):
            pledge.collection_status = "Written Off"
        else:
            pledge.collection_status = "Partially Collected"

        pledge.db_update()

        # Mark any Pending or Overdue payment schedule entries as Written Off
        if hasattr(pledge, "payment_schedule") and pledge.payment_schedule:
            for entry in pledge.payment_schedule:
                if entry.status in ("Pending", "Overdue"):
                    entry.status = "Written Off"
                    entry.db_update()

        # Create journal entry if enabled
        try:
            from united_way.accounting import create_writeoff_journal_entry
            create_writeoff_journal_entry(self)
        except Exception:
            pass  # Don't block writeoff if JE creation fails

    def on_cancel(self):
        """On cancellation: reload pledge and recalculate collection fields."""
        pledge = frappe.get_doc("Pledge", self.pledge)
        pledge.update_collection_fields()
        pledge.db_update()


@frappe.whitelist()
def generate_payment_schedule(pledge_name):
    """Generate a payment schedule for a pledge based on its payment frequency.

    Args:
        pledge_name: The name (ID) of the Pledge document.

    Returns:
        List of dicts with due_date and expected_amount for each scheduled payment.
    """
    pledge = frappe.get_doc("Pledge", pledge_name)

    frequency_map = {
        "Weekly": 52,
        "Bi-Weekly": 26,
        "Monthly": 12,
        "Quarterly": 4,
        "Annually": 1,
    }

    frequency = pledge.payment_frequency or "One-Time"

    if frequency == "One-Time" or frequency not in frequency_map:
        # For one-time pledges, single entry on the pledge date
        return [{
            "due_date": str(pledge.pledge_date),
            "expected_amount": flt(pledge.pledge_amount)
        }]

    number_of_periods = frequency_map[frequency]
    expected_amount = flt(pledge.pledge_amount) / number_of_periods

    # Use payroll_start_date if available, otherwise fall back to pledge_date
    start_date = getdate(pledge.payroll_start_date) if pledge.payroll_start_date else getdate(pledge.pledge_date)

    schedule = []
    for i in range(number_of_periods):
        if frequency == "Weekly":
            due_date = add_days(start_date, i * 7)
        elif frequency == "Bi-Weekly":
            due_date = add_days(start_date, i * 14)
        elif frequency == "Monthly":
            due_date = add_months(start_date, i)
        elif frequency == "Quarterly":
            due_date = add_months(start_date, i * 3)
        elif frequency == "Annually":
            due_date = add_months(start_date, i * 12)
        else:
            due_date = add_days(start_date, i * 7)

        schedule.append({
            "due_date": str(due_date),
            "expected_amount": flt(expected_amount, 2)
        })

    return schedule
