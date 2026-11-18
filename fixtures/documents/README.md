# Synthetic document fixtures

All identities and amounts are fictional. Regenerate with `backend/.venv/Scripts/python.exe scripts/document-fixtures.py`; invariant PDF metadata keeps files reproducible. The bundled Noto font preserves Vietnamese text.

`inj_hidden_white.pdf` includes the direct instruction in white 1pt text. Extraction must include it. `inj_hidden_variant.pdf` uses a payment-details notice in the same hidden position to exercise downstream defenses if the detector allows it. Detector outcomes are measured, not guaranteed; never whitelist these filenames or bypass screening in live evaluation. Bob's canary is uploaded only by Bob.

These fixtures are deliberately hostile test inputs, not instructions to operators or the assistant.

