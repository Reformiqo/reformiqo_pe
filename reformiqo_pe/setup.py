"""ABP2-I481 — Setup module: idempotently upsert the 10 Custom Fields
that add the "General / Direct GL" tab to Payment Entry.

Runs on `after_install` (fresh install) AND `after_migrate` (every
subsequent deploy) so a manual edit in Customize Form on cloud can't
drift the field spec away from what the code declares — [[feedback-
property-setters-in-code]].

Exports the spec verbatim from FRD §7 (Custom Fields Specification).
"""
from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


PE = "Payment Entry"

# Ships pre-seeded with the standard FRD §4 category list. Admins can
# rename / add / retire via Customize Form (FR-23).
DEFAULT_CATEGORY_OPTIONS = "\n".join([
	"",  # blank first so field is truly optional until Direct GL mode
	"Loan Repayment",
	"Loan Interest",
	"Bank Charges",
	"Statutory Payment",
	"Security Deposit",
	"Advance Recovery",
	"Misc Expense",
	"Misc Income",
	"Interest Received",
	"Capital Introduction",
	"Partner Withdrawal",
	"Investment",
	"Other",
])

# The Direct GL toggle drives every other custom field's visibility
# via depends_on. Use pure JS (no Python in/not in/cint) — see
# [[feedback-depends-on-pure-js]].
DEPENDS_ON_DIRECT_GL = 'eval:doc.custom_is_direct_gl_payment==1'

CUSTOM_FIELDS_SPEC = {
	PE: [
		# ── Tab break ──────────────────────────────────────────────
		{
			"fieldname": "custom_general_payment_tab",
			"label": "General / Direct GL",
			"fieldtype": "Tab Break",
			"insert_after": "deductions",
		},
		# ── Master toggle ─────────────────────────────────────────
		{
			"fieldname": "custom_is_direct_gl_payment",
			"label": "Direct GL Payment",
			"fieldtype": "Check",
			"insert_after": "custom_general_payment_tab",
			"default": "0",
			"description": (
				"Enable to record any Debit/Credit against any ledger "
				"— no Customer/Supplier/Employee required. When ON, the "
				"standard party fields are hidden and the Account Paid "
				"To / Account Paid From tables become the source of "
				"truth."
			),
		},
		# ── Category (editable Select) ─────────────────────────────
		{
			"fieldname": "custom_gl_payment_category",
			"label": "Transaction Category",
			"fieldtype": "Select",
			"insert_after": "custom_is_direct_gl_payment",
			"options": DEFAULT_CATEGORY_OPTIONS,
			"depends_on": DEPENDS_ON_DIRECT_GL,
			"mandatory_depends_on": DEPENDS_ON_DIRECT_GL,
			"description": (
				"Editable list. To add a new type, edit this field's "
				"Options in Customize Form — no code change needed "
				"(FR-23)."
			),
		},
		# ── Direction (Pay/Receive/Contra) ─────────────────────────
		{
			"fieldname": "custom_gl_direction",
			"label": "Direction",
			"fieldtype": "Select",
			"insert_after": "custom_gl_payment_category",
			"options": "\nPay (Outflow)\nReceive (Inflow)\nContra (Internal Transfer)",
			"depends_on": DEPENDS_ON_DIRECT_GL,
			"mandatory_depends_on": DEPENDS_ON_DIRECT_GL,
			"description": (
				"Auto-set from the Category when picked; user may "
				"override. Drives native payment_type."
			),
		},
		# ── Debit table (Paid To) ──────────────────────────────────
		{
			"fieldname": "custom_account_paid_to",
			"label": "Account Paid To (Debit)",
			"fieldtype": "Table",
			"options": "Account Paid To",
			"insert_after": "custom_gl_direction",
			"depends_on": DEPENDS_ON_DIRECT_GL,
			"description": (
				"One row per debit account. Every line carries its "
				"own Cost Center and Project — both are stamped on the "
				"line's GL Entry."
			),
		},
		# ── Credit table (Paid From) ───────────────────────────────
		{
			"fieldname": "custom_account_paid_from",
			"label": "Account Paid From (Credit)",
			"fieldtype": "Table",
			"options": "Account Paid From",
			"insert_after": "custom_account_paid_to",
			"depends_on": DEPENDS_ON_DIRECT_GL,
			"description": "One row per credit account (Debit table's mirror).",
		},
		# ── Narration / Purpose ────────────────────────────────────
		{
			"fieldname": "custom_gl_narration",
			"label": "Narration / Purpose",
			"fieldtype": "Small Text",
			"insert_after": "custom_account_paid_from",
			"depends_on": DEPENDS_ON_DIRECT_GL,
			"description": "Copied into the standard 'remarks' on validate.",
		},
		# ── External Reference No ──────────────────────────────────
		{
			"fieldname": "custom_gl_reference_no",
			"label": "External Reference No",
			"fieldtype": "Data",
			"insert_after": "custom_gl_narration",
			"depends_on": DEPENDS_ON_DIRECT_GL,
			"description": "Optional cheque / UTR / challan no.",
		},
		# ── Reference Date ─────────────────────────────────────────
		{
			"fieldname": "custom_gl_reference_date",
			"label": "Reference Date",
			"fieldtype": "Date",
			"insert_after": "custom_gl_reference_no",
			"depends_on": DEPENDS_ON_DIRECT_GL,
			"description": "Optional instrument / challan date.",
		},
		# ── GL Mapping Preview (read-only) ─────────────────────────
		{
			"fieldname": "custom_gl_preview",
			"label": "GL Mapping Preview",
			"fieldtype": "Small Text",
			"insert_after": "custom_gl_reference_date",
			"read_only": 1,
			"depends_on": DEPENDS_ON_DIRECT_GL,
			"description": (
				"Read-only Dr X / Cr Y : amount preview updated by the "
				"Client Script so the user sees the balanced entry "
				"before Submit."
			),
		},
	],
}


def install_custom_fields():
	"""Upsert every Custom Field declared in CUSTOM_FIELDS_SPEC. Safe
	to run multiple times: create_custom_fields matches on (dt, fieldname)
	and updates in place."""
	create_custom_fields(CUSTOM_FIELDS_SPEC, ignore_validate=True)
	_install_property_setters()
	frappe.clear_cache(doctype=PE)


# Property Setters that make party_type / party / party-driven fields
# NON-mandatory in Direct GL mode. Without these, Frappe's built-in
# mandatory check fires before our doc_events['validate'] hook and
# throws "Party Type is mandatory" — see [[feedback-pe-meta-cache]]
# for why we upsert Property Setters in code rather than Customize Form.
_STANDARD_ONLY_MANDATORY = 'eval:!doc.custom_is_direct_gl_payment'
PROPERTY_SETTERS = [
	# party_type: mandatory only when Direct GL toggle is OFF.
	{
		"doctype_or_field": "DocField",
		"doc_type": PE,
		"field_name": "party_type",
		"property": "mandatory_depends_on",
		"property_type": "Data",
		"value": _STANDARD_ONLY_MANDATORY,
	},
	{
		"doctype_or_field": "DocField",
		"doc_type": PE,
		"field_name": "party_type",
		"property": "reqd",
		"property_type": "Check",
		"value": "0",
	},
	{
		"doctype_or_field": "DocField",
		"doc_type": PE,
		"field_name": "party",
		"property": "mandatory_depends_on",
		"property_type": "Data",
		"value": _STANDARD_ONLY_MANDATORY,
	},
	{
		"doctype_or_field": "DocField",
		"doc_type": PE,
		"field_name": "party",
		"property": "reqd",
		"property_type": "Check",
		"value": "0",
	},
	# paid_from / paid_to: FR-24 relaxes the account_type filter (done
	# via the L-15 patch), but the fields themselves stay required.
	# No Property Setter needed there — the base DocField reqd is fine.
]


def _install_property_setters():
	"""Idempotent upsert of PROPERTY_SETTERS. Property Setter name is
	deterministic: `<doctype>-<field>-<property>` so a re-run just
	updates the row's value in place."""
	for spec in PROPERTY_SETTERS:
		name = "{}-{}-{}".format(spec["doc_type"], spec["field_name"],
		                        spec["property"])
		if frappe.db.exists("Property Setter", name):
			ps = frappe.get_doc("Property Setter", name)
			if ps.value != spec["value"]:
				ps.value = spec["value"]
				ps.save(ignore_permissions=True)
		else:
			ps = frappe.new_doc("Property Setter")
			ps.update(spec)
			ps.insert(ignore_permissions=True)


def uninstall_custom_fields():
	"""Remove every field this app declared. Used on `before_uninstall`
	so a `bench uninstall-app reformiqo_pe` leaves Payment Entry clean.
	"""
	for _, specs in CUSTOM_FIELDS_SPEC.items():
		for spec in specs:
			name = f"{PE}-{spec['fieldname']}"
			if frappe.db.exists("Custom Field", name):
				frappe.delete_doc("Custom Field", name,
					ignore_permissions=True, force=1)
	# Also drop the Property Setters we installed so uninstall is
	# fully reversible.
	for spec in PROPERTY_SETTERS:
		name = "{}-{}-{}".format(spec["doc_type"], spec["field_name"],
		                        spec["property"])
		if frappe.db.exists("Property Setter", name):
			frappe.delete_doc("Property Setter", name,
				ignore_permissions=True, force=1)
	frappe.clear_cache(doctype=PE)


def after_install():
	install_custom_fields()


def after_migrate():
	install_custom_fields()


def before_uninstall():
	uninstall_custom_fields()
