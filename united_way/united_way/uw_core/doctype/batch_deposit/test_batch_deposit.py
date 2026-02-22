import frappe
import unittest
from frappe.utils import flt


class TestBatchDeposit(unittest.TestCase):
    """Tests for Batch Deposit validation, campaign inheritance, totals, and donation creation."""

    @classmethod
    def setUpClass(cls):
        """Create test fixtures: agency, donors, campaign, pledges."""
        frappe.flags.ignore_permissions = True

        # Member Agency
        if not frappe.db.exists("Organization", "_Test Agency BatchDep"):
            frappe.get_doc({
                "doctype": "Organization",
                "organization_name": "_Test Agency BatchDep",
                "organization_type": "Member Agency",
                "status": "Active",
                "agency_code": "_TBDEP",
            }).insert()

        # Donor A
        if not frappe.db.exists("Contact", {"first_name": "_TestBDep", "last_name": "DonorA"}):
            frappe.get_doc({
                "doctype": "Contact",
                "first_name": "_TestBDep",
                "last_name": "DonorA",
                "contact_type": "Individual Donor",
                "email": "_testbdep_a@example.com",
            }).insert()

        cls.donor_a = frappe.db.get_value(
            "Contact", {"first_name": "_TestBDep", "last_name": "DonorA"}, "name"
        )

        # Donor B
        if not frappe.db.exists("Contact", {"first_name": "_TestBDep", "last_name": "DonorB"}):
            frappe.get_doc({
                "doctype": "Contact",
                "first_name": "_TestBDep",
                "last_name": "DonorB",
                "contact_type": "Individual Donor",
                "email": "_testbdep_b@example.com",
            }).insert()

        cls.donor_b = frappe.db.get_value(
            "Contact", {"first_name": "_TestBDep", "last_name": "DonorB"}, "name"
        )

        # Campaign
        if not frappe.db.exists("Campaign", {"campaign_name": "_Test BatchDep Campaign"}):
            camp = frappe.get_doc({
                "doctype": "Campaign",
                "campaign_name": "_Test BatchDep Campaign",
                "campaign_type": "Annual Campaign",
                "campaign_year": 2096,
                "status": "Active",
                "start_date": "2096-01-01",
                "end_date": "2096-12-31",
                "fundraising_goal": 80000,
            })
            camp.insert()
            camp.submit()

        cls.campaign_name = frappe.db.get_value(
            "Campaign", {"campaign_name": "_Test BatchDep Campaign"}, "name"
        )

        # Second campaign for testing campaign-specific items
        if not frappe.db.exists("Campaign", {"campaign_name": "_Test BatchDep Campaign2"}):
            camp2 = frappe.get_doc({
                "doctype": "Campaign",
                "campaign_name": "_Test BatchDep Campaign2",
                "campaign_type": "Special Initiative",
                "campaign_year": 2096,
                "status": "Active",
                "start_date": "2096-01-01",
                "end_date": "2096-12-31",
                "fundraising_goal": 20000,
            })
            camp2.insert()
            camp2.submit()

        cls.campaign2_name = frappe.db.get_value(
            "Campaign", {"campaign_name": "_Test BatchDep Campaign2"}, "name"
        )

        # Submitted pledge for Donor A
        pledge = frappe.new_doc("Pledge")
        pledge.campaign = cls.campaign_name
        pledge.donor = cls.donor_a
        pledge.pledge_amount = 4000
        pledge.pledge_date = "2096-06-01"
        pledge.append("allocations", {
            "agency": "_Test Agency BatchDep",
            "designation_type": "Donor Designated",
            "percentage": 100,
        })
        pledge.insert()
        pledge.submit()
        cls.pledge_a = pledge.name

    def _make_batch_deposit(self, total_amount=1000, default_campaign=None, items=None, submit=False):
        """Helper to create a test batch deposit."""
        dep = frappe.new_doc("Batch Deposit")
        dep.deposit_date = "2096-07-15"
        dep.total_amount = total_amount
        if default_campaign:
            dep.default_campaign = default_campaign

        if items is None:
            items = [
                {"donor": self.donor_a, "amount": 500, "payment_method": "Check", "check_number": "1001"},
                {"donor": self.donor_b, "amount": 500, "payment_method": "Cash"},
            ]

        for item in items:
            dep.append("items", item)

        dep.insert()
        if submit:
            dep.submit()
        return dep

    # --- Validation Tests ---

    def test_missing_donor_rejected(self):
        """Item without a donor should raise an error."""
        with self.assertRaises(frappe.ValidationError):
            self._make_batch_deposit(items=[
                {"donor": "", "amount": 500, "payment_method": "Check"},
            ])

    def test_zero_amount_rejected(self):
        """Item with zero amount should raise an error."""
        with self.assertRaises(frappe.ValidationError):
            self._make_batch_deposit(items=[
                {"donor": self.donor_a, "amount": 0, "payment_method": "Check"},
            ])

    def test_negative_amount_rejected(self):
        """Item with negative amount should raise an error."""
        with self.assertRaises(frappe.ValidationError):
            self._make_batch_deposit(items=[
                {"donor": self.donor_a, "amount": -100, "payment_method": "Check"},
            ])

    # --- Campaign Inheritance Tests ---

    def test_items_inherit_default_campaign(self):
        """Items without a campaign should get the default_campaign."""
        dep = self._make_batch_deposit(
            total_amount=500,
            default_campaign=self.campaign_name,
            items=[
                {"donor": self.donor_a, "amount": 500, "payment_method": "Check"},
            ],
        )
        self.assertEqual(dep.items[0].campaign, self.campaign_name)
        dep.delete()

    def test_item_campaign_not_overwritten(self):
        """Items with their own campaign should keep it, not get overwritten by default."""
        dep = self._make_batch_deposit(
            total_amount=500,
            default_campaign=self.campaign_name,
            items=[
                {"donor": self.donor_a, "amount": 500, "campaign": self.campaign2_name, "payment_method": "Check"},
            ],
        )
        self.assertEqual(dep.items[0].campaign, self.campaign2_name)
        dep.delete()

    def test_items_without_default_have_no_campaign(self):
        """Items without campaign and no default_campaign should remain blank."""
        dep = self._make_batch_deposit(
            total_amount=500,
            default_campaign=None,
            items=[
                {"donor": self.donor_a, "amount": 500, "payment_method": "Check"},
            ],
        )
        self.assertFalse(dep.items[0].campaign)
        dep.delete()

    # --- Calculate Totals Tests ---

    def test_items_total_calculated(self):
        """items_total should equal sum of all item amounts."""
        dep = self._make_batch_deposit(total_amount=1500, items=[
            {"donor": self.donor_a, "amount": 700, "payment_method": "Check"},
            {"donor": self.donor_b, "amount": 800, "payment_method": "Cash"},
        ])
        self.assertEqual(flt(dep.items_total), 1500)
        dep.delete()

    def test_variance_calculated(self):
        """variance should equal total_amount minus items_total."""
        dep = self._make_batch_deposit(total_amount=2000, items=[
            {"donor": self.donor_a, "amount": 700, "payment_method": "Check"},
            {"donor": self.donor_b, "amount": 800, "payment_method": "Cash"},
        ])
        self.assertEqual(flt(dep.variance), 500)
        dep.delete()

    def test_item_count_calculated(self):
        """item_count should reflect the number of items."""
        dep = self._make_batch_deposit(total_amount=1500, items=[
            {"donor": self.donor_a, "amount": 500, "payment_method": "Check"},
            {"donor": self.donor_b, "amount": 500, "payment_method": "Cash"},
            {"donor": self.donor_a, "amount": 500, "payment_method": "Money Order"},
        ])
        self.assertEqual(dep.item_count, 3)
        dep.delete()

    # --- On Submit Tests ---

    def test_on_submit_creates_donations(self):
        """Submitting a batch deposit should create one Donation per item."""
        dep = self._make_batch_deposit(
            total_amount=1000,
            default_campaign=self.campaign_name,
            items=[
                {"donor": self.donor_a, "amount": 500, "payment_method": "Check", "check_number": "2001",
                 "pledge": self.pledge_a},
                {"donor": self.donor_b, "amount": 500, "payment_method": "Cash"},
            ],
            submit=True,
        )

        dep.reload()
        self.assertEqual(dep.donations_created, 2)

        for item in dep.items:
            self.assertTrue(item.donation, f"Row {item.idx} should have a donation link")
            donation = frappe.get_doc("Donation", item.donation)
            self.assertEqual(donation.docstatus, 1)
            self.assertEqual(flt(donation.amount), flt(item.amount))
            self.assertEqual(donation.donor, item.donor)

        # Check payment method passed through
        don_a = frappe.get_doc("Donation", dep.items[0].donation)
        self.assertEqual(don_a.payment_method, "Check")
        self.assertEqual(don_a.reference_number, "2001")

        don_b = frappe.get_doc("Donation", dep.items[1].donation)
        self.assertEqual(don_b.payment_method, "Cash")

        dep.cancel()

    def test_on_submit_sets_batch_number(self):
        """Created donations should have batch_number set to the deposit name."""
        dep = self._make_batch_deposit(
            total_amount=500,
            default_campaign=self.campaign_name,
            items=[
                {"donor": self.donor_a, "amount": 500, "payment_method": "Check"},
            ],
            submit=True,
        )

        dep.reload()
        donation = frappe.get_doc("Donation", dep.items[0].donation)
        self.assertEqual(donation.batch_number, dep.name)

        dep.cancel()

    # --- On Cancel Tests ---

    def test_on_cancel_cancels_donations(self):
        """Cancelling a batch deposit should cancel all created donations."""
        dep = self._make_batch_deposit(
            total_amount=1000,
            default_campaign=self.campaign_name,
            items=[
                {"donor": self.donor_a, "amount": 500, "payment_method": "Check"},
                {"donor": self.donor_b, "amount": 500, "payment_method": "Cash"},
            ],
            submit=True,
        )

        dep.reload()
        donation_names = [item.donation for item in dep.items]

        dep.cancel()

        for dname in donation_names:
            donation = frappe.get_doc("Donation", dname)
            self.assertEqual(donation.docstatus, 2)

    def test_on_cancel_clears_donation_links(self):
        """Cancelling should clear donation links on items."""
        dep = self._make_batch_deposit(
            total_amount=500,
            default_campaign=self.campaign_name,
            items=[
                {"donor": self.donor_a, "amount": 500, "payment_method": "Check"},
            ],
            submit=True,
        )

        dep.reload()
        self.assertTrue(dep.items[0].donation)

        dep.cancel()
        dep.reload()
        self.assertFalse(dep.items[0].donation)

    def test_on_cancel_resets_donations_created(self):
        """Cancelling should reset donations_created to 0."""
        dep = self._make_batch_deposit(
            total_amount=500,
            default_campaign=self.campaign_name,
            items=[
                {"donor": self.donor_a, "amount": 500, "payment_method": "Check"},
            ],
            submit=True,
        )

        dep.reload()
        self.assertEqual(dep.donations_created, 1)

        dep.cancel()
        dep.reload()
        self.assertEqual(dep.donations_created, 0)
