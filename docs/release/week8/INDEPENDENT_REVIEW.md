# Week8 scoped independent review

Reviewed on 2026-11-15 by agent `/root/week8_spotlighting` against the root worktree, including integrated uncommitted changes. This reviewer did not implement the reviewed C2 output boundary or C4 transfer step-up. The reviewer did implement spotlighting, QR hardening and synthetic seed generation, so this is not an independent review of those authored components or an external penetration test.

## Findings and verification

| Finding | Reproduction and consequence | Status |
|---|---|---|
| High: alias restoration after the output filter | Through normal customer APIs, save Bob as beneficiary and change the owner's display name to `<ACCOUNT_2>` with password and action OTP. A model answer `<NAME_1>` became the foreign account ID after a second restoration in preview/final. No vault mutation was needed. | Root removed post-filter restoration and checks canonical balance identifiers after restoration. The same public-API probe was rerun: HTTP 200 preview and final both contain literal `<ACCOUNT_2>`; `foreign_id_disclosed=false`. Parent reports ten focused red/green tests; those counts are not independently rerun here. |
| Medium: unsolicited credit debt bypasses minimization | After an authorized 50,000 VND card purchase, ask only for card status. In a valid isolated configuration C session, `get_cards` exposed `outstanding_vnd=50000`, and final prose disclosed the debt. This is unsolicited own-customer financial information, not a foreign-owner breach. | Reproduced and referred to the disclosure owner. Fix verification remains pending at this review snapshot. Include outstanding debt/credit classes and debt vocabulary without hiding authorized operational amounts. |

Probe setup used fresh temporary SQLite databases, normal login/action OTP and real HTTP application handlers under mock inference. It did not exercise a real model. No live user database was written. Reproduction scripts and raw results were kept in the review worktree's ignored `.local` directory; regression tests belong to the root integration owner.

## Other reviewed boundaries

- C4 proofs bind user, session, auth version, transfer fingerprint and enrolled factor; expiration and changed draft/factor invalidate them. Unknown recipients require TOTP step-up followed by a distinct email OTP. Posting remains bank-owned, transaction locked, token-bound and idempotent. No additional concrete bypass was found in this scoped inspection; this is not proof of absence.
- Provenance is monotone and carries source identities/hashes across conversation runs. Critical arguments must come from trusted request values, with a narrow bank-selected funding-account default. Token/lexical provenance is not a formal proof of semantic intent.
- Policy parsing rejects unknown fields, duplicate keys and malformed predicates. Missing/unreadable policy denies or fails the request; a parser failure does not authorize a tool. A-D weakening is restricted to authenticated, scoped, expiring lab sessions.
- `source_origin` is a client-declared capture label. An API client can submit `manual`; the label is not an authenticated QR fingerprint. New-payee trust and step-up must continue to derive from bank records independently of that label.
- `research.week8_runtime.servers` writes into a marked disposable evaluation directory, overrides `DB_PATH`, disables the worker and copies an optional manifest-marked synthetic seed with a read-only SQLite source connection. `assert_disposable` constrains paths and rejects hard-linked destinations. The seed CLI refuses existing target paths. These checks were inspected; arbitrary host compromise remains outside the threat model.

## Limits and handoff

The review covered C2 restoration/disclosure, C4 OTP/posting, provenance/policy failure behavior and evaluation DB isolation. It did not repeat the full backend, frontend or live-model matrix. The exact requested Qwen3 model and Prompt Guard 2 weights/runtime are unavailable; fail-closed unavailability is not a successful benign utility result. Eighteen configuration C smoke attacks with zero strict L1/L2/L3 outcomes do not establish the requested positive L1 baseline or the final ASR threshold. See the root release results for authoritative final checks and measurements.

This review supports concrete fixes and evidence-backed release notes. It does not certify that every feature is bug-free or that the system exceeds other banking systems.
