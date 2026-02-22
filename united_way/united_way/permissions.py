import frappe


def get_pledge_allocation_permission_query(user):
	"""Agency Admins can only see Pledge Allocations for their agency."""
	if is_agency_admin(user):
		agency = get_user_agency(user)
		if agency:
			return "`tabPledge Allocation`.agency = {0}".format(
				frappe.db.escape(agency)
			)
	return ""


def get_distribution_item_permission_query(user):
	"""Agency Admins can only see Distribution Items for their agency."""
	if is_agency_admin(user):
		agency = get_user_agency(user)
		if agency:
			return "`tabDistribution Item`.agency = {0}".format(
				frappe.db.escape(agency)
			)
	return ""


def get_distribution_run_permission_query(user):
	"""Agency Admins see Distribution Runs that have items for their agency."""
	if is_agency_admin(user):
		agency = get_user_agency(user)
		if agency:
			return """`tabDistribution Run`.name IN (
				SELECT parent FROM `tabDistribution Item`
				WHERE agency = {0}
			)""".format(
				frappe.db.escape(agency)
			)
	return ""


def has_pledge_allocation_permission(doc, ptype, user):
	"""Check if user has permission to view a specific Pledge Allocation."""
	if is_agency_admin(user):
		agency = get_user_agency(user)
		if agency and doc.agency != agency:
			return False
	return True


def has_distribution_item_permission(doc, ptype, user):
	"""Check if user has permission to view a specific Distribution Item."""
	if is_agency_admin(user):
		agency = get_user_agency(user)
		if agency and doc.agency != agency:
			return False
	return True


def has_distribution_run_permission(doc, ptype, user):
	"""Check if user has permission to view a specific Distribution Run.

	Agency Admins can only see Distribution Runs that contain at least
	one Distribution Item for their agency.
	"""
	if is_agency_admin(user):
		agency = get_user_agency(user)
		if agency:
			has_agency_item = any(
				item.agency == agency for item in doc.get("items", [])
			)
			if not has_agency_item:
				return False
	return True


def is_agency_admin(user=None):
	"""Check if the user has the Agency Admin role.

	Returns False for Administrator to preserve god-mode access.
	"""
	if not user:
		user = frappe.session.user
	if user == "Administrator":
		return False
	return "Agency Admin" in frappe.get_roles(user)


def get_user_agency(user=None):
	"""Get the linked organization for the user (their agency).

	Looks up the user's email in Contact records to find their organization.
	Returns the Organization name (string) or None if not found.
	"""
	if not user:
		user = frappe.session.user

	# Try to get organization from Contact linked to this user's email
	agency = frappe.db.get_value("Contact", {"email": user}, "organization")
	return agency
