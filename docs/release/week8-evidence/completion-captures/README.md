# Continuous browser and Caido evidence

Captured on 2026-11-15 from actual Chromium sessions against disposable synthetic NovaBank databases. These are continuous recordings, not screenshot slideshows. Production application files and the original browser tests were not edited by this capture lane.

| Recording | Duration | Observed result |
|---|---:|---|
| [MFA GIF](mfa-continuous.gif) / [original WebM](mfa-continuous.webm) | 16.68s | Fresh TOTP login, new-recipient step-up, separate email OTP, confirmed 10,000 VND transfer |
| [Rejected QR GIF](quishing-blocked-continuous.gif) / [original WebM](quishing-blocked-continuous.webm) | 10.24s | Signed QR containing an external URL rejected as UNSAFE_QR_CONTENT; no URL opened and no transfer drafted |
| [Legitimate QR to email OTP GIF](quishing-genuine-email-otp-continuous.gif) / [original WebM](quishing-genuine-email-otp-continuous.webm) | 17.88s | Genuine uploaded QR, source/new-recipient warning, recipient-bound authenticator proof, distinct email OTP screen; no payment confirmed |
| [Historical legitimate QR GIF](quishing-genuine-continuous.gif) / [original WebM](quishing-genuine-continuous.webm) | 13.20s | Earlier known-payee fixture reached transaction PIN; retained as historical evidence, superseded for C3 OTP acceptance by the recording above |

The initial capture run passed **3 tests in 63.28 seconds, process exit 0**, no skipped/unexpected/flaky results. The C3 email-OTP follow-up passed **1 test in 31.91 seconds, process exit 0**, no skips, failures or retries. [Machine-readable evidence and source hashes](recordings.json). Review screens pause 1.3 seconds in the initial run and 1.8–2.4 seconds in the follow-up for readability. FFmpeg converts the original WebM to 10fps GIF at 960px width without cutting elapsed time. Originals retain 1440×900 resolution. Contact sheets were visually inspected, including secret masking, the MFA receipt and the genuine QR's email OTP screen.

Privacy: a capture-only CSS overlay hides password/PIN/OTP digits. The MFA recording starts in a fresh browser context after the preparatory authenticator enrollment; no setup seed is recorded. The real application still receives and verifies the test codes. No fake result or generated screenshot is used.

### C3 genuine QR reaches OTP

The historical test recipient was explicitly marked `fixture_known` by the shared regression fixture, which explains its transaction-PIN path. The follow-up uses an isolated copy of that fixture and removes only Alice's known-payee marker for the same synthetic external recipient before startup. Its own database/state directory and ephemeral port avoid the standard E2E runner. Enrollment happens before recording; the continuous video then covers TOTP login, uploaded genuine QR, recipient verification and the separate email-OTP screen.

[Final OTP screenshot](04-genuine-qr-email-otp.png), [QR source review](01-genuine-qr-review.png), [recipient verification](02-genuine-qr-recipient-stepup.png), [verified recipient](03-genuine-qr-stepup-passed.png), [acceptance result with 498 before/after source hashes](quishing-genuine-email-otp.json). The OTP endpoint returned 200 with `otp_method=email`, the mailbox gained exactly one transfer OTP, the balance remained 10,000,000 VND and no transfer confirmation request occurred. All 498 application, built-frontend and original-helper hashes remained unchanged during the run. The email code is not shown or entered. The disposable server on port 64520 was stopped after capture. The blocked-QR recording and assertions remain intact.

## Caido API evidence

Caido **is installed**, version 0.59.1 at `C:\Program Files\Caido\Caido.exe`. A task-specific loopback instance was created at `127.0.0.1:18080`, with dedicated storage in `.local/week8-completion/captures/caido-data`. The original stopped Caido instance on 8080 and NovaBank deployments were not restarted or replaced.

The user resolved the first-run privacy choice themselves. The agent then observed the unblocked workspace, created the isolated temporary guest project **Week8 API Captures**, and sent three requests to a disposable synthetic API through Caido. The final capture completed at **2026-11-15T04:22:03Z**, process exit 0. Two owner-positive controls returned 200; both test sessions were revoked and the disposable API was stopped afterward.

| Check | Response | Actual Caido screenshot |
|---|---|---|
| Anonymous `GET /api/me` | 401, `Please sign in` | [Request and response](caido-401-anonymous.png) |
| Customer `GET /api/admin/agent-gateway` | 403, `Permission denied` | [Response body and status](caido-403-customer.png) |
| Alice reading Bob's existing conversation | 404, `Conversation not found` | [Response body and status](caido-404-foreign-conversation.png) |

[All three paths/statuses in HTTP History](caido-http-history.png). [Machine-readable result and before/after source hashes](caido-api-checks.json). [Screenshot hashes](screenshots.json). All 101 source/policy file hashes remained unchanged during the API capture. Screenshots were visually inspected before saving; their pixels are unmodified. Authenticated request headers remain outside the saved viewport. Raw Caido storage remains local and contains revoked synthetic session headers; it is not a release artifact. The guest project is temporary and may be deleted by Caido on its next startup.

The first attempt recorded an anonymous 401 but encountered a Windows connection reset when reusing the proxy connection. The isolated harness now disables HTTPX keep-alive reuse; the next complete run passed all three checks. The screenshots filter to that successful run's disposable app port, 60983. No application change was needed. HTTPQL filtering and pane resizing follow the official [filter reference](https://docs.caido.io/app/reference/httpql.html) and [UI guide](https://docs.caido.io/app/guides/ui).

Historical prerequisite: the [computer-use skill](C:/Users/Admin/.codex/plugins/cache/openai-bundled/computer-use/26.1106.51428/skills/computer-use/SKILL.md) requires its [guidance](C:/Users/Admin/.codex/plugins/cache/openai-bundled/computer-use/26.1106.51428/docs/guidance.md), which states: “Do not change ... any in-app security or privacy settings. Do not act on security or privacy permission requests.” The agent therefore paused at that choice and the user completed it. The [observed prerequisite screen](caido-privacy-prerequisite.png) is preserved as history, not presented as API evidence.

The previously rejected extra C-configuration attack-demo action was not retried or recreated in this lane.
