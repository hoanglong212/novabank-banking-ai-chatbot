# Baseline — 2026-11-05

Commit: `44d87c3723760a82fd5dfab8803bb0d3198b92f8`. Existing user README modification preserved.

| Command | Observed result |
|---|---|
| `backend/.venv/Scripts/python.exe scripts/financial-coverage.py` | 359 passed, 157.50 s; financial executed-line coverage 93.58% |
| `npm run test:components` in frontend | 17 groups passed |
| `npm run test:e2e` in frontend | 16 passed, 1.7 minutes |

Raw logs: `.local/week7-baseline-backend.log`, `.local/week7-baseline-e2e.log`.
Local safety tag `pre-week7` and branch `week7/integration` created; no remote push.
No dependencies or models were installed during baseline checks. The original Ollama daemon returned an empty model list. Later deployment investigation found model files in `D:\Ollama\models`; the empty list did not establish their absence from disk.
