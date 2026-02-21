import frappe
import unittest
from frappe.utils import flt


class TestPledge(unittest.TestCase):
    """Tests for Pledge allocation validation, corporate match, and collection tracking."""

    @classmethod
    def setUpClass(cls):
        """Create test fixtures: org, contact, campaign."""
        frappe.flags.ignore_permissions = True

        # Create a Member Agency
        if not frappe.db.exists("Organization", "_Test Agency Alpha"):
            frappe.get_doc({
                "doctype": "Organization",
                "organization_name": "_Test Agency Alpha",
                "organization_type": "Member Agency",
                "status": "Active",
                "agency_code": "_TALPHA",
            }).insert()

        if not frappe.db.exists("Organization", "_Test Agency Beta"):
            frappe.get_doc({
                "doctype": "Organization",
                "organization_name": "_Test Agency Beta",
                "organization_type": "Member Agency",
                "status": "Active",
                "agency_code": "_TBETA",
            }).insert()

        # Create a Corporate Donor org with match program
        if not frappe.db.exists("Organization", "_Test Corp Matcher"):
            frappe.get_doc({
                "doctype": "Organization",
                "organization_name": "_Test Corp Matcher",
                "organization_type": "Corporate Donor",
                "status": "Active",
                "corporate_match": 1,
                "match_ratio": 1.0,
                "match_cap": 5000,
            }).insert()

        # Create a test contact
        if not frappe.db.exists("Contact", {"first_name": "_Test", "last_name": "Donor"}):
            frappe.get_doc({
                "doctype": "Contact",
                "first_name": "_Test",
                "last_name": "Donor",
                "contact_type": "Individual Donor",
                "organization": "_Test Corp Matcher",
                "email": "_testdonor@example.com",
            }).insert()

        cls.donor_name = frappe.db.get_value(
            "Contact", {"first_name": "_Test", "last_name": "Donor"}, "name"
        )

        # Create a test campaign
        if not frappe.db.exists("Campaign", {"campaign_name": "_Test Campaign"}):
            camp = frappe.get_doc({
                "doctype": "Campaign",
                "campaign_name": "_Test Campaign",
                "campaign_type": "Annual Campaign",
                "campaign_year": 2099,
                "status": "Active",
                "start_date": "2099-01-01",
                "end_date": "2099-12-31",
                "fundraising_goal": 100000,
            })
            camp.insert()
            camp.submit()

        cls.campaign_name = frappe.db.get_value(
            "Campaign", {"campaign_name": "_Test Campaign"}, "name"
        )

    def _make_pledge(self, amount=1000, allocations=None, submit=False):
        """Helper to create a test pledge."""
        pledge = frappe.new_doc("Pledge")
        pledge.campaign = self.campaign_name
        pledge.donor = self.donor_name
        pledge.pledge_amount = amount
        pledge.pledge_date = "2099-06-01"

        if allocations is None:
            allocations = [
                {"agency": "_Test Agency Alpha", "designation_type": "Donor Designated", "percentage": 100}
            ]

        for alloc in allocations:
            pledge.append("allocations", alloc)

        pledge.insert()
        if submit:
            pledge.submit()
        return pledge

    # --- Allocation Validation Tests ---

    def test_allocations_must_total_100(self):
        """Percentages that don't total 100% should raise an error."""
        with self.assertRaises(frappe.ValidationError):
            self._make_pledge(allocations=[
                {"agency": "_Test Agency Alpha", "percentage": 50},
            ])

    def test_allocations_exact_100_passes(self):
        """Percentages totaling exactly 100% should pass."""
        pledge = self._make_pledge(allocations=[
            {"agency": "_Test Agency Alpha", "percentage": 60},
            {"agency": "_Test Agency Beta", "percentage": 40},
        ])
        self.assertTrue(pledge.name)
        pledge.delete()

    def test_duplicate_agency_rejected(self):
        """Same agency appearing twice in allocations should raise error."""
        with self.assertRaises(frappe.ValidationError):
            self._make_pledge(allocations=[
                {"agency": "_Test Agency Alpha", "percentage": 60},
                {"agency": "_Test Agency Alpha", "percentage": 40},
            ])

    def test_empty_allocations_rejected(self):
        """Pledge with no allocations should raise error."""
        pledge = frappe.new_doc("Pledge")
        pledge.campaign = self.campaign_name
        pledge.donor = self.donor_name
        pledge.pledge_amount = 1000
        pledge.pledge_date = "2099-06-01"

        with self.assertRaises(frappe.ValidationError):
            pledge.insert()

    # --- Allocation Amount Calculation Tests ---

    def test_allocation_amounts_calculated(self):
        """Allocated dollar amounts should be calculated from percentages."""
        pledge = self._make_pledge(amount=5000, allocations=[
            {"agency": "_Test Agency Alpha", "percentage": 70},
            {"agency": "_Test Agency Beta", "percentage": 30},
        ])

        self.assertEqual(flt(pledge.allocations[0].allocated_amount), 3500)
        self.assertEqual(flt(pledge.allocations[1].allocated_amount), 1500)
        pledge.delete()

    # --- Corporate Match Tests ---

    def test_corporate_match_calculated(self):
        """Corporate match should be calculated when eligible."""
        pledge = self._make_pledge(amount=3000)
        pledge.eligible_for_match = 1
        pledge.save()

        # Match ratio is 1.0, cap is 5000, so match = 3000
        self.assertEqual(flt(pledge.match_amount), 3000)
        pledge.delete()

    def test_corporate_match_capped(self):
        """Corporate match should be capped at match_cap."""
        pledge = self._make_pledge(amount=10000)
        pledge.eligible_for_match = 1
        pledge.save()

        # Match ratio 1.0 * 10000 = 10000, but cap is 5000
        self.assertEqual(flt(pledge.match_amount), 5000)
        pledge.delete()

    def test_corporate_match_zero_when_not_eligible(self):
        """Match amount should be 0 when not eligible."""
        pledge = self._make_pledge(amount=5000)
        pledge.eligible_for_match = 0
        pledge.save()

        self.assertEqual(flt(pledge.match_amount), 0)
        pledge.delete()

    # --- Collection Status Tests ---

    def test_initial_collection_status(self):
        """New pledge should have 'Not Started' collection status."""
        pledge = self._make_pledge()
        self.assertEqual(pledge.collection_status, "Not Started")
        self.assertEqual(flt(pledge.total_collected), 0)
        pledge.delete()
