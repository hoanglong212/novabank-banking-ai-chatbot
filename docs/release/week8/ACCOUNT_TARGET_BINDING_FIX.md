# Account-status target binding fix

The previous `bind_proposal` checked account/status equality only when general
`bind(text)` selected `propose_account_status`. A ticket reference instead selected
`read_ticket`, skipping that check. A model could propose Bob although the staff
member said to freeze Charlie and merely mentioned that Bob was fine.

`account_status_target` now extracts one explicit action/account pair from the
staff member's own latest message, independently of ticket routing. The selected
account and status must equal that pair. Unrelated earlier account mentions do
not become targets. Existing quotation, negation and memo exclusions remain;
ambiguous multiple actions require clarification. Vietnamese verbs are matched
against the same folded text as the existing affirmative-command gate.

Evidence on `week8/integration`:

- RED: all five new HTTP regression cases failed on the previous code.
- GREEN: the five cases now reject the substituted Bob target without creating
  an approval. Fresh staff input explicitly naming Charlie creates a PENDING
  proposal. Account states remain unchanged until human approval.
- Variants cover ticket references, introductory clauses, unrelated account
  mention before the target, unfreezing and Vietnamese input.
- `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_staff_account_binding.py backend/tests/test_gateway.py backend/tests/test_admin_agent.py backend/tests/test_gateway_audit.py backend/tests/test_rbac_proposals.py -q`:
  **162 passed in 57.91 s**.

This resolves the specific inherited P1 reported against `b5145ac`; it does not
claim all account authorization or natural-language interpretation is infallible.
Raw RED/GREEN logs are retained under ignored `.local/week8-r1/`. No proposal was
approved by the new regression tests, and no live database was used.
