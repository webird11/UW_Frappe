import frappe
import unittest
from frappe.utils import flt


class TestDonation(unittest.TestCase):
    """Tests for Donation pledge linkage, validation, and cascade updates."""

    @classmethod
    def setUpClass(cls):
        """Create test fixtures."""
        frappe.flags.ignore_permissions = True

        if not frappe.db.exists("Organization", "_Test Agency Donation"):
            frappe.get_doc({
                "doctype": "Organization",
                "organization_name": "_Test Agency Donation",
                "organization_type": "Member Agency",
                "status": "Active",
                "agency_code": "_TDON",
            }).insert()

        if not frappe.db.exists("Contact", {"first_name": "_TestDon", "last_name": "Donor"}):
            frappe.get_doc({
                "doctype": "Contact",
                "first_name": "_TestDon",
                "last_name": "Donor",
                "contact_type": "Individual Donor",
                "email": "_testdon@example.com",
            }).insert()

        cls.donor_name = frappe.db.get_value(
            "Contact", {"first_name": "_TestDon", "last_name": "Donor"}, "name"
        )

        if not frappe.db.exists("Campaign", {"campaign_name": "_Test Donation Campaign"}):
            camp = frappe.get_doc({
                "doctype": "Campaign",
                "campaign_name": "_Test Donation Campaign",
                "campaign_type": "Annual Campaign",
                "campaign_year": 2098,
                "status": "Active",
                "start_date": "2098-01-01",
                "end_date": "2098-12-31",
                "fundraising_goal": 50000,
            })
            camp.insert()
            camp.submit()

        cls.campaign_name = frappe.db.get_value(
            "Campaign", {"campaign_name": "_Test Donation Campaign"}, "name"
        )

        # Create a submitted pledge
        pledge = frappe.new_doc("Pledge")
        pledge.campaign = cls.campaign_name
        pledge.donor = cls.donor_name
        pledge.pledge_amount = 2000
        pledge.pledge_date = "2098-06-01"
        pledge.append("allocations", {
            "agency": "_Test Agency Donation",
            "designation_type": "Donor Designated",
            "percentage": 100,
        })
        pledge.insert()
        pledge.submit()
        cls.pledge_name = pledge.name

    def _make_donation(self, amount=500, pledge=None, submit=False):
        """Helper to create a test donation."""
        don = frappe.new_doc("Donation")
        don.donation_date = "2098-07-01"
        don.donor = self.donor_name
        don.campaign = self.campaign_name
        don.amount = amount
        don.payment_method = "Check"
        don.tax_deductible = 1
        if pledge:
            don.pledge = pledge
        don.insert()
        if submit:
            don.submit()
        return don

    # --- Pledge Linkage Tests ---

    def test_donation_linked_to_pledge(self):
        """Donation linked to a valid pledge should save without error."""
        don = self._make_donation(pledge=self.pledge_name)
        self.assertTrue(don.name)
        don.delete()

    def test_campaign_mismatch_throws(self):
        """Donation campaign must match the linked pledge's campaign."""
        # Create a different campaign
        if not frappe.db.exists("Campaign", {"campaign_name": "_Test Other Campaign"}):
            other = frappe.get_doc({
                "doctype": "Campaign",
                "campaign_name": "_Test Other Campaign",
                "campaign_type": "Special Initiative",
                "campaign_year": 2098,
                "status": "Active",
                "start_date": "2098-01-01",
                "end_date": "2098-12-31",
                "fundraising_goal": 10000,
            })
            other.insert()
            other.submit()

        other_campaign = frappe.db.get_value(
            "Campaign", {"campaign_name": "_Test Other Campaign"}, "name"
        )

        don = frappe.new_doc("Donation")
        don.donation_date = "2098-07-01"
        don.donor = self.donor_name
        don.campaign = other_campaign
        don.amount = 500
        don.pledge = self.pledge_name  # Linked to pledge in different campaign

        with self.assertRaises(frappe.ValidationError):
            don.insert()

    def test_donor_mismatch_throws(self):
        """Donation donor must match the linked pledge's donor."""
        # Create a different donor
        if not frappe.db.exists("Contact", {"first_name": "_TestOther", "last_name": "Person"}):
            frappe.get_doc({
                "doctype": "Contact",
                "first_name": "_TestOther",
                "last_name": "Person",
                "contact_type": "Individual Donor",
                "email": "_testother@example.com",
            }).insert()

        other_donor = frappe.db.get_value(
            "Contact", {"first_name": "_TestOther", "last_name": "Person"}, "name"
        )

        don = frappe.new_doc("Donation")
        don.donation_date = "2098-07-01"
        don.donor = other_donor
        don.campaign = self.campaign_name
        don.amount = 500
        don.pledge = self.pledge_name  # Linked to pledge from different donor

        with self.assertRaises(frappe.ValidationError):
            don.insert()

    # --- Tax Deductible Tests ---

    def test_tax_deductible_amount_auto_set(self):
        """Tax deductible amount should default to full amount."""
        don = self._make_donation(amount=750)
        self.assertEqual(flt(don.tax_deductible_amount), 750)
        don.delete()

    # --- Standalone Donation ---

    def test_standalone_donation_no_pledge(self):
        """Donation without a pledge link should save fine."""
        don = self._make_donation(amount=100, pledge=None)
        self.assertTrue(don.name)
        self.assertFalse(don.pledge)
        don.delete()

    # --- Pledge Collection Update on Submit ---

    def test_pledge_collection_updates_on_submit(self):
        """Submitting a donation should update the linked pledge's collection fields."""
        don = self._make_donation(amount=500, pledge=self.pledge_name, submit=True)

        pledge = frappe.get_doc("Pledge", self.pledge_name)
        self.assertGreaterEqual(flt(pledge.total_collected), 500)
        self.assertEqual(pledge.collection_status, "In Progress")

        don.cancel()

    def test_donor_stats_update_on_submit(self):
        """Submitting a donation should update the donor's lifetime giving."""
        don = self._make_donation(amount=300, submit=True)

        contact = frappe.get_doc("Contact", self.donor_name)
        self.assertGreaterEqual(flt(contact.lifetime_giving), 300)

        don.cancel()
