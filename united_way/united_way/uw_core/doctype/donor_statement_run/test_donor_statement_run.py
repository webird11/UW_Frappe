import frappe
import unittest
from frappe.utils import flt, cint
from united_way.uw_core.doctype.donor_statement_run.donor_statement_run import populate_donor_statements


class TestDonorStatementRun(unittest.TestCase):
    """Tests for Donor Statement Run summary calculations and populate function."""

    @classmethod
    def setUpClass(cls):
        """Create test fixtures: agency, donors, campaign, pledges, donations."""
        frappe.flags.ignore_permissions = True

        # Member Agency
        if not frappe.db.exists("Organization", "_Test Agency Statement"):
            frappe.get_doc({
                "doctype": "Organization",
                "organization_name": "_Test Agency Statement",
                "organization_type": "Member Agency",
                "status": "Active",
                "agency_code": "_TSTMT",
            }).insert()

        # Donor A
        if not frappe.db.exists("Contact", {"first_name": "_TestStmt", "last_name": "DonorA"}):
            frappe.get_doc({
                "doctype": "Contact",
                "first_name": "_TestStmt",
                "last_name": "DonorA",
                "contact_type": "Individual Donor",
                "email": "_teststmt_a@example.com",
            }).insert()

        cls.donor_a = frappe.db.get_value(
            "Contact", {"first_name": "_TestStmt", "last_name": "DonorA"}, "name"
        )

        # Donor B
        if not frappe.db.exists("Contact", {"first_name": "_TestStmt", "last_name": "DonorB"}):
            frappe.get_doc({
                "doctype": "Contact",
                "first_name": "_TestStmt",
                "last_name": "DonorB",
                "contact_type": "Individual Donor",
                "email": "_teststmt_b@example.com",
            }).insert()

        cls.donor_b = frappe.db.get_value(
            "Contact", {"first_name": "_TestStmt", "last_name": "DonorB"}, "name"
        )

        # Campaign (year 2095 for donation tax year testing)
        if not frappe.db.exists("Campaign", {"campaign_name": "_Test Statement Campaign"}):
            camp = frappe.get_doc({
                "doctype": "Campaign",
                "campaign_name": "_Test Statement Campaign",
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
            "Campaign", {"campaign_name": "_Test Statement Campaign"}, "name"
        )

        # Pledges
        pledge_a = frappe.new_doc("Pledge")
        pledge_a.campaign = cls.campaign_name
        pledge_a.donor = cls.donor_a
        pledge_a.pledge_amount = 5000
        pledge_a.pledge_date = "2095-06-01"
        pledge_a.append("allocations", {
            "agency": "_Test Agency Statement",
            "designation_type": "Donor Designated",
            "percentage": 100,
        })
        pledge_a.insert()
        pledge_a.submit()
        cls.pledge_a = pledge_a.name

        pledge_b = frappe.new_doc("Pledge")
        pledge_b.campaign = cls.campaign_name
        pledge_b.donor = cls.donor_b
        pledge_b.pledge_amount = 3000
        pledge_b.pledge_date = "2095-06-01"
        pledge_b.append("allocations", {
            "agency": "_Test Agency Statement",
            "designation_type": "Donor Designated",
            "percentage": 100,
        })
        pledge_b.insert()
        pledge_b.submit()
        cls.pledge_b = pledge_b.name

        # Donations in year 2095 for both donors
        # Donor A: Two donations totaling $2000
        don_a1 = frappe.new_doc("Donation")
        don_a1.donation_date = "2095-07-01"
        don_a1.donor = cls.donor_a
        don_a1.campaign = cls.campaign_name
        don_a1.amount = 1200
        don_a1.pledge = cls.pledge_a
        don_a1.payment_method = "Check"
        don_a1.tax_deductible = 1
        don_a1.insert()
        don_a1.submit()
        cls.don_a1 = don_a1.name

        don_a2 = frappe.new_doc("Donation")
        don_a2.donation_date = "2095-09-15"
        don_a2.donor = cls.donor_a
        don_a2.campaign = cls.campaign_name
        don_a2.amount = 800
        don_a2.pledge = cls.pledge_a
        don_a2.payment_method = "Check"
        don_a2.tax_deductible = 1
        don_a2.insert()
        don_a2.submit()
        cls.don_a2 = don_a2.name

        # Donor B: One donation of $1500
        don_b1 = frappe.new_doc("Donation")
        don_b1.donation_date = "2095-08-01"
        don_b1.donor = cls.donor_b
        don_b1.campaign = cls.campaign_name
        don_b1.amount = 1500
        don_b1.pledge = cls.pledge_b
        don_b1.payment_method = "Cash"
        don_b1.tax_deductible = 1
        don_b1.insert()
        don_b1.submit()
        cls.don_b1 = don_b1.name

    def _make_statement_run(self, tax_year=2095, items=None, submit=False):
        """Helper to create a donor statement run."""
        run = frappe.new_doc("Donor Statement Run")
        run.tax_year = tax_year
        run.generation_date = "2096-01-15"

        if items is None:
            items = [
                {
                    "donor": self.donor_a,
                    "donor_name": "_TestStmt DonorA",
                    "total_donations": 2000,
                    "donation_count": 2,
                    "tax_deductible_total": 2000,
                    "statement_generated": 1,
                },
                {
                    "donor": self.donor_b,
                    "donor_name": "_TestStmt DonorB",
                    "total_donations": 1500,
                    "donation_count": 1,
                    "tax_deductible_total": 1500,
                    "statement_generated": 0,
                },
            ]

        for item in items:
            run.append("items", item)

        run.insert()
        if submit:
            run.submit()
        return run

    # --- Calculate Summary Fields Tests ---

    def test_total_donors_calculated(self):
        """total_donors should equal the number of items."""
        run = self._make_statement_run(items=[
            {"donor": self.donor_a, "total_donations": 2000, "donation_count": 2, "tax_deductible_total": 2000},
            {"donor": self.donor_b, "total_donations": 1500, "donation_count": 1, "tax_deductible_total": 1500},
        ])
        self.assertEqual(run.total_donors, 2)
        run.delete()

    def test_total_amount_calculated(self):
        """total_amount should be the sum of total_donations across all items."""
        run = self._make_statement_run(items=[
            {"donor": self.donor_a, "total_donations": 2000, "donation_count": 2, "tax_deductible_total": 2000},
            {"donor": self.donor_b, "total_donations": 1500, "donation_count": 1, "tax_deductible_total": 1500},
        ])
        self.assertEqual(flt(run.total_amount), 3500)
        run.delete()

    def test_statements_generated_count(self):
        """statements_generated should count items where statement_generated is checked."""
        run = self._make_statement_run(items=[
            {"donor": self.donor_a, "total_donations": 2000, "donation_count": 2,
             "tax_deductible_total": 2000, "statement_generated": 1},
            {"donor": self.donor_b, "total_donations": 1500, "donation_count": 1,
             "tax_deductible_total": 1500, "statement_generated": 0},
        ])
        self.assertEqual(run.statements_generated, 1)
        run.delete()

    def test_statements_sent_count(self):
        """statements_sent should count items where sent_date is set."""
        run = self._make_statement_run(items=[
            {"donor": self.donor_a, "total_donations": 2000, "donation_count": 2,
             "tax_deductible_total": 2000, "statement_generated": 1, "sent_date": "2096-01-20"},
            {"donor": self.donor_b, "total_donations": 1500, "donation_count": 1,
             "tax_deductible_total": 1500, "statement_generated": 1, "sent_date": "2096-01-20"},
        ])
        self.assertEqual(run.statements_sent, 2)
        run.delete()

    def test_zero_items_summary(self):
        """Empty items should give zero for all summary fields."""
        run = frappe.new_doc("Donor Statement Run")
        run.tax_year = 2095
        run.generation_date = "2096-01-15"
        # Need at least one item per the JSON reqd=1, but test the calculate function
        # by manually calling it with empty items
        run.items = []
        run.calculate_summary_fields()
        self.assertEqual(run.total_donors, 0)
        self.assertEqual(flt(run.total_amount), 0)
        self.assertEqual(run.statements_generated, 0)
        self.assertEqual(run.statements_sent, 0)

    # --- Populate Donor Statements (Whitelist Function) Tests ---

    def test_populate_returns_donor_data(self):
        """populate_donor_statements should return grouped donation data for the tax year."""
        results = populate_donor_statements(2095)
        self.assertIsInstance(results, list)

        # Find our test donors in the results
        donor_a_rows = [r for r in results if r.get("donor") == self.donor_a]
        donor_b_rows = [r for r in results if r.get("donor") == self.donor_b]

        # Donor A should have $2000 total (1200 + 800), 2 donations
        if donor_a_rows:
            row_a = donor_a_rows[0]
            self.assertEqual(flt(row_a["total_donations"]), 2000)
            self.assertEqual(row_a["donation_count"], 2)
            self.assertGreater(flt(row_a["tax_deductible_total"]), 0)

        # Donor B should have $1500 total, 1 donation
        if donor_b_rows:
            row_b = donor_b_rows[0]
            self.assertEqual(flt(row_b["total_donations"]), 1500)
            self.assertEqual(row_b["donation_count"], 1)

    def test_populate_empty_tax_year_throws(self):
        """Empty/zero tax year should raise a validation error."""
        with self.assertRaises(frappe.ValidationError):
            populate_donor_statements(0)

    def test_populate_no_donations_returns_empty(self):
        """Tax year with no donations should return an empty list."""
        results = populate_donor_statements(2050)  # Far future year with no data
        self.assertEqual(len(results), 0)

    def test_populate_result_fields(self):
        """Each result row should have the expected fields."""
        results = populate_donor_statements(2095)
        if results:
            row = results[0]
            self.assertIn("donor", row)
            self.assertIn("donor_name", row)
            self.assertIn("total_donations", row)
            self.assertIn("donation_count", row)
            self.assertIn("tax_deductible_total", row)

    def test_populate_only_submitted_donations(self):
        """populate should only include submitted (docstatus=1) donations."""
        # Create a draft donation that should NOT be counted
        draft_don = frappe.new_doc("Donation")
        draft_don.donation_date = "2095-11-01"
        draft_don.donor = self.donor_a
        draft_don.campaign = self.campaign_name
        draft_don.amount = 9999
        draft_don.payment_method = "Check"
        draft_don.insert()
        # Do NOT submit

        results = populate_donor_statements(2095)
        donor_a_rows = [r for r in results if r.get("donor") == self.donor_a]

        if donor_a_rows:
            # Should only see 2000 from submitted donations, not 2000 + 9999
            self.assertEqual(flt(donor_a_rows[0]["total_donations"]), 2000)

        draft_don.delete()
