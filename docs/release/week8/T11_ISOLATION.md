# T11 isolated ticket reader

The staff proposal workflow remains subject to normal role, signed capability, intent and human-approval checks. This module does not grant authority, send replies, change tickets or read a database. Its purpose is to prevent ticket prose from becoming instructions in the main agent's context.

## Interface and integration

```python
from app.agent.quarantined_llm import isolate_ticket

views = await isolate_ticket(raw_ticket_result, role=user.role)
# Persist views['human'] and views['method'] in an authorized human-only view.
# Never merge that view into a tool result or the main model's messages.
if views['main'].get('unreadable'):
    # Fail closed: deny this tool result. Do not fall back to the raw ticket.
    ...
else:
    result_for_main_model = views['main']
```

The parent integration should call this after `staff_tools.execute(..., 'read_ticket', ...)`, before storing or returning the model-facing result. Pass `user.role` from the authenticated principal; never accept the role from model arguments. Existing human ticket routes still retrieve the original ticket/thread with their current authorization. Human summaries should be stored separately and served only to the ticket's authorized staff/customer view. Do not put summaries into agent trace or classifier details that are later replayed to the main model.

The isolated model receives only bounded subject/description/thread text. It receives no tools, delegated token, bank records or policy documents. Secret-pattern redaction precedes the request. Input is bounded to 8,000 characters, output to 8,000 characters, and time to 12 seconds by default (configurable up to 30 seconds). The expected local model is `llama3.2:3b`; no dependency installation or model download occurs.

The request uses Ollama's JSON-schema `format`; the bank validates that schema again. Fields are exactly `category`, `urgency`, `mentions_instruction` and `summary`. Enum values and a strict boolean are required, unknown fields/duplicate JSON keys are rejected, and the summary must be plain text of at most 200 characters without links, control characters or markup. Failure returns `unreadable`; cancellation propagates.

`main` is built by a whitelist, not by deleting a few dangerous fields from the original result. It contains category/urgency/instruction enums, allowed ticket status/language, and allowed structured customer record facts. It contains no ticket/customer/account/transfer identifiers, names, free-form failure reasons, policy prose, subject, description, thread or summary. Explicitly requested ticket routing identity remains available from the staff's original message/bank DTO; do not reconstruct it from model prose.

For support role, financial amounts and balances are omitted. Admin/operations/auditor retain only the existing numeric fact fields and statuses; this adapter does not expand their API permissions. Actual authorization is still enforced before calling the adapter.

## Legitimate replies and deterministic validation

Existing `staff_tools.ticket_facts` reads original ticket text independently inside deterministic reply validation to check quoted numbers and response language. That does not place the text in the main model's context and need not be removed to enforce this boundary. Numeric grounding remains an additional check, not authorization.

Without the free-form customer text/policy passage, the main model must produce category/status-based replies that acknowledge the issue and ask authorized staff to investigate unknown causes. It must not guess causes, deadlines or completed actions. Server-owned category guidance can improve these replies; free-text summaries must not be used as a shortcut. Main agent tool offerings should also be narrowed to the explicit bound staff task: a ticket-reply request should not advertise account-freeze tools merely because the role is admin. Provenance and signed capabilities must still deny any substituted account target independently.

## Validation evidence

- Red run: 18 tests failed because `quarantined_llm` did not exist (`t11-red.log` in this worktree).
- Focused green: `backend/tests/test_quarantined_llm.py`, **20 passed**, rerun after defensive input-length/direct-helper validation tightening.
- Ruff: new adapter and tests passed configured checks.
- Tests cover poisoned ticket and summary separation, strict schema and malformed JSON, no raw fallback, role-based numeric minimization, explicit mock labeling, no tools in the HTTP request, fixed schema, bounded text and cancellation.
- `provider=mock` is an explicitly labeled `mock_rules_only` mode using fixed enums and deterministic instruction screening. It never calls a live model and must not be counted as real-model evaluation.
- Real local model observations are in `t11-live-evidence.json`: both synthetic llama3.2 calls exhausted the configured 30-second budget and returned unreadable without raw fallback. **Real-model benign utility is not established.** These are two synthetic isolated calls, not full banking/main-agent acceptance or a measured attack-success rate. Full integration, serial model acceptance, main-model tool behavior and authorized human-summary readback remain the parent's verification responsibility.

No existing production file was modified by this isolated task. Only the new adapter, focused tests and this documentation/evidence are committed.

## Integrated serial recheck

The root integration now stores the summary encrypted and shows it only in authorized staff run trace, with an explicit untrusted-assessment notice and link to the original ticket UI. The main model receives whitelisted enums only. Ticket-reply intent no longer offers unrelated account status tools.

[Two later serialized live calls](../week8-evidence/t11-live-recheck.json) to installed Llama3.2:3b returned valid schemas in 5.568s and 0.388s. The ordinary pending-card request produced `mentions_instruction=false`; the instruction-bearing ticket produced `true`. The summary remained absent from `main` in both. These are schema/isolation observations, not full banking acceptance or semantic accuracy: even the card request was categorized ACCOUNT. The original concurrent/time-limited failures remain recorded, rather than being overwritten by these later successes.
