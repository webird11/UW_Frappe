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
        {"fieldname": "agency", "label": "Agency", "fieldtype": "Link", "options": "Organization", "width": 200},
        {"fieldname": "agency_code", "label": "Agency Code", "fieldtype": "Data", "width": 90},
        {"fieldname": "donor", "label": "Donor", "fieldtype": "Link", "options": "Contact", "width": 180},
        {"fieldname": "donor_organization", "label": "Donor Organization", "fieldtype": "Link", "options": "Organization", "width": 160},
        {"fieldname": "campaign", "label": "Campaign", "fieldtype": "Link", "options": "Campaign", "width": 170},
        {"fieldname": "designation_type", "label": "Designation Type", "fieldtype": "Data", "width": 140},
        {"fieldname": "allocation_pct", "label": "Allocation %", "fieldtype": "Percent", "width": 100},
        {"fieldname": "allocated_amount", "label": "Allocated Amount", "fieldtype": "Currency", "width": 130},
        {"fieldname": "collected_against_pledge", "label": "Collected Against Pledge", "fieldtype": "Currency", "width": 150},
        {"fieldname": "pledge_status", "label": "Pledge Status", "fieldtype": "Data", "width": 120},
    ]


def get_data(filters):
    conditions = "p.docstatus = 1"
    values = {}

    if filters and filters.get("agency"):
        conditions += " AND pa.agency = %(agency)s"
        values["agency"] = filters["agency"]

    if filters and filters.get("campaign"):
        conditions += " AND p.campaign = %(campaign)s"
        values["campaign"] = filters["campaign"]

    if filters and filters.get("campaign_year"):
        conditions += " AND c.campaign_year = %(campaign_year)s"
        values["campaign_year"] = filters["campaign_year"]

    if filters and filters.get("designation_type"):
        conditions += " AND pa.designation_type = %(designation_type)s"
        values["designation_type"] = filters["designation_type"]

    data = frappe.db.sql(f"""
        SELECT
            pa.agency,
            o.agency_code,
            p.donor,
            ct.full_name as donor_name,
            p.donor_organization,
            p.campaign,
            pa.designation_type,
            pa.percentage as allocation_pct,
            pa.allocated_amount,
            p.collection_percentage,
            p.collection_status as pledge_status
        FROM `tabPledge Allocation` pa
        JOIN `tabPledge` p ON pa.parent = p.name
        JOIN `tabOrganization` o ON pa.agency = o.name
        JOIN `tabCampaign` c ON p.campaign = c.name
        LEFT JOIN `tabContact` ct ON p.donor = ct.name
        WHERE {conditions}
        ORDER BY o.organization_name, pa.allocated_amount DESC
    """, values, as_dict=True)

    # Calculate proportional collected amount per allocation
    for row in data:
        row.collected_against_pledge = flt(
            flt(row.allocated_amount) * flt(row.collection_percentage) / 100
        )

    return data


def get_chart(data):
    if not data:
        return None

    # Aggregate allocation by agency for pie chart
    agency_totals = {}
    for row in data:
        agency = row.get("agency_code") or row.get("agency", "")[:15]
        agency_totals[agency] = flt(agency_totals.get(agency, 0)) + flt(row.allocated_amount)

    sorted_agencies = sorted(agency_totals.items(), key=lambda x: x[1], reverse=True)

    return {
        "data": {
            "labels": [a[0] for a in sorted_agencies],
            "datasets": [
                {"name": "Allocated", "values": [a[1] for a in sorted_agencies]},
            ],
        },
        "type": "pie",
        "colors": [
            "#5B8FF9", "#5AD8A6", "#F6BD16", "#E86452",
            "#6DC8EC", "#945FB9", "#FF9845", "#1E9493",
            "#FF99C3", "#269A99", "#BDD2FD", "#BEDED1",
        ],
    }


def get_summary(data):
    total_agencies = len(set(row.agency for row in data))
    total_allocated = sum(flt(row.allocated_amount) for row in data)
    total_collected = sum(flt(row.collected_against_pledge) for row in data)
    num_designations = len(data)

    return [
        {"value": total_agencies, "label": "Total Agencies", "datatype": "Int", "indicator": "blue"},
        {"value": total_allocated, "label": "Total Allocated", "datatype": "Currency", "indicator": "blue"},
        {"value": total_collected, "label": "Total Collected", "datatype": "Currency", "indicator": "green"},
        {"value": num_designations, "label": "Designations", "datatype": "Int", "indicator": "blue"},
    ]
