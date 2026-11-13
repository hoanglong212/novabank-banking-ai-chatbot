// Frames are decoded losslessly from the user's Nova Intro v11 (1).mp4, 1280x720/30fps.
// Re-extract: ffmpeg -i INPUT -frames:v 135 -c:v libwebp -lossless 1 -pix_fmt bgra -start_number 0 frames/frame-%03d.webp
import { writeFileSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const folder = new URL('../public/animations/nova-intro-v11/', import.meta.url);
const count = 135;
const assets = Array.from({ length: count }, (_, i) => ({
  id: `frame_${i}`, w: 1280, h: 720, u: 'frames/', p: `frame-${String(i).padStart(3, '0')}.webp`, e: 0,
}));
const layers = assets.map((asset, i) => ({
  ddd: 0, ind: i + 1, ty: 2, nm: asset.id, refId: asset.id, sr: 1,
  ks: { o: { a: 0, k: 100 }, r: { a: 0, k: 0 }, p: { a: 0, k: [0, 0, 0] }, a: { a: 0, k: [0, 0, 0] }, s: { a: 0, k: [100, 100, 100] } },
  ip: i, op: i + 1, st: 0, bm: 0,
}));
const animation = { v: '5.12.2', fr: 30, ip: 0, op: count, w: 1280, h: 720, nm: 'Nova Intro v11 (1) — original frames', ddd: 0, assets, layers, markers: [{ tm: 30, cm: 'loading', dr: 0 }] };
writeFileSync(new URL('animation.json', folder), JSON.stringify(animation));
const bytes = assets.reduce((sum, asset) => sum + statSync(new URL(asset.u + asset.p, folder)).size, 0);
console.log(`${count} frames / ${count / 30}s / ${(bytes / 1024 / 1024).toFixed(2)} MiB; ${fileURLToPath(folder)}`);
