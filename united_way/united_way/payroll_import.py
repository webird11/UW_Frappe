import frappe
from frappe.utils import flt, nowdate, cint
import csv
import io
import json


@frappe.whitelist()
def parse_payroll_file(file_content, file_format="csv", organization=None, campaign=None):
    """Parse a payroll deduction file and return structured data.

    Args:
        file_content: The raw file content (string)
        file_format: "csv", "adp_fixed", or "tab_delimited"
        organization: The employer Organization name
        campaign: The Campaign to associate with

    Returns:
        dict with:
            - rows: list of parsed row dicts {employee_id, employee_name, amount, department}
            - summary: {total_rows, total_amount, unique_employees}
            - errors: list of error messages for unparseable rows
    """
    if not file_content or not file_content.strip():
        frappe.throw("File content is empty.")

    parsers = {
        "csv": _parse_csv,
        "adp_fixed": _parse_adp_fixed,
        "tab_delimited": _parse_tab_delimited,
    }

    parser = parsers.get(file_format)
    if not parser:
        frappe.throw(f"Unsupported file format: {file_format}. Supported: csv, adp_fixed, tab_delimited")

    rows, errors = parser(file_content)

    # Calculate summary
    total_amount = flt(sum(flt(r.get("amount", 0)) for r in rows))
    unique_employees = len(set(r.get("employee_id", "") for r in rows if r.get("employee_id")))

    return {
        "rows": rows,
        "summary": {
            "total_rows": len(rows),
            "total_amount": total_amount,
            "unique_employees": unique_employees,
        },
        "errors": errors,
    }


def _parse_csv(file_content):
    """Parse CSV format payroll file.

    Expected columns: employee_id, employee_name, deduction_amount, deduction_code, department
    """
    rows = []
    errors = []

    # Try UTF-8 first, fall back to Latin-1
    try:
        content = file_content if isinstance(file_content, str) else file_content.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        try:
            content = file_content.decode("latin-1")
        except AttributeError:
            content = str(file_content)

    reader = csv.reader(io.StringIO(content))

    header_skipped = False
    for line_num, row in enumerate(reader, start=1):
        # Skip blank lines
        if not row or all(cell.strip() == "" for cell in row):
            continue

        # Skip header row: detect if first column looks like a header
        if not header_skipped:
            first_cell = row[0].strip().lower()
            if first_cell in ("employee_id", "emp_id", "id", "employee id", "ssn", "employee"):
                header_skipped = True
                continue
            header_skipped = True  # Even if no header detected, don't skip again

        try:
            if len(row) < 3:
                errors.append(f"Row {line_num}: Expected at least 3 columns, got {len(row)}")
                continue

            employee_id = row[0].strip()
            employee_name = row[1].strip()
            amount_str = row[2].strip().replace("$", "").replace(",", "")
            amount = flt(amount_str)

            if amount <= 0:
                errors.append(f"Row {line_num}: Invalid or zero amount '{row[2].strip()}'")
                continue

            department = row[4].strip() if len(row) > 4 else ""
            deduction_code = row[3].strip() if len(row) > 3 else ""

            rows.append({
                "employee_id": employee_id,
                "employee_name": employee_name,
                "amount": amount,
                "department": department,
                "deduction_code": deduction_code,
                "source_line": line_num,
            })

        except Exception as e:
            errors.append(f"Row {line_num}: {str(e)}")

    return rows, errors


def _parse_adp_fixed(file_content):
    """Parse ADP fixed-width format.

    Columns 1-9:   Employee ID (SSN or ID)
    Columns 10-39:  Employee Name (Last, First)
    Columns 40-49:  Deduction Amount (right-justified, 2 decimal places)
    Columns 50-59:  Deduction Code (e.g., "UW" or "UNWAY")
    Columns 60-69:  Department Code
    """
    rows = []
    errors = []

    # Try UTF-8 first, fall back to Latin-1
    try:
        content = file_content if isinstance(file_content, str) else file_content.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        try:
            content = file_content.decode("latin-1")
        except AttributeError:
            content = str(file_content)

    lines = content.splitlines()

    for line_num, line in enumerate(lines, start=1):
        # Skip blank lines
        if not line.strip():
            continue

        # Lines shorter than minimum expected length (at least 49 chars for amount)
        if len(line) < 49:
            errors.append(f"Row {line_num}: Line too short ({len(line)} chars), expected at least 49")
            continue

        try:
            employee_id = line[0:9].strip()
            employee_name = line[9:39].strip()

            amount_str = line[39:49].strip().replace("$", "").replace(",", "")
            amount = flt(amount_str)

            deduction_code = line[49:59].strip() if len(line) > 49 else ""
            department = line[59:69].strip() if len(line) > 59 else ""

            if not employee_id and not employee_name:
                errors.append(f"Row {line_num}: Missing both employee ID and name")
                continue

            if amount <= 0:
                errors.append(f"Row {line_num}: Invalid or zero amount '{line[39:49].strip()}'")
                continue

            rows.append({
                "employee_id": employee_id,
                "employee_name": employee_name,
                "amount": amount,
                "department": department,
                "deduction_code": deduction_code,
                "source_line": line_num,
            })

        except Exception as e:
            errors.append(f"Row {line_num}: {str(e)}")

    return rows, errors


def _parse_tab_delimited(file_content):
    """Parse tab-delimited format.

    Same column layout as CSV but tab-separated.
    """
    rows = []
    errors = []

    # Try UTF-8 first, fall back to Latin-1
    try:
        content = file_content if isinstance(file_content, str) else file_content.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        try:
            content = file_content.decode("latin-1")
        except AttributeError:
            content = str(file_content)

    reader = csv.reader(io.StringIO(content), delimiter="\t")

    header_skipped = False
    for line_num, row in enumerate(reader, start=1):
        # Skip blank lines
        if not row or all(cell.strip() == "" for cell in row):
            continue

        # Skip header row
        if not header_skipped:
            first_cell = row[0].strip().lower()
            if first_cell in ("employee_id", "emp_id", "id", "employee id", "ssn", "employee"):
                header_skipped = True
                continue
            header_skipped = True

        try:
            if len(row) < 3:
                errors.append(f"Row {line_num}: Expected at least 3 columns, got {len(row)}")
                continue

            employee_id = row[0].strip()
            employee_name = row[1].strip()
            amount_str = row[2].strip().replace("$", "").replace(",", "")
            amount = flt(amount_str)

            if amount <= 0:
                errors.append(f"Row {line_num}: Invalid or zero amount '{row[2].strip()}'")
                continue

            department = row[4].strip() if len(row) > 4 else ""
            deduction_code = row[3].strip() if len(row) > 3 else ""

            rows.append({
                "employee_id": employee_id,
                "employee_name": employee_name,
                "amount": amount,
                "department": department,
                "deduction_code": deduction_code,
                "source_line": line_num,
            })

        except Exception as e:
            errors.append(f"Row {line_num}: {str(e)}")

    return rows, errors


@frappe.whitelist()
def match_employees_to_donors(rows, organization):
    """Try to match parsed employee records to existing Contact records.

    Matching strategy:
    1. Exact match on employee_id if Contact has an employee_id field
    2. Fuzzy match on name (last_name, first_name) within the organization
    3. Unmatched rows flagged for manual review

    Args:
        rows: list of parsed row dicts from parse_payroll_file
        organization: The employer Organization name to scope matching

    Returns:
        list of rows with added 'donor' field (Contact name or None)
        and 'match_status' field ('exact', 'name_match', 'unmatched')
    """
    if isinstance(rows, str):
        rows = json.loads(rows)

    # Build a lookup of contacts for this organization
    # Fetch all active contacts linked to this organization
    contacts = frappe.get_all(
        "Contact",
        filters={
            "organization": organization,
            "status": "Active",
        },
        fields=["name", "first_name", "last_name", "full_name"],
    )

    # Build lookup maps for name-based matching (case-insensitive)
    # Key: (last_name_lower, first_name_lower) -> Contact name
    name_lookup = {}
    # Key: full_name_lower -> Contact name
    full_name_lookup = {}

    for contact in contacts:
        first = (contact.get("first_name") or "").strip().lower()
        last = (contact.get("last_name") or "").strip().lower()
        full = (contact.get("full_name") or "").strip().lower()

        if last and first:
            name_lookup[(last, first)] = contact["name"]
        if full:
            full_name_lookup[full] = contact["name"]

    matched_rows = []

    for row in rows:
        employee_name = row.get("employee_name", "").strip()
        donor = None
        match_status = "unmatched"

        # Strategy 1: Check if Contact has employee_id field and try exact match
        # (Contact currently has no employee_id field, but we check dynamically
        # in case it is added later)
        employee_id = row.get("employee_id", "").strip()
        if employee_id:
            has_employee_id_field = "employee_id" in [
                f.fieldname for f in frappe.get_meta("Contact").fields
            ]
            if has_employee_id_field:
                match = frappe.get_all(
                    "Contact",
                    filters={
                        "employee_id": employee_id,
                        "organization": organization,
                        "status": "Active",
                    },
                    fields=["name"],
                    limit=1,
                )
                if match:
                    donor = match[0]["name"]
                    match_status = "exact"

        # Strategy 2: Name-based matching
        if not donor and employee_name:
            # Try "Last, First" format (common in ADP files)
            if "," in employee_name:
                parts = employee_name.split(",", 1)
                last_name = parts[0].strip().lower()
                first_name = parts[1].strip().lower()
            else:
                # Try "First Last" format
                name_parts = employee_name.split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0].strip().lower()
                    last_name = " ".join(name_parts[1:]).strip().lower()
                elif len(name_parts) == 1:
                    first_name = ""
                    last_name = name_parts[0].strip().lower()
                else:
                    first_name = ""
                    last_name = ""

            # Try exact (last, first) match
            if last_name and first_name and (last_name, first_name) in name_lookup:
                donor = name_lookup[(last_name, first_name)]
                match_status = "name_match"

            # Try full name match as fallback
            if not donor:
                full_lower = employee_name.strip().lower()
                if full_lower in full_name_lookup:
                    donor = full_name_lookup[full_lower]
                    match_status = "name_match"

                # Also try reversed "First Last" if original was "Last, First"
                if not donor and "," in employee_name:
                    reversed_name = f"{first_name} {last_name}"
                    if reversed_name in full_name_lookup:
                        donor = full_name_lookup[reversed_name]
                        match_status = "name_match"

        matched_row = dict(row)
        matched_row["donor"] = donor
        matched_row["match_status"] = match_status
        matched_rows.append(matched_row)

    return matched_rows


@frappe.whitelist()
def create_remittance_from_payroll(organization, campaign, remittance_date,
                                   rows, total_amount=None, reference_number=None):
    """Create a Remittance document from matched payroll data.

    Args:
        organization: Employer organization name
        campaign: Campaign name
        remittance_date: Date string
        rows: list of dicts with {donor, amount, pledge (optional)}
        total_amount: Expected total (for variance calculation)
        reference_number: Check/ACH reference number

    Returns:
        The created Remittance document name
    """
    if isinstance(rows, str):
        rows = json.loads(rows)

    # Filter to only rows with matched donors
    matched_rows = [r for r in rows if r.get("donor")]

    if not matched_rows:
        frappe.throw("No matched donor rows to create a remittance from.")

    # Calculate items total from matched rows
    items_total = flt(sum(flt(r.get("amount", 0)) for r in matched_rows))

    # Use items_total as total_amount if no expected total provided
    remittance_total = flt(total_amount) if flt(total_amount) > 0 else items_total

    remittance = frappe.new_doc("Remittance")
    remittance.organization = organization
    remittance.campaign = campaign
    remittance.remittance_date = remittance_date or nowdate()
    remittance.total_amount = remittance_total
    remittance.payment_method = "ACH/Bank Transfer"
    remittance.reference_number = reference_number or ""

    # Try to find active pledges for each donor in this campaign
    for row in matched_rows:
        donor = row["donor"]
        amount = flt(row.get("amount", 0))

        # Look up the donor's active pledge for this campaign
        pledge = row.get("pledge")
        if not pledge:
            pledge_match = frappe.get_all(
                "Pledge",
                filters={
                    "donor": donor,
                    "campaign": campaign,
                    "docstatus": 1,
                    "payment_method": "Payroll Deduction",
                },
                fields=["name"],
                order_by="creation desc",
                limit=1,
            )
            if pledge_match:
                pledge = pledge_match[0]["name"]

        remittance.append("items", {
            "donor": donor,
            "pledge": pledge or "",
            "amount": amount,
        })

    remittance.insert()
    frappe.db.commit()

    return remittance.name
