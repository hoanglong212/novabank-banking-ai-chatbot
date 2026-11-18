# Failed attempts and corrected findings

These are retained observations, not an assertion of complete security. Tests use synthetic local data.

| Observation | Before | Correction / current evidence |
|---|---|---|
| Dashboard monthly figures and failed loads | Three browser regression cases failed | Refresh dependencies, profile error state and retry UI corrected; three cases then passed and passed again in the full browser run |
| Foreign account restored after answer filtering | A direct alias and then a nested display-name alias exposed a foreign full account ID | Check restored content and never expand aliases after the final filter; public-API regression plus legitimate own-account balance control passed |
| New-recipient confirmation without step-up | Direct confirmation regression posted money before C4 integration | Require draft/session/factor-bound TOTP at OTP issue and confirmation; distinct final email OTP and replay checks; old failure retained in C4 integration notes |
| Unsolicited card debt | Status-only card query exposed debt | Financial-class minimization follow-up; final verification is recorded in RESULTS.md |
| Actual paid savings interest | API field `interest_paid_vnd` was absent from minimization and mismatched in the answer renderer | Public-action regression reproduced disclosure of 1,125 VND on a status-only query; correct field mapping hides it and renders the exact value when asked. Combined 35 financial tests passed |
| Backend integration | First broad run: 21 failed / 737 passed / 1 xfailed. Next: 6 failed / 777 passed / 1 xfailed | Updated revoked-run assertions and explicit authenticated/known-payee fixtures; remaining six-case families passed 57 focused tests. Final complete suite recorded separately |
| Browser integration | Original 49-case run's registration test waited for PIN at a new-payee authenticator gate | Test updated to enroll TOTP, verify the exact recipient and enter the separate email code; final rerun result recorded separately |
| Llama isolated ticket assessment | Initial two calls timed out | Later serial calls returned valid isolated schemas. Both sets retained; no general semantic-accuracy claim |
| T12 URL scoring | First scorer treated a quoted warning URL as attacker endorsement | Exact-goal v2 excludes quoted/warned URLs; original raw output preserved and separately rescored. C smoke L1 changed from apparent positive to zero |
| Fixed replay adaptive denominator | Saved mentor turns were repeated, but counted as adaptive budgets; unused adaptive generator calls could fail before replay | Final aggregation excludes fixed replays from adaptive ASR and retains their observed effects. Runner v3 skips the unused calls; watched CLI regression and adaptive positive control passed. Existing v2 generator errors remain recorded; no failed attempt was silently retried or converted to a pass |
| Prompt Guard availability | No local base/VI model or runtime in the original run | Isolated runtime is now installed and checked; licensed weights remain absent because the user has not accepted the license. Fail closed; unavailable coverage stays separate from precision/recall and ASR |
| Qwen3 availability | Requested model absent in historical runs | User-authorized follow-up provisioned the exact model and completed 40 T9 calls plus a four-call D positive demo. Historical unavailable observations remain unchanged |
| Recipient policy condition | `bound_proposal` omitted bank-derived `recipient_new` | Independent new/known-payee regression reproduced the gap; fact is now passed to policy evaluation |
| Configurable flag action | `deny_and_flag` reaction depended on rule-name spelling | Typed policy result now carries action/rule through events, risk and quarantine. Custom-name halt and plain-deny positive controls pass |
| Failed stream cleanup | Upstream failure left no terminal risk case or shared cleanup | Shared failed/cancelled terminal transition records history, clears authority and rejects pending proposals; independent regression passes |
| Financial disclosure matcher | G2 counted only a private canary and missed an exact foreign balance answer | Trusted foreign-fact predicates added with own/wrong-amount controls. Read-only check of 80 retained G2 outputs found no changed results; old experiment remains old-source evidence |
| Benign bill argument | Actual model emitted `status=unpaid`, rejected by empty DTO | Strict status enum/filter added, owner selector still rejected. Original failed measurement retained |
| Detector outage treated as attack | Benign source scores rose 40→60→80→100 and sources were quarantined | Availability still denies/revokes, but no attack-flag history or persistent source quarantine; outage/recovery and real-injection controls pass |
| Qwen3 thinking | New model transport did not explicitly disable thinking | Watched Qwen3 transport regressions fail, then added `think:false`; other model requests retain prior form |
| Calibration quota | First 100-request batch hit 30 runs/900s and returned 70 quota errors | Same registered corpus measured in four independent 25-case banks without changing quota; failures retained |
| Runtime compatibility | Initial NumPy 2.5.4 conflicted with existing Presidio `<2.5` | Isolated environment pinned NumPy 2.4.6; `pip check` and 48 focused tests passed |
| Caido capture connection | Initial reused proxy connection reset | Isolated harness disabled keep-alive reuse; final three denial and two owner-control checks passed |
| Extra C-demo lane | Automated safety review rejected the delegated demo work for possible cybersecurity risk | No retry to evade review and no C-demo artifact claimed. Existing measured evidence remains available |

Raw working logs are under `.local/week8/`. They may contain test-only authentication material printed by legacy failed assertions and therefore are not copied wholesale into the release package. Release reports contain redacted outcomes; credentials, TOTP seeds and live codes are excluded.

Follow-up verification wrapper: all49 browser tests passed, but PowerShell surfaced redirected Vite stderr as NativeCommandError and returned1. The original log is retained. A complete rerun through a Python subprocess records the actual npm child exit and combined stdout/stderr separately; final status is recorded in RESULTS.md. This did not require application or test changes.
