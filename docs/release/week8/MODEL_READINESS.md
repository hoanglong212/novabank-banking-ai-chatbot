# Week8 model readiness and remaining measurements

Updated 2026-11-15. Qwen3 is installed and has actual inference evidence. The isolated CPU measurement runtime is usable. **Neither Prompt Guard variant has been measured:** the user explicitly confirmed that Meta's license has not been accepted. Installation is not license acceptance or model readiness.

| Prerequisite | Observed state |
|---|---|
| Qwen2.5:7b | Existing local model, digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e` |
| Qwen3:8b | Pulled successfully into the existing Ollama model store on D:, 5,225,388,164 bytes, Q4_K_M, digest `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41` |
| Ollama | Existing service on loopback port 11435; observed version 0.40.16 |
| Isolated runtime | `D:/NovaBank-Week8-Lab/runtime/Scripts/python.exe`, Python 3.14.6, Torch 2.15.0+cpu, Transformers 5.23.0, NumPy 2.4.6, sentencepiece 0.2.3, protobuf 7.36.2 |
| Dependency compatibility | `pip check` passed after correcting NumPy to respect the existing Presidio `<2.5` constraint; 48 focused application/adapter tests passed in the isolated runtime |
| Prompt Guard base/VI | No licensed local weights; no actual inference, precision or recall claim. Required human access step remains incomplete |

The existing backend virtual environment, live deployment and model manifests were preserved. The user's follow-up authorized only the named Qwen3 provisioning and isolated measurement environment. The runtime reads existing app dependencies through a `.pth` entry; no service installer or account change was performed.

The application explicitly sends `think:false` for Qwen3 model/guard requests. Transport regressions verify that Qwen2.5 requests retain their prior shape. Qwen3's [40-call T9 run](../week8-evidence/spotlighting/utility-qwen3-20261115.json) measured 18/20 exact reads with marking off and 20/20 on. Its [real D-configuration positive demo](../week8-evidence/live-positive-demo-qwen3.json) captured four primary HTTP-200 calls: the assistant's 80,770,000 VND balance matched the two-account bank total, and a proposed transfer cap changed only after human approval and separate bank OTP. These are legitimate-task checks, not the full attack matrix.

## Prepared full evaluation

The human prerequisite comes directly from [T10 in the supplied plan](../../ke-hoach-agent-build-week8.md): “chấp nhận giấy phép Llama trên Hugging Face và tải model về máy lab. Agent không tự làm bước này.” After the user accepts the relevant terms, receives access and downloads the model/tokenizer files locally, the prepared comparison command is:

```powershell
D:/NovaBank-Week8-Lab/runtime/Scripts/python.exe scripts/week8-guard-eval.py --base-model-path D:/NovaBank-Week8-Lab/models/prompt-guard-base --vi-model-path D:/NovaBank-Week8-Lab/models/prompt-guard-vi --qwen-model qwen2.5:7b --qwen-url http://127.0.0.1:11435 --output .local/week8-completion/three-detectors-licensed.json
```

The two paths above are reserved examples, not claims that weights exist there. Use the actual licensed local directories. The adapter uses local safetensors/tokenizer files only; it does not accept licenses, download weights or execute remote model code. The command returns0 only for complete measured detector coverage and refuses to overwrite an existing output. Its `--help` was checked in the new runtime. No password/token is needed in this repository or chat. Once the base detector is verified, `PROMPT_GUARD_MODEL_PATH` must point to that local directory in the isolated evaluation processes before actual B/D source measurement.

The final integrated application and corrected v4 financial-disclosure matcher are copied into the separate detached worktree `D:/NovaBank-Week8-Lab/source-final`. The earlier `source-current` calibration snapshot is immutable and remains unchanged. `week8-snapshot.json` records 146 source/research/script hashes; the synthetic seed is copied read-only through SQLite backup with its provenance manifest.

The plan-only command below completed with **113 cases, eight model/configuration cells and 7,600 planned observations**, `execute=false`, zero checkpoint rows and zero network calls. This number includes explicit unsupported cases and is not a count of passed tests. Licensed detector readiness and the currently unsupported QR-to-agent ingestion path remain acceptance dependencies. No existing unavailable result is rewritten as a pass.

```powershell
D:/NovaBank-Week8-Lab/runtime/Scripts/python.exe scripts/week8_evaluate.py --project-root D:/NovaBank-Week8-Lab/source-final --out .local/week8-evaluation/full-matrix-v4 --models qwen2.5:7b qwen3:8b --configs A B C D --attempts 10 --seed-db D:/NovaBank-Week8-Lab/source-final/.local/week8-seed/bank.sqlite3
```

The resulting manifest is at `D:/NovaBank-Week8-Lab/source-final/.local/week8-evaluation/full-matrix-v4/manifest.json`. Actual execution must use licensed local weights, an explicitly configured detector, a fresh output directory if source/settings change, and the runner's explicit `--execute` flag. A plan-only manifest is not an executed benchmark. Original historical transcripts do not exist according to the user; the new [current design](../../thiet-ke-gateway.md) documents the implemented baseline without inventing those incidents.

Provisioning evidence: [runtime/dependency probe](../week8-evidence/runtime-readiness.json), [Qwen3 inventory](../week8-evidence/qwen3-provisioning.json). Local setup/failure logs are retained under `.local/week8-completion/`. Public references consulted: [Ollama Qwen3](https://ollama.com/library/qwen3:8b), [Ollama pull API](https://docs.ollama.com/api/pull), [Transformers installation](https://huggingface.co/docs/transformers/installation), [Meta base model/license](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M), [Vietnamese model card](https://huggingface.co/MinhNghia/Llama-Prompt-Guard-2-86M-vi).
