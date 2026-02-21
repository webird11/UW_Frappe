import csv
import frappe
from frappe.utils import flt, getdate


def import_organizations_from_csv(filepath):
    """Import organizations from a CSV file.

    Usage:
        bench --site uw.localhost execute united_way.import_helpers.import_organizations_from_csv --args '["path/to/file.csv"]'
    """
    rows = _read_csv(filepath)
    created, skipped, errors = 0, 0, []

    for i, row in enumerate(rows, start=2):
        org_name = row.get("organization_name", "").strip()
        if not org_name:
            continue

        if frappe.db.exists("Organization", org_name):
            skipped += 1
            continue

        try:
            doc = frappe.new_doc("Organization")
            for field in [
                "organization_name", "organization_type", "status", "ein",
                "website", "phone", "email", "street_address", "street_address_2",
                "city", "state", "zip_code", "county", "agency_code",
                "service_area", "focus_areas", "certification_status",
                "industry",
            ]:
                if row.get(field):
                    doc.set(field, row[field].strip())

            for int_field in ["employee_count"]:
                if row.get(int_field):
                    doc.set(int_field, int(row[int_field]))

            for check_field in ["workplace_campaign", "corporate_match"]:
                if row.get(check_field):
                    doc.set(check_field, int(row[check_field]))

            for float_field in ["match_ratio"]:
                if row.get(float_field):
                    doc.set(float_field, float(row[float_field]))

            for currency_field in ["annual_allocation_cap", "match_cap"]:
                if row.get(currency_field):
                    doc.set(currency_field, flt(row[currency_field]))

            if row.get("date_joined"):
                doc.date_joined = getdate(row["date_joined"])

            doc.insert(ignore_permissions=True)
            created += 1
        except Exception as e:
            errors.append(f"Row {i}: {org_name} - {str(e)}")

    frappe.db.commit()
    result = f"Organizations import: {created} created, {skipped} skipped"
    if errors:
        result += f", {len(errors)} errors:\n" + "\n".join(errors)
    print(result)
    return {"created": created, "skipped": skipped, "errors": errors}


def import_contacts_from_csv(filepath):
    """Import contacts from a CSV file.

    Usage:
        bench --site uw.localhost execute united_way.import_helpers.import_contacts_from_csv --args '["path/to/file.csv"]'
    """
    rows = _read_csv(filepath)
    created, skipped, errors = 0, 0, []

    for i, row in enumerate(rows, start=2):
        first_name = row.get("first_name", "").strip()
        last_name = row.get("last_name", "").strip()
        if not first_name or not last_name:
            continue

        try:
            doc = frappe.new_doc("Contact")
            for field in [
                "first_name", "last_name", "organization", "title",
                "contact_type", "status", "email", "phone", "mobile",
                "preferred_contact_method", "street_address", "street_address_2",
                "city", "state", "zip_code",
            ]:
                if row.get(field):
                    doc.set(field, row[field].strip())

            for check_field in ["do_not_contact", "do_not_email"]:
                if row.get(check_field):
                    doc.set(check_field, int(row[check_field]))

            if row.get("donor_since"):
                doc.donor_since = getdate(row["donor_since"])

            doc.insert(ignore_permissions=True)
            created += 1
        except Exception as e:
            errors.append(f"Row {i}: {first_name} {last_name} - {str(e)}")

    frappe.db.commit()
    result = f"Contacts import: {created} created, {skipped} skipped"
    if errors:
        result += f", {len(errors)} errors:\n" + "\n".join(errors)
    print(result)
    return {"created": created, "skipped": skipped, "errors": errors}


def validate_import_data(doctype, filepath):
    """Pre-validate CSV data before importing. Reports issues without creating records.

    Usage:
        bench --site uw.localhost execute united_way.import_helpers.validate_import_data --args '["Organization", "path/to/file.csv"]'
    """
    rows = _read_csv(filepath)
    issues = []

    meta = frappe.get_meta(doctype)
    required_fields = [f.fieldname for f in meta.fields if f.reqd]
    link_fields = {f.fieldname: f.options for f in meta.fields if f.fieldtype == "Link"}
    select_fields = {
        f.fieldname: [o.strip() for o in (f.options or "").split("\n") if o.strip()]
        for f in meta.fields if f.fieldtype == "Select"
    }

    for i, row in enumerate(rows, start=2):
        # Check required fields
        for field in required_fields:
            if field in row and not row[field].strip():
                issues.append(f"Row {i}: Required field '{field}' is empty")

        # Check Link fields reference existing records
        for field, target_dt in link_fields.items():
            val = row.get(field, "").strip()
            if val and not frappe.db.exists(target_dt, val):
                issues.append(f"Row {i}: {field}='{val}' not found in {target_dt}")

        # Check Select fields have valid options
        for field, options in select_fields.items():
            val = row.get(field, "").strip()
            if val and options and val not in options:
                issues.append(f"Row {i}: {field}='{val}' not in valid options: {options}")

    if issues:
        print(f"Validation found {len(issues)} issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print(f"Validation passed: {len(rows)} rows OK for {doctype}")

    return issues


def _read_csv(filepath):
    """Read a CSV file and return list of dicts."""
    rows = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows
