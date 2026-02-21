import frappe
from frappe.model.document import Document


class PledgeAllocation(Document):
    pass


@frappe.whitelist()
def get_agency_query(doctype, txt, searchfield, start, page_len, filters):
    """Filter organization lookup to show only Member Agencies."""
    return frappe.db.sql("""
        SELECT name, organization_name, agency_code
        FROM `tabOrganization`
        WHERE organization_type = 'Member Agency'
        AND status = 'Active'
        AND (
            name LIKE %(txt)s
            OR organization_name LIKE %(txt)s
            OR agency_code LIKE %(txt)s
        )
        ORDER BY organization_name
        LIMIT %(start)s, %(page_len)s
    """, {
        "txt": f"%{txt}%",
        "start": start,
        "page_len": page_len,
    })
