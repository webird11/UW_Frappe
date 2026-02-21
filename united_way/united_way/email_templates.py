import frappe


def create_email_templates():
    """Create standard email templates for the United Way app."""
    templates = [
        {
            "name": "Pledge Confirmation",
            "subject": "Thank you for your pledge to {{ doc.campaign }}",
            "response": """<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<h2 style="color: #003366;">Thank You for Your Pledge!</h2>

<p>Dear {{ doc.donor_name }},</p>

<p>Thank you for your generous pledge to <strong>{{ doc.campaign }}</strong>. Your commitment to our community makes a real difference.</p>

<h3 style="color: #003366; border-bottom: 1px solid #eee; padding-bottom: 5px;">Pledge Summary</h3>
<table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
<tr><td style="padding: 5px 0; color: #666;">Pledge ID:</td><td style="padding: 5px 0;">{{ doc.name }}</td></tr>
<tr><td style="padding: 5px 0; color: #666;">Pledge Amount:</td><td style="padding: 5px 0;"><strong>{{ frappe.utils.fmt_money(doc.pledge_amount, currency="USD") }}</strong></td></tr>
<tr><td style="padding: 5px 0; color: #666;">Payment Method:</td><td style="padding: 5px 0;">{{ doc.payment_method or "Not specified" }}</td></tr>
<tr><td style="padding: 5px 0; color: #666;">Payment Frequency:</td><td style="padding: 5px 0;">{{ doc.payment_frequency or "One-Time" }}</td></tr>
</table>

<h3 style="color: #003366; border-bottom: 1px solid #eee; padding-bottom: 5px;">Allocation Breakdown</h3>
<table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
<tr style="background: #f8f9fa;">
<th style="padding: 8px; text-align: left;">Agency</th>
<th style="padding: 8px; text-align: right;">Percentage</th>
<th style="padding: 8px; text-align: right;">Amount</th>
</tr>
{% for row in doc.allocations %}
<tr>
<td style="padding: 8px; border-bottom: 1px solid #eee;">{{ row.agency }}</td>
<td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">{{ row.percentage }}%</td>
<td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">{{ frappe.utils.fmt_money(row.allocated_amount, currency="USD") }}</td>
</tr>
{% endfor %}
</table>

{% if doc.payment_method == "Payroll Deduction" and doc.deduction_per_period %}
<h3 style="color: #003366; border-bottom: 1px solid #eee; padding-bottom: 5px;">Payroll Deduction Schedule</h3>
<p>Your payroll deduction of <strong>{{ frappe.utils.fmt_money(doc.deduction_per_period, currency="USD") }}</strong> per period will begin on {{ frappe.utils.formatdate(doc.payroll_start_date) }}{% if doc.payroll_end_date %} and end on {{ frappe.utils.formatdate(doc.payroll_end_date) }}{% endif %}.</p>
{% endif %}

<p style="margin-top: 20px;">Thank you for supporting our community!</p>
</div>""",
            "use_html": 1,
        },
        {
            "name": "Donation Thank You",
            "subject": "Thank you for your gift of {{ frappe.utils.fmt_money(doc.amount, currency='USD') }}",
            "response": """<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<h2 style="color: #003366;">Thank You for Your Donation!</h2>

<p>Dear {{ doc.donor_name }},</p>

<p>We are grateful for your generous gift to <strong>{{ doc.campaign }}</strong>.</p>

<h3 style="color: #003366; border-bottom: 1px solid #eee; padding-bottom: 5px;">Donation Details</h3>
<table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
<tr><td style="padding: 5px 0; color: #666;">Receipt Number:</td><td style="padding: 5px 0;">{{ doc.name }}</td></tr>
<tr><td style="padding: 5px 0; color: #666;">Donation Date:</td><td style="padding: 5px 0;">{{ frappe.utils.formatdate(doc.donation_date) }}</td></tr>
<tr><td style="padding: 5px 0; color: #666;">Amount:</td><td style="padding: 5px 0;"><strong>{{ frappe.utils.fmt_money(doc.amount, currency="USD") }}</strong></td></tr>
{% if doc.tax_deductible and doc.tax_deductible_amount %}
<tr><td style="padding: 5px 0; color: #666;">Tax Deductible Amount:</td><td style="padding: 5px 0;">{{ frappe.utils.fmt_money(doc.tax_deductible_amount, currency="USD") }}</td></tr>
{% endif %}
<tr><td style="padding: 5px 0; color: #666;">Payment Method:</td><td style="padding: 5px 0;">{{ doc.payment_method or "Not specified" }}</td></tr>
</table>

{% if doc.tax_deductible %}
<p style="font-size: 12px; color: #666; border: 1px solid #ddd; padding: 10px; border-radius: 4px; margin-top: 15px;">
<strong>Tax Information:</strong> No goods or services were provided in exchange for this contribution.
Please retain this email as a record of your donation for tax purposes.
</p>
{% endif %}

<p style="margin-top: 20px;">Your support makes our community stronger. Thank you!</p>
</div>""",
            "use_html": 1,
        },
        {
            "name": "Pledge Reminder",
            "subject": "Reminder: Outstanding pledge balance for {{ doc.campaign }}",
            "response": """<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<h2 style="color: #003366;">Pledge Payment Reminder</h2>

<p>Dear {{ doc.donor_name }},</p>

<p>This is a friendly reminder about your outstanding pledge to <strong>{{ doc.campaign }}</strong>.</p>

<h3 style="color: #003366; border-bottom: 1px solid #eee; padding-bottom: 5px;">Pledge Status</h3>
<table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
<tr><td style="padding: 5px 0; color: #666;">Pledge ID:</td><td style="padding: 5px 0;">{{ doc.name }}</td></tr>
<tr><td style="padding: 5px 0; color: #666;">Original Pledge Amount:</td><td style="padding: 5px 0;">{{ frappe.utils.fmt_money(doc.pledge_amount, currency="USD") }}</td></tr>
<tr><td style="padding: 5px 0; color: #666;">Amount Collected:</td><td style="padding: 5px 0;">{{ frappe.utils.fmt_money(doc.total_collected, currency="USD") }}</td></tr>
<tr style="font-weight: bold; font-size: 16px;">
<td style="padding: 10px 0; color: #e65100; border-top: 2px solid #ddd;">Outstanding Balance:</td>
<td style="padding: 10px 0; color: #e65100; border-top: 2px solid #ddd;">{{ frappe.utils.fmt_money(doc.outstanding_balance, currency="USD") }}</td>
</tr>
</table>

<p>We understand that circumstances may change. If you need to adjust your pledge or discuss payment options, please don't hesitate to reach out.</p>

<p style="margin-top: 20px;">Thank you for your continued support!</p>
</div>""",
            "use_html": 1,
        },
        {
            "name": "Campaign Update",
            "subject": "{{ doc.campaign_name }} Progress Update",
            "response": """<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<h2 style="color: #003366;">Campaign Progress Update</h2>

<h3>{{ doc.campaign_name }}</h3>

<div style="background: #f8f9fa; padding: 20px; border-radius: 4px; margin: 15px 0;">
<table style="width: 100%; border-collapse: collapse;">
<tr>
<td style="padding: 8px 0; color: #666;">Campaign Goal:</td>
<td style="padding: 8px 0; font-weight: bold;">{{ frappe.utils.fmt_money(doc.fundraising_goal, currency="USD") }}</td>
</tr>
<tr>
<td style="padding: 8px 0; color: #666;">Total Pledged:</td>
<td style="padding: 8px 0; font-weight: bold; color: #1565c0;">{{ frappe.utils.fmt_money(doc.total_pledged, currency="USD") }}</td>
</tr>
<tr>
<td style="padding: 8px 0; color: #666;">Total Collected:</td>
<td style="padding: 8px 0; font-weight: bold; color: #2e7d32;">{{ frappe.utils.fmt_money(doc.total_collected, currency="USD") }}</td>
</tr>
<tr>
<td style="padding: 8px 0; color: #666;">Progress:</td>
<td style="padding: 8px 0; font-weight: bold;">{{ "%.1f"|format(doc.percent_of_goal or 0) }}% of goal</td>
</tr>
<tr>
<td style="padding: 8px 0; color: #666;">Number of Donors:</td>
<td style="padding: 8px 0; font-weight: bold;">{{ doc.donor_count or 0 }}</td>
</tr>
</table>
</div>

<p>Thank you to everyone who has contributed so far. Together, we are making a difference in our community!</p>
</div>""",
            "use_html": 1,
        },
    ]

    for tmpl_data in templates:
        if frappe.db.exists("Email Template", tmpl_data["name"]):
            print(f"  Email template '{tmpl_data['name']}' already exists, skipping")
            continue

        doc = frappe.get_doc({
            "doctype": "Email Template",
            "name": tmpl_data["name"],
            "subject": tmpl_data["subject"],
            "response": tmpl_data["response"],
            "use_html": tmpl_data.get("use_html", 0),
        })
        doc.insert(ignore_permissions=True)
        print(f"  Created email template: {tmpl_data['name']}")

    frappe.db.commit()
