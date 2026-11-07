import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import type { AnimationItem } from 'lottie-web';
import { ArrowRight } from 'lucide-react';
import '../../styles/intro.css';

const SEEN_KEY = 'novabank-intro-seen';
const ASSET_ROOT = '/animations/nova-intro-vector/';

function alreadySeen() {
  if (typeof window === 'undefined') return true;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return true;
  try { return sessionStorage.getItem(SEEN_KEY) === '1'; } catch { return false; }
}

/** Resolution-independent vector Lottie; recovery links and signed-in sessions bypass it. */
export function IntroGate({ children, bypass = false }: {
  children: (replay?: () => void) => ReactNode; bypass?: boolean;
}) {
  const [playing, setPlaying] = useState(() => !alreadySeen());
  const [loading, setLoading] = useState(false);
  const container = useRef<HTMLDivElement>(null);
  const finish = useCallback(() => {
    try { sessionStorage.setItem(SEEN_KEY, '1'); } catch { /* Private storage may be unavailable. */ }
    setPlaying(false);
  }, []);

  useEffect(() => {
    if (bypass || !playing || !container.current) return;
    const target = container.current;
    const controller = new AbortController();
    let animation: AnimationItem | undefined;
    const resize = new ResizeObserver(() => animation?.resize());
    resize.observe(target);
    let cancelled = false;
    let announcedLoading = false;
    const timeout = setTimeout(finish, 15000);
    setLoading(false);
    void (async () => {
      const [module, response] = await Promise.all([
        import('lottie-web/build/player/lottie_light'),
        fetch(`${ASSET_ROOT}animation.json`, { signal: controller.signal }),
      ]);
      if (!response.ok) throw new Error('Intro unavailable');
      const data = await response.json();
      if (cancelled) return;
      animation = module.default.loadAnimation({
        container: target, renderer: 'svg', loop: false, autoplay: false,
        animationData: data,
        rendererSettings: { preserveAspectRatio: 'xMidYMid meet' },
      });
      animation.addEventListener('DOMLoaded', () => {
        if (cancelled) return;
        clearTimeout(timeout);
        animation?.play();
      });
      animation.addEventListener('enterFrame', event => {
        if (!announcedLoading && event.currentTime >= 30) {
          announcedLoading = true;
          setLoading(true);
        }
      });
      animation.addEventListener('complete', finish);
      animation.addEventListener('data_failed', finish);
      animation.addEventListener('error', finish);
    })().catch(() => { if (!cancelled) finish(); });
    return () => {
      cancelled = true;
      clearTimeout(timeout);
      controller.abort();
      resize.disconnect();
      animation?.destroy();
    };
  }, [bypass, playing, finish]);

  useEffect(() => {
    if (bypass || !playing) return;
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') finish(); };
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const reduce = () => { if (motion.matches) finish(); };
    window.addEventListener('keydown', escape);
    motion.addEventListener('change', reduce);
    return () => { window.removeEventListener('keydown', escape); motion.removeEventListener('change', reduce); };
  }, [bypass, playing, finish]);

  if (bypass || !playing) return children(bypass ? undefined : () => {
    if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) setPlaying(true);
  });

  return <section className="nova-intro" aria-label="NovaBank introduction">
    <div ref={container} className="nova-intro-player" aria-hidden="true" />
    <p className="nova-intro-status" role="status">{loading ? 'Opening NovaBank…' : 'NovaBank introduction'}</p>
    <button className="nova-intro-skip" type="button" onClick={finish}>Skip introduction <ArrowRight size={16} aria-hidden="true" /></button>
  </section>;
}
