"""ABP2-I481 — Account Paid To (debit lines) child doctype.

Every row is one GL debit that will post on Payment Entry submit.
Fields mirror FRD §7 / §8:

    account       Link → Account          Required (non-group ledger)
    cost_center   Link → Cost Center       Required for P&L accounts
    project       Link → Project           Optional
    party_type    Link → Party Type        Conditional (receivable/payable)
    party         Dynamic Link             Conditional
    amount        Currency                 Required (> 0)
    remarks       Small Text               Optional

Validation is centralised in reformiqo_pe.overrides.payment_entry_direct_gl
(FRD §9 L-10, L-11) so we don't scatter checks across the child controller.
"""
from frappe.model.document import Document


class AccountPaidTo(Document):
	pass
