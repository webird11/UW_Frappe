import frappe
import unittest
from frappe.utils import flt
from united_way.uw_core.doctype.pledge_writeoff.pledge_writeoff import generate_payment_schedule


class TestPledgeWriteoff(unittest.TestCase):
    """Tests for Pledge Writeoff validation, on_submit status changes, and payment schedule generation."""

    @classmethod
    def setUpClass(cls):
        """Create test fixtures: agency, donor, campaign, pledges."""
        frappe.flags.ignore_permissions = True

        # Member Agency
        if not frappe.db.exists("Organization", "_Test Agency WriteOff"):
            frappe.get_doc({
                "doctype": "Organization",
                "organization_name": "_Test Agency WriteOff",
                "organization_type": "Member Agency",
                "status": "Active",
                "agency_code": "_TWO",
            }).insert()

        # Donor
        if not frappe.db.exists("Contact", {"first_name": "_TestWO", "last_name": "Donor"}):
            frappe.get_doc({
                "doctype": "Contact",
                "first_name": "_TestWO",
                "last_name": "Donor",
                "contact_type": "Individual Donor",
                "email": "_testwo@example.com",
            }).insert()

        cls.donor_name = frappe.db.get_value(
            "Contact", {"first_name": "_TestWO", "last_name": "Donor"}, "name"
        )

        # Campaign
        if not frappe.db.exists("Campaign", {"campaign_name": "_Test WriteOff Campaign"}):
            camp = frappe.get_doc({
                "doctype": "Campaign",
                "campaign_name": "_Test WriteOff Campaign",
                "campaign_type": "Annual Campaign",
                "campaign_year": 2096,
                "status": "Active",
                "start_date": "2096-01-01",
                "end_date": "2096-12-31",
                "fundraising_goal": 50000,
            })
            camp.insert()
            camp.submit()

        cls.campaign_name = frappe.db.get_value(
            "Campaign", {"campaign_name": "_Test WriteOff Campaign"}, "name"
        )

    def _make_pledge(self, amount=2000, submit=True, with_schedule=False, frequency="One-Time"):
        """Helper to create a submitted pledge for writeoff testing."""
        pledge = frappe.new_doc("Pledge")
        pledge.campaign = self.campaign_name
        pledge.donor = self.donor_name
        pledge.pledge_amount = amount
        pledge.pledge_date = "2096-06-01"
        pledge.payment_frequency = frequency
        pledge.append("allocations", {
            "agency": "_Test Agency WriteOff",
            "designation_type": "Donor Designated",
            "percentage": 100,
        })

        if with_schedule:
            # Add manual payment schedule entries for testing
            pledge.append("payment_schedule", {
                "due_date": "2096-07-01",
                "expected_amount": amount / 2,
                "status": "Pending",
            })
            pledge.append("payment_schedule", {
                "due_date": "2096-08-01",
                "expected_amount": amount / 2,
                "status": "Pending",
            })

        pledge.insert()
        if submit:
            pledge.submit()
        return pledge

    def _make_writeoff(self, pledge_name, writeoff_amount, submit=False):
        """Helper to create a writeoff for a pledge."""
        pledge = frappe.get_doc("Pledge", pledge_name)

        wo = frappe.new_doc("Pledge Writeoff")
        wo.pledge = pledge_name
        wo.pledge_amount = pledge.pledge_amount
        wo.total_collected = pledge.total_collected
        wo.outstanding_balance = pledge.outstanding_balance
        wo.writeoff_date = "2096-09-01"
        wo.writeoff_amount = writeoff_amount
        wo.reason = "Donor Unable to Pay"
        wo.insert()
        if submit:
            wo.submit()
        return wo

    # --- Validation: Pledge Must Be Submitted ---

    def test_draft_pledge_rejected(self):
        """Writeoff linked to a draft (not submitted) pledge should raise an error."""
        pledge = self._make_pledge(submit=False)

        wo = frappe.new_doc("Pledge Writeoff")
        wo.pledge = pledge.name
        wo.pledge_amount = pledge.pledge_amount
        wo.total_collected = 0
        wo.outstanding_balance = pledge.pledge_amount
        wo.writeoff_date = "2096-09-01"
        wo.writeoff_amount = 1000
        wo.reason = "Donor Unable to Pay"

        with self.assertRaises(frappe.ValidationError):
            wo.insert()

        pledge.delete()

    # --- Validation: Writeoff Amount ---

    def test_zero_writeoff_amount_rejected(self):
        """Writeoff amount of zero should raise an error."""
        pledge = self._make_pledge()

        wo = frappe.new_doc("Pledge Writeoff")
        wo.pledge = pledge.name
        wo.pledge_amount = pledge.pledge_amount
        wo.total_collected = 0
        wo.outstanding_balance = pledge.outstanding_balance
        wo.writeoff_date = "2096-09-01"
        wo.writeoff_amount = 0
        wo.reason = "Donor Unable to Pay"

        with self.assertRaises(frappe.ValidationError):
            wo.insert()

        pledge.cancel()

    def test_negative_writeoff_amount_rejected(self):
        """Negative writeoff amount should raise an error."""
        pledge = self._make_pledge()

        wo = frappe.new_doc("Pledge Writeoff")
        wo.pledge = pledge.name
        wo.pledge_amount = pledge.pledge_amount
        wo.total_collected = 0
        wo.outstanding_balance = pledge.outstanding_balance
        wo.writeoff_date = "2096-09-01"
        wo.writeoff_amount = -500
        wo.reason = "Donor Unable to Pay"

        with self.assertRaises(frappe.ValidationError):
            wo.insert()

        pledge.cancel()

    def test_writeoff_exceeding_outstanding_rejected(self):
        """Writeoff amount exceeding outstanding balance should raise an error."""
        pledge = self._make_pledge(amount=1000)

        wo = frappe.new_doc("Pledge Writeoff")
        wo.pledge = pledge.name
        wo.pledge_amount = pledge.pledge_amount
        wo.total_collected = 0
        wo.outstanding_balance = pledge.outstanding_balance
        wo.writeoff_date = "2096-09-01"
        wo.writeoff_amount = 1500  # More than outstanding
        wo.reason = "Donor Unable to Pay"

        with self.assertRaises(frappe.ValidationError):
            wo.insert()

        pledge.cancel()

    def test_valid_writeoff_saves(self):
        """Writeoff with valid amount should save without error."""
        pledge = self._make_pledge(amount=2000)
        wo = self._make_writeoff(pledge.name, 1000)
        self.assertTrue(wo.name)
        wo.delete()
        pledge.cancel()

    # --- On Submit: Collection Status Changes ---

    def test_full_writeoff_sets_written_off_status(self):
        """Full writeoff (amount = outstanding) should set pledge to 'Written Off'."""
        pledge = self._make_pledge(amount=2000)
        outstanding = flt(pledge.outstanding_balance)

        wo = self._make_writeoff(pledge.name, outstanding, submit=True)

        pledge.reload()
        self.assertEqual(pledge.collection_status, "Written Off")

        wo.cancel()
        pledge.cancel()

    def test_partial_writeoff_sets_partially_collected(self):
        """Partial writeoff (amount < outstanding) should set pledge to 'Partially Collected'."""
        pledge = self._make_pledge(amount=2000)
        partial_amount = flt(pledge.outstanding_balance) / 2

        wo = self._make_writeoff(pledge.name, partial_amount, submit=True)

        pledge.reload()
        self.assertEqual(pledge.collection_status, "Partially Collected")

        wo.cancel()
        pledge.cancel()

    def test_on_submit_sets_approved_by(self):
        """On submit, approved_by should be set to the current user."""
        pledge = self._make_pledge(amount=2000)
        wo = self._make_writeoff(pledge.name, 1000, submit=True)

        wo.reload()
        self.assertEqual(wo.approved_by, frappe.session.user)

        wo.cancel()
        pledge.cancel()

    # --- On Submit: Payment Schedule Entries ---

    def test_pending_schedule_entries_written_off(self):
        """Pending payment schedule entries should be marked as 'Written Off'."""
        pledge = self._make_pledge(amount=2000, with_schedule=True)

        # Verify schedule entries exist and are Pending
        pledge.reload()
        pending_count = sum(1 for e in pledge.payment_schedule if e.status == "Pending")
        self.assertGreater(pending_count, 0)

        wo = self._make_writeoff(pledge.name, flt(pledge.outstanding_balance), submit=True)

        pledge.reload()
        for entry in pledge.payment_schedule:
            if entry.status != "Paid":
                self.assertEqual(entry.status, "Written Off")

        wo.cancel()
        pledge.cancel()

    # --- On Cancel: Pledge Recalculation ---

    def test_on_cancel_recalculates_pledge(self):
        """Cancelling a writeoff should trigger pledge collection field recalculation."""
        pledge = self._make_pledge(amount=2000)

        wo = self._make_writeoff(pledge.name, flt(pledge.outstanding_balance), submit=True)

        pledge.reload()
        self.assertEqual(pledge.collection_status, "Written Off")

        wo.cancel()
        pledge.reload()

        # After cancel, pledge should be recalculated. Since no donations exist,
        # total_collected should be 0 and status should be "Not Started"
        self.assertEqual(flt(pledge.total_collected), 0)
        self.assertEqual(pledge.collection_status, "Not Started")

        pledge.cancel()

    # --- Generate Payment Schedule (Whitelist Function) Tests ---

    def test_one_time_schedule(self):
        """One-Time frequency should return a single entry."""
        pledge = self._make_pledge(amount=1200, frequency="One-Time")

        schedule = generate_payment_schedule(pledge.name)
        self.assertEqual(len(schedule), 1)
        self.assertEqual(flt(schedule[0]["expected_amount"]), 1200)
        self.assertEqual(schedule[0]["due_date"], "2096-06-01")

        pledge.cancel()

    def test_monthly_schedule(self):
        """Monthly frequency should return 12 entries."""
        pledge = self._make_pledge(amount=1200, frequency="Monthly")

        schedule = generate_payment_schedule(pledge.name)
        self.assertEqual(len(schedule), 12)

        per_month = flt(1200 / 12, 2)
        for entry in schedule:
            self.assertEqual(flt(entry["expected_amount"]), per_month)
            self.assertTrue(entry["due_date"])

        pledge.cancel()

    def test_weekly_schedule(self):
        """Weekly frequency should return 52 entries."""
        pledge = self._make_pledge(amount=5200, frequency="Weekly")

        schedule = generate_payment_schedule(pledge.name)
        self.assertEqual(len(schedule), 52)

        per_week = flt(5200 / 52, 2)
        for entry in schedule:
            self.assertEqual(flt(entry["expected_amount"]), per_week)

        pledge.cancel()

    def test_quarterly_schedule(self):
        """Quarterly frequency should return 4 entries."""
        pledge = self._make_pledge(amount=4000, frequency="Quarterly")

        schedule = generate_payment_schedule(pledge.name)
        self.assertEqual(len(schedule), 4)

        per_quarter = flt(4000 / 4, 2)
        for entry in schedule:
            self.assertEqual(flt(entry["expected_amount"]), per_quarter)

        pledge.cancel()

    def test_annually_schedule(self):
        """Annual frequency should return 1 entry."""
        pledge = self._make_pledge(amount=6000, frequency="Annually")

        schedule = generate_payment_schedule(pledge.name)
        self.assertEqual(len(schedule), 1)
        self.assertEqual(flt(schedule[0]["expected_amount"]), 6000)

        pledge.cancel()

    def test_biweekly_schedule(self):
        """Bi-Weekly frequency should return 26 entries."""
        pledge = self._make_pledge(amount=2600, frequency="Bi-Weekly")

        schedule = generate_payment_schedule(pledge.name)
        self.assertEqual(len(schedule), 26)

        per_period = flt(2600 / 26, 2)
        for entry in schedule:
            self.assertEqual(flt(entry["expected_amount"]), per_period)

        pledge.cancel()
