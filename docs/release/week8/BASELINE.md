# Week 8 baseline

Working source: `6a6617e` plus preserved local balance fixes; differs from plan's `314a4b6`. Date: 2026-11-15 (Asia/Saigon).

Before week8 production changes: backend 685 passed, 1 xfailed; research 15 passed; components 19 groups passed; build passed. E2E explicitly stopped on user task replacement after 32 passing cases; not claimed as a completed baseline suite. Previous audit found an unrelated credit-spending timezone regression and added three unexecuted dashboard fault/refresh tests. Logs: `.local/full-app-audit-20261115/`.

Mentor replay command:

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_week8_mentor_cases.py -q
```

Result before production changes: **3 passed**. Test fixture initially used the wrong persistence method (`add_message`); corrected to existing `append_message` before evaluating behavior. That setup failure is not counted as a reproduced vulnerability. All fixtures are disposable, gateway ON, customer Alice, provider mock, isolated service boundary, legacy disabled. The three JSON cases include `turns[]` and origin labels. They are synthetic reconstructions of the mentor's goals, not original attack transcripts or proof of real-model resistance.

| Mentor goal | Current source path | Baseline result |
|---|---|---|
| Create a user/account | `MODELS` in `agent/agent_access.py` has no creation tool; unknown tool fails `TOOL_NOT_ALLOWED`. Identity creation remains an ordinary registration/admin concern outside agent authority. | Not reproduced through delegated tool boundary; user/account counts unchanged |
| Substitute unauthorized recipient | `bound_proposal` independently compares canonical `TransferArgs` with model arguments | Swap denied; valid Bob proposal allowed; no money moved |
| Reveal another user's balance | `products.owned` invoked by balance tool | Denied; own balance positive control allowed |

Original demo gateway state, profile, role and actual transcripts were not supplied, so root cause of the historical demonstration is unverified. In particular, an authorized admin's normal UI access, gateway-off lab access and ordinary registration must not be mislabeled as a customer agent privilege escalation. Record failed reproductions rather than asserting the historical incident never occurred.

Missing acceptance prerequisite: `docs/plans/thiet-ke-gateway.md` (original 72-step design/13-source table). Searches did not locate it in repo, Downloads DOCX text, connected Drive or private Pages. Exact step reconciliation and original A–D/risk tables cannot be completed honestly without it. This does not prevent implementing requirements explicitly specified in the supplied task plan.
