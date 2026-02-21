import frappe
import unittest
from frappe.utils import flt


class TestCampaign(unittest.TestCase):
    """Tests for Campaign validation and rollup calculations."""

    @classmethod
    def setUpClass(cls):
        """Create test fixtures."""
        frappe.flags.ignore_permissions = True

        if not frappe.db.exists("Organization", "_Test Agency Campaign"):
            frappe.get_doc({
                "doctype": "Organization",
                "organization_name": "_Test Agency Campaign",
                "organization_type": "Member Agency",
                "status": "Active",
                "agency_code": "_TCAMP",
            }).insert()

        if not frappe.db.exists("Contact", {"first_name": "_TestCamp", "last_name": "DonorA"}):
            frappe.get_doc({
                "doctype": "Contact",
                "first_name": "_TestCamp",
                "last_name": "DonorA",
                "contact_type": "Individual Donor",
                "email": "_testcampa@example.com",
            }).insert()

        cls.donor_a = frappe.db.get_value(
            "Contact", {"first_name": "_TestCamp", "last_name": "DonorA"}, "name"
        )

        if not frappe.db.exists("Contact", {"first_name": "_TestCamp", "last_name": "DonorB"}):
            frappe.get_doc({
                "doctype": "Contact",
                "first_name": "_TestCamp",
                "last_name": "DonorB",
                "contact_type": "Individual Donor",
                "email": "_testcampb@example.com",
            }).insert()

        cls.donor_b = frappe.db.get_value(
            "Contact", {"first_name": "_TestCamp", "last_name": "DonorB"}, "name"
        )

    def _make_campaign(self, goal=100000):
        """Helper to create and submit a test campaign."""
        camp = frappe.new_doc("Campaign")
        camp.campaign_name = f"_Test Rollup Campaign {frappe.generate_hash(length=6)}"
        camp.campaign_type = "Annual Campaign"
        camp.campaign_year = 2097
        camp.status = "Active"
        camp.start_date = "2097-01-01"
        camp.end_date = "2097-12-31"
        camp.fundraising_goal = goal
        camp.insert()
        camp.submit()
        return camp

    # --- Validation Tests ---

    def test_end_date_before_start_date_throws(self):
        """Campaign with end_date before start_date should raise error."""
        camp = frappe.new_doc("Campaign")
        camp.campaign_name = "_Test Invalid Dates"
        camp.campaign_type = "Annual Campaign"
        camp.campaign_year = 2097
        camp.status = "Planning"
        camp.start_date = "2097-12-31"
        camp.end_date = "2097-01-01"
        camp.fundraising_goal = 1000

        with self.assertRaises(frappe.ValidationError):
            camp.insert()

    def test_valid_campaign_creation(self):
        """Campaign with valid data should create and submit."""
        camp = self._make_campaign()
        self.assertTrue(camp.name)
        self.assertEqual(camp.docstatus, 1)
        camp.cancel()

    # --- Rollup Calculation Tests ---

    def test_rollup_totals_after_pledge_submit(self):
        """Campaign totals should update after a pledge is submitted."""
        camp = self._make_campaign(goal=50000)

        # Create and submit a pledge
        pledge = frappe.new_doc("Pledge")
        pledge.campaign = camp.name
        pledge.donor = self.donor_a
        pledge.pledge_amount = 5000
        pledge.pledge_date = "2097-06-01"
        pledge.append("allocations", {
            "agency": "_Test Agency Campaign",
            "percentage": 100,
        })
        pledge.insert()
        pledge.submit()

        # Reload campaign and check totals
        camp.reload()
        self.assertEqual(flt(camp.total_pledged), 5000)
        self.assertEqual(camp.pledge_count, 1)
        self.assertEqual(camp.donor_count, 1)
        self.assertEqual(flt(camp.percent_of_goal), 10.0)

        pledge.cancel()
        camp.cancel()

    def test_rollup_with_multiple_pledges(self):
        """Campaign should correctly sum multiple pledges."""
        camp = self._make_campaign(goal=100000)

        pledges = []
        for donor, amount in [(self.donor_a, 3000), (self.donor_b, 7000)]:
            p = frappe.new_doc("Pledge")
            p.campaign = camp.name
            p.donor = donor
            p.pledge_amount = amount
            p.pledge_date = "2097-06-01"
            p.append("allocations", {
                "agency": "_Test Agency Campaign",
                "percentage": 100,
            })
            p.insert()
            p.submit()
            pledges.append(p)

        camp.reload()
        self.assertEqual(flt(camp.total_pledged), 10000)
        self.assertEqual(camp.pledge_count, 2)
        self.assertEqual(camp.donor_count, 2)
        self.assertEqual(flt(camp.percent_of_goal), 10.0)

        for p in pledges:
            p.cancel()
        camp.cancel()

    def test_rollup_includes_donations(self):
        """Campaign total_collected should update after donation submit."""
        camp = self._make_campaign(goal=50000)

        pledge = frappe.new_doc("Pledge")
        pledge.campaign = camp.name
        pledge.donor = self.donor_a
        pledge.pledge_amount = 2000
        pledge.pledge_date = "2097-06-01"
        pledge.append("allocations", {
            "agency": "_Test Agency Campaign",
            "percentage": 100,
        })
        pledge.insert()
        pledge.submit()

        don = frappe.new_doc("Donation")
        don.donation_date = "2097-07-01"
        don.donor = self.donor_a
        don.campaign = camp.name
        don.amount = 1000
        don.pledge = pledge.name
        don.insert()
        don.submit()

        camp.reload()
        self.assertEqual(flt(camp.total_collected), 1000)
        self.assertGreater(flt(camp.collection_rate), 0)

        don.cancel()
        pledge.cancel()
        camp.cancel()

    def test_cancel_pledge_removes_from_totals(self):
        """Cancelling a pledge should reduce campaign totals."""
        camp = self._make_campaign(goal=50000)

        pledge = frappe.new_doc("Pledge")
        pledge.campaign = camp.name
        pledge.donor = self.donor_a
        pledge.pledge_amount = 5000
        pledge.pledge_date = "2097-06-01"
        pledge.append("allocations", {
            "agency": "_Test Agency Campaign",
            "percentage": 100,
        })
        pledge.insert()
        pledge.submit()

        camp.reload()
        self.assertEqual(flt(camp.total_pledged), 5000)

        pledge.cancel()
        camp.reload()
        self.assertEqual(flt(camp.total_pledged), 0)
        self.assertEqual(camp.pledge_count, 0)

        camp.cancel()
