import { useEffect, useState } from 'react';
import {
  ArrowDownLeft, ArrowLeftRight, ArrowUpRight, Bell, ChevronRight, CreditCard, Info, LifeBuoy, Megaphone, PieChart,
  ReceiptText, RefreshCw, RotateCcw, Search, ShieldCheck, TriangleAlert, X,
} from 'lucide-react';
import { api } from '../../api';
import type { Announcement, BankNotification, DemoUser, NotificationCategory, NotificationPage } from '../../types';
import { navigate } from '../../router';
import { Pagination } from '../ui/Pagination';
import { NewsTeaser, SafetyTip, UpcomingBills } from '../home/Rail';

type TabId = 'all' | NotificationCategory | 'news';
const TABS: { id: TabId; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'transactions', label: 'Transactions' },
  { id: 'account', label: 'Account' },
  { id: 'news', label: 'NovaBank news' },
];
const EMPTY: Record<TabId, string> = {
  all: 'Transfers, security and support updates will appear here.',
  transactions: 'Money in, money out, refunds and bill reminders will appear here.',
  account: 'Sign-in, card, budget and support updates will appear here.',
  news: 'There are no campaigns or service notices right now.',
};
// Icon and colour per alert kind; anything unknown falls back to a neutral bell.
const KINDS: Record<string, { icon: typeof Bell; tone: string }> = {
  MONEY_IN: { icon: ArrowDownLeft, tone: 'green' },
  MONEY_OUT: { icon: ArrowUpRight, tone: 'violet' },
  TRANSFER: { icon: ArrowLeftRight, tone: 'violet' },
  REFUND: { icon: RotateCcw, tone: 'green' },
  BILL: { icon: ReceiptText, tone: 'orange' },
  SECURITY: { icon: ShieldCheck, tone: 'blue' },
  CARD: { icon: CreditCard, tone: 'blue' },
  SUPPORT: { icon: LifeBuoy, tone: 'green' },
  BUDGET: { icon: PieChart, tone: 'orange' },
  RECONCILIATION: { icon: TriangleAlert, tone: 'red' },
};
const ZONE = 'Asia/Ho_Chi_Minh';
const dayKey = (iso: string) => new Date(iso).toLocaleDateString('sv-SE', { timeZone: ZONE });
const clock = (iso: string) => new Date(iso).toLocaleTimeString('en-GB', { timeZone: ZONE, hour: '2-digit', minute: '2-digit' });
const longDate = (iso: string) => new Date(iso).toLocaleDateString('en-GB', { timeZone: ZONE, day: 'numeric', month: 'long', year: 'numeric' });

function dayLabel(key: string) {
  const today = dayKey(new Date().toISOString());
  const yesterday = dayKey(new Date(Date.now() - 86_400_000).toISOString());
  if (key === today) return 'Today';
  if (key === yesterday) return 'Yesterday';
  return new Date(key + 'T12:00:00+07:00').toLocaleDateString('en-GB', { timeZone: ZONE, weekday: 'long', day: 'numeric', month: 'long' });
}

export function Notifications({ user, openTransaction }: { user: DemoUser; openTransaction: (id: string) => void }) {
  const [tab, setTab] = useState<TabId>('all');
  const [data, setData] = useState<NotificationPage | null>(null);
  const [news, setNews] = useState<Announcement[] | null>(null);
  const [counts, setCounts] = useState<Record<NotificationCategory, number>>({ transactions: 0, account: 0 });
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [busy, setBusy] = useState(true);
  const [changing, setChanging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState('');
  const [unreadOnly, setUnreadOnly] = useState(false);
  const filtered = !!search || unreadOnly;
  const category = tab === 'transactions' || tab === 'account' ? tab : undefined;

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') setRevision(n => n + 1);
    }, 15_000);
    return () => window.clearInterval(timer);
  }, []);
  // Debounce typing so the server is asked once the customer pauses.
  useEffect(() => {
    const timer = window.setTimeout(() => { setSearch(query.trim()); setOffset(0); }, 300);
    return () => window.clearTimeout(timer);
  }, [query]);
  useEffect(() => {
    let active = true;
    setBusy(true);
    setError(null);
    const load = tab === 'news'
      ? api.announcements(user).then(result => { if (active) setNews(result.items); })
      : api.notifications(user, offset, category, { q: search, unread: unreadOnly }).then(result => {
        if (!active) return;
        setData(result);
        if (result.unread_by_category) setCounts(result.unread_by_category);
      });
    load.catch(err => { if (active) setError(err.message); }).finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [user, tab, category, offset, revision, search, unreadOnly]);
  // News is fetched once for its badge; the list itself reloads with the tab.
  useEffect(() => { api.announcements(user).then(result => setNews(result.items)).catch(() => { }); }, [user]);

  function choose(next: TabId) {
    setTab(next);
    setOffset(0);
    setData(null);
  }

  async function read(id?: string) {
    if (changing) return;
    setChanging(true);
    setError(null);
    try {
      if (id) {
        const target = data?.items.find(n => n.id === id);
        const result = await api.readNotification(user, id);
        if (target && !target.read_at) {
          const group: NotificationCategory = target.category ?? 'account';
          setCounts(previous => ({ ...previous, [group]: Math.max(0, previous[group] - 1) }));
        }
        setData(previous => previous && ({ ...previous, unread_count: Math.max(0, previous.unread_count - (target?.read_at ? 0 : 1)),
          items: previous.items.map(n => n.id === id ? { ...n, ...result } : n) }));
      } else {
        await api.readAllNotifications(user, category);
        setRevision(n => n + 1);
      }
    } catch (err) { setError((err as Error).message); }
    finally { setChanging(false); }
  }

  const badge: Record<TabId, number> = {
    all: counts.transactions + counts.account, transactions: counts.transactions, account: counts.account,
    // News has no read state; "new" means published in the last 7 days.
    news: news?.filter(n => Date.now() - new Date(n.published_at).getTime() < 7 * 86_400_000).length ?? 0,
  };
  const needle = search.toLowerCase();
  const shownNews = news?.filter(n => !needle || (n.title + ' ' + n.body + ' ' + n.tag).toLowerCase().includes(needle));
  const clearFilters = () => { setQuery(''); setSearch(''); setUnreadOnly(false); setOffset(0); };
  const groups: [string, BankNotification[]][] = [];
  for (const item of data?.items ?? []) {
    const key = dayKey(item.created_at);
    if (groups.at(-1)?.[0] !== key) groups.push([key, []]);
    groups.at(-1)![1].push(item);
  }

  return <div className="page alerts with-rail">
    <div className="rail-main">
    <div className="page-heading">
      <div><h1 className="page-title">Alerts</h1><p className="muted">Your money, your account and news from NovaBank.</p></div>
      <button className="icon-button alerts-refresh" aria-label="Refresh" title="Refresh" disabled={busy || changing} onClick={() => setRevision(n => n + 1)}>
        <RefreshCw size={18} aria-hidden="true" />
      </button>
    </div>

    <div className="alert-tabs" role="group" aria-label="Alert type">
      {TABS.map(({ id, label }) => (
        <button key={id} aria-pressed={tab === id} onClick={() => choose(id)}>
          {label}{badge[id] > 0 && <span className="tab-count" aria-label={`${badge[id]} ${id === 'news' ? 'new' : 'unread'}`}>{badge[id] > 99 ? '99+' : badge[id]}</span>}
        </button>
      ))}
    </div>

    <div className="alerts-tools">
      <label className="alerts-search">
        <Search size={18} aria-hidden="true" />
        <input type="search" value={query} onChange={e => setQuery(e.target.value)} maxLength={100}
          placeholder={tab === 'news' ? 'Search news and campaigns' : 'Search alerts, names or amounts'} aria-label="Search alerts" />
        {query && <button type="button" className="icon-button" aria-label="Clear search" onClick={() => setQuery('')}><X size={16} /></button>}
      </label>
      {tab !== 'news' && <button className="filter-chip" aria-pressed={unreadOnly} onClick={() => { setUnreadOnly(v => !v); setOffset(0); }}>Unread only</button>}
    </div>

    {error && <div className="form-error" role="alert">{error} <button className="link-button" onClick={() => setRevision(n => n + 1)}>Try again</button></div>}
    {busy && !data && !news && <p className="muted" role="status">Loading alerts…</p>}

    {tab === 'news' ? shownNews && (shownNews.length === 0 ? (search ? <NoMatch query={search} clear={clearFilters} /> : <Empty text={EMPTY.news} />) : <>
      <ul className="news-list">{shownNews.map(item => <NewsCard key={item.id} item={item} />)}</ul>
      <p className="muted small center">Campaigns are fictional and shown for this demo only.</p>
    </>) : data && <>
      <div className="alerts-bar">
        <span className="muted small" role="status">{data.unread_count} unread</span>
        <button className="link-button" disabled={changing || busy || data.unread_count === 0} onClick={() => read()}>Mark all as read</button>
      </div>
      {data.total === 0 ? (filtered ? <NoMatch query={search} clear={clearFilters} /> : <Empty text={EMPTY[tab]} />) : groups.map(([key, items]) => (
        <section className="alert-day" key={key} aria-label={dayLabel(key)}>
          <h2 className="day-label">{dayLabel(key)}</h2>
          <ul className="notification-list">{items.map(n => {
            const { icon: Icon, tone } = KINDS[n.kind] ?? { icon: Bell, tone: 'gray' };
            return <li className="notification" key={n.id} data-unread={!n.read_at}>
              <span className={`note-icon tone-${tone}`} aria-hidden="true"><Icon size={20} /></span>
              <div className="notification-content">
                <div className="note-head">
                  <h3>{n.title}</h3>
                  <time className="muted small" dateTime={n.created_at}>{clock(n.created_at)}</time>
                </div>
                <p>{n.body}</p>
                {(n.transaction_id || !n.read_at) && <div className="inline-actions">
                  {n.transaction_id && <button className="link-button" onClick={() => { void read(n.id); openTransaction(n.transaction_id!); }}>View transaction <ChevronRight size={15} aria-hidden="true" /></button>}
                  {!n.read_at && <button className="link-button" disabled={changing || busy} onClick={() => read(n.id)}>Mark as read</button>}
                </div>}
              </div>
              {!n.read_at && <span className="unread-dot" title="Unread"><span className="sr-only">Unread</span></span>}
            </li>;
          })}</ul>
        </section>
      ))}
      <Pagination {...data} busy={busy || changing} change={setOffset} />
    </>}
    </div>
    <aside className="side-rail" aria-label="At a glance">
      <NewsTeaser user={user} />
      <UpcomingBills user={user} />
      <SafetyTip />
    </aside>
  </div>;
}

function Empty({ text }: { text: string }) {
  return <section className="card empty-state"><Bell size={28} aria-hidden="true" /><h2>You’re all caught up</h2><p className="muted">{text}</p></section>;
}

function NoMatch({ query, clear }: { query: string; clear: () => void }) {
  return <section className="card empty-state"><Search size={28} aria-hidden="true" />
    <h2>No matching alerts</h2><p className="muted">{query ? `Nothing matches “${query}” here.` : 'There are no unread alerts here.'}</p>
    <button className="secondary-button" onClick={clear}>Clear filters</button></section>;
}

function NewsCard({ item }: { item: Announcement }) {
  const campaign = item.kind === 'CAMPAIGN';
  const Icon = campaign ? Megaphone : Info;
  return <li className={`news-card ${campaign ? 'is-campaign' : 'is-notice'}`}>
    <div className="news-art" aria-hidden="true"><Icon size={26} /><span>{item.tag}</span></div>
    <div className="news-body">
      <small className="muted">{campaign ? 'Campaign' : 'Notice'} · {longDate(item.published_at)}{item.ends_at ? ` · until ${longDate(item.ends_at)}` : ''}</small>
      <h3>{item.title}</h3>
      <p>{item.body}</p>
      {item.action_label && item.action_path && <button className="secondary-button" onClick={() => navigate(item.action_path!)}>{item.action_label} <ChevronRight size={16} aria-hidden="true" /></button>}
    </div>
  </li>;
}
