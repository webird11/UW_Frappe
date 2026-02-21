import frappe
from frappe.model.document import Document
from frappe.utils import flt


class Donation(Document):
    def validate(self):
        self.validate_pledge_link()
        self.set_tax_deductible_amount()

    def validate_pledge_link(self):
        """If linked to a pledge, validate campaign matches and check overpayment."""
        if self.pledge:
            pledge = frappe.get_doc("Pledge", self.pledge)

            # Campaign must match
            if pledge.campaign != self.campaign:
                frappe.throw(
                    f"Campaign mismatch: This donation is for campaign '{self.campaign}' "
                    f"but the linked pledge belongs to campaign '{pledge.campaign}'."
                )

            # Donor must match
            if pledge.donor != self.donor:
                frappe.throw(
                    f"Donor mismatch: This donation is from '{self.donor}' "
                    f"but the linked pledge belongs to '{pledge.donor}'."
                )

            # Warn on overpayment (don't block)
            total_existing = frappe.db.get_value(
                "Donation",
                {"pledge": self.pledge, "docstatus": 1, "name": ("!=", self.name)},
                "SUM(amount)",
            ) or 0

            if flt(total_existing) + flt(self.amount) > flt(pledge.pledge_amount):
                frappe.msgprint(
                    f"Note: Total donations ({flt(total_existing) + flt(self.amount):,.2f}) "
                    f"will exceed pledge amount ({flt(pledge.pledge_amount):,.2f}).",
                    indicator="orange",
                    title="Overpayment",
                )

    def set_tax_deductible_amount(self):
        """Default tax deductible amount to full amount if not set."""
        if self.tax_deductible and not self.tax_deductible_amount:
            self.tax_deductible_amount = self.amount

    def on_submit(self):
        """Update linked pledge collection status and campaign totals."""
        self.update_pledge()
        self.update_campaign()
        self.update_donor_stats()

    def on_cancel(self):
        """Reverse updates on cancellation."""
        self.update_pledge()
        self.update_campaign()
        self.update_donor_stats()

    def update_pledge(self):
        """Trigger pledge recalculation."""
        if self.pledge:
            pledge = frappe.get_doc("Pledge", self.pledge)
            pledge.update_collection_fields()
            pledge.db_update()
            frappe.db.commit()

    def update_campaign(self):
        """Trigger campaign recalculation."""
        if self.campaign:
            from united_way.uw_core.doctype.campaign.campaign import recalculate_campaign
            recalculate_campaign(self.campaign)

    def update_donor_stats(self):
        """Trigger donor stats recalculation."""
        if self.donor:
            try:
                contact = frappe.get_doc("Contact", self.donor)
                contact.update_donor_stats()
            except Exception:
                pass  # Don't block donation processing if stats update fails


# Hook functions referenced in hooks.py
def validate_donation(doc, method):
    pass


def on_submit_donation(doc, method):
    pass


@frappe.whitelist()
def get_pledge_query(doctype, txt, searchfield, start, page_len, filters):
    """Filter pledge lookup to show only submitted pledges for the selected donor/campaign."""
    conditions = ["p.docstatus = 1"]
    values = {"txt": f"%{txt}%", "start": start, "page_len": page_len}

    if filters and filters.get("donor"):
        conditions.append("p.donor = %(donor)s")
        values["donor"] = filters["donor"]

    if filters and filters.get("campaign"):
        conditions.append("p.campaign = %(campaign)s")
        values["campaign"] = filters["campaign"]

    where = " AND ".join(conditions)

    return frappe.db.sql(f"""
        SELECT p.name, p.donor_name, p.pledge_amount, p.campaign
        FROM `tabPledge` p
        WHERE {where}
        AND (p.name LIKE %(txt)s OR p.donor_name LIKE %(txt)s)
        ORDER BY p.pledge_date DESC
        LIMIT %(start)s, %(page_len)s
    """, values)
