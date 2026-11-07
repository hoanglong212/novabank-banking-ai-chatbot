import { copyFileSync, mkdirSync, readdirSync } from 'node:fs';
const root = new URL('../', import.meta.url);
const target = new URL('public/ocr/runtime/', root);
mkdirSync(new URL('core/', target), { recursive: true });
copyFileSync(new URL('node_modules/tesseract.js/dist/worker.min.js', root), new URL('worker.min.js', target));
copyFileSync(new URL('node_modules/tesseract.js/LICENSE.md', root), new URL('LICENSE-tesseract-js', target));
const core = new URL('node_modules/tesseract.js-core/', root);
// OEM.LSTM_ONLY uses one of these three embedded-WASM variants, chosen by device capability.
for (const file of readdirSync(core).filter(name => name.endsWith('-lstm.wasm.js'))) {
  copyFileSync(new URL(file, core), new URL(`core/${file}`, target));
}
copyFileSync(new URL('LICENSE', core), new URL('LICENSE-tesseract-core', target));
console.log('Prepared local OCR worker and LSTM cores; no runtime CDN required.');
