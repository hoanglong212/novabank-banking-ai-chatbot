import { useEffect, useState } from 'react';
import { api } from './api';
import { Login } from './components/auth/Login';
import { NavBar, type Tab } from './components/app/NavBar';
import { Home } from './components/home/Home';
import { Activity } from './components/activity/Activity';
import { QrStudio } from './components/qr/QrStudio';
import { Profile } from './components/profile/Profile';
import { Assistant } from './components/chat/Assistant';
import { TransferSheet } from './components/transfer/TransferSheet';
import { useBankingChat } from './hooks/useBankingChat';
import { useSession } from './hooks/useSession';
import type { DemoUser, Profile as ProfileData, TransferStart } from './types';

export default function App() {
  const session = useSession();
  if (!session.user) return <Login onLogin={session.login} notice={session.notice} />;
  // Keyed by user so no state from a previous customer survives a new sign-in.
  return <BankApp key={session.user.id} user={session.user} logout={() => session.logout()} />;
}

function BankApp({ user, logout }: { user: DemoUser; logout: () => void }) {
  const chat = useBankingChat(user);
  const [tab, setTab] = useState<Tab>('home');
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [transfer, setTransfer] = useState<TransferStart | null>(null);
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
        {tab === 'home' && <Home user={user} profile={profile} navigate={setTab} ask={ask} transfer={() => setTransfer({})} />}
        {tab === 'activity' && <Activity profile={profile} ask={ask} />}
        {tab === 'qr' && <QrStudio user={user} pay={setTransfer} />}
        {tab === 'profile' && <Profile user={user} profile={profile} logout={logout} />}
        {tab === 'assistant' && <Assistant chat={chat} openTransfer={draftId => setTransfer({ draftId })} />}
      </main>
      <TransferSheet user={user} start={transfer} onClose={() => setTransfer(null)} onDone={() => setRefresh(n => n + 1)} />
    </div>
  );
}
