# Ultimate UIUX integration implementation plan

> For implementation: use `msi-aef-executing-plans` sequentially. This document is a plan, not authorization to implement it or change NovaBank.

**Goal:** Turn the installed Ultimate UIUX toolkit into a configuration-driven coordinator that reuses installed skills, routes work for Codex and Claude Code, and verifies visual repairs within three iterations.

**Architecture:** The Python CLI owns configuration, capability evidence, deterministic checks and run state. Existing skills supply design knowledge and implementation guidance by reference. The active coding agent reads those skills, inspects screenshots and performs authorized edits; no second LLM service or duplicated design database is introduced.

**Stack:** Existing Python >=3.10, standard-library JSON/unittest/subprocess, optional installed Playwright, and the current agent host. Preserve NovaBank's React/TypeScript/Vite/npm stack.

**Specification:** The user's six requirements in this conversation, expanded below into changes, dependencies, acceptance criteria and verification. Inspection date: 2026-10-17, Asia/Saigon.

## 1. Scope and path map

| Alias | Actual location |
| --- | --- |
| `TOOLKIT` | `C:/Users/Admin/Downloads/ultimate-uiux-agent/ultimate-uiux-agent` |
| `UIUX` | `TOOLKIT/.venv/Scripts/uiux.exe` |
| `PYTHON` | `TOOLKIT/.venv/Scripts/python.exe` |
| `CODEX_SKILL` | `C:/Users/Admin/.agents/skills/ultimate-uiux` |
| `CLAUDE_SKILL` | `C:/Users/Admin/.claude/skills/ultimate-uiux` |
| `PROJECT` | `C:/Users/Admin/Downloads/NovaBank_Banking_AI_Chatbot_MVP/banking-ai-chatbot` |
| `PRO_MAX` | `PROJECT/.claude/skills/ui-ux-pro-max` |

All proposed Python and toolkit configuration changes belong to TOOLKIT. NovaBank is a later consumer and optional validation target, not the implementation location. This planning task creates only this Markdown document in NovaBank.

Constraints:

- No NovaBank application, package, dependency, API, business-logic or design changes in this task.
- No automatic installation, credential discovery, login, SaaS calls, copying upstream skills, or model downloads.
- Keep existing third-party files and notices untouched. References and original adapters are preferred to vendoring.
- Existing repository instructions and the user's scope outrank advisory skill content. `msi-aef` remains the software-engineering process owner; Ultimate UIUX supplies its UI-specific stages, avoiding competing planning loops.
- A design overhaul uses three substantively distinct directions. A targeted defect uses the smallest relevant search, without generating a new design system.
- Three QA iterations maximum, including the initial assessment; no unverified repair after the third assessment.

## 2. Findings from the installed code

| Source | Observed behavior / gap |
| --- | --- |
| `TOOLKIT/ultimate_uiux/cli.py` | Only `init`, `audit`, `qa`, `loop`. No config loading, skill registry or capability detection. Loop defaults to three but accepts 1–10. A repair command is optional; no integrated LLM fixer. |
| `TOOLKIT/ultimate_uiux/core.py` | Phases, three template directions, acceptance text and draft tokens are hardcoded. Static audit scans HTML only, excludes common build directories and uses regex heuristics. It does not inspect React-rendered UI. |
| `TOOLKIT/ultimate_uiux/visual.py` | Three hardcoded viewport dimensions, 150ms readiness delay, screenshot capture and four DOM heuristics. Captures page exceptions and main-document HTTP errors; does not comprehensively monitor failed subresources or API calls. No screenshots-reviewed gate, functional scenarios, contrast engine or visual-diff test. |
| `TOOLKIT/config/workflow.json` | Six phases, three variants, widths 375/768/1440, maximum three iterations, automatic LLM editing and external setup disabled. Currently descriptive, not consumed. |
| `TOOLKIT/config/integrations.json` | Human-readable status strings. Pro Max is marked absent despite an executable workspace installation. |
| `TOOLKIT/pyproject.toml` | Editable installation verified. CLI entry point and optional Playwright extra exist. JSON defaults outside the package need explicit wheel resource packaging. |
| Installed skill directories | Codex and Claude each have Ultimate UIUX instructions and companion configuration copies. The source skill lacks their Windows installation appendix, creating drift risk. |
| `PRO_MAX/scripts/search.py`, `core.py`, `design_system.py` | Existing standard-library-only local search and design-system generator. JSON output is supported. CSV paths are resolved relative to the installed script. No new implementation of BM25 or its datasets is needed. |

### Operational status and evidence

| Capability | Current status | Evidence / boundary |
| --- | --- | --- |
| UIUX CLI | Operational | Absolute-path `--help` succeeds; editable package points to TOOLKIT. |
| UIUX init/static audit | Operational | Six existing toolkit unittest tests rerun successfully during this inspection, including non-destructive scaffolding and error exit behavior. |
| Local Playwright + Chromium | End-to-end verified earlier in this session | Showcase QA exited 0; 375/768/1440 PNGs were opened and inspected. Report: `C:/Users/Admin/AppData/Local/Temp/uiux-verification-bz9r0ao5/qa/report.json`. Not a NovaBank QA pass. |
| Pro Max domain search | Operational | `keyboard focus dropdown --domain ux --json -n 2` returned two results from `ux-guidelines.csv`, led by Focus States. |
| Pro Max React search | Operational | `state component composition --stack react --json -n 2` returned two results from `stacks/react.csv`. Recommendations must be checked against the project's actual React version. |
| Pro Max design-system generation | Operational, advisory | Non-persisting banking query returned a JSON design-system object with `persistence: null`. Product relevance is an agent review, not established by exit code. |
| `design-system`, `brand`, `ui-styling`, `design` | Installed guidance | Workspace skill files read. Their generation/asset scripts have not been validated; do not mark those scripts operational. |
| `banner-design`, `slides` | Installed, outside current web-app scope | SKILL files present; do not route ordinary UI repair to them. |
| `msi-aef` React/composition/review skills | Available guidance | Existing Codex skill catalog and local files; reuse, do not install parallel equivalents. |
| Codex host | Active host; standalone launcher present | Current agent can use local skills/tools. Launcher presence is not an unattended child-agent integration test. |
| Claude Code host | Skill wrapper installed; runtime unverified | `CLAUDE_SKILL` exists; `claude` was not found on PATH. Discovery in another location is still possible. |
| Anthropic frontend-design | Optional, not discovered | Not equivalent to the workspace's `design` or `ui-styling` skills. Custom license must be inspected if installed later. |
| Vercel Web Design Guidelines | Optional, not discovered as that skill | Existing React best-practices guidance is a different capability. |
| Stitch | Unavailable to this session; adapter absent | No callable Stitch tools found. Do not infer account access. |
| SuperDesign | Unavailable/unverified; adapter absent | No executable on PATH or callable tool found; login not checked. |
| Vercel Agent Browser | Not discovered on PATH | Not needed for the working local Playwright backend. |

## 3. Proposed changes

### Change 1 — Load and validate effective configuration

**Files:** Modify `TOOLKIT/ultimate_uiux/cli.py`, `core.py`, `visual.py`, `pyproject.toml`, `config/workflow.json`, `README.md`. Create `ultimate_uiux/configuration.py`, `ultimate_uiux/defaults/{workflow,quality-gates,integrations}.json`, `config/quality-gates.json`, `tests/test_configuration.py`, `tests/test_packaging.py`. Existing root `config/` files become documented examples; packaged defaults are authoritative defaults, not an additional active configuration source.

**Dependencies:** Python standard library, `importlib.resources`; existing setuptools packaging. No new runtime library.

**Interface:** `load_settings(target: Path, config_dir: Path | None, overrides: dict) -> EffectiveConfig`; include resolved values, origin per key and content digest. `uiux config show --target PATH [--config-dir PATH] --json` exposes the effective configuration without writing anything.

**Approach:**

- Precedence: packaged defaults < target `.uiux/config/` < explicit `--config-dir` < flags explicitly supplied. Do not use the process working directory when a target is supplied. `qa` and `loop` gain `--target` too. Missing optional files use defaults; an explicit missing directory or malformed file fails.
- Deep-merge dictionaries, replace arrays, reject unknown keys and invalid types. Relative paths resolve against the declaring file. Validate unique viewport names, positive dimensions, timeouts, phase values and a numeric iteration budget of 1–3. Reject booleans as integer values.
- Migrate old width arrays `[375,768,1440]` to named width/height records with the current heights 812/1024/900. Output a migration notice; never rewrite user files implicitly.
- Route all defaults through settings: scaffold phases/variants, visual viewports/readiness, static severity policy and loop budget. Config must not enable auto-installation or hidden model invocation.
- Keep source defaults in package resources and include them in built distributions. Installed skill wrappers reference configuration through the CLI; stop treating copied JSON files as independently authoritative. If explicitly selected as config directories, report their origin and digest.

**Acceptance:** Changing a viewport in an explicit config changes screenshots. Invalid JSON and `max_iterations: 4` fail before browser launch or output creation. Running outside TOOLKIT gives identical defaults. `init` still preserves existing files.

**Verification:** Tests for precedence, missing/malformed files, unknown keys, legacy migration, duplicate viewports, Windows paths/spaces and iteration bounds; subprocess CLI tests from an unrelated temporary directory. Build a wheel using existing available build tooling, inspect packaged resources and test it in an isolated environment without network access. If the build prerequisite is unavailable, record packaging verification as blocked rather than install it silently.

### Change 2 — Separate quality gates from findings

**Files:** Create `TOOLKIT/ultimate_uiux/gates.py`, `tests/test_gates.py`, `tests/fixtures/qa/`; modify `core.py`, `visual.py`, `cli.py`, `config/quality-gates.json`, packaged defaults and `docs/VISUAL_QA.md`.

**Dependencies:** Change 1 and the existing Playwright extra. No claim of a bundled full WCAG/axe engine.

**Interface:** `evaluate_gates(evidence: RunEvidence, settings: EffectiveConfig) -> GateReport`; each gate returns `pass`, `fail`, `not_run`, `not_applicable`, or `error`, with evidence references. Required `not_run` or `error` cannot produce an overall pass.

**Approach:** Define required gates for readiness, screenshots at all configured viewports, no page overflow, named buttons, relevant image alternatives, runtime errors, configured functional checks, visual review and permitted file scope. Keep static HTML shell findings distinct from rendered-page findings. Missing an H1 in an SPA shell is not proof the rendered screen lacks one; page-state expectations belong to the target profile.

Represent optional build/test checks as explicit executable-plus-argv lists with working directory and timeout, never shell command strings. Config describes checks but does not authorize running arbitrary project commands: the host approves the resolved commands for the run. Differentiate zero HTML files from an audited rendered app.

Suggested initial gate shape:

```json
{
  "schema_version": 1,
  "required": ["ready", "screenshots", "no_horizontal_overflow", "named_buttons", "image_alternatives", "runtime_errors", "visual_review", "scope"],
  "static": {"html-lang": "warning", "heading": "warning", "missing-alt": "error"},
  "checks": [],
  "review": {"require_current_screenshot_hashes": true},
  "warnings_block": false
}
```

**Acceptance:** A clean DOM report with no screenshot review remains pending, not passed. A required skipped check fails overall acceptance. Optional integrations absent from the profile do not fail core QA. Existing audit exit codes remain meaningful: 0 for applicable nonblocking static findings, 1 for blocking findings, 2 for configuration/runtime errors; reports explicitly identify the limited scope.

**Verification:** Table-driven tests for every gate state, warning policies, absent evidence, expired screenshot hashes, no matching HTML and React-shell versus rendered-heading fixtures. Tests assert that JSON failure and CLI exit status agree.

### Change 3 — Discover capabilities and reuse installed skills

**Files:** Create `TOOLKIT/ultimate_uiux/capabilities.py`, `skill_registry.py`, `adapters/pro_max.py`, `tests/test_capabilities.py`, `tests/test_pro_max_adapter.py`; modify `cli.py`, `config/integrations.json`, packaged integration defaults and `docs/INTEGRATIONS.md`.

**Dependencies:** Change 1; standard library. Use configured absolute Python and existing PRO_MAX scripts. Playwright probing uses the installed package only.

**Interfaces:** `detect_capabilities(target, host, settings, probe=False) -> CapabilityReport`; `query_pro_max(skill_path, interpreter, query, mode, limit) -> ResearchResult`. Proposed commands: `uiux doctor --target PATH --host codex --json` and `uiux research --target PATH --skill ui-ux-pro-max --domain ux --query "focus visible" --json`.

**Approach:**

- Replace mutable status prose with declarative descriptors: capability ID, candidate paths, entry point, dependency/probe, host applicability, optional/required designation and license references. Store observed status in reports, not back into configuration.
- Search only configured roots: project `.agents/skills`, project `.claude/skills`, user `.agents/skills`, user `.claude/skills`, and explicit paths. Include other host paths only when configured or supplied by the host. Resolve aliases/junctions, deduplicate canonical paths and hashes; do not crawl the entire disk. Prefer explicit mappings, then project, then user scope; report same-ID/different-content collisions instead of silently switching.
- Record availability dimensions separately: discovered, readable, runtime present, executable probe passed, host-exposed, access verified, licensing status, verified timestamp. MCP access comes from the active host's live inventory; Python cannot infer it from a directory or credential file.
- `doctor` is read-only; execution probes require the explicit probe option. Do not log token values or unrelated environment variables. Probe failures retain their reason and do not trigger installation.
- Reuse PRO_MAX by invoking `[absolute_python, '-B', absolute_search_script, query, '--domain', domain, '--json']` with `shell=False`, UTF-8, output limits and a timeout. For stack and design-system modes use its existing flags. Preserve source file, row identity, query, installed digest and original output; do not copy CSVs or search logic.
- Verify domain/stack and result relevance. Allow one narrower retry; no match after that is explicit fallback guidance. No `--persist` or `--force` by default. Validated research is subordinate to existing project tokens and actual framework versions.

**Acceptance:** This machine detects the existing workspace Pro Max and reports its successful probes; does not recommend reinstalling it. Standard operation makes no network calls and writes no third-party files. Unavailable cloud adapters remain unavailable rather than simulated. A design-system query without persistence leaves PROJECT unchanged.

**Verification:** Temporary fake skill roots cover duplicates, collisions, stale paths, symlinks, missing scripts/interpreters, nonzero exit, invalid JSON and timeout. Mock subprocess tests verify exact argv and no shell. Live optional smoke tests rerun the three non-persisting Pro Max queries used during inspection. A live success proves script capability, not host auto-discovery.

### Change 4 — Route work consistently for Codex and Claude Code

**Files:** Create `TOOLKIT/ultimate_uiux/routing.py`, `config/routing.json`, packaged routing defaults, `docs/HOST_ROUTING.md`, `tests/test_routing.py`; modify `AGENTS.md`, `CLAUDE.md`, `skills/ultimate-uiux/SKILL.md`, and later update owned wrappers in CODEX_SKILL and CLAUDE_SKILL. Do not edit other authors' skills.

**Dependencies:** Changes 1 and 3. The active host's ability to read local files and execute tools; neither a new SDK nor an unattended child CLI is required.

**Interface:** `route_task(request: TaskIntent, capabilities: CapabilityReport) -> RoutePlan`. Proposed `uiux route --host codex|claude --task review|repair|redesign|tokens|react --target PATH --json` returns ordered skill paths, purpose, prerequisites and fallback reasons. It does not falsely claim to activate host-native skills.

Routing policy:

| Intent | Primary existing guidance | Conditional supplement |
| --- | --- | --- |
| Existing UI review or focused repair | Pro Max explicit UX domain | Relevant React/composition guidance only when implementation needs it |
| Whole-page redesign | Ultimate UIUX direction comparison + Pro Max design-system research | Existing brand guidance if brand decisions are involved |
| Tokens/component states | Workspace `design-system` | Pro Max contrast/interaction guidance |
| React performance/composition | Existing `msi-aef-vercel-*` skills | A separate Pro Max query for a distinct UX issue |
| Visual QA | Local UIUX Playwright | Agent screenshot and keyboard inspection |
| Slides/banners/assets | Existing specialized skill only on matching request | External generation only if already configured and authorized |

Codex and Claude wrappers read the returned original paths rather than containing copied upstream bodies. An agent may explicitly read a workspace skill even when it is not in the host's native skill catalog; report this as manual routing, not automatic registration. Preserve repository process ownership and scope; do not run shadcn initialization merely because `ui-styling` suggests it. Default routing favors Pro Max and existing React guidance for NovaBank's current stack.

**Acceptance:** Identical task and capability snapshots produce the same semantic route on both hosts. Workspace Pro Max resolves for either host without duplication. Missing Claude runtime is reported; host-format generation can pass while live Claude activation remains unverified. No recursion between `design`, Ultimate UIUX and `msi-aef` workflow owners.

**Verification:** Route-matrix fixtures for each intent, disabled integrations, host capabilities and conflicting guidance. Snapshot wrapper outputs; run read-only actual Codex routing and, only when available, a separate Claude session smoke test. Test that unavailable integrations do not appear as executable steps.

### Change 5 — Implement bounded visual QA and agent-led repair

**Files:** Modify `TOOLKIT/ultimate_uiux/visual.py`, `cli.py`, `docs/VISUAL_QA.md`, `AGENTS.md`, `CLAUDE.md`; create `run_state.py`, `repair.py`, `tests/test_run_state.py`, `tests/test_loop.py`, `tests/test_visual.py`, and local fixture pages/scenario profiles under `tests/fixtures/qa/`.

**Dependencies:** Changes 1–4; installed Playwright/Chromium; active agent screenshot-reading and code-editing tools. The agent loop is autonomous within an already authorized edit scope; the CLI does not invoke an unconfigured LLM.

**Interfaces:** `start_run(target, settings, allowed_paths) -> RunState`; `assess_run(run_id) -> EvidenceBundle`; `record_review(run_id, review) -> RunState`; `advance_run(run_id) -> NextAction`. CLI subcommands `uiux run start|assess|review|next|status` implement this resumable protocol; existing `loop` uses the same budget/state engine.

**Approach:**

1. Preflight: resolve settings and capabilities, verify target/server, snapshot existing file hashes/diff, record allowed edit paths, chosen design direction and validated command list. Report a missing server/browser as blocked, not a visual defect to repair.
2. Iteration 1: run configured static/build/component checks and browser scenarios; capture PNGs plus DOM/runtime evidence. Wait for target-specific readiness selectors, loaded fonts and a bounded settling condition instead of the current fixed 150ms delay. Use isolated contexts and deterministic demo fixtures.
3. The active agent opens every required screenshot, reads reports, and submits a structured review with current screenshot hashes, reviewer identity, concrete defects, severity and proposed fixes. The CLI validates evidence freshness; it cannot prove human/agent perception or judge aesthetics itself.
4. If all required checks and review pass, finish. Otherwise, when budget remains, the agent applies the smallest repair inside the allowlist, checks its diff, then requests the next assessment. No package installs, backend/auth edits, repository publishing or external service calls follow from a visual defect.
5. Iterations 2 and 3 repeat assessment and review after repairs. After assessment 3, stop with success or unresolved findings. Thus there are at most three assessments and two intervening repair batches. No fourth run via resume, nested loop or fix-command retries.
6. Stop early on runtime/configuration errors, out-of-scope writes, a failed repair command or repeated unchanged findings/source hashes. Preserve user changes and evidence; do not automatically reset the repository. A fresh budget for the same task requires an explicit new run authorization.

Persist an atomic run manifest with an exclusive run lock, immutable budget, current iteration, config digest, source hashes, screenshot hashes, findings, edits, command results and stop reason. A changed source/config invalidates old pass evidence. `automatic_llm_editing: false` continues to mean no CLI-spawned model; add an explicit `repair_mode: agent` run selection for the host-managed workflow. Legacy `--fix-command` remains explicit opt-in, uses an argv list with timeout, and consumes the same budget; no fix command executes after iteration 3.

Current UIUX cannot test dropdown interactions or keyboard behavior. Add configurable trusted scenario steps for named locators, click/keyboard actions, visibility/value assertions and viewport/state captures; do not accept arbitrary page-provided executable strings. Capture request failures and console/page exceptions with configurable expected-error allowances so intentional error-state tests are not false failures. Capture native/custom dropdown states only where supported; report OS-rendered picker limitations instead of claiming screenshot coverage.

For a later authorized NovaBank run, use isolated demo fixtures for welcome, populated conversation, mobile navigation, insights open, both dropdowns, permission allow/deny, loading and connection failure. Protect real conversation history. Source scope would default to presentation components/styles; `useBankingChat.ts`, API code and backend need separate approval for behavioral repairs. Reuse `npm run build`, `npm run test:components`, and `npm run test:identity` when their prerequisites are available. New Playwright scenarios must not be described as a passing replacement for the existing identity test.

**Acceptance:** Fresh evidence exists at all configured widths/states; screenshots actually reviewed; required commands pass; task interactions work; no out-of-scope changes; success only with both machine and review gates. A third failing assessment yields an unresolved report and no further edits. This remains a scoped QA result, not WCAG certification.

**Verification:** Mock agent/browser tests for pass-first-run, repair-then-pass, three failures, no repair provider, interrupted resume, concurrent processes, stale review, repeated findings, failed command and scope violation. A controlled bad fixture demonstrates a genuine fail/repair/pass cycle with an explicit local repair script; another fixture stays bad and proves the hard stop. Real Chromium smoke tests cover readiness, overflow, broken requests, keyboard operation, open menus and screenshots; inspect resulting PNGs. Do not run these against NovaBank during implementation without separate authorization.

### Change 6 — Preserve provenance, licensing and maintainable installation

**Files:** Modify `TOOLKIT/THIRD_PARTY.md`, `docs/INTEGRATIONS.md`, `README.md`; create `config/skill-references.json`, `docs/INSTALLATION.md`, `tests/test_reference_integrity.py`. Update only the Ultimate UIUX-owned installed wrappers after the coordinator passes its tests. Retain TOOLKIT/LICENSE unchanged.

**Dependencies:** Capability registry and local metadata. Any future upstream license verification uses the exact version's authoritative license; no installer or network refresh runs automatically.

**Approach:** Record canonical skill path, skill name, declared author/version, file digest, known upstream origin, local modifications if known, license-file path/digest, declared license, conflicts and redistribution status. Unknown origin/version is `unknown`, not guessed from an upstream project with a similar name. Record provenance for consumed dataset rows; research output remains attributable and advisory.

- TOOLKIT is MIT, copyright Ultimate UIUX Agent contributors. That license does not relicense external skills.
- Workspace `design`, `design-system`, `banner-design` declare MIT and author `claudekit`; retain those original declarations and seek accompanying license evidence before redistribution.
- Workspace `ui-styling` declares MIT but includes Apache 2.0 text. Mark `license_conflict`; preserve both; block bundling/redistribution pending clarification.
- No standalone LICENSE/NOTICE was found inside the inspected Pro Max directory. Its nearby provenance and font-license data do not establish the license of the full skill. Treat redistribution as unverified; reference the already-installed copy rather than incorporating it into TOOLKIT.
- Brand/slides provenance headers are present but do not establish complete license terms. Preserve them and record the missing evidence.
- Keep Anthropic frontend-design's custom terms distinct if added later. Hosted-service permissions remain separate from code licensing.

Generate or update thin owned wrappers from one toolkit template with dry-run diffs, preserving existing host instructions and local additions. Store machine-specific root mappings outside portable package defaults. Do not copy Pro Max or overwrite its files. Optional adapters remain disabled until their runtime, access and scope are verified; absence never triggers installation.

**Acceptance:** Before/after hashes show no third-party skill or dataset modified by integration. Reports retain attribution and conflicts. Repeated wrapper updates are idempotent and do not duplicate content. New installation notes distinguish operational local capabilities from optional cloud integrations.

**Verification:** Integrity snapshots before/after smoke runs; tests for conflicting/missing license records, duplicate wrappers and unknown versions. Review wheel contents to ensure third-party skills/data are absent. Review generated docs against actual `doctor` evidence; do not mark Claude/cloud integrations verified from static files alone.

## 4. Implementation order and verification ledger

For each change, first write the listed failing tests, run them, implement only that change, rerun the relevant tests and review the diff. No automatic commits or installation steps.

- [ ] Change 1: configuration loader and package resources.
- [ ] Change 2: quality gates and evidence schema.
- [ ] Change 3: discovery registry and existing Pro Max adapter.
- [ ] Change 4: routing and host wrappers.
- [ ] Change 5: resumable three-assessment visual repair loop.
- [ ] Change 6: provenance records, installation docs and integrity checks.
- [ ] Full toolkit unittest run and temporary fixture end-to-end run.
- [ ] Actual Codex host check; Claude check if runtime becomes available, otherwise explicitly pending.
- [ ] Independent review when an authorized reviewer is available; do not claim it from self-review.

Use the installed absolute executables. Example verification commands after implementation:

```powershell
$uiuxRoot = 'C:\Users\Admin\Downloads\ultimate-uiux-agent\ultimate-uiux-agent'
& "$uiuxRoot\.venv\Scripts\python.exe" -B -m unittest discover -s "$uiuxRoot\tests" -v
& "$uiuxRoot\.venv\Scripts\uiux.exe" config show --target '<temporary fixture>' --json
& "$uiuxRoot\.venv\Scripts\uiux.exe" doctor --target '<temporary fixture>' --host codex --json
& "$uiuxRoot\.venv\Scripts\uiux.exe" route --target '<temporary fixture>' --host codex --task review --json
```

The last three commands are proposed interfaces, not commands supported by version 0.1.0 today. Run browser fixture servers on a temporary loopback port and put all outputs outside NovaBank. Tests that need unavailable browsers, build tooling or host sessions must be reported as blocked, never silently counted as passed.

## 5. Review focus and rollout

1. Packaged install versus editable install and unrelated working directories: configuration/resource tests in Change 1.
2. Duplicate skills, local customizations and disputed licenses: discovery tests in Change 3 and integrity gates in Change 6.
3. React readiness, intentional error states and native dropdown limitations: browser fixtures in Change 5.
4. Restart/concurrency bypass of the three-iteration budget: state-machine tests in Change 5.
5. Fabricated success from skipped checks or stale screenshots: evidence tests in Changes 2 and 5.

Roll out against the bundled showcase first, then deterministic interactive fixtures, then actual host sessions. Only after those pass should a separate NovaBank UI task consume the new workflow. Back up owned toolkit files/wrappers before implementation; roll back only those owned changes, never third-party skill directories or NovaBank's existing working tree.

Plan self-review: all six user requirements map to Changes 1–6; dependency order is explicit; currently verified capabilities are separated from proposed behavior and unverified integrations. No implementation performed as part of this plan.
