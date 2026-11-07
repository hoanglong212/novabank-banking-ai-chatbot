import type { ReactNode } from 'react';
import { Play } from 'lucide-react';
import { AuthArtwork } from './AuthArtwork';
import '../../styles/auth-experience.css';

export function AuthShell({ children, stage, onReplayIntro }: { children: ReactNode; stage: string; onReplayIntro?: () => void }) {
  return (
    <div className="auth-experience">
      <a className="skip-link" href="#auth-main">Skip to form</a>
      <header className="auth-masthead">
        <div className="auth-wordmark" aria-label="NovaBank"><span className="auth-logo" aria-hidden="true">N</span><span>nova<span>bank</span></span></div>
        <span className="auth-demo-tag">Demo experience</span>
      </header>
      <div className="auth-layout">
        <aside className="auth-editorial" aria-label="About NovaBank">
          <AuthArtwork />
          <p className="auth-editorial-bottom">DEMO ENVIRONMENT · SAMPLE DETAILS ONLY</p>
        </aside>
        <main id="auth-main" className="auth-main" tabIndex={-1}>
          <div className={`auth-surface auth-surface-${stage}`}>
            <div className="auth-stage" key={stage}>{children}</div>
          </div>
        </main>
      </div>
      <footer className="auth-page-footer">
        {onReplayIntro && <button type="button" className="nova-intro-replay" onClick={onReplayIntro}><Play size={12} aria-hidden="true" /> Replay introduction</button>}
        <p>Classroom demo. Use sample details only.</p>
      </footer>
    </div>
  );
}
