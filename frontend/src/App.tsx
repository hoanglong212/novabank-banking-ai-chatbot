import { useEffect, useState } from 'react';
import { api } from './api';
import { AuthFlow } from './components/auth/AuthFlow';
import { parseAuthLink } from './components/auth/authLink';
import { NavBar, type Tab } from './components/app/NavBar';
import { Home } from './components/home/Home';
import { Activity } from './components/activity/Activity';
import { TransactionDetails } from './components/activity/TransactionDetails';
import { Notifications } from './components/notifications/Notifications';
import { AdminConsole } from './components/admin/AdminConsole';
import { QrStudio } from './components/qr/QrStudio';
import { Profile } from './components/profile/Profile';
import { Explore } from './components/explore/Explore';
import { Support } from './components/explore/Support';
import './styles/services.css';
import { Assistant } from './components/chat/Assistant';
import { TransferSheet } from './components/transfer/TransferSheet';
import { useBankingChat } from './hooks/useBankingChat';
import { useSession } from './hooks/useSession';
import type { DemoUser, Profile as ProfileData, TransferStart } from './types';
import { navigate, usePath } from './router';
import { Outbox } from './components/dev/Outbox';
import { ApprovalPage } from './components/chat/ApprovalPage';

export default function App() {
  const path = usePath();
  const session = useSession();
  const [authLink, setAuthLink] = useState(() => parseAuthLink(window.location.hash));
  const logout = session.logout;
  useEffect(() => {
    function consumeLink() {
      const link = parseAuthLink(window.location.hash);
      if (!link) return;
      setAuthLink(link);
      window.history.replaceState(null, '', window.location.pathname + window.location.search);
      logout();
    }
    consumeLink();
    window.addEventListener('hashchange', consumeLink);
    return () => window.removeEventListener('hashchange', consumeLink);
  }, [logout]);
  if (path === '/outbox') return <Outbox />;
  if (!session.user || authLink) return <AuthFlow key={authLink ? authLink.mode + authLink.token : 'login'}
    link={authLink} onLogin={session.login} onVerified={result => { session.completeLogin(result); setAuthLink(null); }} notice={session.notice} />;
  // Keyed by session so no state from a prior sign-in survives, even for the same customer.
  return <BankApp key={session.user.sessionId} user={session.user} logout={() => { navigate('/'); void session.logout(); }} />;
}

function BankApp({ user, logout }: { user: DemoUser; logout: () => void }) {
  const customer = !user.role || user.role === 'customer';
  const path = usePath();
  const chat = useBankingChat(user);
  const defaultTab: Tab = customer ? 'home' : user.permissions?.includes('admin:transactions:read') ? 'admin' : user.permissions?.includes('support:read') ? 'support' : 'profile';
  const routes: Record<string, Tab> = { '/': defaultTab, '/home': 'home', '/activity': 'activity', '/qr': 'qr', '/assistant': 'assistant', '/admin/assistant': 'assistant', '/profile': 'profile', '/notifications': 'notifications', '/admin': 'admin', '/explore': 'explore', '/support': 'support' };
  const tab = routes[path] ?? defaultTab;
  const setTab = (next: Tab) => navigate(next === 'assistant' && !customer ? '/admin/assistant' : '/' + next);
  const [transactionId, setTransactionId] = useState<string | null>(null);
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [prefill, setPrefill] = useState<TransferStart>({});
  const transferMatch = path.match(/^\/transfer\/([A-Za-z0-9-]+)\/(review|otp|receipt)$/);
  const qrMatch = path.match(/^\/qr\/pay\/([A-Za-z0-9-]+)$/);
  const approvalMatch = path.match(/^\/approvals\/([A-Za-z0-9-]+)$/);
  const transfer = customer ? (path === '/transfer/new' ? prefill : transferMatch || qrMatch ? { draftId: (transferMatch || qrMatch)![1] } : null) : null;
  const setTransfer = (start: TransferStart) => {
    setPrefill(start);
    navigate(start.draftId ? '/transfer/' + encodeURIComponent(start.draftId) + '/review' : '/transfer/new');
  };
  const denied = (customer && path.startsWith('/admin')) || (!customer && (path.startsWith('/transfer') || !!qrMatch || !!approvalMatch));
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    // Refresh on every tab change so balances and history stay current.
    api.me(user).then(setProfile).catch(() => { });
  }, [user, tab, refresh]);

  const ask = (text: string) => {
    setTab('assistant');
    void chat.askNew(text);
  };

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">Skip to content</a>
      <NavBar tab={tab} setTab={setTab} user={user} logout={logout} />
      {/* key restarts the enter animation on every tab change */}
      <main id="main" key={tab} className={`app-main ${tab === 'assistant' ? 'is-assistant' : ''}`}>
        {denied ? <p role="alert" className="form-error">403 · Your role does not have access to this page.</p> : approvalMatch ? <ApprovalPage key={approvalMatch[1]} user={user} id={approvalMatch[1]} /> : <>
        {tab === 'home' && <Home user={user} profile={profile} navigate={setTab} ask={ask} transfer={() => setTransfer({})} />}
        {tab === 'activity' && <Activity user={user} profile={profile} openTransaction={setTransactionId} />}
        {tab === 'notifications' && <Notifications user={user} openTransaction={setTransactionId} />}
        {tab === 'admin' && <AdminConsole user={user} />}
        {tab === 'qr' && <QrStudio user={user} pay={setTransfer} />}
        {tab === 'explore' && <Explore user={user} pay={setTransfer} />}
        {tab === 'support' && <div className="page"><h1 className="page-title">Support</h1><Support user={user} /></div>}
        {tab === 'profile' && <Profile user={user} profile={profile} logout={logout} />}
        {tab === 'assistant' && <Assistant chat={chat} openTransfer={draftId => setTransfer({ draftId })} />}
        </>}
      </main>
      <TransferSheet user={user} start={transfer} step={transferMatch?.[2] ?? (qrMatch ? 'review' : 'new')}
        onNavigate={(id, step) => navigate('/transfer/' + encodeURIComponent(id) + '/' + step)}
        onClose={() => navigate('/home')} onDone={() => setRefresh(n => n + 1)} />
      <TransactionDetails user={user} id={transactionId} onClose={() => setTransactionId(null)} ask={customer ? text => { setTransactionId(null); ask(text); } : undefined} />
    </div>
  );
}
