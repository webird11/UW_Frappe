import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate


class DistributionRun(Document):
    def validate(self):
        self.validate_period_dates()
        self.validate_item_amounts()
        self.calculate_totals()

    def validate_period_dates(self):
        """Ensure period end is on or after period start."""
        if self.period_start and self.period_end:
            if getdate(self.period_end) < getdate(self.period_start):
                frappe.throw(
                    "Period End date cannot be before Period Start date."
                )

    def validate_item_amounts(self):
        """Ensure all distribution items have a positive amount."""
        for item in self.items:
            if flt(item.distribution_amount) <= 0:
                frappe.throw(
                    f"Row {item.idx}: Distribution amount for {item.agency or 'unnamed agency'} "
                    f"must be greater than zero."
                )

    def calculate_totals(self):
        """Calculate total distribution amount and agency count."""
        self.total_distribution = sum(
            flt(item.distribution_amount) for item in self.items
        )
        self.agency_count = len(self.items)

    def on_submit(self):
        """Record the distribution decision and create journal entries if enabled."""
        self.db_update()
        try:
            from united_way.accounting import create_distribution_journal_entries
            create_distribution_journal_entries(self)
        except Exception:
            pass  # Don't block distribution if JE creation fails

    def on_cancel(self):
        """Cancel the distribution run."""
        self.db_update()


@frappe.whitelist()
def populate_distribution_items(campaign, period_start, period_end):
    """Build distribution line items for all agencies with pledge allocations in a campaign.

    For each agency:
    - total_allocated: sum of allocated_amount from submitted Pledge Allocations
    - total_collected: proportional collections based on each pledge's collection_percentage
    - previously_distributed: sum of distribution_amount from prior submitted Distribution Runs
    - distribution_amount: total_collected - previously_distributed (minimum 0)

    Args:
        campaign: Campaign name (link value)
        period_start: Start of distribution period (not currently used in query but
            reserved for future period-based filtering)
        period_end: End of distribution period (reserved for future use)

    Returns:
        list of dicts ready to populate the Distribution Item child table
    """
    # Step 1: Get all agencies with pledge allocations for this campaign,
    # along with their total allocated amounts and proportional collections.
    agency_data = frappe.db.sql("""
        SELECT
            pa.agency,
            SUM(pa.allocated_amount) AS total_allocated,
            SUM(pa.allocated_amount * IFNULL(p.collection_percentage, 0) / 100) AS total_collected
        FROM `tabPledge Allocation` pa
        JOIN `tabPledge` p ON pa.parent = p.name
        WHERE p.campaign = %s
          AND p.docstatus = 1
        GROUP BY pa.agency
        ORDER BY pa.agency
    """, campaign, as_dict=True)

    if not agency_data:
        frappe.msgprint(
            "No submitted pledge allocations found for this campaign.",
            indicator="orange",
            title="No Data"
        )
        return []

    # Step 2: For each agency, get the total previously distributed amount
    # from prior submitted Distribution Runs for this campaign.
    previously_distributed_data = frappe.db.sql("""
        SELECT
            di.agency,
            SUM(di.distribution_amount) AS previously_distributed
        FROM `tabDistribution Item` di
        JOIN `tabDistribution Run` dr ON di.parent = dr.name
        WHERE dr.campaign = %s
          AND dr.docstatus = 1
        GROUP BY di.agency
    """, campaign, as_dict=True)

    prev_dist_map = {
        row.agency: flt(row.previously_distributed)
        for row in previously_distributed_data
    }

    # Step 3: Build the result list
    items = []
    for row in agency_data:
        total_allocated = flt(row.total_allocated)
        total_collected = flt(row.total_collected)
        previously_distributed = flt(prev_dist_map.get(row.agency, 0))
        distribution_amount = max(flt(total_collected) - flt(previously_distributed), 0)

        # Only include agencies that have something to distribute
        if distribution_amount > 0:
            items.append({
                "agency": row.agency,
                "total_allocated": total_allocated,
                "total_collected": total_collected,
                "previously_distributed": previously_distributed,
                "distribution_amount": distribution_amount,
            })

    if not items:
        frappe.msgprint(
            "All collected funds have already been distributed for this campaign.",
            indicator="blue",
            title="Fully Distributed"
        )

    return items
