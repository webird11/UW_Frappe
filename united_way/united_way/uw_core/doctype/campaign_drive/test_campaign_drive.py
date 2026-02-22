import frappe
import unittest
from frappe.utils import flt
from united_way.uw_core.doctype.campaign_drive.campaign_drive import refresh_drive_totals


class TestCampaignDrive(unittest.TestCase):
    """Tests for Campaign Drive date validation, drive totals, participation, and goal tracking."""

    @classmethod
    def setUpClass(cls):
        """Create test fixtures: org, agency, donors, campaign, pledges."""
        frappe.flags.ignore_permissions = True

        # Member Agency for pledge allocations
        if not frappe.db.exists("Organization", "_Test Agency Drive"):
            frappe.get_doc({
                "doctype": "Organization",
                "organization_name": "_Test Agency Drive",
                "organization_type": "Member Agency",
                "status": "Active",
                "agency_code": "_TDRV",
            }).insert()

        # Corporate employer (the org that runs the drive)
        if not frappe.db.exists("Organization", "_Test Corp Drive"):
            frappe.get_doc({
                "doctype": "Organization",
                "organization_name": "_Test Corp Drive",
                "organization_type": "Corporate Donor",
                "status": "Active",
            }).insert()

        # Donor A (linked to the corp)
        if not frappe.db.exists("Contact", {"first_name": "_TestDrv", "last_name": "DonorA"}):
            frappe.get_doc({
                "doctype": "Contact",
                "first_name": "_TestDrv",
                "last_name": "DonorA",
                "contact_type": "Individual Donor",
                "organization": "_Test Corp Drive",
                "email": "_testdrv_a@example.com",
            }).insert()

        cls.donor_a = frappe.db.get_value(
            "Contact", {"first_name": "_TestDrv", "last_name": "DonorA"}, "name"
        )

        # Donor B (linked to the corp)
        if not frappe.db.exists("Contact", {"first_name": "_TestDrv", "last_name": "DonorB"}):
            frappe.get_doc({
                "doctype": "Contact",
                "first_name": "_TestDrv",
                "last_name": "DonorB",
                "contact_type": "Individual Donor",
                "organization": "_Test Corp Drive",
                "email": "_testdrv_b@example.com",
            }).insert()

        cls.donor_b = frappe.db.get_value(
            "Contact", {"first_name": "_TestDrv", "last_name": "DonorB"}, "name"
        )

        # Campaign
        if not frappe.db.exists("Campaign", {"campaign_name": "_Test Drive Campaign"}):
            camp = frappe.get_doc({
                "doctype": "Campaign",
                "campaign_name": "_Test Drive Campaign",
                "campaign_type": "Annual Campaign",
                "campaign_year": 2097,
                "status": "Active",
                "start_date": "2097-01-01",
                "end_date": "2097-12-31",
                "fundraising_goal": 100000,
            })
            camp.insert()
            camp.submit()

        cls.campaign_name = frappe.db.get_value(
            "Campaign", {"campaign_name": "_Test Drive Campaign"}, "name"
        )

        # Create submitted pledges from both donors for this org
        # Pledge A: $3000
        pledge_a = frappe.new_doc("Pledge")
        pledge_a.campaign = cls.campaign_name
        pledge_a.donor = cls.donor_a
        pledge_a.donor_organization = "_Test Corp Drive"
        pledge_a.pledge_amount = 3000
        pledge_a.pledge_date = "2097-06-01"
        pledge_a.append("allocations", {
            "agency": "_Test Agency Drive",
            "designation_type": "Donor Designated",
            "percentage": 100,
        })
        pledge_a.insert()
        pledge_a.submit()
        cls.pledge_a = pledge_a.name

        # Pledge B: $7000
        pledge_b = frappe.new_doc("Pledge")
        pledge_b.campaign = cls.campaign_name
        pledge_b.donor = cls.donor_b
        pledge_b.donor_organization = "_Test Corp Drive"
        pledge_b.pledge_amount = 7000
        pledge_b.pledge_date = "2097-06-01"
        pledge_b.append("allocations", {
            "agency": "_Test Agency Drive",
            "designation_type": "Donor Designated",
            "percentage": 100,
        })
        pledge_b.insert()
        pledge_b.submit()
        cls.pledge_b = pledge_b.name

    def _make_drive(self, goal_amount=20000, employee_count=100):
        """Helper to create a campaign drive."""
        drive = frappe.new_doc("Campaign Drive")
        drive.organization = "_Test Corp Drive"
        drive.campaign = self.campaign_name
        drive.drive_start_date = "2097-05-01"
        drive.drive_end_date = "2097-06-30"
        drive.goal_amount = goal_amount
        drive.employee_count = employee_count
        drive.status = "Active"
        drive.insert()
        return drive

    # --- Date Validation Tests ---

    def test_end_before_start_rejected(self):
        """Drive end date before start date should raise an error."""
        drive = frappe.new_doc("Campaign Drive")
        drive.organization = "_Test Corp Drive"
        drive.campaign = self.campaign_name
        drive.drive_start_date = "2097-06-30"
        drive.drive_end_date = "2097-05-01"
        drive.status = "Planning"

        with self.assertRaises(frappe.ValidationError):
            drive.insert()

    def test_same_start_and_end_allowed(self):
        """Same start and end date should be allowed."""
        drive = frappe.new_doc("Campaign Drive")
        drive.organization = "_Test Corp Drive"
        drive.campaign = self.campaign_name
        drive.drive_start_date = "2097-06-15"
        drive.drive_end_date = "2097-06-15"
        drive.status = "Planning"
        drive.insert()
        self.assertTrue(drive.name)
        drive.delete()

    def test_no_dates_allowed(self):
        """Drive with no start/end dates should save without error."""
        drive = frappe.new_doc("Campaign Drive")
        drive.organization = "_Test Corp Drive"
        drive.campaign = self.campaign_name
        drive.status = "Planning"
        drive.insert()
        self.assertTrue(drive.name)
        drive.delete()

    # --- Update Drive Totals Tests ---

    def test_update_drive_totals_calculates_pledges(self):
        """update_drive_totals should query submitted pledges for campaign+organization."""
        drive = self._make_drive(goal_amount=20000, employee_count=100)
        drive.update_drive_totals()
        drive.reload()

        # Two pledges: $3000 + $7000 = $10000
        self.assertEqual(flt(drive.total_pledged), 10000)
        self.assertEqual(drive.pledge_count, 2)

        drive.delete()

    def test_participation_rate_calculated(self):
        """participation_rate should be pledge_count / employee_count * 100."""
        drive = self._make_drive(goal_amount=20000, employee_count=100)
        drive.update_drive_totals()
        drive.reload()

        # 2 pledges / 100 employees = 2%
        self.assertEqual(flt(drive.participation_rate), 2.0)

        drive.delete()

    def test_percent_of_goal_calculated(self):
        """percent_of_goal should be total_pledged / goal_amount * 100."""
        drive = self._make_drive(goal_amount=20000, employee_count=100)
        drive.update_drive_totals()
        drive.reload()

        # $10000 / $20000 = 50%
        self.assertEqual(flt(drive.percent_of_goal), 50.0)

        drive.delete()

    # --- Zero Division Handling ---

    def test_zero_employee_count_no_error(self):
        """participation_rate should be 0 when employee_count is 0 (no division error)."""
        drive = self._make_drive(goal_amount=20000, employee_count=0)
        drive.update_drive_totals()
        drive.reload()

        self.assertEqual(flt(drive.participation_rate), 0)

        drive.delete()

    def test_zero_goal_amount_no_error(self):
        """percent_of_goal should be 0 when goal_amount is 0 (no division error)."""
        drive = self._make_drive(goal_amount=0, employee_count=100)
        drive.update_drive_totals()
        drive.reload()

        self.assertEqual(flt(drive.percent_of_goal), 0)

        drive.delete()

    def test_both_zero_no_error(self):
        """Both zero employee_count and goal_amount should not raise division errors."""
        drive = self._make_drive(goal_amount=0, employee_count=0)
        drive.update_drive_totals()
        drive.reload()

        self.assertEqual(flt(drive.participation_rate), 0)
        self.assertEqual(flt(drive.percent_of_goal), 0)

        drive.delete()

    # --- Refresh Drive Totals (Whitelist Function) Tests ---

    def test_refresh_drive_totals_returns_data(self):
        """refresh_drive_totals should return updated totals dict."""
        drive = self._make_drive(goal_amount=20000, employee_count=100)

        result = refresh_drive_totals(drive.name)

        self.assertIn("total_pledged", result)
        self.assertIn("pledge_count", result)
        self.assertIn("participation_rate", result)
        self.assertIn("percent_of_goal", result)
        self.assertEqual(flt(result["total_pledged"]), 10000)
        self.assertEqual(result["pledge_count"], 2)
        self.assertEqual(flt(result["participation_rate"]), 2.0)
        self.assertEqual(flt(result["percent_of_goal"]), 50.0)

        drive.delete()

    def test_refresh_updates_saved_values(self):
        """refresh_drive_totals should persist the updated values to the database."""
        drive = self._make_drive(goal_amount=20000, employee_count=100)

        refresh_drive_totals(drive.name)
        drive.reload()

        self.assertEqual(flt(drive.total_pledged), 10000)
        self.assertEqual(drive.pledge_count, 2)

        drive.delete()
