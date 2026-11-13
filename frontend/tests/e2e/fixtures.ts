import { test as base, expect } from '@playwright/test';
import { spawn } from 'node:child_process';
import { existsSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

export { expect };
export type { Page, Locator } from '@playwright/test';

// Each test gets the real application and a fresh database. This prevents balances,
// sessions, MFA settings and rate-limit budgets leaking between independent tests.
export const test = base.extend<{ bankServer: void }>({
  bankServer: [async ({}, use, info) => {
    const root = resolve('..');
    const localPython = resolve(root, process.platform === 'win32' ? 'backend/.venv/Scripts/python.exe' : 'backend/.venv/bin/python');
    const python = process.env.NOVABANK_PYTHON || (existsSync(localPython) ? localPython : 'python');
    const health = 'http://127.0.0.1:8092/api/health';
    const occupied = await fetch(health).then(() => true, () => false);
    if (occupied) throw new Error('E2E port 8092 is already in use; refusing to use another server.');
    const child = spawn(python, [resolve(root, 'scripts/run-e2e-server.py')], {
      cwd: root, windowsHide: true, env: { ...process.env, E2E_PORT: '8092' },
    });
    let log = '', startupError: Error | undefined;
    child.stdout.on('data', chunk => { log += chunk.toString(); });
    child.stderr.on('data', chunk => { log += chunk.toString(); });
    child.on('error', error => { startupError = error; });
    const exited = new Promise<void>(resolveExit => child.once('close', () => resolveExit()));
    try {
      await expect.poll(async () => {
        if (startupError) throw startupError;
        if (child.exitCode !== null) throw new Error(`E2E server exited: ${log}`);
        return fetch(health).then(response => response.ok, () => false);
      }, { timeout: 30_000, message: 'Fresh banking server becomes ready' }).toBe(true);
      await use();
    } finally {
      child.kill('SIGTERM');
      await exited;
      const path = info.outputPath('bank-server.log');
      writeFileSync(path, log);
      if (info.status !== info.expectedStatus) await info.attach('bank-server', { path, contentType: 'text/plain' });
    }
  }, { auto: true, timeout: 40_000 }],
});
