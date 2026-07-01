# ABP2-I481 — Client UAT Script

**Feature:** Generic / Direct GL Payment Entry
**FRD:** v2.0 (BalanceSheet-flavoured PDF, Nainsi 2026-07-01)
**Site under test:** _{{TBD by tester}}_
**Tester:** _{{name}}_
**Date:** _{{date}}_

## 0. Pre-flight

- [ ] `reformiqo_pe` installed on the site (bench group → App list).
- [ ] Site migrated after install (Frappe Cloud → Migrate).
- [ ] Login as an **Accounts User** (not Administrator) so we exercise the real permission scope.
- [ ] Chart of Accounts already carries the required ledger heads (Loan Account, Interest Expense, Bank Charges, Rent Expense, Bank Account, Partner Capital, Cash, etc.). Add any missing ones via Accounting → Chart of Accounts before starting.

## 1. TC-01 — Standard mode untouched

_Every existing Customer / Supplier / Employee Payment Entry must behave EXACTLY as before._

1. Open **Accounting → Payment Entry → + Add Payment Entry**.
2. Leave the **Direct GL Payment** toggle OFF (default).
3. Select **Payment Type = Receive**, **Party Type = Customer**, pick any customer.
4. Fill Received Amount, Paid To, References (link a Sales Invoice), Save + Submit.
5. **Expected:** works exactly as before. Party balance updates. References allocate. No new fields interfere.

☐ PASS ☐ FAIL — Notes: _______________

## 2. TC-02 — Bank charges (Pay)

_A payment with no counter-party. Pure debit-charges credit-bank._

1. **+ Add Payment Entry**.
2. Switch to the **General / Direct GL** tab.
3. Check **Direct GL Payment**. Verify:
   - Party Type / Party fields disappear.
   - Category and Direction dropdowns appear.
   - Two child tables (Account Paid To / Account Paid From) appear.
4. Category = **Bank Charges**. Direction should auto-set to **Pay (Outflow)**.
5. Account Paid To (Debit) row 1: Account = Bank Charges Expense, Cost Center = HO, Amount = **250**.
6. Account Paid From (Credit) row 1: Account = HDFC Bank A/c, Amount = **250**.
7. Narration = "January bank charges — HDFC statement".
8. Save. GL Mapping Preview should show `Dr Bank Charges Expense 250.00 (CC HO)` / `Cr HDFC Bank A/c 250.00`.
9. Submit.
10. Click **Ledger** button. Expected 2 GL Entries: Dr Bank Charges 250 stamped `HO`, Cr HDFC 250.

☐ PASS ☐ FAIL — Notes: _______________

## 3. TC-03 — Interest received (Receive)

1. New PE, toggle Direct GL ON.
2. Category = **Interest Received**. Direction auto-sets to **Receive (Inflow)**.
3. Paid To (Debit): HDFC Bank A/c, Amount = 5,000.
4. Paid From (Credit): Interest Income, Amount = 5,000.
5. Submit. Ledger: Dr HDFC 5000, Cr Interest Income 5000.

☐ PASS ☐ FAIL — Notes: _______________

## 4. TC-04 — Cash withdrawal (Contra)

1. New PE, toggle Direct GL ON.
2. Category = _(pick anything, then manually change)_. Direction = **Contra (Internal Transfer)**.
3. Paid To (Debit): Cash-in-Hand, Amount = 10,000.
4. Paid From (Credit): HDFC Bank A/c, Amount = 10,000.
5. Submit. Ledger: Dr Cash 10000, Cr HDFC 10000.

☐ PASS ☐ FAIL — Notes: _______________

## 5. TC-05 — Capital introduction

1. New PE, Direct GL ON. Category = **Capital Introduction**. Direction = Receive (Inflow) auto.
2. Paid To (Debit): HDFC Bank, Amount = 100,000.
3. Paid From (Credit): Partner Capital A/c, Amount = 100,000.
4. Submit. Ledger: Dr HDFC 100000, Cr Partner Capital 100000.

☐ PASS ☐ FAIL — Notes: _______________

## 6. TC-06 — Cost Center stamped on GL

1. Any of the above — after submit, open the GL Entry via **Ledger** button.
2. Every GL row must carry the Cost Center you picked on the child row.

☐ PASS ☐ FAIL — Notes: _______________

## 7. TC-07 — Finance Book stamped (Should)

1. Repeat TC-02 but on the header set **Finance Book = _{your book_**.
2. Submit. GL Entries must carry that Finance Book value.

☐ PASS ☐ FAIL — Notes: _______________

## 8. TC-08 — Receivable head blocked without party

1. New PE, Direct GL ON. Category = Misc Expense.
2. Paid To row: pick a **Receivable-type** account (e.g. Sundry Debtors) WITHOUT filling Party Type / Party.
3. Paid From: any bank, same amount.
4. Save.
5. **Expected:** Server rejects with a message like _"Account X is a Receivable type — it needs a party. Fill Party Type + Party on the row, or use the standard Payment Entry."_

☐ PASS ☐ FAIL — Notes: _______________

## 9. TC-09 — Missing data guard

Three quick sub-scenarios — each must throw a clear message:

- **9a** Add row to Paid To with **Account blank**, Amount 500. Save → "Account is required on every Debit (Paid To) line (row 1)."
- **9b** Amount **= 0** on row 1. Save → "Amount must be greater than 0 on Debit (Paid To) row 1."
- **9c** Delete every row from Paid To (empty table). Save → "Add at least one row to Account Paid To (Debit)."

☐ PASS ☐ FAIL — Notes: _______________

## 10. TC-10 — Same-account guard

1. Paid To (Debit) row 1 Account = HDFC Bank. Paid From row 1 Account = HDFC Bank. Same amount.
2. Save. Must reject: "The first Debit and Credit rows post to the same account (HDFC Bank). That would net to zero — split them across different ledgers."

☐ PASS ☐ FAIL — Notes: _______________

## 11. TC-11 — Narration → remarks

1. New PE, Direct GL ON. Fill Narration = "June utilities + bank charges".
2. Fill valid rows, Save. Reload the doc. Standard **Remarks** field on the Details tab should also read "June utilities + bank charges".

☐ PASS ☐ FAIL — Notes: _______________

## 12. TC-12 — Cancel reverses GL

1. Open any submitted Direct GL Payment Entry from TCs above.
2. Click **Cancel**. Confirm.
3. Reopen its Ledger. Every original GL Entry must have a matching reversal (opposite Dr/Cr) tied to the same voucher_no. Audit trail intact (status: Cancelled).

☐ PASS ☐ FAIL — Notes: _______________

## 13. TC-13 — Multi-leg EMI (multiple debit lines)

_One credit line (Bank) balancing THREE debit lines._

1. New PE, Direct GL ON. Category = Misc Expense.
2. Paid To (Debit) 3 rows: Rent 40000 (CC A, Proj P1), Electricity 15000 (CC A, P1), Bank Charges 5000 (CC B, no project).
3. Paid From (Credit) 1 row: HDFC Bank 60000.
4. Save + Submit.
5. Ledger must show 4 GL Entries: Dr Rent 40000/CC A/P1, Dr Electricity 15000/CC A/P1, Dr Bank Charges 5000/CC B, Cr HDFC 60000.
6. Balance check: Σ Debit = Σ Credit = 60000.

☐ PASS ☐ FAIL — Notes: _______________

## 14. TC-14 — Multi-currency (Should)

_Only relevant if the client posts multi-currency PEs._

1. New PE, Direct GL ON. Set the primary leg to a foreign-currency account (e.g. USD bank).
2. Verify source_exchange_rate / target_exchange_rate get populated from the currency master.
3. GL Entries post in base currency; FX difference (if any) routes to the configured Exchange Gain/Loss account.

☐ PASS ☐ FAIL — N/A ☐ — Notes: _______________

## 15. Add a new Category (FR-23)

_Prove the category list is admin-editable with no code change._

1. Log in as System Manager.
2. Customize Form → Payment Entry → find `custom_gl_payment_category`.
3. Add "Franchise Fee" on its own line under Options. Update.
4. Open a new Payment Entry, Direct GL ON. Category dropdown must now include "Franchise Fee".

☐ PASS ☐ FAIL — Notes: _______________

## 16. Print format

1. Open any submitted Direct GL PE.
2. Print → pick format **"Direct GL Voucher"**.
3. Voucher should render: header block, category + direction, two Debit / Credit panels with all rows + totals, green balance-check banner, three signature lines.

☐ PASS ☐ FAIL — Notes: _______________

## Sign-off

I confirm that scenarios 1–16 pass on the SEPPL live site as expected.

_For Client:_

Name: ______________________ Designation: _______________ Signature: ________________ Date: _______

_For Reformiqo:_

Name: ______________________ Designation: _______________ Signature: ________________ Date: _______
