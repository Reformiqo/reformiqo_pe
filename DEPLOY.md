# ABP2-I481 — Deploy Checklist (Frappe Cloud)

**Target sites (in order):**

1. `detox.m.frappe.cloud` (SEPPL)
2. Others (DGEPL / DCPL / Palriwal) once client signs off on SEPPL

## 0. Pre-requisites

- [x] Repo `Reformiqo/reformiqo_pe` exists and is **Public** on GitHub.
- [x] All 4 phases committed (`main` = f9264a4 + df903a6).
- [ ] Frappe Cloud login (Momodou's account).

## 1. Add the app to the bench group

1. Frappe Cloud → **Bench Groups** → pick the SEPPL bench group.
2. **Apps** tab → **+ Add App**.
3. Source: **Public GitHub repository**.
4. Repository URL: `https://github.com/Reformiqo/reformiqo_pe`
5. Branch: `main`
6. Click **Add**. Frappe Cloud will fetch + validate the app.
7. When it appears in the list, click **Deploy** to build a new bench version with `reformiqo_pe` baked in.
8. Wait for the build (~5–10 min).

## 2. Install on the SEPPL site

1. Once the deploy is Complete → **Sites** → `detox.m.frappe.cloud`.
2. **Apps** tab → **Install App** → pick `Reformiqo PE`.
3. Confirm. Frappe Cloud runs `bench install-app reformiqo_pe`. This will:
   - Register the `Reformiqo PE` module
   - Create the 2 child DocTypes (Account Paid To / Account Paid From)
   - Fire `after_install` → upserts all 10 Custom Fields + 4 Property Setters on Payment Entry
   - Install the `Direct GL Voucher` print format

## 3. Verify install

Use the fcssh helper (see `~/.claude/projects/-home-frappe-v16-apps-detox-waste-management/memory/reference_fcssh_via_bash.md` for auth).

```bash
fcssh v16 detox.m.frappe.cloud <<'CMD'
bench --site detox.m.frappe.cloud console <<'PY'
import frappe
print("CFs:", frappe.db.count("Custom Field", {"dt": "Payment Entry", "fieldname": ["like", "custom_%gl%"]}))
print("Direct GL toggle:", frappe.db.exists("Custom Field", "Payment Entry-custom_is_direct_gl_payment"))
print("Paid To DT:", frappe.db.exists("DocType", "Account Paid To"))
print("Paid From DT:", frappe.db.exists("DocType", "Account Paid From"))
print("Print Format:", frappe.db.exists("Print Format", "Direct GL Voucher"))
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
print("L-15 patch:", getattr(PaymentEntry, "_reformiqo_pe_relaxed", False))
PY
CMD
```

Expected:
- CFs ≥ 5 (the gl-prefixed ones)
- Direct GL toggle: present
- Both child DocTypes: present
- Print Format: present
- L-15 patch: True

## 4. Smoke test one Direct GL PE on prod

Log into `https://seppl.erpera.io/` as Accounts User → Accounting → Payment Entry → New → toggle Direct GL Payment → follow **UAT.md §2 TC-02 Bank Charges (Pay)**. Confirm the voucher submits and posts 2 GL Entries with per-line CC.

## 5. Roll to DGEPL / DCPL / Palriwal

Repeat §1–§4 on each site's bench group. The 4 sites are on different bench groups on Frappe Cloud (per the app list on each site).

## 6. Rollback plan

If something breaks on prod:

1. Frappe Cloud → Site → **Apps** → uninstall `Reformiqo PE`. This fires `before_uninstall` which deletes every Custom Field + Property Setter the app installed. Payment Entry is left in its stock ERPNext state.
2. Site restart.
3. Check the standard Party payment flow (TC-01) still works.

_Note: the L-15 monkey patch on `validate_bank_accounts` unwinds automatically because the reformiqo_pe module is no longer imported by hooks after uninstall._

## 7. Announce to Sahil / Nainsi

Comment on the Zoho ticket (Momodou will draft — do NOT auto-post per [[feedback-no-unsolicited-zoho-comments]]):

> Direct GL Payment Entry deployed on SEPPL. Please walk through the UAT
> script in `Reformiqo/reformiqo_pe/UAT.md` and share findings for each
> TC. Once signed off, we'll roll to DGEPL / DCPL / Palriwal.
