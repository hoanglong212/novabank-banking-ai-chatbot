// Requires an isolated Edge CDP session :9224 and same-origin UI/API :5173.
// Reads local credentials without printing them; no demo token bypass.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { call, evaluate, until, close, capture } from './browser-session.mjs';
const env = readFileSync(new URL('../../backend/.env', import.meta.url), 'utf8');
const password = who => {
  const value = env.match(new RegExp(`^DEMO_${who.toUpperCase()}_PASSWORD=['"]?([^'"\\r\\n]+)`, 'm'))?.[1];
  if (!value) throw new Error('Configure local demo passwords first');
  return value;
};
const ids = {};
async function reload() {
  await evaluate("window.__novabankReloadMarker='pending'");
  await call('Page.reload');
  await until("window.__novabankReloadMarker!=='pending' && document.readyState==='complete'");
}
async function login(who) {
  await until("!!document.querySelector('input[name=username]')");
  const fields = [['username',who],['password',password(who)]];
  await evaluate(`(()=>{for(const [name,value] of ${JSON.stringify(fields)}){const e=document.querySelector('input[name='+name+']');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}));}document.querySelector('button[type=submit]').click();})()`);
  await until("!!document.querySelector('.profile-name')");
}
async function logout() {
  await evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.textContent==='Sign out').click()");
  await until("!!document.querySelector('input[name=username]')");
}
async function create(who) {
  ids[who] = await evaluate(`(async()=>{const s=await fetch('/api/auth/session').then(r=>r.json());const r=await fetch('/api/conversations',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':s.csrf_token},body:JSON.stringify({title:'Session regression ${who}'})});if(!r.ok)throw new Error('create failed');return (await r.json()).id;})()`);
}
try {
  await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await call('Page.navigate',{url:process.env.NOVABANK_TEST_URL || 'http://127.0.0.1:5173'});
  await until("!!document.querySelector('input[name=username], .profile-name')");
  if (await evaluate("!!document.querySelector('.profile-name')")) await logout();
  await login('alice'); await create('alice');
  await reload();
  await until("Array.from(document.querySelectorAll('.conversation-open')).some(b=>b.title==='Session regression alice')");
  console.log('PASS: session and own history survive reload');
  await evaluate("Array.from(document.querySelectorAll('.workspace-tabs button')).find(b=>b.textContent==='Accounts & transfers').click()");
  await until("!!document.querySelector('input[name=recipient]') && !document.querySelector('input[name=recipient]').disabled");
  await evaluate(`(()=>{for(const [name,value] of [['recipient','ACC-BOB-001'],['amount','100000'],['description','Browser simulated transfer']]){const e=document.querySelector('input[name='+name+']');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}));}})()`);
  await evaluate("document.querySelector('.banking-panel button[type=submit]').click()");
  await until("!!document.querySelector('[aria-label=\"Transfer preview\"]')");
  await reload();
  await until("Array.from(document.querySelectorAll('.banking-panel button')).some(b=>b.textContent==='Confirm transfer' && !b.disabled)");
  await evaluate("Array.from(document.querySelectorAll('.banking-panel button')).find(b=>b.textContent==='Confirm transfer').click()");
  await until("!!document.querySelector('[aria-label=\"Transfer receipt\"]') && document.querySelector('.account-cards').textContent.includes('12,400,000')");
  await capture('../docs/day2-evidence-2026-10-23/transfer-receipt.png');
  console.log('PASS: manual transfer preview survives reload; confirmation produces receipt and updated balance');
  await logout(); await login('bob'); await create('bob');
  const denied = await evaluate(`fetch('/api/conversations/${ids.alice}/messages').then(r=>r.status)`);
  assert.equal(denied,404);
  assert.equal(await evaluate("Array.from(document.querySelectorAll('.conversation-open')).some(b=>b.title==='Session regression alice')"),false);
  console.log('PASS: Bob cannot read Alice history');
  await evaluate("Array.from(document.querySelectorAll('.workspace-tabs button')).find(b=>b.textContent==='Accounts & transfers').click()");
  await until("!!document.querySelector('.account-cards') && document.querySelector('.account-cards').textContent.includes('8,850,000')");
  assert.ok(await evaluate("document.querySelector('.bank-history').textContent.includes('Browser simulated transfer')"));
  console.log('PASS: recipient sees credited balance and transfer history');
  await logout(); await login('alice');
  await until("Array.from(document.querySelectorAll('.conversation-open')).some(b=>b.title==='Session regression alice')");
  console.log('PASS: sign out/sign in restores correct identity');
} finally {
  for(const who of Object.keys(ids)) {
    try {
      if(await evaluate("!!document.querySelector('.profile-name')")) await logout();
      await login(who);
      await evaluate(`(async()=>{const s=await fetch('/api/auth/session').then(r=>r.json());await fetch('/api/conversations/${ids[who]}',{method:'DELETE',headers:{'X-CSRF-Token':s.csrf_token}});})()`);
      await logout();
    } catch { console.error('Cleanup incomplete; remove temporary Session regression conversation after sign-in.'); }
  }
  close();
}
