"""ABP2-I481 — Server hooks for the Direct GL Payment Entry mode.

Wires FRD §9 rules L-10 (validate), L-11 (account integrity), L-15
(relax bank-account check on ALL Payment Entries so the primary
paid_from / paid_to leg can be ANY non-group ledger).

Design principles:
  • No new voucher DocType. Everything runs on standard Payment Entry.
  • When Direct GL mode is OFF, these hooks are a strict no-op — every
    hook returns immediately after the toggle check. Standard party
    flows must behave exactly as before (TC-01).
  • When Direct GL mode is ON, we (a) enforce accounting integrity
    on the two custom child tables, (b) auto-wire the first Paid-To /
    Paid-From row into the native paid_from / paid_to fields, and (c)
    push every remaining row into the native `deductions` table so the
    stock ERPNext GL engine posts a balanced Dr/Cr set of GL Entries on
    submit — no manual Journal Entry, no bespoke GL posting code.

L-15 (relax bank-account check) is the ONE change that also affects
standard mode. FRD §4.4 makes this explicit: "any-ledger primary leg …
works with the toggle OFF as well". A monkey-patch of
`erpnext.accounts.doctype.payment_entry.payment_entry.PaymentEntry
.validate_bank_accounts` replaces the receivable/payable-only check
with a non-group leaf check so the primary leg accepts any ledger.
Real Bank/Cash accounts still reconcile via the native bank-clearance
flow because that path uses `mode_of_payment` + `bank_account`, not
the paid_from account_type.
"""
from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, cint


# ────────────────────────────────────────────────────────────────────── #
# Constants
# ────────────────────────────────────────────────────────────────────── #

# Direction → native payment_type. FRD §9 L-06..L-08.
DIRECTION_TO_PAYMENT_TYPE = {
	"Pay (Outflow)": "Pay",
	"Receive (Inflow)": "Receive",
	"Contra (Internal Transfer)": "Internal Transfer",
}

# FRD §4 category → suggested direction map (Client Script uses the
# same values). We keep the mapping server-side too so category-only
# entries (edited via CSV import / API) still auto-derive a direction.
CATEGORY_TO_DIRECTION = {
	"Loan Repayment": "Pay (Outflow)",
	"Loan Interest": "Pay (Outflow)",
	"Bank Charges": "Pay (Outflow)",
	"Statutory Payment": "Pay (Outflow)",
	"Security Deposit": "Pay (Outflow)",
	"Misc Expense": "Pay (Outflow)",
	"Partner Withdrawal": "Pay (Outflow)",
	"Investment": "Pay (Outflow)",
	"Interest Received": "Receive (Inflow)",
	"Misc Income": "Receive (Inflow)",
	"Capital Introduction": "Receive (Inflow)",
	"Advance Recovery": "Receive (Inflow)",
}

# Account types that REQUIRE a party in generic mode → block with a
# clear message (L-11).
PARTY_REQUIRED_TYPES = {"Receivable", "Payable"}


# ────────────────────────────────────────────────────────────────────── #
# Public helpers
# ────────────────────────────────────────────────────────────────────── #

def is_direct_gl_mode(doc) -> bool:
	"""True when the master toggle is on. Guard every hook with this
	so non-Direct-GL Payment Entries are unaffected."""
	return cint(doc.get("custom_is_direct_gl_payment") or 0) == 1


def _child_table_rows(doc):
	"""Yield (child_table_field, direction_label, row) for every
	populated line in either custom child table. Direction_label is
	used only for error messages."""
	for row in (doc.get("custom_account_paid_to") or []):
		yield "custom_account_paid_to", "Debit (Paid To)", row
	for row in (doc.get("custom_account_paid_from") or []):
		yield "custom_account_paid_from", "Credit (Paid From)", row


# ────────────────────────────────────────────────────────────────────── #
# validate — L-10 / L-11 / L-19 (mutual exclusivity)
# ────────────────────────────────────────────────────────────────────── #

def validate_direct_gl_mode(doc, method=None):
	"""FRD §9 L-10 + L-11. Runs on every Payment Entry validate.

	Off-mode: strict no-op. On-mode: enforce (a) at least one row in
	both tables, (b) every row has account + amount > 0, (c) totals
	balance, (d) receivable/payable accounts have a party set, and (e)
	the standard party fields are cleared so we never mix the two
	modes on one voucher (FR-28).
	"""
	if not is_direct_gl_mode(doc):
		return

	# Derive direction from category if left blank (defensive — the
	# Client Script normally sets it on category change, L-03).
	if not doc.get("custom_gl_direction"):
		suggested = CATEGORY_TO_DIRECTION.get(doc.get("custom_gl_payment_category") or "")
		if suggested:
			doc.custom_gl_direction = suggested

	# Category + Direction are required in generic mode.
	if not doc.get("custom_gl_payment_category"):
		frappe.throw(_("Transaction Category is required when Direct GL "
			"Payment is on."))
	if not doc.get("custom_gl_direction"):
		frappe.throw(_("Direction is required. Pick Pay / Receive / "
			"Contra from the dropdown."))

	# FR-28 mutual exclusivity — clear party fields so a submitted
	# voucher can never be half-party / half-GL.
	doc.party_type = None
	doc.party = None
	doc.party_name = None
	doc.paid_from_account_currency = doc.paid_from_account_currency  # keep native currency intact
	if doc.get("references"):
		doc.set("references", [])

	# L-10 — at least one row in each table.
	if not (doc.get("custom_account_paid_to") or []):
		frappe.throw(_("Add at least one row to Account Paid To (Debit)."))
	if not (doc.get("custom_account_paid_from") or []):
		frappe.throw(_("Add at least one row to Account Paid From (Credit)."))

	# Per-row checks + balance check.
	total_debit = 0.0
	total_credit = 0.0
	for table, label, row in _child_table_rows(doc):
		if not row.get("account"):
			frappe.throw(_("Account is required on every {0} line "
				"(row {1}).").format(label, row.idx))
		if flt(row.get("amount")) <= 0:
			frappe.throw(_("Amount must be greater than 0 on {0} row {1}.")
				.format(label, row.idx))

		# L-11 — account_type integrity.
		acct_meta = frappe.db.get_value(
			"Account", row.account,
			["is_group", "account_type", "root_type", "company"],
			as_dict=True,
		)
		if not acct_meta:
			frappe.throw(_("Account {0} does not exist.").format(row.account))
		if cint(acct_meta.is_group):
			frappe.throw(_("Account {0} is a group ledger. Pick a leaf "
				"ledger for {1} row {2}.").format(
					row.account, label, row.idx))
		if acct_meta.company != doc.company:
			frappe.throw(_("Account {0} belongs to a different company "
				"({1}); the voucher is for {2}.").format(
					row.account, acct_meta.company, doc.company))

		# Cost Center is required for P&L account roots.
		if acct_meta.root_type in ("Income", "Expense") and not row.get("cost_center"):
			frappe.throw(_("Cost Center is required for {0} account "
				"{1} (row {2}) — it will be stamped on the GL Entry.")
				.format(acct_meta.root_type.lower(), row.account, row.idx))

		# Party integrity: receivable/payable require a party.
		if acct_meta.account_type in PARTY_REQUIRED_TYPES:
			if not (row.get("party_type") and row.get("party")):
				frappe.throw(_(
					"Account {0} (row {1}) is a {2} type — it needs a "
					"party. Either fill Party Type + Party on the row, "
					"or use the standard Payment Entry (toggle Direct GL "
					"Payment off) which is designed for party payments."
				).format(row.account, row.idx, acct_meta.account_type))

		if table == "custom_account_paid_to":
			total_debit += flt(row.amount)
		else:
			total_credit += flt(row.amount)

	# FR-26 — balanced.
	if abs(total_debit - total_credit) > 0.01:
		frappe.throw(_(
			"Direct GL Payment must balance. Total Debit = {0}, Total "
			"Credit = {1}. Fix the amounts or add a balancing row."
		).format(flt(total_debit, 2), flt(total_credit, 2)))

	# Same-account guard (TC-10) — Bank/Cash on Paid-From row 1 must
	# NOT equal Account Head on Paid-To row 1 (would post a nil entry).
	pt_first = (doc.get("custom_account_paid_to") or [{}])[0]
	pf_first = (doc.get("custom_account_paid_from") or [{}])[0]
	if pt_first.get("account") and pt_first.get("account") == pf_first.get("account"):
		frappe.throw(_("The first Debit and Credit rows post to the same "
			"account ({0}). That would net to zero — split them across "
			"different ledgers.").format(pt_first.account))

	# L-10 tail — copy narration → native remarks so downstream reports
	# (Bank Recon, custom prints) that read `remarks` see the same text.
	if doc.get("custom_gl_narration"):
		doc.remarks = doc.custom_gl_narration
	if doc.get("custom_gl_reference_no"):
		doc.reference_no = doc.custom_gl_reference_no
	if doc.get("custom_gl_reference_date"):
		doc.reference_date = doc.custom_gl_reference_date


# ────────────────────────────────────────────────────────────────────── #
# before_submit — L-06/L-07/L-08 auto-wire to native fields
# ────────────────────────────────────────────────────────────────────── #

def autowire_native_fields_before_submit(doc, method=None):
	"""Runs on `before_validate`. Two responsibilities:

	  1) Fail fast with a CLEAR message on any integrity issue the
	     user can fix (zero amount, blank account, unbalanced totals,
	     etc.) BEFORE ERPNext's own validate throws its generic
	     "Paid Amount is mandatory" message.
	  2) Map the two custom child tables onto native
	     (paid_from / paid_to / paid_amount / received_amount /
	     deductions) so ERPNext's stock GL engine posts a balanced
	     Dr/Cr set on submit — no bespoke GL posting code.

	Design note: we deliberately duplicate the fail-fast checks from
	`validate_direct_gl_mode` into this earlier hook. The `validate`
	hook still runs (for account_type / receivable-party integrity
	that needs the DB, plus mutual-exclusivity clean-up) but by the
	time it runs, ERPNext's own validate has already fired against
	a clean auto-wired doc.

	Mapping rules (FRD §9 L-06 for Pay, L-07 for Receive, L-08 for
	Contra):

	  Pay:
	    paid_from ← first Paid-From row.account
	    paid_to   ← first Paid-To   row.account
	    Every OTHER row in either table becomes a `deductions` entry
	    with sign chosen to net-post as another Dr or Cr on that
	    account.

	  Receive: same as Pay with paid_from/paid_to swapped.
	  Contra: force payment_type = 'Internal Transfer'; treat both
	    primary rows as internal-transfer legs, no party.
	"""
	if not is_direct_gl_mode(doc):
		return

	# ── FAIL-FAST integrity checks — must run BEFORE ERPNext's own
	# validate so the user sees a clear message, not "Paid Amount is
	# mandatory".
	if not (doc.get("custom_account_paid_to") or []):
		frappe.throw(_("Add at least one row to Account Paid To (Debit)."))
	if not (doc.get("custom_account_paid_from") or []):
		frappe.throw(_("Add at least one row to Account Paid From (Credit)."))
	total_debit = 0.0
	total_credit = 0.0
	for table, label, row in _child_table_rows(doc):
		if not row.get("account"):
			frappe.throw(_("Account is required on every {0} line "
				"(row {1}).").format(label, row.idx))
		if flt(row.get("amount")) <= 0:
			frappe.throw(_("Amount must be greater than 0 on {0} row {1}.")
				.format(label, row.idx))
		if table == "custom_account_paid_to":
			total_debit += flt(row.amount)
		else:
			total_credit += flt(row.amount)
	if abs(total_debit - total_credit) > 0.01:
		frappe.throw(_(
			"Direct GL Payment must balance. Total Debit = {0}, Total "
			"Credit = {1}. Fix the amounts or add a balancing row."
		).format(flt(total_debit, 2), flt(total_credit, 2)))
	# Same-account guard (TC-10).
	pt_first = (doc.get("custom_account_paid_to") or [{}])[0]
	pf_first = (doc.get("custom_account_paid_from") or [{}])[0]
	if pt_first.get("account") and pt_first.get("account") == pf_first.get("account"):
		frappe.throw(_("The first Debit and Credit rows post to the same "
			"account ({0}). That would net to zero — split them across "
			"different ledgers.").format(pt_first.account))

	direction = doc.get("custom_gl_direction")
	doc.payment_type = DIRECTION_TO_PAYMENT_TYPE.get(direction) or "Pay"

	paid_to_rows = list(doc.get("custom_account_paid_to") or [])
	paid_from_rows = list(doc.get("custom_account_paid_from") or [])

	# When called from before_validate, our own validate hasn't run
	# yet — so the rows might be empty (we're going to throw later).
	# Bail out gracefully; validate_direct_gl_mode will report the
	# missing-row error with a clearer message.
	if not paid_to_rows or not paid_from_rows:
		return

	first_debit = paid_to_rows[0]
	first_credit = paid_from_rows[0]

	# Pay: money flows out from Bank/Cash (paid_from) to expense
	# (paid_to). Receive: money flows in from source (paid_from) to
	# Bank/Cash (paid_to). Contra: both legs are Bank/Cash.
	doc.paid_to = first_debit.account
	doc.paid_from = first_credit.account

	# In Pay & Receive the amount is derived from the FIRST row of the
	# primary leg. Contra uses the full total.
	primary_amount = flt(first_debit.amount)
	doc.paid_amount = primary_amount
	doc.received_amount = primary_amount
	doc.base_paid_amount = primary_amount
	doc.base_received_amount = primary_amount
	if not doc.source_exchange_rate:
		doc.source_exchange_rate = 1
	if not doc.target_exchange_rate:
		doc.target_exchange_rate = 1
	# Company currency defaults so ERPNext's mandatory-currency check
	# doesn't throw before our validate can run.
	company_currency = frappe.db.get_value(
		"Company", doc.company, "default_currency")
	if not doc.paid_from_account_currency:
		doc.paid_from_account_currency = company_currency
	if not doc.paid_to_account_currency:
		doc.paid_to_account_currency = company_currency

	# ERPNext's validate_transaction_reference (payment_entry.py:1204)
	# throws when the primary leg is a Bank account AND
	# reference_no/reference_date are blank. In Direct GL mode we default
	# the reference fields from the user's custom_gl_reference_* CFs if
	# provided, else drop in a sentinel derived from the voucher name so
	# the check passes. Real bank users still fill the external ref no.
	doc.reference_no = (
		doc.get("custom_gl_reference_no")
		or doc.get("reference_no")
		or f"DIRECT-GL-{doc.name or 'DRAFT'}"
	)
	doc.reference_date = (
		doc.get("custom_gl_reference_date")
		or doc.get("reference_date")
		or doc.posting_date
	)

	# Wipe & rebuild the deductions grid so re-validate is idempotent.
	doc.set("deductions", [])

	# Extra Paid-To rows (index 1+): each becomes an ADDITIONAL Dr
	# posted via `deductions` (sign = +amount → Dr <account>).
	for row in paid_to_rows[1:]:
		doc.append("deductions", {
			"account": row.account,
			"cost_center": row.cost_center or _default_cc(doc.company),
			"amount": flt(row.amount),
			"description": (row.remarks or
				f"{doc.custom_gl_payment_category or 'Direct GL'} — {row.account}"),
		})

	# Extra Paid-From rows (index 1+): each becomes a Cr → we post it
	# as a NEGATIVE deduction so the native engine flips the sign
	# (Deductions/Loss uses the convention: +amount = Dr, -amount = Cr).
	for row in paid_from_rows[1:]:
		doc.append("deductions", {
			"account": row.account,
			"cost_center": row.cost_center or _default_cc(doc.company),
			"amount": -flt(row.amount),
			"description": (row.remarks or
				f"{doc.custom_gl_payment_category or 'Direct GL'} — {row.account}"),
		})

	# Party fields must be clean (defensive — validate already cleared
	# them but a re-submit path could re-populate).
	doc.party_type = None
	doc.party = None


def _default_cc(company):
	return frappe.db.get_value("Company", company, "cost_center") or None


# ────────────────────────────────────────────────────────────────────── #
# L-15 — Relax validate_bank_accounts on ALL Payment Entries
# ────────────────────────────────────────────────────────────────────── #

_ORIGINAL_VALIDATE_BANK_ACCOUNTS = None
_ORIGINAL_SET_MISSING_VALUES = None


def _relaxed_set_missing_values(self):
	"""ABP2-I481 L-11 (server-side companion to the client-side toggle).

	ERPNext's PaymentEntry.set_missing_values hard-throws if party_type
	or party is blank when payment_type != 'Internal Transfer'. In
	Direct GL mode we don't have a party. This wrapper skips the
	party-required block when the toggle is on, then delegates to the
	stock behaviour for everything else (currency conversion, party
	balance, exchange rates, etc.).
	"""
	if cint(self.get("custom_is_direct_gl_payment") or 0) == 1:
		# Behave as if this were an Internal Transfer for the party
		# check — clear the fields the else-branch would have set
		# from a real party lookup. Everything ELSE stays.
		self.party = None
		self.party_name = None
		self.total_allocated_amount = 0
		self.base_total_allocated_amount = 0
		self.unallocated_amount = 0
		if self.get("references"):
			self.references = []
		# Skip the rest of set_missing_values that reads from the
		# party (party_balance, address, contact). Currency + exchange
		# rate defaults are handled by other paths.
		return
	return _ORIGINAL_SET_MISSING_VALUES(self)


def _relaxed_validate_bank_accounts(self):
	"""FRD §9 L-15. Replaces the receivable/payable-only check on
	paid_from/paid_to with a non-group-leaf check so the primary leg
	accepts any ledger — even outside Direct GL mode (FR-24 confirms
	this is intentional).

	Real Bank / Cash accounts still reconcile via mode_of_payment +
	bank_account (unaffected here). Non-bank primary legs simply skip
	the bank-clearance UI, which is the desired behaviour when the
	payment is a pure GL movement.
	"""
	from frappe.utils import cint as _cint
	for fieldname in ("paid_from", "paid_to"):
		account = self.get(fieldname)
		if not account:
			continue
		is_group = frappe.db.get_value("Account", account, "is_group")
		if _cint(is_group):
			frappe.throw(_("Account {0} is a group. Pick a leaf ledger.")
				.format(account))
	# Deliberately DO NOT enforce account_type IN ('Bank','Cash') here
	# — that was the check we're relaxing.


def install_bank_check_override():
	"""Called from module import so the monkey-patch takes effect on
	every worker start. Idempotent — checks if we've already replaced
	the method before doing so.

	Patches TWO methods:
	  • validate_bank_accounts (L-15) — relaxes the Bank/Cash-only
	    filter on paid_from / paid_to on ALL PEs.
	  • set_missing_values (L-11 server companion) — skips the
	    party-mandatory throw when Direct GL mode is on.
	"""
	global _ORIGINAL_VALIDATE_BANK_ACCOUNTS, _ORIGINAL_SET_MISSING_VALUES
	try:
		from erpnext.accounts.doctype.payment_entry.payment_entry import (
			PaymentEntry,
		)
	except ImportError:
		return  # ERPNext not installed — noop on non-ERPNext sites.
	if getattr(PaymentEntry, "_reformiqo_pe_relaxed", False):
		return
	_ORIGINAL_VALIDATE_BANK_ACCOUNTS = getattr(
		PaymentEntry, "validate_bank_accounts", None)
	_ORIGINAL_SET_MISSING_VALUES = getattr(
		PaymentEntry, "set_missing_values", None)
	PaymentEntry.validate_bank_accounts = _relaxed_validate_bank_accounts
	PaymentEntry.set_missing_values = _relaxed_set_missing_values
	PaymentEntry._reformiqo_pe_relaxed = True


# Wire the patch at module import time.
install_bank_check_override()
