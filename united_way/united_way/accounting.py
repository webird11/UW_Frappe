import frappe
from frappe.utils import flt, nowdate

# Default account mappings — can be overridden in UW Settings
DEFAULT_ACCOUNTS = {
    "donations_receivable": "1200 - Donations Receivable",
    "donation_revenue": "4100 - Donation Revenue",
    "agency_payable": "2100 - Agency Payable",
    "distribution_expense": "5100 - Agency Distributions",
    "writeoff_expense": "5200 - Pledge Write-offs",
    "cash": "1000 - Cash",
}

def create_donation_journal_entry(donation):
    """Create a journal entry when a Donation is submitted.

    Debit: Cash/Donations Receivable
    Credit: Donation Revenue
    """
    if not should_create_journal_entries():
        return

    entry = frappe.new_doc("UW Journal Entry")
    entry.posting_date = donation.donation_date or nowdate()
    entry.entry_type = "Donation Receipt"
    entry.reference_doctype = "Donation"
    entry.reference_name = donation.name
    entry.debit_account = DEFAULT_ACCOUNTS["cash"]
    entry.credit_account = DEFAULT_ACCOUNTS["donation_revenue"]
    entry.amount = flt(donation.amount)
    entry.campaign = donation.campaign
    entry.donor = donation.donor
    entry.remarks = f"Donation {donation.name} from {donation.donor_name or donation.donor}"
    entry.insert(ignore_permissions=True)
    return entry.name

def create_distribution_journal_entries(distribution_run):
    """Create journal entries for each agency distribution item.

    For each agency:
    Debit: Agency Distribution Expense
    Credit: Agency Payable
    """
    if not should_create_journal_entries():
        return

    entries = []
    for item in distribution_run.items:
        entry = frappe.new_doc("UW Journal Entry")
        entry.posting_date = distribution_run.distribution_date or nowdate()
        entry.entry_type = "Agency Distribution"
        entry.reference_doctype = "Distribution Run"
        entry.reference_name = distribution_run.name
        entry.debit_account = DEFAULT_ACCOUNTS["distribution_expense"]
        entry.credit_account = DEFAULT_ACCOUNTS["agency_payable"]
        entry.amount = flt(item.distribution_amount)
        entry.campaign = distribution_run.campaign
        entry.agency = item.agency
        entry.remarks = f"Distribution to {item.agency} - {distribution_run.name}"
        entry.insert(ignore_permissions=True)
        entries.append(entry.name)

    return entries

def create_writeoff_journal_entry(writeoff):
    """Create a journal entry when a Pledge Writeoff is submitted.

    Debit: Writeoff Expense
    Credit: Donations Receivable (reducing the receivable)
    """
    if not should_create_journal_entries():
        return

    entry = frappe.new_doc("UW Journal Entry")
    entry.posting_date = writeoff.writeoff_date or nowdate()
    entry.entry_type = "Pledge Writeoff"
    entry.reference_doctype = "Pledge Writeoff"
    entry.reference_name = writeoff.name
    entry.debit_account = DEFAULT_ACCOUNTS["writeoff_expense"]
    entry.credit_account = DEFAULT_ACCOUNTS["donations_receivable"]
    entry.amount = flt(writeoff.writeoff_amount)
    entry.campaign = writeoff.campaign
    entry.donor = writeoff.donor
    entry.remarks = f"Write-off of {writeoff.writeoff_amount} for pledge {writeoff.pledge}"
    entry.insert(ignore_permissions=True)
    return entry.name

def should_create_journal_entries():
    """Check if journal entry creation is enabled in UW Settings.
    Returns True if auto_create_journal_entries is checked in settings."""
    try:
        return frappe.db.get_single_value("UW Settings", "auto_create_journal_entries") or 0
    except Exception:
        return False

@frappe.whitelist()
def get_accounting_summary(campaign=None):
    """Get a summary of all journal entries, optionally filtered by campaign.

    Returns totals by entry_type.
    """
    filters = {}
    if campaign:
        filters["campaign"] = campaign

    summary = frappe.db.sql("""
        SELECT
            entry_type,
            COUNT(*) as count,
            SUM(amount) as total_amount
        FROM `tabUW Journal Entry`
        {where}
        GROUP BY entry_type
        ORDER BY entry_type
    """.format(where="WHERE campaign = %(campaign)s" if campaign else ""),
    filters, as_dict=True)

    return summary
