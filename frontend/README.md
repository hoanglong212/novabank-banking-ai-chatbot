# Frontend maintenance guide

Run commands from this directory:

```powershell
npm run dev
npm run build
npm run test:components
```

`npm run test:e2e` builds the app and runs Playwright against the real backend. Each test starts its own server on port 8092 with a fresh database under `.local/e2e`; keep that port free. The fixture uses the existing backend virtual environment or `NOVABANK_PYTHON`. Browser dependencies must already be available.

Import `test` and `expect` from `tests/e2e/fixtures.ts` in browser specs. Keep one worker: the local inbox helpers read the current test database from `.local/e2e/latest.json`. Each test must arrange its own transactions and accounts; it cannot rely on another test's balances, login sessions, MFA settings, or rate-limit budget. Server logs are retained in each test's output directory.

## Where to make changes

| Location | Responsibility |
| --- | --- |
| `src/App.tsx` | Page layout and wiring components to the controller |
| `src/hooks/useBankingChat.ts` | Session initialization, user/conversation selection, request coordination, drafts, panels, and focus/scroll effects |
| `src/components/layout/Sidebar.tsx` | Branding, conversation history, profile and mobile navigation |
| `src/components/layout/Topbar.tsx` | Title, model status, customer selector and panel toggles |
| `src/components/chat/Welcome.tsx` | Welcome screen and suggestion cards |
| `src/components/chat/MessageThread.tsx` | Message history and typing state |
| `src/components/chat/messageFormatting.tsx` | Safe inline emphasis and displayed timestamps |
| `src/components/chat/Composer.tsx` | Input, send button, errors and quick suggestions |
| `src/components/chat/suggestions.tsx` | Shared suggestion content for welcome cards and quick chips |
| `src/components/insights/TestingInsights.tsx` | Insights panel layout and gateway/model summary |
| `src/components/insights/ToolActivity.tsx` | Recent tool decisions |
| `src/components/insights/PolicyTest.tsx` | Dry-run controls and permission results |
| `src/api.ts` / `src/types.ts` | HTTP boundary and API data contracts |

Components receive typed values and callbacks. Keep network requests and cross-component state in the controller instead of duplicating them in presentation components. The controller stays mounted when panels close, so their form state is retained. User switching continues to reset identity-sensitive state centrally.

## Styling

`src/index.css` imports the files under `src/styles/` in cascade order:

1. `base.css`: fonts, Tailwind directives, design tokens, resets and shared primitives.
2. `sidebar.css`: navigation and profile.
3. `layout.css`: main area and top bar.
4. `chat.css`: welcome cards, messages, composer and suggestions.
5. `insights.css`: inspector, activity and permission form.
6. `interactions.css`: animation, dropdown enhancement and interaction states.
7. `responsive.css`: viewport overrides and reduced-motion rules.

Change shared colors in `base.css`. Preserve import order: mobile and reduced-motion rules intentionally override earlier declarations. The class names and DOM structure are also used by the live identity regression script.

## Checks

The production build checks application TypeScript. `test:components` bundles server-render checks with the esbuild toolchain already installed by Vite. It covers escaped message content, emphasis, selected navigation, disabled controls, permission outcomes, recent activity order and empty-draft state. It does not replace browser tests of clicks, keyboard input or asynchronous user switching.
