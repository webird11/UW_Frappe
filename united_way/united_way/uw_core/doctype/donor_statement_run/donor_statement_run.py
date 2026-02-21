import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint


class DonorStatementRun(Document):
    def validate(self):
        self.calculate_summary_fields()

    def calculate_summary_fields(self):
        """Calculate rollup totals from the child items table."""
        self.total_donors = len(self.items) if self.items else 0
        self.total_amount = sum(flt(item.total_donations) for item in self.items) if self.items else 0
        self.statements_generated = sum(
            1 for item in self.items if cint(item.statement_generated)
        ) if self.items else 0
        self.statements_sent = sum(
            1 for item in self.items if item.sent_date
        ) if self.items else 0

    def on_submit(self):
        self.db_update()

    def on_cancel(self):
        self.db_update()


@frappe.whitelist()
def populate_donor_statements(tax_year):
    """Query all submitted donations for the given tax year, grouped by donor.

    Returns a list of dicts suitable for populating the Donor Statement Item child table:
        - donor: Contact name (ID)
        - donor_name: full name
        - total_donations: SUM(amount)
        - donation_count: COUNT(*)
        - tax_deductible_total: SUM(tax_deductible_amount)

    Only includes donors who have at least one submitted donation in the tax year.
    """
    tax_year = cint(tax_year)
    if not tax_year:
        frappe.throw("Please provide a valid tax year.")

    results = frappe.db.sql("""
        SELECT
            d.donor AS donor,
            d.donor_name AS donor_name,
            SUM(d.amount) AS total_donations,
            COUNT(d.name) AS donation_count,
            SUM(COALESCE(d.tax_deductible_amount, 0)) AS tax_deductible_total
        FROM `tabDonation` d
        WHERE YEAR(d.donation_date) = %s
          AND d.docstatus = 1
        GROUP BY d.donor, d.donor_name
        HAVING COUNT(d.name) >= 1
        ORDER BY d.donor_name
    """, (tax_year,), as_dict=True)

    return results
