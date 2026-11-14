import { test as base, expect } from '@playwright/test';
import { spawn } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { writeFileSync } from 'node:fs';
import { createServer } from 'node:net';
import { resolve } from 'node:path';

export { expect };

// A separate ephemeral port lets this focused security suite run without
// borrowing another worktree's demo or fixed-port browser-test instance.
export const test = base.extend<{ qrBank: { url: string; signingKey: string } }>({
  qrBank: [async ({}, use, info) => {
    const reservation = createServer();
    const port = await new Promise<number>((resolvePort, reject) => {
      reservation.once('error', reject);
      reservation.listen(0, '127.0.0.1', () => {
        const address = reservation.address();
        if (!address || typeof address === 'string') return reject(new Error('No local test port'));
        reservation.close(() => resolvePort(address.port));
      });
    });
    const root = resolve('..');
    const python = process.env.NOVABANK_PYTHON || resolve(root, 'backend/.venv/Scripts/python.exe');
    const signingKey = randomBytes(32).toString('hex');
    const child = spawn(python, [resolve(root, 'scripts/run-e2e-server.py')], { cwd: root, windowsHide: true,
      env: { ...process.env, E2E_PORT: String(port), QR_SIGNING_KEY: signingKey } });
    let log = '', startup: Error | undefined;
    child.stdout.on('data', data => { log += data.toString(); });
    child.stderr.on('data', data => { log += data.toString(); });
    child.on('error', error => { startup = error; });
    const exited = new Promise<void>(done => child.once('close', () => done()));
    const url = `http://127.0.0.1:${port}`;
    try {
      await expect.poll(async () => {
        if (startup) throw startup;
        if (child.exitCode !== null) throw new Error(log);
        return fetch(url + '/api/health').then(response => response.ok, () => false);
      }, { timeout: 30000 }).toBe(true);
      await use({ url, signingKey });
    } finally {
      child.kill('SIGTERM');
      await exited;
      writeFileSync(info.outputPath('qr-bank.log'), log);
    }
  }, { auto: true, timeout: 40000 }],
  baseURL: async ({ qrBank }, use) => use(qrBank.url),
});
