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
	_install_client_script()
	frappe.clear_cache(doctype=PE)


# ABP2-I481 re-reopen #4 (Sahil 2026-07-01, Image #66): the bundled
# public/js patch never survived — either Frappe Cloud didn't rebuild,
# or the browser cached a stale bundle. Sahil asked explicitly for a
# Client Script. This one lives in the DB, is loaded by Frappe on
# every Payment Entry form render, and needs no bench build to
# activate. See [[feedback-client-scripts-fixtures]] for the pattern.
_CLIENT_SCRIPT_NAME = "Payment Entry - Reformiqo PE Relax Mandatory"
_CLIENT_SCRIPT_BODY = r"""
// ABP2-I481 re-reopen #4 — Reformiqo PE
// Relax client-side mandatory checks on the Payment Entry fields we
// autowire server-side so the "Missing Fields" alert never blocks
// save on Paid Amount / Received Amount / Project / Cost Center /
// Party / Paid From / Paid To. Server (ERPNext) still enforces
// genuine invalidity on submit.
(function () {
    var RELAXED = [
        "party_type", "party", "party_name", "party_balance",
        "party_bank_account", "contact_person", "contact_email",
        "paid_from", "paid_to",
        "paid_amount", "received_amount",
        "paid_from_account_currency", "paid_to_account_currency",
        "source_exchange_rate", "target_exchange_rate",
        "reference_no", "reference_date",
        "project", "cost_center"
    ];
    var RELAXED_SET = {};
    for (var i = 0; i < RELAXED.length; i++) RELAXED_SET[RELAXED[i]] = 1;

    function strip_mandatory(frm) {
        RELAXED.forEach(function (f) {
            if (frm.fields_dict[f]) {
                frm.fields_dict[f].df.reqd = 0;
                frm.fields_dict[f].df.mandatory_depends_on = "";
                try { frm.toggle_reqd(f, false); } catch (e) {}
            }
            var meta_list = frappe.meta.docfield_list["Payment Entry"] || [];
            for (var j = 0; j < meta_list.length; j++) {
                if (meta_list[j].fieldname === f) {
                    meta_list[j].reqd = 0;
                    meta_list[j].mandatory_depends_on = "";
                }
            }
            try {
                var per_doc = frappe.meta.get_docfield("Payment Entry", f, frm.doc.name);
                if (per_doc) {
                    per_doc.reqd = 0;
                    per_doc.mandatory_depends_on = "";
                }
            } catch (e) {}
        });
    }

    // Wrap check_mandatory once so no race condition in ERPNext's
    // controller can undo our strip between refresh and save.
    if (!window.__reformiqo_pe_check_mandatory_wrapped) {
        window.__reformiqo_pe_check_mandatory_wrapped = 1;
        var _orig = frappe.ui.form.check_mandatory;
        frappe.ui.form.check_mandatory = function (frm) {
            try {
                if (frm && frm.doc && frm.doc.doctype === "Payment Entry") {
                    var dfl = frappe.meta.docfield_list["Payment Entry"] || [];
                    for (var k = 0; k < dfl.length; k++) {
                        if (RELAXED_SET[dfl[k].fieldname]) {
                            dfl[k].reqd = 0;
                            dfl[k].mandatory_depends_on = "";
                        }
                    }
                }
            } catch (e) { console.warn("reformiqo_pe pre-patch failed", e); }
            return _orig.apply(this, arguments);
        };
    }

    frappe.ui.form.on("Payment Entry", {
        refresh:     function (frm) { strip_mandatory(frm); },
        onload:      function (frm) { strip_mandatory(frm); },
        before_save: function (frm) { strip_mandatory(frm); },
        validate:    function (frm) { strip_mandatory(frm); }
    });
})();
"""


def _install_client_script():
	"""Upsert the Client Script that relaxes PE mandatory checks.
	Lives in the DB so Frappe loads it on every form render — no
	bench build required, no browser bundle to invalidate."""
	if frappe.db.exists("Client Script", _CLIENT_SCRIPT_NAME):
		cs = frappe.get_doc("Client Script", _CLIENT_SCRIPT_NAME)
		if cs.script != _CLIENT_SCRIPT_BODY.strip():
			cs.script = _CLIENT_SCRIPT_BODY.strip()
			cs.enabled = 1
			cs.save(ignore_permissions=True)
	else:
		cs = frappe.new_doc("Client Script")
		cs.name = _CLIENT_SCRIPT_NAME
		cs.dt = PE
		cs.view = "Form"
		cs.enabled = 1
		cs.script = _CLIENT_SCRIPT_BODY.strip()
		cs.insert(ignore_permissions=True)


# Property Setters that make party_type / party / party-driven fields
# NON-mandatory in Direct GL mode. Without these, Frappe's built-in
# mandatory check fires before our doc_events['validate'] hook and
# throws "Party Type is mandatory" — see [[feedback-pe-meta-cache]]
# for why we upsert Property Setters in code rather than Customize Form.
_STANDARD_ONLY_MANDATORY = 'eval:!doc.custom_is_direct_gl_payment'


def _ps(field_name, prop, value, property_type="Data"):
	return {
		"doctype_or_field": "DocField",
		"doc_type": PE,
		"field_name": field_name,
		"property": prop,
		"property_type": property_type,
		"value": value,
	}


# Fields Frappe's client-side check_mandatory would otherwise block save
# on. All are populated SERVER-side by our autowire hook, but the client
# fires check_mandatory BEFORE the request even leaves the browser. So we
# also flip reqd=0 + mandatory_depends_on=<standard-only> at the meta
# layer via Property Setters. See [[feedback-pe-meta-cache]].
_DIRECT_GL_OPTIONAL_FIELDS = (
	"party_type", "party",
	"paid_from", "paid_to",
	"paid_amount", "received_amount",
	"paid_from_account_currency", "paid_to_account_currency",
	"source_exchange_rate", "target_exchange_rate",
	"reference_no", "reference_date",
	# ABP2-I481 re-reopen (Sahil 2026-07-01, Image #63): on the Panchhi
	# bench (and any tenant that flipped these two to reqd=1 via a
	# Custom Field), the client-side check_mandatory blocks save with
	# "Project / Cost Center is mandatory" even though every row in
	# our Debit / Credit child tables already carries its own CC and
	# Project. Header-level CC + Project are NOT needed in Direct GL
	# mode — the per-line values are what stamp on the GL entry.
	"project", "cost_center",
)

PROPERTY_SETTERS = []
for _f in _DIRECT_GL_OPTIONAL_FIELDS:
	# ABP2-I481 re-reopen #2 (Sahil 2026-07-01, Image #64): the
	# `eval:!doc.custom_is_direct_gl_payment` condition kept these
	# fields client-side mandatory when Direct GL was off, and Sahil
	# hit the alert repeatedly. Per his ask ("we need to override"),
	# unconditionally clear reqd + wipe mandatory_depends_on so the
	# browser NEVER blocks save on these fields.
	# Server-side safety net:
	#   * Direct GL mode  → autowire_native_fields_before_submit
	#     populates paid_amount / received_amount / paid_from / paid_to
	#     from the child tables before ERPNext's validate runs.
	#   * Standard mode   → ERPNext's own validate_mandatory
	#     (payment_entry.py:646) still throws "Paid Amount is
	#     mandatory" server-side, so a truly-empty standard PE can't
	#     submit. Only the client-side pre-check is relaxed.
	PROPERTY_SETTERS.append(_ps(_f, "mandatory_depends_on", ""))
	PROPERTY_SETTERS.append(_ps(_f, "reqd", "0", property_type="Check"))


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
	# Also drop the Client Script + Property Setters so uninstall is
	# fully reversible.
	if frappe.db.exists("Client Script", _CLIENT_SCRIPT_NAME):
		frappe.delete_doc("Client Script", _CLIENT_SCRIPT_NAME,
			ignore_permissions=True, force=1)
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
