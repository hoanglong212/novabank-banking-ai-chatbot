// Sign-in illustration follows the pointer a little. Sets --mx/--my (-1..1) on .auth-editorial;
// CSS turns them into per-card offsets. Eased with rAF so cards glide instead of jumping.
export function startPointerParallax() {
  if (!window.matchMedia('(prefers-reduced-motion: no-preference)').matches || !window.matchMedia('(pointer: fine)').matches) return;
  let target = { x: 0, y: 0 }, current = { x: 0, y: 0 }, frame = 0;
  const step = () => {
    current = { x: current.x + (target.x - current.x) * 0.08, y: current.y + (target.y - current.y) * 0.08 };
    const panel = document.querySelector<HTMLElement>('.auth-editorial');
    if (panel) { panel.style.setProperty('--mx', current.x.toFixed(3)); panel.style.setProperty('--my', current.y.toFixed(3)); }
    frame = Math.abs(target.x - current.x) + Math.abs(target.y - current.y) > 0.002 ? requestAnimationFrame(step) : 0;
  };
  window.addEventListener('pointermove', event => {
    if (!document.querySelector('.auth-editorial')) return;
    target = { x: event.clientX / innerWidth * 2 - 1, y: event.clientY / innerHeight * 2 - 1 };
    if (!frame) frame = requestAnimationFrame(step);
  }, { passive: true });
}
