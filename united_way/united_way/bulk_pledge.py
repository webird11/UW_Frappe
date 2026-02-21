import csv
import io
import frappe
from frappe.utils import flt, getdate


@frappe.whitelist()
def process_bulk_pledges(campaign, csv_data):
    """Process a CSV of pledges for a single campaign.

    CSV format: donor,pledge_amount,payment_method,payment_frequency,agency,designation_type,percentage
    For multi-allocation pledges, repeat the donor row with different agency/percentage.

    Args:
        campaign: Campaign name (must exist, must be active)
        csv_data: CSV string content

    Returns:
        dict with created, errors counts and details
    """
    # Validate campaign exists and is active
    camp = frappe.get_doc("Campaign", campaign)
    if camp.docstatus != 1:
        frappe.throw(f"Campaign '{campaign}' is not submitted.")
    if camp.status not in ("Active", "Planning"):
        frappe.throw(f"Campaign '{campaign}' status is '{camp.status}' — must be Active or Planning.")

    reader = csv.DictReader(io.StringIO(csv_data))

    # Group rows by donor to handle multi-allocation pledges
    pledge_groups = []
    current_group = None

    for row in reader:
        donor = (row.get("donor") or "").strip()
        amount = (row.get("pledge_amount") or "").strip()

        if donor and amount:
            # New pledge
            if current_group:
                pledge_groups.append(current_group)
            current_group = {
                "donor": donor,
                "pledge_amount": flt(amount),
                "payment_method": (row.get("payment_method") or "").strip(),
                "payment_frequency": (row.get("payment_frequency") or "One-Time").strip(),
                "allocations": [],
            }

        # Add allocation row (applies to current group)
        agency = (row.get("agency") or "").strip()
        pct = (row.get("percentage") or "").strip()
        if current_group and agency and pct:
            current_group["allocations"].append({
                "agency": agency,
                "designation_type": (row.get("designation_type") or "Undesignated").strip(),
                "percentage": flt(pct),
            })

    if current_group:
        pledge_groups.append(current_group)

    created = 0
    errors = []

    for i, group in enumerate(pledge_groups, start=1):
        try:
            # Validate donor exists
            if not frappe.db.exists("Contact", group["donor"]):
                errors.append(f"Row {i}: Donor '{group['donor']}' not found")
                continue

            # Validate allocations total 100%
            total_pct = sum(a["percentage"] for a in group["allocations"])
            if abs(total_pct - 100) > 0.01:
                errors.append(
                    f"Row {i}: Donor '{group['donor']}' allocations total {total_pct}%, must be 100%"
                )
                continue

            # Validate agencies exist
            bad_agencies = [
                a["agency"] for a in group["allocations"]
                if not frappe.db.exists("Organization", a["agency"])
            ]
            if bad_agencies:
                errors.append(f"Row {i}: Unknown agencies: {', '.join(bad_agencies)}")
                continue

            pledge = frappe.new_doc("Pledge")
            pledge.campaign = campaign
            pledge.donor = group["donor"]
            pledge.pledge_date = frappe.utils.nowdate()
            pledge.pledge_amount = group["pledge_amount"]
            pledge.payment_method = group["payment_method"] or None
            pledge.payment_frequency = group["payment_frequency"]

            for alloc in group["allocations"]:
                pledge.append("allocations", {
                    "agency": alloc["agency"],
                    "designation_type": alloc["designation_type"],
                    "percentage": alloc["percentage"],
                })

            pledge.insert(ignore_permissions=True)
            pledge.submit()
            created += 1

        except Exception as e:
            errors.append(f"Row {i}: Donor '{group.get('donor', '?')}' — {str(e)}")

    frappe.db.commit()

    return {
        "created": created,
        "total": len(pledge_groups),
        "errors": errors,
    }
