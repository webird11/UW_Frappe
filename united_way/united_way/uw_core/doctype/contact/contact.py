import frappe
from frappe.model.document import Document
from frappe.utils import flt


class Contact(Document):
    def validate(self):
        self.full_name = f"{self.first_name} {self.last_name}".strip()

    def before_save(self):
        self.full_name = f"{self.first_name} {self.last_name}".strip()

    def update_donor_stats(self):
        """Recalculate lifetime giving, last donation, consecutive years, donor level."""
        donations = frappe.get_all(
            "Donation",
            filters={"donor": self.name, "docstatus": 1},
            fields=["amount", "donation_date"],
            order_by="donation_date desc",
        )

        if donations:
            self.lifetime_giving = flt(sum(flt(d.amount) for d in donations))
            self.last_donation_date = donations[0].donation_date
            self.last_donation_amount = flt(donations[0].amount)

            # Calculate consecutive years giving (backward from most recent year)
            years = sorted(
                set(d.donation_date.year for d in donations if d.donation_date),
                reverse=True,
            )
            consecutive = 1
            for i in range(1, len(years)):
                if years[i] == years[i - 1] - 1:
                    consecutive += 1
                else:
                    break
            self.consecutive_years_giving = consecutive
        else:
            self.lifetime_giving = 0
            self.last_donation_date = None
            self.last_donation_amount = 0
            self.consecutive_years_giving = 0
            self.donor_level = ""

        self.autoset_donor_level()
        self.save()

    def autoset_donor_level(self):
        """Set donor level based on lifetime giving thresholds.
        Tocqueville Society: $10,000+
        Leadership Circle: $1,000 - $9,999
        Community Builder: $500 - $999
        Partner: $100 - $499
        Supporter: Under $100
        """
        giving = flt(self.lifetime_giving)
        if giving >= 10000:
            self.donor_level = "Tocqueville Society ($10,000+)"
        elif giving >= 1000:
            self.donor_level = "Leadership Circle ($1,000-$9,999)"
        elif giving >= 500:
            self.donor_level = "Community Builder ($500-$999)"
        elif giving >= 100:
            self.donor_level = "Partner ($100-$499)"
        elif giving > 0:
            self.donor_level = "Supporter (Under $100)"
        else:
            self.donor_level = ""
