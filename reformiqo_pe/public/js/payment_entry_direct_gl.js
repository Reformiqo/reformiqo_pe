// ABP2-I481 — Generic / Direct GL Payment Entry (FRD v2.0)
// Client Script wiring: FRD §9 L-01..L-09 + L-14 preview.
//
// Loaded on every Payment Entry form via hooks.doctype_js. All logic
// is gated on `frm.doc.custom_is_direct_gl_payment` so standard party
// PEs are unaffected (TC-01).

frappe.provide("reformiqo_pe");

// FRD §4 category → suggested direction. User may override; we only
// AUTO-SET on category change, never overwrite an existing choice
// unless it's blank.
reformiqo_pe.CATEGORY_TO_DIRECTION = {
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
};

reformiqo_pe.is_direct_gl = function (frm) {
	return !!(frm && frm.doc && frm.doc.custom_is_direct_gl_payment);
};

// L-04 / L-05 — relaxed account get_query. Returns any non-group leaf
// ledger on the current company. Applied to child-table `account` and
// the header paid_from/paid_to fields.
reformiqo_pe.relaxed_account_query = function (frm) {
	return {
		filters: {
			company: frm.doc.company,
			is_group: 0,
		},
	};
};

// L-09 — GL preview: "Dr <paid_to> / Cr <paid_from> : <amount>".
// Multi-line safe: one line per row in either table.
reformiqo_pe.build_preview = function (frm) {
	const debits = (frm.doc.custom_account_paid_to || [])
		.filter((r) => r.account && r.amount)
		.map((r) => `Dr ${r.account} ${format_currency(r.amount)}` +
			(r.cost_center ? ` (CC ${r.cost_center})` : ""));
	const credits = (frm.doc.custom_account_paid_from || [])
		.filter((r) => r.account && r.amount)
		.map((r) => `Cr ${r.account} ${format_currency(r.amount)}` +
			(r.cost_center ? ` (CC ${r.cost_center})` : ""));
	if (!debits.length && !credits.length) return "";
	return [...debits, ...credits].join("\n");
};

reformiqo_pe.refresh_preview = function (frm) {
	if (!reformiqo_pe.is_direct_gl(frm)) return;
	const preview = reformiqo_pe.build_preview(frm);
	if ((frm.doc.custom_gl_preview || "") !== preview) {
		frm.set_value("custom_gl_preview", preview);
	}
};

// L-01 — Direct GL toggle turned ON. Hide party fields form-wide,
// empty the references table, drop party-driven mandatoriness.
reformiqo_pe.apply_direct_gl_on = function (frm) {
	// Hide the standard party controls everywhere they appear.
	["party_type", "party", "party_name", "party_balance",
		"party_bank_account", "contact_person", "contact_email"].forEach(
		(f) => frm.toggle_display(f, false));
	// References table — hide + empty
	frm.toggle_display("references_section", false);
	frm.toggle_display("references", false);
	if ((frm.doc.references || []).length) {
		frm.clear_table("references");
	}
	// Party-driven mandatoriness OFF
	["party_type", "party"].forEach((f) => frm.toggle_reqd(f, false));
	// Category + Direction + tables ON is done via the CF's own
	// depends_on/mandatory_depends_on — nothing to do here.
};

// L-02 — Direct GL toggle turned OFF. Restore standard behaviour.
reformiqo_pe.apply_direct_gl_off = function (frm) {
	["party_type", "party", "party_name", "party_balance"].forEach(
		(f) => frm.toggle_display(f, true));
	frm.toggle_display("references_section", true);
	frm.toggle_display("references", true);
	// Clear any generic-mode data so a switched-off voucher is
	// never half-GL (FR-28).
	["custom_gl_payment_category", "custom_gl_direction",
		"custom_gl_narration", "custom_gl_reference_no",
		"custom_gl_reference_date", "custom_gl_preview"].forEach(
		(f) => frm.set_value(f, null));
	if ((frm.doc.custom_account_paid_to || []).length) {
		frm.clear_table("custom_account_paid_to");
	}
	if ((frm.doc.custom_account_paid_from || []).length) {
		frm.clear_table("custom_account_paid_from");
	}
	frm.refresh_fields();
};

frappe.ui.form.on("Payment Entry", {
	refresh: function (frm) {
		// Apply the current toggle state on every refresh so a
		// re-opened submitted voucher also has the party fields
		// hidden if it was posted in Direct GL mode.
		if (reformiqo_pe.is_direct_gl(frm)) {
			reformiqo_pe.apply_direct_gl_on(frm);
			reformiqo_pe.refresh_preview(frm);
		}
		// Any-ledger get_query on the header paid_from / paid_to
		// (applies in BOTH modes per FR-24).
		frm.set_query("paid_from", () =>
			reformiqo_pe.relaxed_account_query(frm));
		frm.set_query("paid_to", () =>
			reformiqo_pe.relaxed_account_query(frm));
	},

	custom_is_direct_gl_payment: function (frm) {
		if (reformiqo_pe.is_direct_gl(frm)) {
			reformiqo_pe.apply_direct_gl_on(frm);
		} else {
			reformiqo_pe.apply_direct_gl_off(frm);
		}
	},

	// L-03 — Category change auto-derives Direction.
	custom_gl_payment_category: function (frm) {
		if (!reformiqo_pe.is_direct_gl(frm)) return;
		const cat = frm.doc.custom_gl_payment_category;
		if (!cat) return;
		const suggested = reformiqo_pe.CATEGORY_TO_DIRECTION[cat];
		if (suggested && !frm.doc.custom_gl_direction) {
			frm.set_value("custom_gl_direction", suggested);
		}
	},

	custom_gl_direction: function (frm) {
		if (!reformiqo_pe.is_direct_gl(frm)) return;
		reformiqo_pe.refresh_preview(frm);
	},

	custom_gl_narration: function (frm) {
		// L-10 (server) copies narration → remarks on validate. For
		// visual parity in the UI, mirror the change into the standard
		// 'remarks' field so users don't wonder where their text went.
		if (!reformiqo_pe.is_direct_gl(frm)) return;
		if (frm.doc.custom_gl_narration &&
			frm.doc.custom_gl_narration !== frm.doc.remarks) {
			frm.set_value("remarks", frm.doc.custom_gl_narration);
		}
	},
});

// L-04 — Child-table account get_query for both tables.
["Account Paid To", "Account Paid From"].forEach((child) => {
	frappe.ui.form.on(child, {
		account: function (frm) {
			reformiqo_pe.refresh_preview(frm);
		},
		amount: function (frm) {
			reformiqo_pe.refresh_preview(frm);
		},
		cost_center: function (frm) {
			reformiqo_pe.refresh_preview(frm);
		},
		[child === "Account Paid To" ?
			"custom_account_paid_to_add" :
			"custom_account_paid_from_add"]: function (frm) {
			reformiqo_pe.refresh_preview(frm);
		},
	});
});

// Bind the get_query for child-table account fields when the form
// loads. This is done via setup so the query is registered before the
// user starts editing.
frappe.ui.form.on("Payment Entry", {
	setup: function (frm) {
		frm.set_query("account", "custom_account_paid_to", () =>
			reformiqo_pe.relaxed_account_query(frm));
		frm.set_query("account", "custom_account_paid_from", () =>
			reformiqo_pe.relaxed_account_query(frm));
	},
});
