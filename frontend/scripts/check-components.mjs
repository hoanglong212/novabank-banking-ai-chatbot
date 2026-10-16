// Render real components using the existing Vite/esbuild toolchain; no DOM dependency.
import { build } from 'esbuild';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const directory = mkdtempSync(join(tmpdir(), 'novabank-components-'));
try {
  const outfile = join(directory, 'checks.cjs');
  await build({
    entryPoints: [fileURLToPath(new URL('../tests/components.test.tsx', import.meta.url))],
    bundle: true,
    platform: 'node',
    format: 'cjs',
    jsx: 'automatic',
    outfile,
  });
  execFileSync(process.execPath, [outfile], { stdio: 'inherit' });
} finally {
  rmSync(directory, { recursive: true, force: true });
}
