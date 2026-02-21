import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate


class CampaignDrive(Document):
    def validate(self):
        self.validate_dates()

    def validate_dates(self):
        """Ensure drive_end_date is on or after drive_start_date if both are set."""
        if self.drive_start_date and self.drive_end_date:
            if getdate(self.drive_end_date) < getdate(self.drive_start_date):
                frappe.throw(
                    "Drive End Date cannot be before Drive Start Date."
                )

    def update_drive_totals(self):
        """Query submitted pledges for this campaign + organization and update rollup fields."""
        result = frappe.db.sql("""
            SELECT
                COALESCE(SUM(p.pledge_amount), 0) AS total_pledged,
                COUNT(p.name) AS pledge_count
            FROM `tabPledge` p
            WHERE p.campaign = %s
              AND p.donor_organization = %s
              AND p.docstatus = 1
        """, (self.campaign, self.organization), as_dict=True)

        row = result[0] if result else {}

        self.total_pledged = flt(row.get("total_pledged", 0))
        self.pledge_count = row.get("pledge_count", 0) or 0

        # Calculate participation rate
        if self.employee_count:
            self.participation_rate = flt(self.pledge_count) / flt(self.employee_count) * 100
        else:
            self.participation_rate = 0

        # Calculate percent of goal
        if self.goal_amount:
            self.percent_of_goal = flt(self.total_pledged) / flt(self.goal_amount) * 100
        else:
            self.percent_of_goal = 0

        self.db_update()


@frappe.whitelist()
def refresh_drive_totals(drive_name):
    """Whitelisted function to recalculate drive totals from the frontend."""
    drive = frappe.get_doc("Campaign Drive", drive_name)
    drive.update_drive_totals()
    return {
        "total_pledged": drive.total_pledged,
        "pledge_count": drive.pledge_count,
        "participation_rate": drive.participation_rate,
        "percent_of_goal": drive.percent_of_goal,
    }
