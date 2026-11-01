import assert from 'node:assert/strict';
import { acceptSession, clearSession, currentSession, refreshSession, expireIfIdle, recordActivity } from '../src/sessionStore';
import { api } from '../src/api';
import type { LoginResponse } from '../src/types';

export async function checkSessionCoordination() {
  const originalFetch = globalThis.fetch;
  const originalNow = Date.now;
  let now = originalNow();
  Date.now = () => now;
  const initial: LoginResponse = { access_token: 'access-one', refresh_token: 'refresh-one', session_id: 'session-one',
    expires_in: 300, idle_expires_at: now / 1000 + 300, absolute_expires_at: now / 1000 + 28800,
    user: { id: 'alice', name: 'Alice', role: 'customer', permissions: [] } };
  let finish!: (value: Response) => void;
  let calls = 0;
  globalThis.fetch = async () => { calls++; return new Promise<Response>(resolve => { finish = resolve; }); };
  try {
    acceptSession(initial);
    const one = refreshSession();
    const two = refreshSession();
    assert.equal(calls, 1, 'concurrent requests share one rotation');
    finish(new Response(JSON.stringify({ ...initial, access_token: 'access-two', refresh_token: 'refresh-two' })));
    await Promise.all([one, two]);
    assert.equal(currentSession()?.refreshToken, 'refresh-two');
    const late = refreshSession();
    clearSession();
    acceptSession({ ...initial, session_id: 'new-session' });
    finish(new Response(JSON.stringify({ ...initial, access_token: 'stale', refresh_token: 'stale' })));
    await assert.rejects(late);
    assert.equal(currentSession()?.sessionId, 'new-session', 'late refresh cannot replace a new login');
    // A failed response from an old authenticated request must not log out a later login.
    let finishOld!: (value: Response) => void;
    globalThis.fetch = async () => new Promise<Response>(resolve => { finishOld = resolve; });
    const oldRequest = api.me(currentSession()!.user);
    await new Promise(resolve => setTimeout(resolve, 0));
    clearSession();
    acceptSession({ ...initial, session_id: 'third-session' });
    finishOld(new Response('{}', { status: 401 }));
    await assert.rejects(oldRequest);
    assert.equal(currentSession()?.sessionId, 'third-session');

    // Rotation during background reads cannot extend the idle deadline or replace user identity.
    const identity = currentSession()!.user;
    globalThis.fetch = async () => new Response(JSON.stringify({ ...initial, session_id: 'third-session',
      access_token: 'fresh', refresh_token: 'rotated' }));
    now += 240_000;
    await refreshSession();
    assert.equal(currentSession()?.user, identity);
    now += 60_000;
    assert.equal(expireIfIdle(), true);
    assert.equal(currentSession(), null, 'refresh and polling never extend idle expiry');

    acceptSession({ ...initial, idle_expires_at: now / 1000 + 300 });
    let activityCalls = 0;
    globalThis.fetch = async url => {
      assert.equal(url, '/api/auth/activity');
      activityCalls++;
      return new Response(JSON.stringify({ idle_expires_at: now / 1000 + 300 }));
    };
    // Give this session a current access token and then advance a minute.
    now += 60_000;
    await recordActivity();
    await recordActivity();
    assert.equal(activityCalls, 1, 'interaction heartbeat is throttled');
    now += 240_000;
    assert.equal(expireIfIdle(), false, 'acknowledged interaction extends the idle deadline');
    now += 60_000;
    assert.equal(expireIfIdle(), true);

    acceptSession({ ...initial, idle_expires_at: now / 1000 + 300, absolute_expires_at: now / 1000 + 60 });
    now += 60_000;
    assert.equal(expireIfIdle(), true, 'absolute expiry is enforced even when idle time remains');

    acceptSession({ ...initial, idle_expires_at: now / 1000 + 300 });
    globalThis.fetch = async () => new Response('{}', { status: 401 });
    await assert.rejects(refreshSession());
    assert.equal(currentSession(), null, 'rejected rotation clears credentials');

    acceptSession({ ...initial, idle_expires_at: now / 1000 + 300 });
    globalThis.fetch = async () => new Response(JSON.stringify({ ...initial,
      idle_expires_at: now / 1000 + 300, user: { ...initial.user, id: 'bob' } }));
    await assert.rejects(refreshSession());
    assert.equal(currentSession(), null, 'a refresh cannot change the signed-in identity');

    acceptSession({ ...initial, idle_expires_at: now / 1000 + 300 });
    now += 300_000;
    assert.equal(expireIfIdle(), true);
    assert.equal(currentSession(), null, 'wall-clock timeout is enforced even after background suspension');
    console.log('PASS: refresh single-flight, stale responses, identity binding, interaction throttle and idle/absolute expiry');
  } finally { clearSession(); globalThis.fetch = originalFetch; Date.now = originalNow; }
}
