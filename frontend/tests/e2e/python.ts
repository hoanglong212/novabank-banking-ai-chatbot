import { existsSync } from 'node:fs';
import { resolve } from 'node:path';

// Match the bank server and every fixture subprocess on developer machines and CI.
export function pythonExecutable(root: string) {
  const venv = resolve(root, process.platform === 'win32'
    ? 'backend/.venv/Scripts/python.exe' : 'backend/.venv/bin/python');
  return process.env.NOVABANK_PYTHON || (existsSync(venv) ? venv : 'python');
}
