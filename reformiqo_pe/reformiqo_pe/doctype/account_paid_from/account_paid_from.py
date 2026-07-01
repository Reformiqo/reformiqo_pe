"""ABP2-I481 — Account Paid From (credit lines) child doctype.

Mirrors Account Paid To but posts as a Credit on submit. See that
sibling doctype's docstring for the field contract.
"""
from frappe.model.document import Document


class AccountPaidFrom(Document):
	pass
