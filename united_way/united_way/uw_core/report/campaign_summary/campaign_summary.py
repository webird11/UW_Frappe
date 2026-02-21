import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {"fieldname": "agency", "label": "Agency", "fieldtype": "Link", "options": "Organization", "width": 250},
        {"fieldname": "agency_code", "label": "Code", "fieldtype": "Data", "width": 80},
        {"fieldname": "donor_count", "label": "Donors", "fieldtype": "Int", "width": 80},
        {"fieldname": "pledge_count", "label": "Pledges", "fieldtype": "Int", "width": 80},
        {"fieldname": "total_pledged", "label": "Total Pledged", "fieldtype": "Currency", "width": 140},
        {"fieldname": "total_collected", "label": "Total Collected", "fieldtype": "Currency", "width": 140},
        {"fieldname": "outstanding", "label": "Outstanding", "fieldtype": "Currency", "width": 140},
        {"fieldname": "collection_rate", "label": "Collection %", "fieldtype": "Percent", "width": 100},
    ]


def get_data(filters):
    conditions = "p.docstatus = 1"
    values = {}

    if filters and filters.get("campaign"):
        conditions += " AND p.campaign = %(campaign)s"
        values["campaign"] = filters["campaign"]

    if filters and filters.get("campaign_year"):
        conditions += " AND c.campaign_year = %(campaign_year)s"
        values["campaign_year"] = filters["campaign_year"]

    data = frappe.db.sql(f"""
        SELECT
            pa.agency,
            o.agency_code,
            o.organization_name,
            COUNT(DISTINCT p.donor) as donor_count,
            COUNT(DISTINCT p.name) as pledge_count,
            SUM(pa.allocated_amount) as total_pledged
        FROM `tabPledge Allocation` pa
        JOIN `tabPledge` p ON pa.parent = p.name
        JOIN `tabOrganization` o ON pa.agency = o.name
        JOIN `tabCampaign` c ON p.campaign = c.name
        WHERE {conditions}
        GROUP BY pa.agency, o.agency_code, o.organization_name
        ORDER BY total_pledged DESC
    """, values, as_dict=True)

    # Add collection data
    for row in data:
        collected = frappe.db.sql("""
            SELECT COALESCE(SUM(d.amount), 0) as total
            FROM `tabDonation` d
            JOIN `tabPledge` p ON d.pledge = p.name
            JOIN `tabPledge Allocation` pa ON pa.parent = p.name
            WHERE pa.agency = %s AND d.docstatus = 1 AND p.docstatus = 1
        """, row.agency, as_dict=True)[0].get("total", 0)

        # Approximate collection proportional to pledge allocation
        if row.total_pledged:
            row.total_collected = collected * (row.total_pledged / (row.total_pledged or 1))
        else:
            row.total_collected = 0

        row.outstanding = (row.total_pledged or 0) - (row.total_collected or 0)
        row.collection_rate = ((row.total_collected or 0) / row.total_pledged * 100) if row.total_pledged else 0

    return data


def get_chart(data):
    if not data:
        return None

    labels = [d.get("agency_code") or d.get("agency", "")[:10] for d in data[:10]]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Pledged", "values": [d.get("total_pledged", 0) for d in data[:10]]},
                {"name": "Collected", "values": [d.get("total_collected", 0) for d in data[:10]]},
            ],
        },
        "type": "bar",
        "colors": ["#5B8FF9", "#5AD8A6"],
    }


def get_summary(data):
    total_pledged = sum(d.get("total_pledged", 0) for d in data)
    total_collected = sum(d.get("total_collected", 0) for d in data)
    total_donors = sum(d.get("donor_count", 0) for d in data)

    return [
        {"value": total_pledged, "label": "Total Pledged", "datatype": "Currency", "indicator": "blue"},
        {"value": total_collected, "label": "Total Collected", "datatype": "Currency", "indicator": "green"},
        {"value": total_pledged - total_collected, "label": "Outstanding", "datatype": "Currency", "indicator": "orange"},
        {"value": total_donors, "label": "Unique Donors", "datatype": "Int", "indicator": "blue"},
        {
            "value": (total_collected / total_pledged * 100) if total_pledged else 0,
            "label": "Collection Rate",
            "datatype": "Percent",
            "indicator": "green" if total_pledged and (total_collected / total_pledged) > 0.7 else "orange",
        },
    ]
