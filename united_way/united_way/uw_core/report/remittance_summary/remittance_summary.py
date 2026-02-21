import frappe
from frappe.utils import flt


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {"fieldname": "name", "label": "Remittance ID", "fieldtype": "Link", "options": "Remittance", "width": 160},
        {"fieldname": "organization", "label": "Organization", "fieldtype": "Link", "options": "Organization", "width": 200},
        {"fieldname": "campaign", "label": "Campaign", "fieldtype": "Link", "options": "Campaign", "width": 180},
        {"fieldname": "remittance_date", "label": "Date", "fieldtype": "Date", "width": 110},
        {"fieldname": "total_amount", "label": "Total Amount", "fieldtype": "Currency", "width": 140},
        {"fieldname": "items_count", "label": "Items Count", "fieldtype": "Int", "width": 100},
        {"fieldname": "donations_created", "label": "Donations Created", "fieldtype": "Int", "width": 130},
        {"fieldname": "payment_method", "label": "Payment Method", "fieldtype": "Data", "width": 130},
        {"fieldname": "reference_number", "label": "Reference Number", "fieldtype": "Data", "width": 140},
    ]


def get_data(filters):
    conditions = "r.docstatus = 1"
    values = {}

    if filters and filters.get("campaign"):
        conditions += " AND r.campaign = %(campaign)s"
        values["campaign"] = filters["campaign"]

    if filters and filters.get("organization"):
        conditions += " AND r.organization = %(organization)s"
        values["organization"] = filters["organization"]

    if filters and filters.get("from_date"):
        conditions += " AND r.remittance_date >= %(from_date)s"
        values["from_date"] = filters["from_date"]

    if filters and filters.get("to_date"):
        conditions += " AND r.remittance_date <= %(to_date)s"
        values["to_date"] = filters["to_date"]

    data = frappe.db.sql(f"""
        SELECT
            r.name,
            r.organization,
            r.organization_name,
            r.campaign,
            r.remittance_date,
            r.total_amount,
            r.donations_created,
            r.payment_method,
            r.reference_number,
            COUNT(ri.name) as items_count
        FROM `tabRemittance` r
        LEFT JOIN `tabRemittance Item` ri ON ri.parent = r.name
        WHERE {conditions}
        GROUP BY r.name, r.organization, r.organization_name, r.campaign,
                 r.remittance_date, r.total_amount, r.donations_created,
                 r.payment_method, r.reference_number
        ORDER BY r.remittance_date DESC, r.total_amount DESC
    """, values, as_dict=True)

    return data


def get_chart(data):
    if not data:
        return None

    # Aggregate by organization - top 10 by total amount
    org_totals = {}
    for row in data:
        org = row.get("organization_name") or row.get("organization", "")[:20]
        org_totals[org] = flt(org_totals.get(org, 0)) + flt(row.total_amount)

    sorted_orgs = sorted(org_totals.items(), key=lambda x: x[1], reverse=True)[:10]

    if not sorted_orgs:
        return None

    return {
        "data": {
            "labels": [o[0] for o in sorted_orgs],
            "datasets": [
                {"name": "Total Remitted", "values": [o[1] for o in sorted_orgs]},
            ],
        },
        "type": "bar",
        "colors": ["#5B8FF9"],
    }


def get_summary(data):
    total_count = len(data)
    total_amount = sum(flt(row.total_amount) for row in data)
    total_donations = sum(flt(row.donations_created) for row in data)
    avg_size = total_amount / total_count if total_count else 0

    return [
        {"value": total_count, "label": "Total Remittances", "datatype": "Int", "indicator": "blue"},
        {"value": total_amount, "label": "Total Amount", "datatype": "Currency", "indicator": "green"},
        {"value": total_donations, "label": "Donations Created", "datatype": "Int", "indicator": "blue"},
        {"value": avg_size, "label": "Avg Remittance Size", "datatype": "Currency", "indicator": "green"},
    ]
