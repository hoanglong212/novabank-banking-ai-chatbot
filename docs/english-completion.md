# English language update

The user requested English throughout the app. Navigation, accessibility labels, suggestions, composer, policy inspector, demo identities, FAQs and new assistant replies now use English. HTML language and time formatting use English; VND amounts use comma grouping. README and the current demo script reflect the new language.

Mock mode now shares the guarded request binding and response renderer with Ollama mode, so English prompts behave consistently and future copy changes cannot drift between modes. Mock mode still makes no model request; authorization continues through the existing dispatcher. Historical chat content and evaluation records are preserved. Vietnamese regression inputs remain to check compatibility, but replies are English.

Validation:

- Added two English conversation-flow tests, observed failing before implementation, then passing.
- `backend/.venv/Scripts/python.exe -m pytest -q --tb=short` from backend (using `.venv/Scripts/python.exe` there): 51 passed, one existing Starlette/httpx deprecation warning.
- `npm.cmd run build --prefix frontend`: passed, existing Tailwind no-utility warning.
- Live Ollama: greeting, balance, affordability, transaction, VietQR and ticket creation all returned the expected English response. Temporary verification conversation removed; one simulated support ticket was created.
- Source scan: no Vietnamese UI/output copy remains. The accent-normalization helper and legacy input keywords remain intentionally.
- `git diff --check`: passed.

Visual browser recheck was not completed: automatic execution review blocked launching the isolated headless Edge browser. Self-review only; independent review remains pending. No new dependencies installed.

Rollback: revert the English-language update commit and rebuild the frontend. No database migration or history rewrite was performed.
