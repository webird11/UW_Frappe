import frappe


def format_currency_short(value):
    """Format currency in short form for dashboards. e.g., $1.2M, $45K"""
    if not value:
        return "$0"
    value = float(value)
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"${value / 1_000:.1f}K"
    else:
        return f"${value:,.0f}"
