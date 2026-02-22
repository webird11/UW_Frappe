import frappe
from frappe.utils import flt


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data, filters)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {"fieldname": "category", "label": "Category", "fieldtype": "Data", "width": 200},
        {"fieldname": "metric", "label": "Metric", "fieldtype": "Data", "width": 220},
        {"fieldname": "value", "label": "Value", "fieldtype": "Currency", "width": 160},
        {"fieldname": "goal", "label": "Goal", "fieldtype": "Currency", "width": 140},
        {"fieldname": "percent_of_goal", "label": "% of Goal", "fieldtype": "Percent", "width": 110},
        {"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 120},
    ]


def get_data(filters):
    if not filters or not filters.get("campaign"):
        return []

    campaign = filters["campaign"]
    data = []

    # ---------------------------------------------------------------
    # Section 1 - Campaign Overview
    # ---------------------------------------------------------------
    campaign_doc = frappe.db.get_value(
        "Campaign",
        campaign,
        ["campaign_name", "fundraising_goal", "total_pledged", "total_collected",
         "donor_count", "pledge_count", "collection_rate", "campaign_year"],
        as_dict=True,
    )

    if not campaign_doc:
        return []

    goal = flt(campaign_doc.fundraising_goal)
    total_pledged = flt(campaign_doc.total_pledged)
    total_collected = flt(campaign_doc.total_collected)
    donor_count = campaign_doc.donor_count or 0
    collection_rate = flt(campaign_doc.collection_rate)

    # Total Pledged vs Goal
    pledge_pct = flt(total_pledged / goal * 100, 1) if goal else 0
    data.append({
        "category": "Campaign Overview",
        "metric": "Total Pledged vs Goal",
        "value": total_pledged,
        "goal": goal,
        "percent_of_goal": pledge_pct,
        "status": _goal_status(pledge_pct),
    })

    # Total Collected vs Pledged
    collected_pct = flt(total_collected / total_pledged * 100, 1) if total_pledged else 0
    data.append({
        "category": "Campaign Overview",
        "metric": "Total Collected vs Pledged",
        "value": total_collected,
        "goal": total_pledged,
        "percent_of_goal": collected_pct,
        "status": _collection_status(collected_pct),
    })

    # Collection Rate
    data.append({
        "category": "Campaign Overview",
        "metric": "Collection Rate",
        "value": collection_rate,
        "goal": None,
        "percent_of_goal": collection_rate,
        "status": _collection_status(collection_rate),
    })

    # Donor Count
    data.append({
        "category": "Campaign Overview",
        "metric": "Donor Count",
        "value": donor_count,
        "goal": None,
        "percent_of_goal": None,
        "status": "",
    })

    # Average Gift Size
    avg_gift = flt(total_pledged / donor_count, 2) if donor_count else 0
    data.append({
        "category": "Campaign Overview",
        "metric": "Average Gift Size",
        "value": avg_gift,
        "goal": None,
        "percent_of_goal": None,
        "status": "",
    })

    # New Donors - donors who pledged this campaign but did NOT pledge in
    # campaigns from the prior year
    campaign_year = campaign_doc.campaign_year or 0
    prior_year = campaign_year - 1 if campaign_year else 0

    new_donor_count = _get_new_donor_count(campaign, prior_year)
    data.append({
        "category": "Campaign Overview",
        "metric": "New Donors (vs Prior Year)",
        "value": new_donor_count,
        "goal": None,
        "percent_of_goal": None,
        "status": "",
    })

    # ---------------------------------------------------------------
    # Section 2 - Top 10 Donors
    # ---------------------------------------------------------------
    top_donors = _get_top_donors(campaign, limit=10)
    for rank, donor in enumerate(top_donors, 1):
        collected_for_donor = flt(donor.total_collected)
        pct = flt(collected_for_donor / flt(donor.pledge_amount) * 100, 1) if flt(donor.pledge_amount) else 0
        data.append({
            "category": "Top 10 Donors",
            "metric": "{rank}. {name}{org}".format(
                rank=rank,
                name=donor.donor_name or donor.donor,
                org=" ({})".format(donor.org_name) if donor.org_name else "",
            ),
            "value": flt(donor.pledge_amount),
            "goal": collected_for_donor,
            "percent_of_goal": pct,
            "status": "",
        })

    # ---------------------------------------------------------------
    # Section 3 - Agency Allocation Summary
    # ---------------------------------------------------------------
    agency_rows = _get_agency_allocations(campaign)
    total_allocated = sum(flt(r.allocated_amount) for r in agency_rows)

    for row in agency_rows:
        alloc = flt(row.allocated_amount)
        pct_of_total = flt(alloc / total_allocated * 100, 1) if total_allocated else 0
        data.append({
            "category": "Agency Allocations",
            "metric": row.agency_name or row.agency,
            "value": alloc,
            "goal": flt(row.collected_proportional),
            "percent_of_goal": pct_of_total,
            "status": "",
        })

    # ---------------------------------------------------------------
    # Section 4 - Campaign Drives Summary
    # ---------------------------------------------------------------
    drives = _get_campaign_drives(campaign)
    for drive in drives:
        drive_goal = flt(drive.goal_amount)
        drive_pledged = flt(drive.total_pledged)
        drive_pct = flt(drive_pledged / drive_goal * 100, 1) if drive_goal else 0
        participation = flt(drive.participation_rate, 1)

        status_label = ""
        if participation:
            status_label = "{pct}% participation".format(pct=participation)

        data.append({
            "category": "Campaign Drives",
            "metric": drive.organization_name or drive.organization,
            "value": drive_pledged,
            "goal": drive_goal,
            "percent_of_goal": drive_pct,
            "status": status_label,
        })

    return data


def get_chart(data):
    """Horizontal bar chart: top 10 agencies by allocation amount."""
    agency_rows = [r for r in data if r.get("category") == "Agency Allocations"]
    if not agency_rows:
        return None

    # Already sorted by allocated_amount DESC from the query; take top 10
    top = agency_rows[:10]

    labels = [r["metric"] for r in top]
    values = [flt(r["value"]) for r in top]

    return {
        "data": {
            "labels": labels,
            "datasets": [{"name": "Allocated Amount", "values": values}],
        },
        "type": "bar",
        "colors": ["#5B8FF9"],
        "barOptions": {"stacked": False},
    }


def get_summary(data, filters):
    """KPI summary cards for the top of the report."""
    if not filters or not filters.get("campaign"):
        return []

    campaign = filters["campaign"]
    campaign_doc = frappe.db.get_value(
        "Campaign",
        campaign,
        ["fundraising_goal", "total_pledged", "total_collected", "collection_rate"],
        as_dict=True,
    )

    if not campaign_doc:
        return []

    goal = flt(campaign_doc.fundraising_goal)
    total_pledged = flt(campaign_doc.total_pledged)
    total_collected = flt(campaign_doc.total_collected)
    collection_rate = flt(campaign_doc.collection_rate)

    pledge_pct = flt(total_pledged / goal * 100) if goal else 0

    return [
        {
            "value": goal,
            "label": "Campaign Goal",
            "datatype": "Currency",
            "indicator": "blue",
        },
        {
            "value": total_pledged,
            "label": "Total Pledged",
            "datatype": "Currency",
            "indicator": "green" if pledge_pct >= 80 else "orange",
        },
        {
            "value": total_collected,
            "label": "Total Collected",
            "datatype": "Currency",
            "indicator": "green" if collection_rate >= 70 else "orange",
        },
        {
            "value": collection_rate,
            "label": "Collection Rate",
            "datatype": "Percent",
            "indicator": "green" if collection_rate >= 70 else "orange",
        },
    ]


# ===================================================================
# Private helpers
# ===================================================================

def _goal_status(percent):
    """Return a status label based on percent-of-goal thresholds."""
    if percent >= 100:
        return "Ahead"
    elif percent >= 75:
        return "On Track"
    else:
        return "Behind"


def _collection_status(percent):
    """Return a status label based on collection-rate thresholds."""
    if percent >= 90:
        return "Ahead"
    elif percent >= 60:
        return "On Track"
    else:
        return "Behind"


def _get_new_donor_count(campaign, prior_year):
    """Count donors who gave in this campaign but not in any prior-year campaign."""
    if not prior_year:
        # No prior year available -- count all donors as new
        result = frappe.db.sql("""
            SELECT COUNT(DISTINCT p.donor) as cnt
            FROM `tabPledge` p
            WHERE p.campaign = %s AND p.docstatus = 1
        """, campaign, as_dict=True)
        return result[0].cnt if result else 0

    result = frappe.db.sql("""
        SELECT COUNT(DISTINCT p.donor) as cnt
        FROM `tabPledge` p
        WHERE p.campaign = %s
          AND p.docstatus = 1
          AND p.donor NOT IN (
              SELECT DISTINCT p2.donor
              FROM `tabPledge` p2
              JOIN `tabCampaign` c2 ON p2.campaign = c2.name
              WHERE c2.campaign_year = %s
                AND p2.docstatus = 1
          )
    """, (campaign, prior_year), as_dict=True)
    return result[0].cnt if result else 0


def _get_top_donors(campaign, limit=10):
    """Return top donors by pledge amount with their collected totals."""
    return frappe.db.sql("""
        SELECT
            p.donor,
            p.donor_name,
            p.donor_organization,
            o.organization_name AS org_name,
            SUM(p.pledge_amount) AS pledge_amount,
            COALESCE(
                (SELECT SUM(d.amount)
                 FROM `tabDonation` d
                 WHERE d.donor = p.donor
                   AND d.campaign = p.campaign
                   AND d.docstatus = 1),
                0
            ) AS total_collected
        FROM `tabPledge` p
        LEFT JOIN `tabOrganization` o ON p.donor_organization = o.name
        WHERE p.campaign = %s AND p.docstatus = 1
        GROUP BY p.donor, p.donor_name, p.donor_organization, o.organization_name
        ORDER BY pledge_amount DESC
        LIMIT %s
    """, (campaign, limit), as_dict=True)


def _get_agency_allocations(campaign):
    """Return agency allocation totals with proportional collected amounts."""
    return frappe.db.sql("""
        SELECT
            pa.agency,
            o.organization_name AS agency_name,
            o.agency_code,
            SUM(pa.allocated_amount) AS allocated_amount,
            COALESCE(
                SUM(pa.allocated_amount) *
                (SELECT COALESCE(SUM(d.amount), 0)
                 FROM `tabDonation` d
                 WHERE d.campaign = %s AND d.docstatus = 1)
                /
                NULLIF(
                    (SELECT COALESCE(SUM(p2.pledge_amount), 0)
                     FROM `tabPledge` p2
                     WHERE p2.campaign = %s AND p2.docstatus = 1),
                    0
                ),
                0
            ) AS collected_proportional
        FROM `tabPledge Allocation` pa
        JOIN `tabPledge` p ON pa.parent = p.name
        LEFT JOIN `tabOrganization` o ON pa.agency = o.name
        WHERE p.campaign = %s AND p.docstatus = 1
        GROUP BY pa.agency, o.organization_name, o.agency_code
        ORDER BY allocated_amount DESC
    """, (campaign, campaign, campaign), as_dict=True)


def _get_campaign_drives(campaign):
    """Return all campaign drives for this campaign."""
    return frappe.db.sql("""
        SELECT
            cd.name,
            cd.organization,
            cd.organization_name,
            cd.goal_amount,
            cd.total_pledged,
            cd.pledge_count,
            cd.employee_count,
            cd.participation_rate,
            cd.percent_of_goal
        FROM `tabCampaign Drive` cd
        WHERE cd.campaign = %s
        ORDER BY cd.total_pledged DESC
    """, campaign, as_dict=True)
