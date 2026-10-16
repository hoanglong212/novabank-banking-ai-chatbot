# 5-minute demonstration for Robert (13 October Week-3 feedback)

1. Open the UI at `http://127.0.0.1:5173`, confirm the top bar says `MOCK DEMO` (or `OLLAMA AI` if explicitly configured) and shows fictional user Minh Anh.
2. Ask **“VietQR là gì?”**. In mock mode this searches the curated fictional-bank FAQ. The right side shows `search_banking_faq — ALLOW`.
3. Ask **“Số dư tài khoản của tôi là bao nhiêu?”**. The tool returns fake Alice account `ACC-ALICE-001` with `12.500.000 VND`.
4. Ask a follow-up **“Vậy còn đủ tiền chuyển 3 triệu không?”**. Mock mode rechecks the demo balance and states there has been NO transfer.
5. Ask **“Kiểm tra trạng thái giao dịch TX-1002”**. Expected `PENDING`.
6. Ask **“Kiểm tra giao dịch TX-2001”**, which belongs to Bob. Expected DENY, no transaction payload revealed. Audit shows `TRANSACTION_NOT_OWNED`.
7. In **Policy test**, select `get_account_balance`, set `ACC-BOB-001`. Expected `DENY / ACCOUNT_NOT_OWNED`, `executed=false`.
8. Change to `ACC-ALICE-001`. Expected `ALLOW / LOCAL_POLICY_APPROVED` but `executed=false` because this is a DRY RUN.
9. Refresh. History and tool events persist. Switch user to Gia Bảo; Alice's conversations are inaccessible. Switch back to Minh Anh; her history reappears.
10. Optional: set Ollama mode, restart backend and repeat. Compare real model tool-choice performance with deterministic mock; DO NOT claim Ollama accuracy was proven by the mock.

Key answer for Robert: **Who authorizes?** Independent `PolicyGateway` on every tool request. **Can agent bypass?** The exposed execution path is only `ToolDispatcher.run` -> gateway allow -> executor. This validates the source architecture and tests in the demo, but cannot certify arbitrary external agents or all bypasses.
