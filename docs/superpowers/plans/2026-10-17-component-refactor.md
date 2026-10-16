# Frontend component refactor

Goal: make the existing interface easier to maintain without changing behavior, markup, styling, dependencies or API contracts.
Architecture: App composes typed presentation components; useBankingChat owns the existing session, request and interaction coordination. Suggestions and message formatting have focused modules. CSS is split by responsibility with the original cascade preserved.
Stack: existing React 19, TypeScript, Vite, npm and plain CSS.

- [x] Capture initial rendered HTML as a refactor baseline.
- [x] Extract Sidebar, Topbar, Welcome, MessageThread, Composer and TestingInsights (including PolicyTest and ToolActivity).
- [x] Move existing orchestration into useBankingChat and keep App as layout wiring.
- [x] Split CSS into ordered files and verify byte-equivalent concatenated rules.
- [x] Build, run render regression checks and attempt the existing identity check.
- [x] Review diff and document module ownership and verification limits.

No dependencies, services, commits or backend changes are required. Existing working-tree edits must be preserved.

Live identity verification was attempted but remains blocked by the unavailable browser debugging endpoint. See docs/component-refactor-completion.md for evidence and limitations.
