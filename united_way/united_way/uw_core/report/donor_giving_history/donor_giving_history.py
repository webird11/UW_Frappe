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
        {"fieldname": "donor", "label": "Donor", "fieldtype": "Link", "options": "Contact", "width": 200},
        {"fieldname": "organization", "label": "Organization", "fieldtype": "Link", "options": "Organization", "width": 180},
        {"fieldname": "campaign", "label": "Campaign", "fieldtype": "Link", "options": "Campaign", "width": 180},
        {"fieldname": "pledge_amount", "label": "Pledge Amount", "fieldtype": "Currency", "width": 130},
        {"fieldname": "total_donated", "label": "Total Donated", "fieldtype": "Currency", "width": 130},
        {"fieldname": "outstanding", "label": "Outstanding", "fieldtype": "Currency", "width": 120},
        {"fieldname": "collection_pct", "label": "Collection %", "fieldtype": "Percent", "width": 100},
        {"fieldname": "pledge_count", "label": "Pledge Count", "fieldtype": "Int", "width": 100},
        {"fieldname": "donor_since", "label": "Donor Since", "fieldtype": "Date", "width": 110},
        {"fieldname": "lifetime_giving", "label": "Lifetime Giving", "fieldtype": "Currency", "width": 130},
    ]


def get_data(filters):
    conditions = "p.docstatus = 1"
    values = {}

    if filters and filters.get("campaign"):
        conditions += " AND p.campaign = %(campaign)s"
        values["campaign"] = filters["campaign"]

    if filters and filters.get("from_date"):
        conditions += " AND p.pledge_date >= %(from_date)s"
        values["from_date"] = filters["from_date"]

    if filters and filters.get("to_date"):
        conditions += " AND p.pledge_date <= %(to_date)s"
        values["to_date"] = filters["to_date"]

    if filters and filters.get("organization"):
        conditions += " AND ct.organization = %(organization)s"
        values["organization"] = filters["organization"]

    if filters and filters.get("donor_level"):
        conditions += " AND ct.donor_level = %(donor_level)s"
        values["donor_level"] = filters["donor_level"]

    data = frappe.db.sql(f"""
        SELECT
            p.donor,
            ct.full_name as donor_name,
            ct.organization,
            p.campaign,
            SUM(p.pledge_amount) as pledge_amount,
            COUNT(DISTINCT p.name) as pledge_count,
            ct.donor_since,
            ct.lifetime_giving
        FROM `tabPledge` p
        JOIN `tabContact` ct ON p.donor = ct.name
        WHERE {conditions}
        GROUP BY p.donor, ct.full_name, ct.organization, p.campaign,
                 ct.donor_since, ct.lifetime_giving
        ORDER BY ct.lifetime_giving DESC, pledge_amount DESC
    """, values, as_dict=True)

    # Calculate donation totals per donor+campaign
    for row in data:
        donated = frappe.db.sql("""
            SELECT COALESCE(SUM(d.amount), 0) as total
            FROM `tabDonation` d
            WHERE d.donor = %s AND d.campaign = %s AND d.docstatus = 1
        """, (row.donor, row.campaign), as_dict=True)[0].total

        row.total_donated = flt(donated)
        row.outstanding = flt(row.pledge_amount) - flt(row.total_donated)
        row.collection_pct = (
            flt(row.total_donated) / flt(row.pledge_amount) * 100
            if flt(row.pledge_amount) else 0
        )

    return data


def get_chart(data):
    if not data:
        return None

    # Top 10 donors by lifetime giving (deduplicate donors across campaigns)
    seen = {}
    for row in data:
        if row.donor not in seen:
            seen[row.donor] = {
                "label": row.get("donor_name") or row.donor,
                "lifetime": flt(row.lifetime_giving),
            }

    top_donors = sorted(seen.values(), key=lambda x: x["lifetime"], reverse=True)[:10]

    if not top_donors:
        return None

    return {
        "data": {
            "labels": [d["label"] for d in top_donors],
            "datasets": [
                {"name": "Lifetime Giving", "values": [d["lifetime"] for d in top_donors]},
            ],
        },
        "type": "bar",
        "colors": ["#5B8FF9"],
        "barOptions": {"stacked": False},
    }


def get_summary(data):
    unique_donors = len(set(row.donor for row in data))
    total_pledged = sum(flt(row.pledge_amount) for row in data)
    total_collected = sum(flt(row.total_donated) for row in data)
    avg_gift = total_collected / unique_donors if unique_donors else 0

    return [
        {"value": unique_donors, "label": "Total Donors", "datatype": "Int", "indicator": "blue"},
        {"value": total_pledged, "label": "Total Pledged", "datatype": "Currency", "indicator": "blue"},
        {"value": total_collected, "label": "Total Collected", "datatype": "Currency", "indicator": "green"},
        {"value": avg_gift, "label": "Average Gift Size", "datatype": "Currency", "indicator": "green"},
    ]
