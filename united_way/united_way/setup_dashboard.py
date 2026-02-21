import frappe


def create_dashboard_elements():
    """Create Number Cards and Dashboard Charts for the UW Core workspace.

    Usage:
        bench --site uw.localhost execute united_way.setup_dashboard.create_dashboard_elements
    """
    create_number_cards()
    create_dashboard_charts()
    frappe.db.commit()
    print("Dashboard elements created successfully.")


def create_number_cards():
    """Create Number Card records for the workspace."""
    cards = [
        {
            "name": "Total Pledged",
            "label": "Total Pledged",
            "document_type": "Pledge",
            "function": "Sum",
            "aggregate_function_based_on": "pledge_amount",
            "filters_json": '{"docstatus": 1}',
            "show_percentage_stats": 1,
            "stats_time_interval": "Monthly",
            "color": "#5B8FF9",
        },
        {
            "name": "Total Collected",
            "label": "Total Collected",
            "document_type": "Donation",
            "function": "Sum",
            "aggregate_function_based_on": "amount",
            "filters_json": '{"docstatus": 1}',
            "show_percentage_stats": 1,
            "stats_time_interval": "Monthly",
            "color": "#5AD8A6",
        },
        {
            "name": "Active Campaigns",
            "label": "Active Campaigns",
            "document_type": "Campaign",
            "function": "Count",
            "filters_json": '{"status": "Active", "docstatus": 1}',
            "color": "#F6BD16",
        },
        {
            "name": "Total Donors",
            "label": "Total Donors",
            "document_type": "Contact",
            "function": "Count",
            "filters_json": '{"contact_type": "Individual Donor"}',
            "color": "#6DC8EC",
        },
    ]

    for card_data in cards:
        if frappe.db.exists("Number Card", card_data["name"]):
            print(f"  Number Card '{card_data['name']}' already exists, skipping")
            continue

        doc = frappe.get_doc({
            "doctype": "Number Card",
            "name": card_data["name"],
            "label": card_data["label"],
            "document_type": card_data["document_type"],
            "function": card_data["function"],
            "aggregate_function_based_on": card_data.get("aggregate_function_based_on", ""),
            "filters_json": card_data.get("filters_json", "{}"),
            "show_percentage_stats": card_data.get("show_percentage_stats", 0),
            "stats_time_interval": card_data.get("stats_time_interval", "Daily"),
            "color": card_data.get("color"),
            "is_standard": 0,
        })
        doc.insert(ignore_permissions=True)
        print(f"  Created Number Card: {card_data['name']}")


def create_dashboard_charts():
    """Create Dashboard Chart records for the workspace."""
    charts = [
        {
            "name": "Monthly Donation Trend",
            "chart_name": "Monthly Donation Trend",
            "chart_type": "Sum",
            "document_type": "Donation",
            "based_on": "donation_date",
            "value_based_on": "amount",
            "group_by_type": "Count",
            "time_interval": "Monthly",
            "timespan": "Last Year",
            "timeseries": 1,
            "filters_json": '{"docstatus": 1}',
            "type": "Line",
            "color": "#5AD8A6",
        },
        {
            "name": "Campaign Progress",
            "chart_name": "Campaign Progress",
            "chart_type": "Group By",
            "document_type": "Campaign",
            "group_by_based_on": "campaign_name",
            "aggregate_function_based_on": "percent_of_goal",
            "group_by_type": "Sum",
            "filters_json": '{"status": "Active", "docstatus": 1}',
            "type": "Bar",
            "color": "#5B8FF9",
        },
        {
            "name": "Donor Level Distribution",
            "chart_name": "Donor Level Distribution",
            "chart_type": "Group By",
            "document_type": "Contact",
            "group_by_based_on": "donor_level",
            "group_by_type": "Count",
            "filters_json": '{"contact_type": "Individual Donor"}',
            "type": "Pie",
            "color": "#F6BD16",
        },
    ]

    for chart_data in charts:
        if frappe.db.exists("Dashboard Chart", chart_data["name"]):
            print(f"  Dashboard Chart '{chart_data['name']}' already exists, skipping")
            continue

        doc_dict = {
            "doctype": "Dashboard Chart",
            "name": chart_data["name"],
            "chart_name": chart_data["chart_name"],
            "chart_type": chart_data["chart_type"],
            "document_type": chart_data["document_type"],
            "filters_json": chart_data.get("filters_json", "{}"),
            "type": chart_data.get("type", "Line"),
            "color": chart_data.get("color"),
            "is_standard": 0,
            "timeseries": chart_data.get("timeseries", 0),
        }

        if chart_data.get("based_on"):
            doc_dict["based_on"] = chart_data["based_on"]
        if chart_data.get("value_based_on"):
            doc_dict["value_based_on"] = chart_data["value_based_on"]
        if chart_data.get("time_interval"):
            doc_dict["time_interval"] = chart_data["time_interval"]
        if chart_data.get("timespan"):
            doc_dict["timespan"] = chart_data["timespan"]
        if chart_data.get("group_by_based_on"):
            doc_dict["group_by_based_on"] = chart_data["group_by_based_on"]
        if chart_data.get("aggregate_function_based_on"):
            doc_dict["aggregate_function_based_on"] = chart_data["aggregate_function_based_on"]
        if chart_data.get("group_by_type"):
            doc_dict["group_by_type"] = chart_data["group_by_type"]

        doc = frappe.get_doc(doc_dict)
        doc.insert(ignore_permissions=True)
        print(f"  Created Dashboard Chart: {chart_data['name']}")
