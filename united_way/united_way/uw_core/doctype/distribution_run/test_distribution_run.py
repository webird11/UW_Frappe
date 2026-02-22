import frappe
import unittest
from frappe.utils import flt
from united_way.uw_core.doctype.distribution_run.distribution_run import populate_distribution_items


class TestDistributionRun(unittest.TestCase):
    """Tests for Distribution Run date validation, item amounts, totals, and populate function."""

    @classmethod
    def setUpClass(cls):
        """Create test fixtures: agencies, donors, campaign, pledges with donations."""
        frappe.flags.ignore_permissions = True

        # Agency Alpha
        if not frappe.db.exists("Organization", "_Test Agency DistAlpha"):
            frappe.get_doc({
                "doctype": "Organization",
                "organization_name": "_Test Agency DistAlpha",
                "organization_type": "Member Agency",
                "status": "Active",
                "agency_code": "_TDSTA",
            }).insert()

        # Agency Beta
        if not frappe.db.exists("Organization", "_Test Agency DistBeta"):
            frappe.get_doc({
                "doctype": "Organization",
                "organization_name": "_Test Agency DistBeta",
                "organization_type": "Member Agency",
                "status": "Active",
                "agency_code": "_TDSTB",
            }).insert()

        # Donor
        if not frappe.db.exists("Contact", {"first_name": "_TestDist", "last_name": "Donor"}):
            frappe.get_doc({
                "doctype": "Contact",
                "first_name": "_TestDist",
                "last_name": "Donor",
                "contact_type": "Individual Donor",
                "email": "_testdist@example.com",
            }).insert()

        cls.donor_name = frappe.db.get_value(
            "Contact", {"first_name": "_TestDist", "last_name": "Donor"}, "name"
        )

        # Campaign for distribution tests
        if not frappe.db.exists("Campaign", {"campaign_name": "_Test Distribution Campaign"}):
            camp = frappe.get_doc({
                "doctype": "Campaign",
                "campaign_name": "_Test Distribution Campaign",
                "campaign_type": "Annual Campaign",
                "campaign_year": 2095,
                "status": "Active",
                "start_date": "2095-01-01",
                "end_date": "2095-12-31",
                "fundraising_goal": 50000,
            })
            camp.insert()
            camp.submit()

        cls.campaign_name = frappe.db.get_value(
            "Campaign", {"campaign_name": "_Test Distribution Campaign"}, "name"
        )

        # Pledge with allocations to both agencies (60/40 split)
        pledge = frappe.new_doc("Pledge")
        pledge.campaign = cls.campaign_name
        pledge.donor = cls.donor_name
        pledge.pledge_amount = 10000
        pledge.pledge_date = "2095-06-01"
        pledge.append("allocations", {
            "agency": "_Test Agency DistAlpha",
            "designation_type": "Donor Designated",
            "percentage": 60,
        })
        pledge.append("allocations", {
            "agency": "_Test Agency DistBeta",
            "designation_type": "Donor Designated",
            "percentage": 40,
        })
        pledge.insert()
        pledge.submit()
        cls.pledge_name = pledge.name

        # Create a donation to partially collect the pledge
        don = frappe.new_doc("Donation")
        don.donation_date = "2095-07-01"
        don.donor = cls.donor_name
        don.campaign = cls.campaign_name
        don.amount = 5000
        don.pledge = cls.pledge_name
        don.payment_method = "Check"
        don.insert()
        don.submit()
        cls.donation_name = don.name

    def _make_distribution_run(self, items=None, submit=False):
        """Helper to create a distribution run."""
        dist = frappe.new_doc("Distribution Run")
        dist.campaign = self.campaign_name
        dist.distribution_date = "2095-08-01"
        dist.period_start = "2095-07-01"
        dist.period_end = "2095-07-31"
        dist.distribution_type = "Monthly"

        if items is None:
            items = [
                {
                    "agency": "_Test Agency DistAlpha",
                    "total_allocated": 6000,
                    "total_collected": 3000,
                    "previously_distributed": 0,
                    "distribution_amount": 3000,
                },
            ]

        for item in items:
            dist.append("items", item)

        dist.insert()
        if submit:
            dist.submit()
        return dist

    # --- Date Validation Tests ---

    def test_period_end_before_start_rejected(self):
        """Period end before period start should raise an error."""
        dist = frappe.new_doc("Distribution Run")
        dist.campaign = self.campaign_name
        dist.distribution_date = "2095-08-01"
        dist.period_start = "2095-08-31"
        dist.period_end = "2095-08-01"
        dist.distribution_type = "Monthly"
        dist.append("items", {
            "agency": "_Test Agency DistAlpha",
            "distribution_amount": 1000,
        })

        with self.assertRaises(frappe.ValidationError):
            dist.insert()

    def test_same_start_and_end_date_allowed(self):
        """Period start equal to period end should be allowed."""
        dist = frappe.new_doc("Distribution Run")
        dist.campaign = self.campaign_name
        dist.distribution_date = "2095-08-01"
        dist.period_start = "2095-08-01"
        dist.period_end = "2095-08-01"
        dist.distribution_type = "Monthly"
        dist.append("items", {
            "agency": "_Test Agency DistAlpha",
            "distribution_amount": 1000,
        })
        dist.insert()
        self.assertTrue(dist.name)
        dist.delete()

    # --- Item Amount Validation Tests ---

    def test_zero_distribution_amount_rejected(self):
        """Distribution item with zero amount should raise an error."""
        with self.assertRaises(frappe.ValidationError):
            self._make_distribution_run(items=[
                {
                    "agency": "_Test Agency DistAlpha",
                    "distribution_amount": 0,
                },
            ])

    def test_negative_distribution_amount_rejected(self):
        """Distribution item with negative amount should raise an error."""
        with self.assertRaises(frappe.ValidationError):
            self._make_distribution_run(items=[
                {
                    "agency": "_Test Agency DistAlpha",
                    "distribution_amount": -500,
                },
            ])

    # --- Calculate Totals Tests ---

    def test_total_distribution_calculated(self):
        """total_distribution should be the sum of all item distribution_amounts."""
        dist = self._make_distribution_run(items=[
            {
                "agency": "_Test Agency DistAlpha",
                "distribution_amount": 3000,
            },
            {
                "agency": "_Test Agency DistBeta",
                "distribution_amount": 2000,
            },
        ])
        self.assertEqual(flt(dist.total_distribution), 5000)
        dist.delete()

    def test_agency_count_calculated(self):
        """agency_count should reflect the number of distribution items."""
        dist = self._make_distribution_run(items=[
            {
                "agency": "_Test Agency DistAlpha",
                "distribution_amount": 3000,
            },
            {
                "agency": "_Test Agency DistBeta",
                "distribution_amount": 2000,
            },
        ])
        self.assertEqual(dist.agency_count, 2)
        dist.delete()

    def test_single_item_totals(self):
        """Single item should set total_distribution and agency_count correctly."""
        dist = self._make_distribution_run(items=[
            {
                "agency": "_Test Agency DistAlpha",
                "distribution_amount": 7500,
            },
        ])
        self.assertEqual(flt(dist.total_distribution), 7500)
        self.assertEqual(dist.agency_count, 1)
        dist.delete()

    # --- Populate Distribution Items (Whitelist Function) Tests ---

    def test_populate_returns_agency_data(self):
        """populate_distribution_items should return items for agencies with collections."""
        items = populate_distribution_items(
            self.campaign_name, "2095-07-01", "2095-07-31"
        )
        self.assertIsInstance(items, list)
        # Should have at least one agency with distribution_amount > 0
        if items:
            for item in items:
                self.assertIn("agency", item)
                self.assertIn("total_allocated", item)
                self.assertIn("total_collected", item)
                self.assertIn("previously_distributed", item)
                self.assertIn("distribution_amount", item)
                self.assertGreater(flt(item["distribution_amount"]), 0)

    def test_populate_returns_empty_for_unknown_campaign(self):
        """populate_distribution_items with a nonexistent campaign should return empty."""
        items = populate_distribution_items(
            "NONEXISTENT-CAMPAIGN-12345", "2095-07-01", "2095-07-31"
        )
        self.assertEqual(items, [])

    def test_populate_distribution_amounts_non_negative(self):
        """All returned distribution_amounts should be >= 0."""
        items = populate_distribution_items(
            self.campaign_name, "2095-07-01", "2095-07-31"
        )
        for item in items:
            self.assertGreaterEqual(flt(item["distribution_amount"]), 0)
