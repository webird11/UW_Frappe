import frappe
import unittest
from frappe.utils import flt


class TestRemittance(unittest.TestCase):
    """Tests for Remittance validation, totals calculation, and donation creation on submit."""

    @classmethod
    def setUpClass(cls):
        """Create test fixtures: org, agency, contact, campaign, pledge."""
        frappe.flags.ignore_permissions = True

        # Member Agency for pledge allocations
        if not frappe.db.exists("Organization", "_Test Agency Remittance"):
            frappe.get_doc({
                "doctype": "Organization",
                "organization_name": "_Test Agency Remittance",
                "organization_type": "Member Agency",
                "status": "Active",
                "agency_code": "_TREM",
            }).insert()

        # Corporate employer org (sender of remittances)
        if not frappe.db.exists("Organization", "_Test Corp Remittance"):
            frappe.get_doc({
                "doctype": "Organization",
                "organization_name": "_Test Corp Remittance",
                "organization_type": "Corporate Donor",
                "status": "Active",
            }).insert()

        # Donor A
        if not frappe.db.exists("Contact", {"first_name": "_TestRem", "last_name": "DonorA"}):
            frappe.get_doc({
                "doctype": "Contact",
                "first_name": "_TestRem",
                "last_name": "DonorA",
                "contact_type": "Individual Donor",
                "email": "_testrem_a@example.com",
            }).insert()

        cls.donor_a = frappe.db.get_value(
            "Contact", {"first_name": "_TestRem", "last_name": "DonorA"}, "name"
        )

        # Donor B
        if not frappe.db.exists("Contact", {"first_name": "_TestRem", "last_name": "DonorB"}):
            frappe.get_doc({
                "doctype": "Contact",
                "first_name": "_TestRem",
                "last_name": "DonorB",
                "contact_type": "Individual Donor",
                "email": "_testrem_b@example.com",
            }).insert()

        cls.donor_b = frappe.db.get_value(
            "Contact", {"first_name": "_TestRem", "last_name": "DonorB"}, "name"
        )

        # Campaign
        if not frappe.db.exists("Campaign", {"campaign_name": "_Test Remittance Campaign"}):
            camp = frappe.get_doc({
                "doctype": "Campaign",
                "campaign_name": "_Test Remittance Campaign",
                "campaign_type": "Annual Campaign",
                "campaign_year": 2095,
                "status": "Active",
                "start_date": "2095-01-01",
                "end_date": "2095-12-31",
                "fundraising_goal": 100000,
            })
            camp.insert()
            camp.submit()

        cls.campaign_name = frappe.db.get_value(
            "Campaign", {"campaign_name": "_Test Remittance Campaign"}, "name"
        )

        # Submitted pledge for Donor A
        pledge = frappe.new_doc("Pledge")
        pledge.campaign = cls.campaign_name
        pledge.donor = cls.donor_a
        pledge.pledge_amount = 5000
        pledge.pledge_date = "2095-06-01"
        pledge.append("allocations", {
            "agency": "_Test Agency Remittance",
            "designation_type": "Donor Designated",
            "percentage": 100,
        })
        pledge.insert()
        pledge.submit()
        cls.pledge_a = pledge.name

        # Submitted pledge for Donor B
        pledge_b = frappe.new_doc("Pledge")
        pledge_b.campaign = cls.campaign_name
        pledge_b.donor = cls.donor_b
        pledge_b.pledge_amount = 3000
        pledge_b.pledge_date = "2095-06-01"
        pledge_b.append("allocations", {
            "agency": "_Test Agency Remittance",
            "designation_type": "Donor Designated",
            "percentage": 100,
        })
        pledge_b.insert()
        pledge_b.submit()
        cls.pledge_b = pledge_b.name

    def _make_remittance(self, total_amount=1000, items=None, submit=False):
        """Helper to create a test remittance."""
        rem = frappe.new_doc("Remittance")
        rem.organization = "_Test Corp Remittance"
        rem.campaign = self.campaign_name
        rem.remittance_date = "2095-07-01"
        rem.total_amount = total_amount

        if items is None:
            items = [
                {"donor": self.donor_a, "amount": 500, "pledge": self.pledge_a},
                {"donor": self.donor_b, "amount": 500, "pledge": self.pledge_b},
            ]

        for item in items:
            rem.append("items", item)

        rem.insert()
        if submit:
            rem.submit()
        return rem

    # --- Validation Tests ---

    def test_empty_items_rejected(self):
        """Remittance with no items should raise an error."""
        rem = frappe.new_doc("Remittance")
        rem.organization = "_Test Corp Remittance"
        rem.campaign = self.campaign_name
        rem.remittance_date = "2095-07-01"
        rem.total_amount = 1000

        with self.assertRaises(frappe.ValidationError):
            rem.insert()

    def test_missing_donor_rejected(self):
        """Item without a donor should raise an error."""
        with self.assertRaises(frappe.ValidationError):
            self._make_remittance(items=[
                {"donor": "", "amount": 500},
            ])

    def test_zero_amount_rejected(self):
        """Item with zero amount should raise an error."""
        with self.assertRaises(frappe.ValidationError):
            self._make_remittance(items=[
                {"donor": self.donor_a, "amount": 0},
            ])

    def test_negative_amount_rejected(self):
        """Item with negative amount should raise an error."""
        with self.assertRaises(frappe.ValidationError):
            self._make_remittance(items=[
                {"donor": self.donor_a, "amount": -100},
            ])

    # --- Calculate Totals Tests ---

    def test_items_total_calculated(self):
        """items_total should equal the sum of all item amounts."""
        rem = self._make_remittance(total_amount=1000, items=[
            {"donor": self.donor_a, "amount": 400, "pledge": self.pledge_a},
            {"donor": self.donor_b, "amount": 600, "pledge": self.pledge_b},
        ])
        self.assertEqual(flt(rem.items_total), 1000)
        rem.delete()

    def test_variance_calculated(self):
        """variance should equal total_amount minus items_total."""
        rem = self._make_remittance(total_amount=1200, items=[
            {"donor": self.donor_a, "amount": 500, "pledge": self.pledge_a},
            {"donor": self.donor_b, "amount": 500, "pledge": self.pledge_b},
        ])
        self.assertEqual(flt(rem.items_total), 1000)
        self.assertEqual(flt(rem.variance), 200)
        rem.delete()

    def test_zero_variance_when_balanced(self):
        """variance should be 0 when items total matches total_amount."""
        rem = self._make_remittance(total_amount=1000, items=[
            {"donor": self.donor_a, "amount": 500, "pledge": self.pledge_a},
            {"donor": self.donor_b, "amount": 500, "pledge": self.pledge_b},
        ])
        self.assertEqual(flt(rem.variance), 0)
        rem.delete()

    # --- On Submit Tests ---

    def test_on_submit_creates_donations(self):
        """Submitting a remittance should create one Donation per item."""
        rem = self._make_remittance(total_amount=1000, items=[
            {"donor": self.donor_a, "amount": 400, "pledge": self.pledge_a},
            {"donor": self.donor_b, "amount": 600, "pledge": self.pledge_b},
        ], submit=True)

        rem.reload()
        self.assertEqual(rem.donations_created, 2)

        # Check each item has a linked donation
        for item in rem.items:
            self.assertTrue(item.donation, f"Row {item.idx} should have a donation link")
            donation = frappe.get_doc("Donation", item.donation)
            self.assertEqual(donation.docstatus, 1)
            self.assertEqual(donation.payment_method, "Payroll Deduction")
            self.assertEqual(flt(donation.amount), flt(item.amount))
            self.assertEqual(donation.donor, item.donor)
            self.assertEqual(donation.campaign, self.campaign_name)

        # Cleanup
        rem.cancel()

    def test_on_submit_links_donation_back_to_item(self):
        """Each remittance item should have the created donation name stored."""
        rem = self._make_remittance(total_amount=500, items=[
            {"donor": self.donor_a, "amount": 500, "pledge": self.pledge_a},
        ], submit=True)

        rem.reload()
        self.assertTrue(rem.items[0].donation)
        self.assertTrue(frappe.db.exists("Donation", rem.items[0].donation))

        rem.cancel()

    def test_on_submit_sets_donations_created_count(self):
        """donations_created should reflect the number of items."""
        rem = self._make_remittance(total_amount=900, items=[
            {"donor": self.donor_a, "amount": 300, "pledge": self.pledge_a},
            {"donor": self.donor_b, "amount": 300, "pledge": self.pledge_b},
            {"donor": self.donor_a, "amount": 300, "pledge": self.pledge_a},
        ], submit=True)

        rem.reload()
        self.assertEqual(rem.donations_created, 3)

        rem.cancel()

    # --- On Cancel Tests ---

    def test_on_cancel_cancels_donations(self):
        """Cancelling a remittance should cancel all created donations."""
        rem = self._make_remittance(total_amount=1000, items=[
            {"donor": self.donor_a, "amount": 500, "pledge": self.pledge_a},
            {"donor": self.donor_b, "amount": 500, "pledge": self.pledge_b},
        ], submit=True)

        rem.reload()
        donation_names = [item.donation for item in rem.items]
        self.assertEqual(len(donation_names), 2)

        rem.cancel()

        # Donations should now be cancelled (docstatus=2)
        for dname in donation_names:
            donation = frappe.get_doc("Donation", dname)
            self.assertEqual(donation.docstatus, 2)

    def test_on_cancel_clears_donation_links(self):
        """Cancelling should clear the donation field on each item."""
        rem = self._make_remittance(total_amount=500, items=[
            {"donor": self.donor_a, "amount": 500, "pledge": self.pledge_a},
        ], submit=True)

        rem.reload()
        self.assertTrue(rem.items[0].donation)

        rem.cancel()
        rem.reload()

        # After cancel, donation link should be cleared
        self.assertFalse(rem.items[0].donation)

    def test_on_cancel_resets_donations_created(self):
        """Cancelling should reset donations_created to 0."""
        rem = self._make_remittance(total_amount=500, items=[
            {"donor": self.donor_a, "amount": 500, "pledge": self.pledge_a},
        ], submit=True)

        rem.reload()
        self.assertEqual(rem.donations_created, 1)

        rem.cancel()
        rem.reload()
        self.assertEqual(rem.donations_created, 0)
