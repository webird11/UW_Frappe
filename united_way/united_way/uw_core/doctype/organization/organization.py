import frappe
from frappe.model.document import Document


class Organization(Document):
    def validate(self):
        if self.organization_type == "Member Agency" and not self.agency_code:
            frappe.throw("Agency Code is required for Member Agency organizations.")

        if self.corporate_match and not self.match_ratio:
            frappe.throw("Match Ratio is required when Corporate Match Program is enabled.")

    def get_total_pledges(self, campaign=None):
        """Get total pledge allocations directed to this organization."""
        filters = {"agency": self.name, "docstatus": 1}
        if campaign:
            filters["parent"] = ("in",
                frappe.get_all("Pledge", filters={"campaign": campaign, "docstatus": 1}, pluck="name")
            )
        return frappe.db.sql("""
            SELECT COALESCE(SUM(allocated_amount), 0) as total
            FROM `tabPledge Allocation`
            WHERE agency = %s AND docstatus = 1
        """, self.name, as_dict=True)[0].get("total", 0)

    def get_total_donations(self, campaign=None):
        """Get total donations received for this organization."""
        filters = {"allocated_agency": self.name, "docstatus": 1}
        if campaign:
            filters["campaign"] = campaign
        return frappe.db.get_value("Donation", filters, "SUM(amount)") or 0
