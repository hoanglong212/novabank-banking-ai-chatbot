import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const python = fileURLToPath(new URL(process.platform === 'win32'
  ? '../../backend/.venv/Scripts/python.exe' : '../../backend/.venv/bin/python', import.meta.url));
const script = fileURLToPath(new URL('../../scripts/verify-browser.py',import.meta.url));
const result = spawnSync(python,[script],{stdio:'inherit',windowsHide:true});
if(result.error) console.error(result.error.message);
process.exit(result.status ?? 1);
