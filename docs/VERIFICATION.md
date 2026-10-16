# Verification performed — 15 October 2026

- `python -m pytest -q` from `backend`: **21 passed**.
- Python `compileall` for backend: passed.
- TypeScript/TSX syntax transpilation for `App.tsx`, `api.ts`, `main.tsx`, `types.ts` using global TypeScript compiler: no syntactic diagnostics.
- `npm install --offline` failed with `ENOTCACHED`; the environment did not have the needed npm packages.
- Registry-based `npm install` timed out in this environment. Therefore **`npm run build` and browser UI interaction have not been verified here**.
- Ollama Llama 3.2 3B actual responses have **not been run here**; tests simulate the Ollama chat API and verify tool response formatting and policy denial behavior.
- Group 10's actual gateway contract is not supplied or wired: remote gateway adapter is a **proposed interface only**.

To complete on Windows: install dependencies, run `npm run build`, launch frontend/backend, and run the demo cases in `docs/DEMO_SCRIPT.md`. Run the true Ollama mode to measure the LLM's tool use. Never expose demo user credentials outside a local development machine.
