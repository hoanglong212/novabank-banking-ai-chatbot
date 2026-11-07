# Gateway investigation

User request: reproduce the reported prompt transfer, understand the deployed gateway, test actual bypasses, identify the admitting layer, fix or document before feature work.

Scope: current bank/isolated agent HTTP path; Qwen2.5:7b already installed locally, explicit baseline/defended, synthetic accounts in new disposable SQLite only. No real transfers or external target. Existing local deployment is inspected read-only until a verified fix is ready. No new dependencies. Existing unrelated edits preserved.

- [ ] Map prompt/input, intent binding, delegation, tool authorization, source screening, output, approval and OTP/ledger boundaries; distinguish legacy and research paths.
- [ ] Reproduce exact archived SYSTEM OVERRIDE prompt and new variants through real HTTP/model; capture input, decision/reason, answer, approvals/drafts/ledger changes.
- [ ] Exercise compromised-agent API boundaries independently of model refusal (owner, role, intent parameters, audience, cancellation, confirmation).
- [ ] Add failing regressions for demonstrated defects, minimal root-cause fixes, replay live cases and benign controls.
- [ ] Record reproducible commands, per-case evidence, tested limits and mentor-ready conclusions. Update local backend only after checks pass.

Do not report a proposed transfer as completed money movement. Do not count source not fetched, model/service failure, or an untested prompt as a successful defense. No blanket immunity claim. Historical demo cause remains unknown without its original run evidence.
