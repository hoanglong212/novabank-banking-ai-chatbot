# C6 reproducible realistic synthetic data

All names, accounts, employers, merchants and requests are fictional. Email addresses use reserved `.test` domains. The generator creates a **new** database only; it does not connect to the running demo or reseed an existing file.

## Actual generated dataset

CLI run on 2026-11-15, seed 20261115, fixed anchor 2026-11-15 and six months 2026-06 through 2026-11:

| Item | Count |
|---|---|
| Customers with Vietnamese display names | 50 |
| Payment accounts, each customer has 2 or 3 | 125 |
| Staff, three per support/operations/auditor/admin role | 12 |
| Posted payment-account transactions | 4,150 |
| Ledger entries | 8,900 |
| Saved internal recipients | 150 |
| Debit/credit cards | 100 |
| Card purchases/repayments | 600 |
| Bills: 50 paid, 150 unpaid | 200 |
| Term savings / linked goals | 50 / 50 |
| Support tickets: 50 open, 50 resolved | 100 |

`manifest-20261115.json` is the actual CLI result. SQLite integrity and foreign keys passed; ledger reconciliation was balanced. The manifest's business fingerprint was `58e358900b644940d510e365097301a967fd705df82f1143fbf1b861ce075aab`.

Income, expenses, credit purchases/repayments, savings and bill payment use the existing bank posting/product functions. Every financial journal balances. New accounts begin at zero, and all seed activity is posted; the seven display-only legacy demo transactions are deliberately excluded. Events are ordered by business date for consistent recorded balances. Card debt remains within configured limits. Terms, labels, dates and integer VND values are synthetic fixture choices, not observations about real customers.

## Reproduce without overwriting

From repository root:

```powershell
backend/.venv/Scripts/python.exe scripts/seed_realistic.py --output .local/week8/realistic-NEW.sqlite3 --seed 20261115
```

`--seedvalue` is an alias for `--seed`. Choose a new output name every time. Existing database/report/SQLite sidecar/MFA-key files and named symbolic links are refused. File reservation uses exclusive creation. A failure leaves the new target for diagnosis rather than deleting it or touching an older database. The adjacent `.seed.json` manifest is also written exclusively.

The generator calls the current `Database.initialize()` and does not hard-code a maximum schema version. It may be replayed after later registered migrations. Existing Alice/Bob/Charlie demo credentials remain available. Added customer/staff identities receive random, unlogged passwords and salts; use the ordinary simulated recovery flow if an added identity needs interactive access. Credentials are not included in this manifest.

Business IDs, dates and values are reproducible for the same code/schema and seed. Password hashes, security material and operational audit timestamps are intentionally not byte-reproducible. The fingerprint excludes those items. UUID/date overrides are scoped to this offline generator and restored in `finally`; do not invoke this script as an in-process utility inside a concurrently running bank server.

## Regression evidence

`backend/tests/test_realistic_seed.py` initially failed because the generator did not exist. A subsequent bill-variety assertion correctly failed with 0 paid bills. After implementation, **3 tests passed in 48.69 seconds**: complete dataset/ledger/integrity, refusal to overwrite, and matching business fingerprints from two independent databases with seed 23. Ruff and `git diff --check` passed. The actual CLI run above also exited 0.

These artifacts prove dataset construction and reproducibility. The root subsequently ran a selected A–D N=10 experiment on read-only copies of this dataset; its measured numbers and excluded trials are in [RESULTS.md](../../week8/RESULTS.md). This is not the full requested two-model/source/goal matrix. A separate final-source real Qwen/D demo verified the two-account balance and an approved, OTP-confirmed customer transfer-limit change.
