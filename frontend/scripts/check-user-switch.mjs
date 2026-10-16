// Live regression check. Requires frontend :5173, backend :8000 and isolated Edge CDP :9224.
// Uses existing Node WebSocket; no browser automation dependency is installed.
import assert from 'node:assert/strict';
import { call, evaluate, until, close } from './browser-session.mjs';
const api='http://127.0.0.1:8000/api';
const clients={alice:{Authorization:'Bearer demo-alice-token','Content-Type':'application/json'},bob:{Authorization:'Bearer demo-bob-token','Content-Type':'application/json'}};
const seeds=[];
const expected={};
try {
  for(const who of ['alice','bob']) {
    const response=await fetch(api+'/conversations',{method:'POST',headers:clients[who],body:JSON.stringify({title:`Identity regression ${who} ${Date.now()}`})});
    assert.equal(response.status,201);
    seeds.push({who,...await response.json()});
    expected[who]=(await fetch(api+'/conversations',{headers:clients[who]}).then(r=>r.json())).map(c=>c.title).sort();
  }
  await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await call('Page.navigate',{url:'http://127.0.0.1:5173'});
  await until("!!document.querySelector('.user-select-wrap select')");
  await evaluate("sessionStorage.setItem('novabank-demo-user','alice')");
  await call('Page.reload');
  await until("document.querySelectorAll('.conversation-open').length>0");
  const select=who=>evaluate(`(()=>{const s=document.querySelector('.user-select-wrap select');s.value=${JSON.stringify(who)};s.dispatchEvent(new Event('change',{bubbles:true}));})()`);
  async function verify(who){
    await new Promise(r=>setTimeout(r,700));
    const state=await evaluate("({titles:Array.from(document.querySelectorAll('.conversation-open'),b=>b.title).sort(),error:document.querySelector('.error-banner')?.textContent||null,draft:document.querySelector('textarea').value})");
    assert.equal(state.error,null,`${who}: no stale conversation 404`);
    assert.deepEqual(state.titles,expected[who],`${who}: complete, own conversation list`);
    assert.equal(state.draft,'',`${who}: previous user's draft cleared`);
  }
  for(let round=1;round<=3;round++){
    await evaluate(`Array.from(document.querySelectorAll('.conversation-open')).find(b=>b.title===${JSON.stringify(seeds[0].title)}).click()`);
    await new Promise(r=>setTimeout(r,200));
    await evaluate("(()=>{const el=document.querySelector('textarea');Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(el,'Alice private draft');el.dispatchEvent(new Event('input',{bubbles:true}));})()");
    await select('bob'); await verify('bob');
    await select('alice'); await verify('alice');
    console.log(`PASS: Alice -> Bob -> Alice round ${round}`);
  }
  await call('Network.enable');
  await call('Network.emulateNetworkConditions',{offline:false,latency:200,downloadThroughput:-1,uploadThroughput:-1});
  for(const who of ['bob','alice','bob','alice']){await select(who);await new Promise(r=>setTimeout(r,40));}
  await new Promise(r=>setTimeout(r,600));await verify('alice');
  console.log('PASS: fast identity switches with delayed network');
} finally {
  await call('Network.emulateNetworkConditions',{offline:false,latency:0,downloadThroughput:-1,uploadThroughput:-1}).catch(()=>{});
  for(const seed of seeds) await fetch(`${api}/conversations/${seed.id}`,{method:'DELETE',headers:clients[seed.who]});
  close();
}