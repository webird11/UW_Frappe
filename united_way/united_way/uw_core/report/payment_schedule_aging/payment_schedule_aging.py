import frappe
from frappe.utils import flt, getdate, date_diff, nowdate


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {"fieldname": "pledge", "label": "Pledge", "fieldtype": "Link", "options": "Pledge", "width": 150},
        {"fieldname": "donor", "label": "Donor", "fieldtype": "Link", "options": "Contact", "width": 160},
        {"fieldname": "donor_name", "label": "Donor Name", "fieldtype": "Data", "width": 160},
        {"fieldname": "organization", "label": "Organization", "fieldtype": "Link", "options": "Organization", "width": 180},
        {"fieldname": "campaign", "label": "Campaign", "fieldtype": "Link", "options": "Campaign", "width": 170},
        {"fieldname": "due_date", "label": "Due Date", "fieldtype": "Date", "width": 110},
        {"fieldname": "expected_amount", "label": "Expected Amount", "fieldtype": "Currency", "width": 130},
        {"fieldname": "actual_amount", "label": "Actual Amount", "fieldtype": "Currency", "width": 120},
        {"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 110},
        {"fieldname": "days_overdue", "label": "Days Overdue", "fieldtype": "Int", "width": 110},
        {"fieldname": "donation", "label": "Donation", "fieldtype": "Link", "options": "Donation", "width": 150},
    ]


def get_data(filters):
    conditions = "p.docstatus = 1"
    values = {}

    if filters and filters.get("campaign"):
        conditions += " AND p.campaign = %(campaign)s"
        values["campaign"] = filters["campaign"]

    if filters and filters.get("from_date"):
        conditions += " AND pse.due_date >= %(from_date)s"
        values["from_date"] = filters["from_date"]

    if filters and filters.get("to_date"):
        conditions += " AND pse.due_date <= %(to_date)s"
        values["to_date"] = filters["to_date"]

    if filters and filters.get("organization"):
        conditions += " AND p.donor_organization = %(organization)s"
        values["organization"] = filters["organization"]

    status_filter = filters.get("status") if filters else None
    if status_filter and status_filter != "All":
        conditions += " AND pse.status = %(status)s"
        values["status"] = status_filter

    data = frappe.db.sql(f"""
        SELECT
            p.name as pledge,
            p.donor,
            ct.full_name as donor_name,
            p.donor_organization as organization,
            p.campaign,
            pse.due_date,
            pse.expected_amount,
            pse.actual_amount,
            pse.status,
            pse.donation,
            CASE
                WHEN pse.status IN ('Pending', 'Overdue', 'Partially Paid')
                     AND pse.due_date < CURDATE()
                THEN DATEDIFF(CURDATE(), pse.due_date)
                ELSE 0
            END as days_overdue
        FROM `tabPayment Schedule Entry` pse
        JOIN `tabPledge` p ON pse.parent = p.name
        LEFT JOIN `tabContact` ct ON p.donor = ct.name
        WHERE {conditions}
        ORDER BY pse.due_date ASC, pse.expected_amount DESC
    """, values, as_dict=True)

    return data


def get_chart(data):
    if not data:
        return None

    # Count entries by status
    status_counts = {}
    for row in data:
        status = row.get("status", "Unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    if not status_counts:
        return None

    return {
        "data": {
            "labels": list(status_counts.keys()),
            "datasets": [
                {"name": "Entries", "values": list(status_counts.values())},
            ],
        },
        "type": "pie",
        "colors": [
            "#5B8FF9", "#5AD8A6", "#F6BD16", "#E86452",
            "#6DC8EC", "#945FB9",
        ],
    }


def get_summary(data):
    total_expected = sum(flt(row.expected_amount) for row in data)
    total_collected = sum(flt(row.actual_amount) for row in data)

    overdue_rows = [row for row in data if flt(row.days_overdue) > 0]
    total_overdue = sum(flt(row.expected_amount) - flt(row.actual_amount) for row in overdue_rows)
    overdue_count = len(overdue_rows)

    return [
        {"value": total_expected, "label": "Total Expected", "datatype": "Currency", "indicator": "blue"},
        {"value": total_collected, "label": "Total Collected", "datatype": "Currency", "indicator": "green"},
        {
            "value": total_overdue,
            "label": "Total Overdue",
            "datatype": "Currency",
            "indicator": "red" if total_overdue > 0 else "green",
        },
        {
            "value": overdue_count,
            "label": "Overdue Count",
            "datatype": "Int",
            "indicator": "red" if overdue_count > 0 else "green",
        },
    ]
