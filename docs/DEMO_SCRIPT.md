# 5-minute demonstration for Robert (13 October Week-3 feedback)

For the single-port launcher or Docker image, use `http://127.0.0.1:8080`
instead of port 5173 below. See [simple demo setup](SIMPLE_DEMO.md) for startup,
model preflight, reset behavior and an acceptance checklist.

1. Open the UI at `http://127.0.0.1:5173`, confirm the top bar says `Demo mode` (or `Ollama AI` if explicitly configured) and shows fictional user Alice.
2. Ask **“What is VietQR?”**. In mock mode this searches the curated fictional-bank FAQ. The right side shows `search_banking_faq — ALLOW`.
3. Ask **“What is my account balance?”**. The tool returns fake Alice account `ACC-ALICE-001` with `12,500,000 VND`.
4. Ask a follow-up **“Do I have enough money to transfer 3 million?”**. Mock mode rechecks the demo balance and states there has been NO transfer.
5. Ask **“Check transaction TX-1002”**. Expected `PENDING`.
6. Ask **“Check transaction TX-2001”**, which belongs to Bob. Expected DENY, no transaction payload revealed. Audit shows `TRANSACTION_NOT_OWNED`.
7. Open **Testing insights**, then under **Check permissions**, select `get_account_balance`, set `ACC-BOB-001`. Expected `DENY / ACCOUNT_NOT_OWNED`, `executed=false`.
8. Change to `ACC-ALICE-001`. Expected `ALLOW / LOCAL_POLICY_APPROVED` but `executed=false` because this is a DRY RUN.
9. Refresh. History and tool events persist. Switch user to Bob; Alice's conversations are inaccessible. Switch back to Alice; her history reappears.
10. Optional: set Ollama mode, restart backend and repeat. Inspect response_source to distinguish constrained native proposals from application fallback. Both modes use application-bound workflows and English replies; this is not an independent model reasoning benchmark.

Key answer for Robert: **Who authorizes?** Independent `PolicyGateway` on every tool request. **Can agent bypass?** The exposed execution path is only `ToolDispatcher.run` -> gateway allow -> executor. This validates the source architecture and tests in the demo, but cannot certify arbitrary external agents or all bypasses.
