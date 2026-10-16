# Threat model, safeguards, known limits

**Security status:** This is an educational local demonstration, **not banking-grade**. It must not be hosted publicly, connected to real bank data or used for financial actions.

- Local demo identity tokens are PUBLIC in the frontend by design. The two user-switch choices simulate authenticated principal semantics but are not real login. Actual deployment would require OIDC and backend JWT verification.
- Do not enter any real customer PII, API keys, OTP, PINs or payment information. The fabricated bank, balances, transactions and FAQ are synthetic.
- All conversation/message read and delete routes check owner ID derived from the (insecure demo) bearer token, not just conversation ID. This prevents accidental cross-conversation leakage under the local identity model.
- `PolicyGateway` performs independent policy authorization; the LLM is not entrusted with decisions. Local allowlist + JSON schemas + owner checks are enforced even when the model chooses an inappropriate tool.
- Remote adapter is **only a proposed contract**: POST `{GATEWAY_URL}/authorize` with `principal_id`, `conversation_id`, `tool_name`, `arguments`; response `{"decision":"ALLOW"}` or `{"decision":"DENY"}`. A real gateway will require stronger authentication, action context, intent/grant and verified execution controls. Unauthorized remote calls fail closed.
- The gateway still cannot reliably infer whether every syntactically valid, resource-authorised call matches the original user intent. The demo checks resource ownership and tool permissions; it does not solve semantic task intent, sequence authorization or data-flow taint.
- FAQ tool results are synthetic and may be controlled differently in a real system. No protection against arbitrary malicious internet content or exfiltration through generated final text has been proven.
- Frontend makes separate standard JSON requests; streaming/SSE is not implemented in this version. User message may remain in DB if Ollama subsequently fails; UI displays explicit error.
- SQLite is for local testing. Multiple backend workers, concurrency, backup, encryption-at-rest and rate limiting need design before any realistic deployment.
- Tool-event arguments might include data users input; audit log is mock-only and is not security-hardened. A real audit system must minimize/redact sensitive fields, control retention and protect integrity.
- Do not use `mock` tests to claim the LLM can withstand prompt injection. Run controlled tests with a real model and compromised-agent scenario.
