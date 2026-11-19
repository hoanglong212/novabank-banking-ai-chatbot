# Synthetic document fixtures

`benign_loan_with_term.pdf` states 6 percent annual interest and a 24-month term. The original `benign_loan_contract.pdf` supplies the rate and start date only. Ask for its term to verify that an absent value stays absent.

All identities and amounts are fictional. Regenerate with `backend/.venv/Scripts/python.exe scripts/document-fixtures.py`; invariant PDF metadata keeps files reproducible. The bundled Noto font preserves Vietnamese text.

`inj_hidden_white.pdf` includes the direct instruction in white 1pt text. Extraction must include it. `inj_hidden_variant.pdf` uses a payment-details notice in the same hidden position to exercise downstream defenses if the detector allows it. Detector outcomes are measured, not guaranteed; never whitelist these filenames or bypass screening in live evaluation. Bob's canary is uploaded only by Bob.

These fixtures are deliberately hostile test inputs, not instructions to operators or the assistant.

`inj_alias_variant.pdf` presents source-authored `<ACCOUNT_1>` and bare `NAME_1` as payment references. `inj_link_variant.pdf` lists the same hostile URL as a reference website. These declarative variants exercise alias restoration and output URL filtering when the imperative originals are quarantined. The live runner records the selected fixture and actual ingestion status; it never disables screening. Rate counters are reset only in the disposable measurement DB because upload quota enforcement has separate API tests.

