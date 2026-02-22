import frappe
from frappe.utils import flt, cint


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data, filters)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {"fieldname": "donor", "label": "Donor", "fieldtype": "Link", "options": "Contact", "width": 180},
        {"fieldname": "donor_name", "label": "Donor Name", "fieldtype": "Data", "width": 180},
        {"fieldname": "organization", "label": "Organization", "fieldtype": "Link", "options": "Organization", "width": 180},
        {"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 120},
        {"fieldname": "current_year_giving", "label": "Current Year Giving", "fieldtype": "Currency", "width": 150},
        {"fieldname": "previous_year_giving", "label": "Previous Year Giving", "fieldtype": "Currency", "width": 150},
        {"fieldname": "change_amount", "label": "Change Amount", "fieldtype": "Currency", "width": 130},
        {"fieldname": "change_pct", "label": "Change %", "fieldtype": "Percent", "width": 100},
        {"fieldname": "lifetime_giving", "label": "Lifetime Giving", "fieldtype": "Currency", "width": 140},
        {"fieldname": "donor_level", "label": "Donor Level", "fieldtype": "Data", "width": 200},
    ]


def get_data(filters):
    current_year = cint(filters.get("current_year")) if filters else 0
    if not current_year:
        current_year = 2025
    previous_year = current_year - 1

    campaign_condition = ""
    campaign_value = {}
    if filters and filters.get("campaign"):
        campaign_condition = " AND d.campaign = %(campaign)s"
        campaign_value["campaign"] = filters["campaign"]

    # Donors who gave in current year (submitted donations)
    current_year_donors = frappe.db.sql("""
        SELECT
            d.donor,
            SUM(d.amount) as total_given
        FROM `tabDonation` d
        WHERE d.docstatus = 1
            AND YEAR(d.donation_date) = %(current_year)s
            {campaign_condition}
        GROUP BY d.donor
    """.format(campaign_condition=campaign_condition),
        dict(current_year=current_year, **campaign_value),
        as_dict=True
    )
    current_map = {row.donor: flt(row.total_given) for row in current_year_donors}

    # Donors who gave in previous year (submitted donations)
    previous_year_donors = frappe.db.sql("""
        SELECT
            d.donor,
            SUM(d.amount) as total_given
        FROM `tabDonation` d
        WHERE d.docstatus = 1
            AND YEAR(d.donation_date) = %(previous_year)s
            {campaign_condition}
        GROUP BY d.donor
    """.format(campaign_condition=campaign_condition),
        dict(previous_year=previous_year, **campaign_value),
        as_dict=True
    )
    previous_map = {row.donor: flt(row.total_given) for row in previous_year_donors}

    # Donors who gave before previous year (to distinguish New vs Reactivated)
    # These are donors with any submitted donation before Jan 1 of previous_year
    historical_donors = frappe.db.sql("""
        SELECT DISTINCT d.donor
        FROM `tabDonation` d
        WHERE d.docstatus = 1
            AND YEAR(d.donation_date) < %(previous_year)s
            {campaign_condition}
    """.format(campaign_condition=campaign_condition),
        dict(previous_year=previous_year, **campaign_value),
        as_dict=True
    )
    historical_set = {row.donor for row in historical_donors}

    # Union of all donors from current and previous year
    all_donors = set(current_map.keys()) | set(previous_map.keys())

    if not all_donors:
        return []

    # Fetch contact details for all relevant donors
    donor_list = list(all_donors)
    contact_details = frappe.db.sql("""
        SELECT
            ct.name,
            ct.full_name,
            ct.organization,
            ct.lifetime_giving,
            ct.donor_level
        FROM `tabContact` ct
        WHERE ct.name IN %(donors)s
    """, {"donors": donor_list}, as_dict=True)
    contact_map = {c.name: c for c in contact_details}

    data = []
    for donor in sorted(all_donors):
        in_current = donor in current_map
        in_previous = donor in previous_map
        in_historical = donor in historical_set

        # Categorize the donor
        if in_current and in_previous:
            status = "Retained"
        elif in_current and not in_previous and not in_historical:
            status = "New"
        elif in_current and not in_previous and in_historical:
            status = "Reactivated"
        elif not in_current and in_previous:
            status = "Lapsed"
        else:
            # Should not happen given our union, but guard just in case
            continue

        current_giving = flt(current_map.get(donor, 0))
        previous_giving = flt(previous_map.get(donor, 0))
        change_amount = flt(current_giving) - flt(previous_giving)

        if flt(previous_giving):
            change_pct = flt(change_amount) / flt(previous_giving) * 100
        elif flt(current_giving):
            # New or reactivated donor with no previous year giving
            change_pct = 100.0
        else:
            change_pct = 0.0

        contact = contact_map.get(donor, {})

        data.append({
            "donor": donor,
            "donor_name": contact.get("full_name", ""),
            "organization": contact.get("organization", ""),
            "status": status,
            "current_year_giving": current_giving,
            "previous_year_giving": previous_giving,
            "change_amount": change_amount,
            "change_pct": change_pct,
            "lifetime_giving": flt(contact.get("lifetime_giving", 0)),
            "donor_level": contact.get("donor_level", ""),
        })

    # Sort: Retained first, then New, Reactivated, Lapsed; within each group by current year giving desc
    status_order = {"Retained": 0, "New": 1, "Reactivated": 2, "Lapsed": 3}
    data.sort(key=lambda r: (status_order.get(r["status"], 99), -flt(r["current_year_giving"])))

    return data


def get_chart(data):
    if not data:
        return None

    status_counts = {}
    for row in data:
        s = row.get("status", "Unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

    # Fixed order for consistent chart display
    labels = ["Retained", "New", "Reactivated", "Lapsed"]
    values = [status_counts.get(label, 0) for label in labels]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Donors", "values": values}
            ],
        },
        "type": "pie",
        "colors": ["#5AD8A6", "#5B8FF9", "#F6BD16", "#E86452"],
    }


def get_summary(data, filters=None):
    if not data:
        return []

    current_year_donors = [r for r in data if r["status"] != "Lapsed"]
    retained = [r for r in data if r["status"] == "Retained"]
    lapsed = [r for r in data if r["status"] == "Lapsed"]
    previous_year_donors = [r for r in data if r["status"] in ("Retained", "Lapsed")]

    total_current = len(current_year_donors)
    total_previous = len(previous_year_donors)
    total_retained = len(retained)
    total_lapsed = len(lapsed)

    # Retention rate: percentage of previous year donors who gave again this year
    retention_rate = (
        flt(total_retained) / flt(total_previous) * 100
        if total_previous else 0.0
    )

    # Average gift change for retained donors
    if retained:
        avg_change = flt(
            sum(flt(r["change_amount"]) for r in retained)
        ) / len(retained)
    else:
        avg_change = 0.0

    return [
        {
            "value": total_current,
            "label": "Current Year Donors",
            "datatype": "Int",
            "indicator": "blue",
        },
        {
            "value": retention_rate,
            "label": "Retention Rate",
            "datatype": "Percent",
            "indicator": "green" if retention_rate >= 60 else "orange",
        },
        {
            "value": total_lapsed,
            "label": "Lapsed Donors",
            "datatype": "Int",
            "indicator": "red" if total_lapsed > 0 else "green",
        },
        {
            "value": avg_change,
            "label": "Avg Gift Change (Retained)",
            "datatype": "Currency",
            "indicator": "green" if avg_change >= 0 else "red",
        },
    ]
