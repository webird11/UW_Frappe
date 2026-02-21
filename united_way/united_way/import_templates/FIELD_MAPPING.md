# Salesforce to United Way (Frappe) Field Mapping Guide

## Organizations

| Salesforce Field | Frappe Field | Notes |
|---|---|---|
| Account.Name | organization_name | Required, must be unique |
| Account.Type | organization_type | Map: "Nonprofit" → "Member Agency", "Business" → "Corporate Donor" |
| Account.BillingStreet | street_address | |
| Account.BillingCity | city | |
| Account.BillingState | state | |
| Account.BillingPostalCode | zip_code | |
| Account.Phone | phone | |
| Account.Website | website | |
| Account.Tax_ID__c | ein | Custom field in SF |
| Account.Agency_Code__c | agency_code | Only for Member Agencies |
| Account.Industry | industry | Only for Corporate Donors |
| Account.NumberOfEmployees | employee_count | Only for Corporate Donors |
| Account.Corporate_Match__c | corporate_match | 1 or 0 |
| Account.Match_Ratio__c | match_ratio | e.g., 1.0 for dollar-for-dollar |
| Account.Match_Cap__c | match_cap | Annual cap in dollars |

## Contacts

| Salesforce Field | Frappe Field | Notes |
|---|---|---|
| Contact.FirstName | first_name | Required |
| Contact.LastName | last_name | Required |
| Contact.Account.Name | organization | Must match an existing Organization name |
| Contact.Title | title | |
| Contact.Email | email | |
| Contact.Phone | phone | |
| Contact.MobilePhone | mobile | |
| Contact.MailingStreet | street_address | |
| Contact.MailingCity | city | |
| Contact.MailingState | state | |
| Contact.MailingPostalCode | zip_code | |
| Contact.Contact_Type__c | contact_type | Map SF values to: Individual Donor, Corporate Contact, Agency Staff, etc. |
| Contact.Donor_Since__c | donor_since | Date format: YYYY-MM-DD |
| Contact.DoNotCall | do_not_contact | 1 or 0 |
| Contact.HasOptedOutOfEmail | do_not_email | 1 or 0 |

## Pledges

| Salesforce Field | Frappe Field | Notes |
|---|---|---|
| Opportunity.Name | (auto-generated) | Frappe auto-names as PLG-YYYY-##### |
| Opportunity.Campaign.Name | campaign | Must match existing Campaign name |
| Opportunity.Contact.Name | donor | Must match Contact name (format: FirstName-LastName-####) |
| Opportunity.CloseDate | pledge_date | Date format: YYYY-MM-DD |
| Opportunity.Amount | pledge_amount | Required |
| Opportunity.Payment_Method__c | payment_method | Map to: Payroll Deduction, One-Time Gift, Credit Card, Check, etc. |
| Opportunity.Frequency__c | payment_frequency | Map to: One-Time, Weekly, Bi-Weekly, Monthly, Quarterly, Annually |
| OpportunityLineItem.Agency__c | allocations.agency | Child table: must match Organization name |
| OpportunityLineItem.Designation__c | allocations.designation_type | Donor Designated, Community Impact Fund, etc. |
| OpportunityLineItem.Percentage__c | allocations.percentage | Must total 100% per pledge |

**Note on child table rows:** For pledges with multiple allocations, the first row contains all pledge fields. Subsequent rows only need the allocation fields (agency, designation_type, percentage). Leave other columns blank for continuation rows.

## Donations

| Salesforce Field | Frappe Field | Notes |
|---|---|---|
| Payment.Name | (auto-generated) | Frappe auto-names as DON-YYYY-##### |
| Payment.Date | donation_date | Required, format: YYYY-MM-DD |
| Payment.Contact.Name | donor | Must match Contact name |
| Payment.Campaign.Name | campaign | Required, must match Campaign name |
| Payment.Opportunity.Name | pledge | Optional, must match Pledge name if provided |
| Payment.Amount | amount | Required |
| Payment.Payment_Method__c | payment_method | Map to Frappe payment method options |
| Payment.Check_Number__c | reference_number | |
| Payment.Batch__c | batch_number | |
| Payment.Tax_Deductible__c | tax_deductible | 1 or 0 (default: 1) |

## Import Order

**Always import in this order:**
1. Organizations (no dependencies)
2. Contacts (depends on Organizations)
3. Campaigns (if not already created)
4. Pledges (depends on Contacts + Campaigns)
5. Donations (depends on Contacts + Campaigns + optionally Pledges)
