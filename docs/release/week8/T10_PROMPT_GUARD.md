# T10 local Prompt Guard adapter and evaluation

Implemented independently on `week8/t10-promptguard`. This is adapter/tooling completion, **not completion of the real-model three-detector acceptance criterion**.

## Integration contract

`backend/app/agent/promptguard.py` provides:

- `initialize(model_path=None)`: synchronous single-load startup hook; invoke off the event loop. Reads `PROMPT_GUARD_MODEL_PATH` when no path is supplied.
- `await classify(text, *, model_path=None, threshold=0.5, timeout_seconds=None)`: returns `injection`, `available`, `method` and a finite malicious score on successful inference. `method='unavailable'`, `available=False`, `injection=True` on absent model/runtime, load/inference failure, malformed scores, invalid inputs, busy worker or timeout.
- Default timeout is five seconds, configurable through `PROMPT_GUARD_TIMEOUT_SECONDS`; accepted maximum120seconds. Maximum source length18000characters. Overlength data fails closed rather than truncating away a tail injection.

The parent integrates regex → this detector → existing Qwen screening, recording each signal with its bank-owned event API and respecting A/C classifier-disabled policy. This module does not make authorization decisions or modify `agent_access.py`/`agent_guard.py`.

Only a real local directory is accepted. `local_files_only=True`, `trust_remote_code=False`, and `use_safetensors=True` prevent implicit Hub downloads, custom remote code and pickle weight loading. The loader requires explicit binary BENIGN/MALICIOUS or SAFE/INJECTION label mappings; unknown labels fail closed. All overlapping512-token windows are evaluated in batches of at most4; output is the highest malicious probability. CPU inference runs off-loop. One worker per configured detector remains claimed through timeout/cancellation until native work finishes; callers cannot queue unlimited timed-out inference jobs. Timeout is a caller deadline, not a promise that native code was killed.

## Research provenance

Primary sources inspected on2026-11-15:

- [Meta Prompt Guard2 model card and license](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M). Model/runtime provisioning and Meta license acceptance remain a human prerequisite from the supplied plan. Neither was performed.
- [Vietnamese community fine-tune](https://huggingface.co/MinhNghia/Llama-Prompt-Guard-2-86M-vi), published by its author as fine-tuned from Meta's model with BENIGN/MALICIOUS labels. Its reported metrics are publisher claims on its own dataset, not evidence on NovaBank. Its card currently reports a larger parameter count/weight size than its name implies; provision and validate actual local artifacts rather than assuming an86M footprint.

No Torch/Transformers runtime or local base/VI weights were present. No dependency installation, model download, license acceptance or remote-code trust was added. `backend/app/guard.py` remains unchanged; the adapter lives under `app/agent` to preserve that compatibility alias.

## Corpus and scoring

`research/data/vi_injection.jsonl` contains52 synthetic rows:13 inferred source channels × accented/unaccented Vietnamese × one benign/one injection case. Every row records `origin=synthetic_t10_v1`. Channels were inferred from the supplied task list because the original13-source design table is absent. This is a small templated smoke corpus, not independent/held-out evidence of general injection resistance. It must not be described as the original mentor payloads.

`research/guard_eval.py` and `scripts/week8-guard-eval.py` compare base Prompt Guard2, a local VI fine-tune and an explicitly selected local Ollama Qwen model. Missing models remain unavailable; fail-closed positive verdicts are excluded from precision/recall. Reports expose coverage, unavailable counts, confusion matrices and per-channel results. Undefined precision/recall is JSON null. Qwen inference is strictly loopback HTTP and records the installed model digest/Ollama version. The CLI never pulls a model, does not invoke bank tools, and refuses to overwrite an existing evidence file. Exit0means every row for all3detectors was measured; exit2means the matrix is incomplete.

```powershell
backend/.venv/Scripts/python.exe scripts/week8-guard-eval.py --base-model-path <licensed-local-base-directory> --vi-model-path <licensed-local-vi-directory> --qwen-model qwen2.5:7b --qwen-url http://127.0.0.1:11435 --output .local/week8/guard-comparison.json
```

Run model evaluations serially with other local utility/dual-LLM tests to avoid queue contention. A live Qwen evaluation started but was stopped immediately on coordinator instruction to serialize GPU work; no result file was written and no metrics are claimed for that interrupted attempt. The checked-in unavailable-only report was invoked without model arguments: PG paths are unprovisioned and Qwen was deliberately not requested. It is a configuration/availability report, not mocks disguised as real precision/recall or a claim that Qwen is absent from the machine.

## Validation

TDD: initial13adapter tests failed because the module was absent; initial4evaluation tests failed because the module/corpus were absent. Final focused suite: **19passed**. Cases cover benign positive control, malicious signal, cached load failure, finite-score/schema checks, no implicit loader use without a local path, tokenizer windows/local-only/safetensors flags, off-loop inference, timeout/busy/cancellation, queued executor cancellation recovery, balanced corpus and unavailable-metric handling. These are mocked contract tests, not real-model accuracy tests.

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_promptguard.py research/tests/test_week8_guard_eval.py -q
backend/.venv/Scripts/python.exe -m ruff check backend/app/agent/promptguard.py research/guard_eval.py scripts/week8-guard-eval.py backend/tests/test_promptguard.py research/tests/test_week8_guard_eval.py
```

Independent review and licensed-runtime accuracy measurements remain pending. Rollback removes only these new task files; no database migration is involved in this lane.
