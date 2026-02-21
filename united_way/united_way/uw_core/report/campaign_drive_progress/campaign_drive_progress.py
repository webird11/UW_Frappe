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
        {"fieldname": "name", "label": "Drive ID", "fieldtype": "Link", "options": "Campaign Drive", "width": 150},
        {"fieldname": "organization", "label": "Organization", "fieldtype": "Link", "options": "Organization", "width": 200},
        {"fieldname": "campaign", "label": "Campaign", "fieldtype": "Link", "options": "Campaign", "width": 180},
        {"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 110},
        {"fieldname": "coordinator_name", "label": "Coordinator", "fieldtype": "Data", "width": 150},
        {"fieldname": "goal_amount", "label": "Goal", "fieldtype": "Currency", "width": 120},
        {"fieldname": "total_pledged", "label": "Total Pledged", "fieldtype": "Currency", "width": 130},
        {"fieldname": "percent_of_goal", "label": "% of Goal", "fieldtype": "Percent", "width": 100},
        {"fieldname": "pledge_count", "label": "Pledge Count", "fieldtype": "Int", "width": 100},
        {"fieldname": "employee_count", "label": "Employee Count", "fieldtype": "Int", "width": 110},
        {"fieldname": "participation_rate", "label": "Participation Rate", "fieldtype": "Percent", "width": 120},
        {"fieldname": "drive_start_date", "label": "Drive Start", "fieldtype": "Date", "width": 110},
        {"fieldname": "drive_end_date", "label": "Drive End", "fieldtype": "Date", "width": 110},
    ]


def get_data(filters):
    conditions = "1=1"
    values = {}

    if filters and filters.get("campaign"):
        conditions += " AND cd.campaign = %(campaign)s"
        values["campaign"] = filters["campaign"]

    if filters and filters.get("status"):
        conditions += " AND cd.status = %(status)s"
        values["status"] = filters["status"]

    if filters and filters.get("organization"):
        conditions += " AND cd.organization = %(organization)s"
        values["organization"] = filters["organization"]

    data = frappe.db.sql(f"""
        SELECT
            cd.name,
            cd.organization,
            cd.organization_name,
            cd.campaign,
            cd.status,
            cd.coordinator_name,
            cd.goal_amount,
            cd.total_pledged,
            cd.percent_of_goal,
            cd.pledge_count,
            cd.employee_count,
            cd.participation_rate,
            cd.drive_start_date,
            cd.drive_end_date
        FROM `tabCampaign Drive` cd
        WHERE {conditions}
        ORDER BY cd.total_pledged DESC, cd.goal_amount DESC
    """, values, as_dict=True)

    return data


def get_chart(data):
    if not data:
        return None

    # Top 10 drives by total pledged
    top_drives = sorted(data, key=lambda x: flt(x.total_pledged), reverse=True)[:10]

    if not top_drives:
        return None

    labels = [
        d.get("organization_name") or d.get("organization", "")[:20]
        for d in top_drives
    ]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Goal", "values": [flt(d.goal_amount) for d in top_drives]},
                {"name": "Pledged", "values": [flt(d.total_pledged) for d in top_drives]},
            ],
        },
        "type": "bar",
        "colors": ["#E8E8E8", "#5B8FF9"],
    }


def get_summary(data):
    total_drives = len(data)
    total_goal = sum(flt(row.goal_amount) for row in data)
    total_pledged = sum(flt(row.total_pledged) for row in data)

    # Average participation rate across drives that have employee counts
    drives_with_employees = [row for row in data if flt(row.employee_count) > 0]
    if drives_with_employees:
        avg_participation = sum(
            flt(row.participation_rate) for row in drives_with_employees
        ) / len(drives_with_employees)
    else:
        avg_participation = 0

    return [
        {"value": total_drives, "label": "Total Drives", "datatype": "Int", "indicator": "blue"},
        {"value": total_goal, "label": "Total Goal", "datatype": "Currency", "indicator": "blue"},
        {"value": total_pledged, "label": "Total Pledged", "datatype": "Currency", "indicator": "green"},
        {
            "value": avg_participation,
            "label": "Avg Participation %",
            "datatype": "Percent",
            "indicator": "green" if avg_participation >= 50 else "orange",
        },
    ]
