import frappe
from frappe.model.document import Document


class UWSettings(Document):
    pass


def get_settings():
    """Utility to get UW Settings singleton."""
    return frappe.get_single("UW Settings")
