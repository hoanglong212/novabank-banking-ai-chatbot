import { expect, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

export function localMessage(email: string, kind: string) {
  const root = resolve('..');
  const db = JSON.parse(readFileSync(resolve(root, '.local/e2e/latest.json'), 'utf8')).db_path;
  const venv = resolve(root, process.platform === 'win32' ? 'backend/.venv/Scripts/python.exe' : 'backend/.venv/bin/python');
  const python = process.env.NOVABANK_PYTHON || (existsSync(venv) ? venv : 'python');
  const cli = resolve(root, 'scripts/dev-outbox.py');
  const rows = JSON.parse(execFileSync(python, [cli, '--db', db, '--email', email], { encoding: 'utf8' }));
  const row = rows.find((r: { kind: string }) => r.kind === kind);
  expect(row).toBeTruthy();
  return JSON.parse(execFileSync(python, [cli, '--db', db, '--id', row.id, '--origin', 'http://127.0.0.1:8092'], { encoding: 'utf8' }));
}

export async function completeEmailMfa(page: Page, email: string) {
  await expect(page.getByRole('heading', { name: 'Verify sign-in', exact: true })).toBeVisible();
  await page.getByLabel('Verification code', { exact: true }).fill(localMessage(email, 'LOGIN_OTP').code);
  await page.getByRole('button', { name: 'Verify and sign in', exact: true }).click();
  await expect(page.getByRole('navigation', { name: 'Main', exact: true })).toBeVisible();
}

export async function beginDemoLogin(page: Page, username: string) {
  await page.goto('/');
  await page.getByLabel('Username', { exact: true }).fill(username);
  await page.getByLabel('Password', { exact: true }).fill(username[0].toUpperCase() + username.slice(1) + '@2026');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Verify sign-in', exact: true })).toBeVisible();
}

export async function demoLogin(page: Page, username: string) {
  await beginDemoLogin(page, username);
  await completeEmailMfa(page, username + '@novabank.test');
}
