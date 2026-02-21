"""
Seed data generator for United Way Frappe app.

Usage:
    bench --site uw.localhost execute united_way.seed.run

Creates realistic sample data for demonstration and testing.
"""
import frappe
from frappe.utils import add_days, nowdate, getdate
import random


def run():
    """Main entry point for seeding data."""
    frappe.flags.ignore_permissions = True

    print("Seeding United Way demo data...")

    agencies = create_organizations()
    contacts = create_contacts(agencies)
    campaigns = create_campaigns()
    pledges = create_pledges(contacts, campaigns, agencies)
    create_donations(pledges)

    frappe.db.commit()
    frappe.flags.ignore_permissions = False
    print("Seed data complete!")


def create_organizations():
    """Create member agencies and corporate donors."""
    agencies_data = [
        {"name": "Big Brothers Big Sisters", "code": "BBBS", "focus": ["Youth Development"]},
        {"name": "Meals on Wheels", "code": "MOW", "focus": ["Senior Services", "Basic Needs"]},
        {"name": "Habitat for Humanity", "code": "HFH", "focus": ["Basic Needs", "Income/Financial Stability"]},
        {"name": "Boys & Girls Club", "code": "BGC", "focus": ["Youth Development", "Education"]},
        {"name": "American Red Cross - Local Chapter", "code": "ARC", "focus": ["Disaster Relief", "Health"]},
        {"name": "Salvation Army - Metro", "code": "SAM", "focus": ["Basic Needs"]},
        {"name": "Family Services Center", "code": "FSC", "focus": ["Health", "Basic Needs"]},
        {"name": "Literacy Council", "code": "LIT", "focus": ["Education"]},
        {"name": "Mental Health Alliance", "code": "MHA", "focus": ["Health"]},
        {"name": "Community Food Bank", "code": "CFB", "focus": ["Basic Needs"]},
    ]

    agencies = []
    for a in agencies_data:
        if not frappe.db.exists("Organization", a["name"]):
            org = frappe.get_doc({
                "doctype": "Organization",
                "organization_name": a["name"],
                "organization_type": "Member Agency",
                "status": "Active",
                "agency_code": a["code"],
                "focus_areas": ",".join(a["focus"]),
                "city": "Metro City",
                "state": "TX",
                "certification_status": "Certified",
                "date_joined": "2015-01-01",
            })
            org.insert()
            agencies.append(org)
            print(f"  Created agency: {a['name']}")

    # Corporate donors
    corporates_data = [
        {"name": "Acme Corporation", "employees": 5000, "match": True, "ratio": 1.0, "cap": 50000},
        {"name": "Metro Bank & Trust", "employees": 2000, "match": True, "ratio": 0.5, "cap": 25000},
        {"name": "Southwest Energy", "employees": 8000, "match": True, "ratio": 1.0, "cap": 100000},
        {"name": "TechForward Solutions", "employees": 500, "match": False, "ratio": 0, "cap": 0},
        {"name": "Regional Healthcare System", "employees": 12000, "match": True, "ratio": 0.5, "cap": 75000},
    ]

    corporates = []
    for c in corporates_data:
        if not frappe.db.exists("Organization", c["name"]):
            org = frappe.get_doc({
                "doctype": "Organization",
                "organization_name": c["name"],
                "organization_type": "Corporate Donor",
                "status": "Active",
                "employee_count": c["employees"],
                "workplace_campaign": 1,
                "corporate_match": 1 if c["match"] else 0,
                "match_ratio": c["ratio"],
                "match_cap": c["cap"],
                "city": "Metro City",
                "state": "TX",
            })
            org.insert()
            corporates.append(org)
            print(f"  Created corporate: {c['name']}")

    return agencies


def create_contacts(agencies):
    """Create individual donor contacts."""
    contacts_data = [
        {"first": "Sarah", "last": "Johnson", "type": "Individual Donor", "org": "Acme Corporation", "title": "VP Marketing"},
        {"first": "Michael", "last": "Chen", "type": "Individual Donor", "org": "Metro Bank & Trust", "title": "Branch Manager"},
        {"first": "Patricia", "last": "Williams", "type": "Individual Donor", "org": "Southwest Energy", "title": "Engineer"},
        {"first": "Robert", "last": "Garcia", "type": "Individual Donor", "org": "TechForward Solutions", "title": "Developer"},
        {"first": "Jennifer", "last": "Martinez", "type": "Individual Donor", "org": "Regional Healthcare System", "title": "Nurse Manager"},
        {"first": "David", "last": "Brown", "type": "Individual Donor", "org": "Acme Corporation", "title": "Sales Director"},
        {"first": "Lisa", "last": "Anderson", "type": "Individual Donor", "org": None, "title": None},
        {"first": "James", "last": "Wilson", "type": "Individual Donor", "org": None, "title": None},
        {"first": "Maria", "last": "Rodriguez", "type": "Corporate Contact", "org": "Southwest Energy", "title": "HR Director"},
        {"first": "Thomas", "last": "Taylor", "type": "Corporate Contact", "org": "Acme Corporation", "title": "CSR Manager"},
        {"first": "Karen", "last": "Davis", "type": "Agency Staff", "org": None, "title": "Executive Director"},
        {"first": "John", "last": "Miller", "type": "Campaign Coordinator", "org": "Metro Bank & Trust", "title": "Campaign Chair"},
        {"first": "Amanda", "last": "Thompson", "type": "Individual Donor", "org": "Regional Healthcare System", "title": "Physician"},
        {"first": "Kevin", "last": "White", "type": "Individual Donor", "org": "Southwest Energy", "title": "Supervisor"},
        {"first": "Emily", "last": "Clark", "type": "Individual Donor", "org": None, "title": "Retired Teacher"},
        {"first": "Richard", "last": "Moore", "type": "Board Member", "org": None, "title": "Attorney"},
        {"first": "Susan", "last": "Hall", "type": "Individual Donor", "org": "TechForward Solutions", "title": "CTO"},
        {"first": "Daniel", "last": "Lee", "type": "Individual Donor", "org": "Acme Corporation", "title": "Analyst"},
        {"first": "Nancy", "last": "Walker", "type": "Volunteer", "org": None, "title": None},
        {"first": "Christopher", "last": "Young", "type": "Individual Donor", "org": "Metro Bank & Trust", "title": "Loan Officer"},
    ]

    contacts = []
    for c in contacts_data:
        full_name = f"{c['first']} {c['last']}"
        existing = frappe.db.exists("Contact", {"full_name": full_name})
        if not existing:
            doc = frappe.get_doc({
                "doctype": "Contact",
                "first_name": c["first"],
                "last_name": c["last"],
                "contact_type": c["type"],
                "organization": c["org"],
                "title": c["title"],
                "email": f"{c['first'].lower()}.{c['last'].lower()}@example.com",
                "status": "Active",
                "donor_since": add_days(nowdate(), -random.randint(365, 2000)),
                "city": "Metro City",
                "state": "TX",
            })
            doc.insert()
            contacts.append(doc)
            print(f"  Created contact: {full_name}")
        else:
            contacts.append(frappe.get_doc("Contact", existing))

    return contacts


def create_campaigns():
    """Create sample campaigns."""
    campaigns_data = [
        {
            "name": "2025 Annual Campaign",
            "type": "Annual Campaign",
            "year": 2025,
            "goal": 2500000,
            "start": "2025-01-15",
            "end": "2025-12-31",
            "status": "Active",
        },
        {
            "name": "2025 Acme Workplace Campaign",
            "type": "Workplace Campaign",
            "year": 2025,
            "goal": 250000,
            "start": "2025-09-01",
            "end": "2025-11-30",
            "status": "Active",
        },
        {
            "name": "2024 Annual Campaign",
            "type": "Annual Campaign",
            "year": 2024,
            "goal": 2200000,
            "start": "2024-01-15",
            "end": "2024-12-31",
            "status": "Closed",
        },
    ]

    campaigns = []
    for c in campaigns_data:
        if not frappe.db.exists("Campaign", {"campaign_name": c["name"]}):
            doc = frappe.get_doc({
                "doctype": "Campaign",
                "campaign_name": c["name"],
                "campaign_type": c["type"],
                "campaign_year": c["year"],
                "fundraising_goal": c["goal"],
                "start_date": c["start"],
                "end_date": c["end"],
                "status": c["status"],
            })
            doc.insert()
            if c["status"] in ["Active", "Closed"]:
                doc.submit()
            campaigns.append(doc)
            print(f"  Created campaign: {c['name']}")
        else:
            campaigns.append(
                frappe.get_doc("Campaign", {"campaign_name": c["name"]})
            )

    return campaigns


def create_pledges(contacts, campaigns, agencies):
    """Create sample pledges with allocations."""
    donor_contacts = [c for c in contacts if c.contact_type == "Individual Donor"]
    active_campaigns = [c for c in campaigns if c.docstatus == 1]

    if not active_campaigns:
        print("  No submitted campaigns found, skipping pledges.")
        return []

    pledges = []
    pledge_amounts = [100, 250, 500, 750, 1000, 1500, 2000, 2500, 5000, 10000]

    for donor in donor_contacts:
        campaign = random.choice(active_campaigns)
        amount = random.choice(pledge_amounts)

        # Generate random allocations that sum to 100%
        num_allocations = random.randint(1, min(3, len(agencies)))
        selected_agencies = random.sample(agencies, num_allocations)

        if num_allocations == 1:
            percentages = [100]
        elif num_allocations == 2:
            split = random.choice([30, 40, 50, 60, 70])
            percentages = [split, 100 - split]
        else:
            p1 = random.choice([30, 40, 50])
            p2 = random.choice([20, 25, 30])
            percentages = [p1, p2, 100 - p1 - p2]

        allocations = []
        for i, agency in enumerate(selected_agencies):
            allocations.append({
                "agency": agency.name,
                "designation_type": "Donor Designated",
                "percentage": percentages[i],
            })

        payment_methods = ["Payroll Deduction", "One-Time Gift", "Credit Card", "Check"]

        try:
            pledge = frappe.get_doc({
                "doctype": "Pledge",
                "campaign": campaign.name,
                "donor": donor.name,
                "pledge_date": add_days(campaign.start_date, random.randint(0, 60)),
                "pledge_amount": amount,
                "payment_method": random.choice(payment_methods),
                "payment_frequency": "One-Time" if amount < 1000 else random.choice(["One-Time", "Monthly"]),
                "allocations": allocations,
            })
            pledge.insert()
            pledge.submit()
            pledges.append(pledge)
            print(f"  Created pledge: {donor.full_name} -> ${amount:,} ({campaign.campaign_name})")
        except Exception as e:
            print(f"  Skipped pledge for {donor.full_name}: {e}")

    return pledges


def create_donations(pledges):
    """Create sample donations against pledges."""
    for pledge in pledges:
        # 70% chance of having at least one donation
        if random.random() > 0.3:
            # Full payment or partial
            if random.random() > 0.3:
                # Full payment
                amount = pledge.pledge_amount
            else:
                # Partial payment
                amount = round(pledge.pledge_amount * random.choice([0.25, 0.5, 0.75]), 2)

            try:
                donation = frappe.get_doc({
                    "doctype": "Donation",
                    "donation_date": add_days(pledge.pledge_date, random.randint(1, 45)),
                    "donor": pledge.donor,
                    "campaign": pledge.campaign,
                    "pledge": pledge.name,
                    "amount": amount,
                    "payment_method": pledge.payment_method or "Check",
                    "reference_number": f"REF-{random.randint(10000, 99999)}",
                    "tax_deductible": 1,
                    "tax_deductible_amount": amount,
                })
                donation.insert()
                donation.submit()
                print(f"  Created donation: ${amount:,.2f} for {pledge.name}")
            except Exception as e:
                print(f"  Skipped donation for {pledge.name}: {e}")

    frappe.db.commit()
