import frappe
from frappe.model.document import Document
from frappe.utils import flt


class PayrollUpload(Document):
    def validate(self):
        """Basic validation before save."""
        if self.expected_total and flt(self.expected_total) < 0:
            frappe.throw("Expected Total cannot be negative.")


@frappe.whitelist()
def process_payroll_upload(payroll_upload_name):
    """Full pipeline: parse file -> match employees -> create remittance.

    Args:
        payroll_upload_name: Name of the Payroll Upload document to process

    Returns:
        dict with remittance name, matched count, and unmatched count
    """
    doc = frappe.get_doc("Payroll Upload", payroll_upload_name)

    # Step 1: Read the attached file content
    file_url = doc.payroll_file
    file_content = read_attached_file(file_url)

    # Step 2: Parse the file
    format_map = {
        "CSV": "csv",
        "ADP Fixed Width": "adp_fixed",
        "Tab Delimited": "tab_delimited",
    }
    from united_way.payroll_import import (
        parse_payroll_file,
        match_employees_to_donors,
        create_remittance_from_payroll,
    )

    result = parse_payroll_file(
        file_content,
        format_map.get(doc.file_format, "csv"),
        organization=doc.organization,
        campaign=doc.campaign,
    )

    # Build parse log
    error_detail = ""
    if result["errors"]:
        error_detail = "\n" + "\n".join(result["errors"][:50])  # Cap at 50 errors in log
        if len(result["errors"]) > 50:
            error_detail += f"\n... and {len(result['errors']) - 50} more errors"

    parse_log = (
        f"Parsed {result['summary']['total_rows']} rows, "
        f"Total: {result['summary']['total_amount']}, "
        f"Unique Employees: {result['summary']['unique_employees']}, "
        f"Errors: {len(result['errors'])}"
        f"{error_detail}"
    )

    doc.db_set("parse_log", parse_log)
    doc.db_set("status", "Parsed")

    if not result["rows"]:
        frappe.throw("No valid rows found in the uploaded file. Check the parse log for details.")

    # Step 3: Match employees to donor Contact records
    matched = match_employees_to_donors(result["rows"], doc.organization)
    matched_count = sum(1 for r in matched if r.get("donor"))
    unmatched_count = sum(1 for r in matched if not r.get("donor"))

    # Build match log with details
    match_details = []
    for r in matched:
        status_icon = "[OK]" if r.get("donor") else "[??]"
        donor_info = r.get("donor", "NO MATCH")
        match_details.append(
            f"{status_icon} {r.get('employee_name', 'Unknown')} -> {donor_info} ({r.get('match_status', 'unmatched')})"
        )

    match_log = (
        f"Matched: {matched_count}, Unmatched: {unmatched_count}\n\n"
        + "\n".join(match_details[:100])  # Cap at 100 detail lines
    )
    if len(match_details) > 100:
        match_log += f"\n... and {len(match_details) - 100} more rows"

    doc.db_set("match_log", match_log)
    doc.db_set("status", "Matched")

    # Step 4: Create Remittance (only matched rows)
    matched_rows = [r for r in matched if r.get("donor")]
    if matched_rows:
        remittance_name = create_remittance_from_payroll(
            organization=doc.organization,
            campaign=doc.campaign,
            remittance_date=str(doc.remittance_date),
            rows=matched_rows,
            total_amount=doc.expected_total,
            reference_number=doc.reference_number,
        )
        doc.db_set("remittance", remittance_name)
        doc.db_set("status", "Remittance Created")

        frappe.msgprint(
            f"Remittance {remittance_name} created with {matched_count} items. "
            f"{unmatched_count} employees could not be matched.",
            title="Payroll Upload Processed",
            indicator="green" if unmatched_count == 0 else "orange",
        )

        return {
            "remittance": remittance_name,
            "matched": matched_count,
            "unmatched": unmatched_count,
        }
    else:
        frappe.throw(
            "No employees could be matched to donors. "
            "Please check that donor Contact records exist for this organization "
            "and that names in the payroll file match."
        )


def read_attached_file(file_url):
    """Read content from an attached file.

    Args:
        file_url: The file URL from the Attach field

    Returns:
        File content as a string
    """
    if not file_url:
        frappe.throw("No file attached.")

    file_doc = frappe.get_doc("File", {"file_url": file_url})
    file_path = file_doc.get_full_path()

    # Try UTF-8 first, fall back to Latin-1 for Windows-origin files
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="latin-1") as f:
            return f.read()
    except FileNotFoundError:
        frappe.throw(f"Attached file not found at path: {file_path}")
