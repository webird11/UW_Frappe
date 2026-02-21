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
        {"fieldname": "name", "label": "Distribution Run", "fieldtype": "Link", "options": "Distribution Run", "width": 160},
        {"fieldname": "campaign", "label": "Campaign", "fieldtype": "Link", "options": "Campaign", "width": 180},
        {"fieldname": "distribution_date", "label": "Date", "fieldtype": "Date", "width": 110},
        {"fieldname": "period", "label": "Period", "fieldtype": "Data", "width": 170},
        {"fieldname": "distribution_type", "label": "Type", "fieldtype": "Data", "width": 100},
        {"fieldname": "agency", "label": "Agency", "fieldtype": "Link", "options": "Organization", "width": 200},
        {"fieldname": "agency_code", "label": "Agency Code", "fieldtype": "Data", "width": 90},
        {"fieldname": "total_allocated", "label": "Allocated", "fieldtype": "Currency", "width": 130},
        {"fieldname": "total_collected", "label": "Collected", "fieldtype": "Currency", "width": 130},
        {"fieldname": "previously_distributed", "label": "Previously Distributed", "fieldtype": "Currency", "width": 150},
        {"fieldname": "distribution_amount", "label": "This Distribution", "fieldtype": "Currency", "width": 140},
    ]


def get_data(filters):
    conditions = "dr.docstatus = 1"
    values = {}

    if filters and filters.get("campaign"):
        conditions += " AND dr.campaign = %(campaign)s"
        values["campaign"] = filters["campaign"]

    if filters and filters.get("from_date"):
        conditions += " AND dr.distribution_date >= %(from_date)s"
        values["from_date"] = filters["from_date"]

    if filters and filters.get("to_date"):
        conditions += " AND dr.distribution_date <= %(to_date)s"
        values["to_date"] = filters["to_date"]

    if filters and filters.get("agency"):
        conditions += " AND di.agency = %(agency)s"
        values["agency"] = filters["agency"]

    data = frappe.db.sql(f"""
        SELECT
            dr.name,
            dr.campaign,
            dr.campaign_name,
            dr.distribution_date,
            dr.period_start,
            dr.period_end,
            dr.distribution_type,
            di.agency,
            di.agency_code,
            di.total_allocated,
            di.total_collected,
            di.previously_distributed,
            di.distribution_amount
        FROM `tabDistribution Run` dr
        JOIN `tabDistribution Item` di ON di.parent = dr.name
        WHERE {conditions}
        ORDER BY dr.distribution_date DESC, di.distribution_amount DESC
    """, values, as_dict=True)

    # Build human-readable period string
    for row in data:
        if row.period_start and row.period_end:
            row.period = f"{row.period_start} to {row.period_end}"
        else:
            row.period = ""

    return data


def get_chart(data):
    if not data:
        return None

    # Aggregate distributions by agency
    agency_totals = {}
    for row in data:
        agency = row.get("agency_code") or row.get("agency", "")[:15]
        agency_totals[agency] = flt(agency_totals.get(agency, 0)) + flt(row.distribution_amount)

    sorted_agencies = sorted(agency_totals.items(), key=lambda x: x[1], reverse=True)[:10]

    if not sorted_agencies:
        return None

    return {
        "data": {
            "labels": [a[0] for a in sorted_agencies],
            "datasets": [
                {"name": "Distributed", "values": [a[1] for a in sorted_agencies]},
            ],
        },
        "type": "bar",
        "colors": ["#5AD8A6"],
    }


def get_summary(data):
    # Count unique distribution runs
    unique_runs = len(set(row.name for row in data))
    total_distributed = sum(flt(row.distribution_amount) for row in data)
    unique_agencies = len(set(row.agency for row in data))
    avg_per_agency = total_distributed / unique_agencies if unique_agencies else 0

    return [
        {"value": unique_runs, "label": "Total Runs", "datatype": "Int", "indicator": "blue"},
        {"value": total_distributed, "label": "Total Distributed", "datatype": "Currency", "indicator": "green"},
        {"value": unique_agencies, "label": "Total Agencies", "datatype": "Int", "indicator": "blue"},
        {"value": avg_per_agency, "label": "Avg per Agency", "datatype": "Currency", "indicator": "green"},
    ]
