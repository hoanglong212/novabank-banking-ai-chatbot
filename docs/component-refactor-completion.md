# Component refactor evidence — 2026-10-17

## Changes

- Extracted eight typed presentation components under `frontend/src/components/`.
- Moved existing state, handlers and effects into `frontend/src/hooks/useBankingChat.ts`.
- Reduced `App.tsx` to page composition and explicit prop wiring.
- Centralized suggestions and message formatting in focused chat modules.
- Split CSS into seven ordered files, preserving the original rules and cascade.
- Added the `test:components` npm command and a frontend maintenance guide.
- Preserved pre-existing working-tree changes. No dependency, lockfile, backend or API changes.

## Verification

| Acceptance criterion | Evidence |
| --- | --- |
| Application compiles | `npm run build`: passed TypeScript and Vite |
| Rendering contracts preserved | `npm run test:components`: six scenario groups passed |
| Initial markup unchanged | Server-rendered App HTML compared byte-for-byte with the pre-refactor working-tree baseline: passed |
| Styling unchanged | Concatenated CSS matched the pre-refactor source exactly; compiled CSS retained the same content hash |
| State and handlers unchanged | Compared TypeScript syntax trees of the original App body and extracted hook, excluding return values and the relocated model label: passed |
| Whitespace checks | `git diff --check`: passed |
| Live identity switching | `npm run test:identity`: could not run; connection refused at `127.0.0.1:9224` |

Tailwind still reports that no utility classes were detected. Git reports LF/CRLF normalization notices. No lint command is configured. Browser interaction verification remains pending. Local review was performed by the implementing agent; independent review was not performed.

The one-time before/after comparison inputs are local artifacts under ignored `.local/refactor/`; the component checks are committed-source candidates under `frontend/tests/` and are repeatable with the npm command.

## Rollback

Restore the pre-refactor App and stylesheet snapshots from `.local/refactor/` if needed, then remove only the new component/hook/style modules, test runner, test script entry and documentation from this task. Do not reset whole files to HEAD: the working tree contained earlier UI and ignore-rule changes.
