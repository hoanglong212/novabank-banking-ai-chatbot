import { writeFile } from 'node:fs/promises';
const targets = await fetch('http://127.0.0.1:9224/json/list').then(r=>r.json());
const target = targets.find(t=>t.type==='page');
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{ ws.onopen=resolve; ws.onerror=reject; });
let id=0; const pending=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data); if(pending.has(m.id)){ const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result); }};
export function call(method,params={}){return new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method,params}));});}
export async function evaluate(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
export async function until(expression){for(let i=0;i<60;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,150));}throw Error('Timed out: '+expression);}
export async function capture(file){const r=await call('Page.captureScreenshot',{format:'png'});await writeFile(file,Buffer.from(r.data,'base64'));}
export function close(){ws.close();}