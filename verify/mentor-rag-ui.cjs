// Render the checked-out React Documents component in Chromium using the measured
// benign API states. Quarantine is a UI fixture only and never executes a payload.
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createRequire } = require('node:module');
const root = path.resolve(__dirname, '..');
const dependencies = createRequire(path.join(root, 'frontend/package.json'));
const { chromium } = dependencies('playwright');
const { build } = dependencies('esbuild');
const evidence = path.join(root, 'docs/release/week8/verify-evidence');
const measured = JSON.parse(fs.readFileSync(path.join(evidence, 'rag-results.json'), 'utf8'));

async function run() {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'mentor-docs-render-'));
  const src = path.join(folder,'source');
  let browser;
  try {
    execFileSync('git',['clone','-q','--shared','--no-checkout',root,src]);
    execFileSync('git',['checkout','-q','--detach',measured.commit],{cwd:src});
    if (execFileSync('git',['status','--porcelain'],{cwd:src}).length) throw Error('Expected clean checkout');
    const entry = `import React from 'react'; import {createRoot} from 'react-dom/client';
        import {Documents} from './src/components/explore/Documents';
        import {acceptSession,currentSession} from './src/sessionStore';
        const expires=Math.floor(Date.now()/1000)+600;
        acceptSession({user:{id:'alice',name:'Demo'},access_token:'ui-only',refresh_token:'ui-only',session_id:'ui-only',expires_in:600,idle_expires_at:expires,absolute_expires_at:expires});
        createRoot(document.getElementById('root')).render(<Documents user={currentSession().user} ask={()=>{}}/>);`;
    const bundled = await build({stdin:{contents:entry,resolveDir:path.join(src,'frontend'),loader:'tsx'},
      bundle:true,write:false,jsx:'automatic',loader:{'.css':'empty'},nodePaths:[path.join(root,'frontend/node_modules')],define:{'process.env.NODE_ENV':'"production"'}});
    const rows = Object.entries(measured.api).filter(([,entry])=>entry?.state==='rejected').map(([name,entry],index)=>({
      id:'synthetic-'+index,filename_display:name,status:entry.state,status_reason:entry.reason,size_bytes:100
    }));
    rows.push({id:'ui-state',filename_display:'quarantine-state.txt',status:'quarantined',status_reason:'SOURCE_INJECTION',size_bytes:100});
    const expected={
      'image.png':'Choose a text-based PDF, TXT or Markdown file.',
      'pages.pdf':'Choose a PDF with up to 50 pages.',
      'empty.txt':'No readable text was found. Scanned documents are not supported.',
      'large.txt':'Choose a file up to 5 MB.',
      'quarantine-state.txt':'This document contains instructions aimed at the assistant.'
    };
    const chrome=process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
    browser=await chromium.launch({headless:true,executablePath:chrome});
    const page=await browser.newPage();
    await page.route('http://127.0.0.1:18215/**',route=>{
      const url=new URL(route.request().url());
      if(url.pathname==='/app.js') return route.fulfill({contentType:'application/javascript',body:bundled.outputFiles[0].text});
      if(url.pathname==='/api/documents') return route.fulfill({contentType:'application/json',body:JSON.stringify({items:rows})});
      return route.fulfill({contentType:'text/html',body:'<div id="root"></div><script src="/app.js"></script>'});
    });
    await page.goto('http://127.0.0.1:18215/');
    const results={};
    for(const [name,text] of Object.entries(expected)){
      if(name==='large.txt' && measured.api[name]?.http===422){
        await page.getByLabel('Choose a document').setInputFiles({
          name, mimeType:'text/plain', buffer:Buffer.alloc(5*1024*1024+1,65)
        });
        await page.getByRole('button',{name:'Upload document',exact:true}).click();
        const alert=page.getByRole('alert').filter({hasText:text});
        await alert.waitFor();
        results[name]={label:'Upload validation',reason:text,visible:await alert.isVisible(),
                       no_document_row:await page.getByRole('article').filter({hasText:name}).count()===0};
        continue;
      }
      const article=page.getByRole('article').filter({hasText:name});
      await article.getByText(text,{exact:true}).waitFor({timeout:15000});
      const label = name==='quarantine-state.txt' ? 'Unavailable for chat' : 'Not supported';
      results[name]={label,reason:text,visible:await article.getByText(label,{exact:true}).isVisible()};
    }
    const output={commit:measured.commit,source:'Chromium mounted Documents component; GET list replay of observed invalid-upload states. Quarantine is a synthetic UI-only state.',results};
    fs.writeFileSync(path.join(evidence,'rag-ui.json'),JSON.stringify(output,null,2));
    if(!Object.values(results).every(row=>row.visible && row.no_document_row!==false)) throw Error('Unexpected document state');
    console.log('Document state labels and reasons verified in Chromium:',Object.keys(results).length);
  } finally {
    if (browser) await browser.close();
    const prefix=path.join(path.resolve(os.tmpdir()),'mentor-docs-render-');
    if(path.resolve(folder).startsWith(prefix)) fs.rmSync(folder,{recursive:true,force:true,maxRetries:3});
  }
}
run().catch(error=>{ console.error(error.message);process.exitCode=1; });
