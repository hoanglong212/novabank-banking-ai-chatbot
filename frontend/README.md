# Frontend maintenance guide

Follow the [Docker quick start](../README.md#quick-start-with-docker) to try the full app and Agent. For frontend development, first start the app on port 8080 using Docker or the [Windows launcher](../README.md#native-windows-development). Then run these commands from `frontend/`:

```sh
npm ci
npm run dev
```

Open the URL printed by Vite, normally <http://127.0.0.1:5173>. Vite forwards `/api` to `http://127.0.0.1:8080`. If you change the app port, update the proxy target in [vite.config.ts](vite.config.ts).

## Where to make changes

| Location | Responsibility |
| --- | --- |
| [src/App.tsx](src/App.tsx) | Page layout and feature wiring |
| [src/hooks/useSession.ts](src/hooks/useSession.ts), [src/sessionStore.ts](src/sessionStore.ts) | Sign-in and session state |
| [src/hooks/useBankingChat.ts](src/hooks/useBankingChat.ts) | Conversations and Agent requests |
| [src/components/app/NavBar.tsx](src/components/app/NavBar.tsx) | Main navigation |
| [src/components/chat/](src/components/chat/) | Assistant, composer, history, approvals and Agent activity |
| [src/components/explore/](src/components/explore/) | Banking services and product screens |
| [src/components/admin/](src/components/admin/) | Admin dashboard, settings and operations |
| [src/api.ts](src/api.ts), [src/types.ts](src/types.ts) | HTTP client and API types |

Keep network requests and shared state in the existing hooks. Pass typed values and callbacks to presentation components.

[src/index.css](src/index.css) defines the global cascade order. Shared tokens live in [src/styles/base.css](src/styles/base.css). Keep the import order so layout and reduced-motion overrides apply as intended.

## Checks

```sh
npm run build
npm run test:components
npm run test:e2e
```

`npm run test:e2e` builds the app and runs Playwright against a test backend on port 8092. Prepare the backend virtual environment and Playwright Chromium first. Set `NOVABANK_PYTHON` to use a different Python interpreter.

Import `test` and `expect` from [tests/e2e/fixtures.ts](tests/e2e/fixtures.ts). The inbox helpers use the fresh test database identified by `.local/e2e/latest.json`. Keep one worker so tests use the correct database. Server logs are kept in the test output directory.
