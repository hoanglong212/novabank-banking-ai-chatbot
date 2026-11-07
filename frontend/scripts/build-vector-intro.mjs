import { svgContours } from './source-paths.mjs';
const sourceData = JSON.parse(readFileSync(new URL('./nova-intro-source-paths.json', import.meta.url), 'utf8'));
const traced = sourceData.shapes;
// Source-derived paths from v11, with reconstructed motion. MP4 has no original vector layers.
// Run export-intro-type.ps1 only when changing the outlined system typography.
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
const outlines = JSON.parse(readFileSync(new URL('./nova-intro-outlines.json', import.meta.url), 'utf8'));
const output = new URL('../public/animations/nova-intro-vector/', import.meta.url);
const C = { purple: '#5c28db', dark: '#1d242d', paper: '#f8f6fd', line: '#bba2ef' };
const color = value => {
  const hex = value.length === 4 ? '#' + [...value.slice(1)].map(c => c+c).join('') : value;
  return [1,3,5].map(i => parseInt(hex.slice(i,i+2),16)/255).concat(1);
};
const fixed = k => ({ a:0, k });
const frames = (values, linear = false) => ({ a:1, k:values.map(([t,s],index) => ({
  t, s: Array.isArray(s) ? s : [s], ...(index < values.length-1 ? { i:{x:linear?1:.8,y:1}, o:{x:linear?0:.2,y:0} } : {}),
})) });
const fill = (hex, opacity=100) => ({ty:'fl', c:fixed(color(hex)), o:fixed(opacity), r:1});
const stroke = (hex, width=1, opacity=100, dashed=false) => ({ty:'st',c:fixed(color(hex)),o:fixed(opacity),w:fixed(width),lc:2,lj:2,...(dashed?{d:[{n:'d',v:fixed(2)},{n:'g',v:fixed(8)},{n:'o',v:fixed(0)}]}:{})});
const transform = (p=[0,0], r=0, s=[100,100]) => ({ty:'tr',p:fixed(p),a:fixed([0,0]),s:fixed(s),r:fixed(r),o:fixed(100),sk:fixed(0),sa:fixed(0)});
const group = (items,p=[0,0],r=0,s=[100,100]) => ({ty:'gr',it:[...items,transform(p,r,s)]});
const rect = (w,h,r=0,p=[0,0]) => ({ty:'rc',d:1,s:fixed([w,h]),p:fixed(p),r:fixed(r)});
const ellipse = (w,h,p=[0,0]) => ({ty:'el',d:1,s:fixed([w,h]),p:fixed(p)});
const path = (v,closed=false) => ({ty:'sh',ks:fixed({v,i:v.map(()=>[0,0]),o:v.map(()=>[0,0]),c:closed})});
function glyph(name, hex) {
  const source=outlines[name], contours=[];
  let contour;
  for(let j=0;j<source.points.length;j++) {
    const [x,y,type]=source.points[j];
    if((type&7)===0) { contour={v:[[x,y]],i:[[0,0]],o:[[0,0]],c:false};contours.push(contour); }
    else if((type&7)===1) { contour.v.push([x,y]);contour.i.push([0,0]);contour.o.push([0,0]); }
    else if((type&7)===3) {
      const control2=source.points[++j],end=source.points[++j];
      const last=contour.v.at(-1);
      contour.o[contour.o.length-1]=[x-last[0],y-last[1]];
      contour.v.push(end.slice(0,2));contour.i.push([control2[0]-end[0],control2[1]-end[1]]);contour.o.push([0,0]);
      if(end[2]&128) contour.c=true;
    }
    if(type&128) contour.c=true;
  }
  return group([...contours.map(c=>({ty:'sh',ks:fixed(c)})),fill(hex)],[-source.width/2,-source.height/2]);
}
const layers=[];
function layer(name,shapes,p=[0,0],options={}) {
  const item={ddd:0,ind:layers.length+1,ty:4,nm:name,sr:1,ks:{
    o:fixed(100),r:fixed(0),p:fixed([...p,0]),a:fixed([0,0,0]),s:fixed([100,100,100]),...options.ks,
  },ao:0,shapes,ip:options.ip??0,op:options.op??135,st:0,bm:0};
  layers.push(item);return item;
}
const appear = (start=20,end=30) => frames([[0,0],[start,0],[end,100],[120,100],[126,0]]);
function source(name, override) {
  if(name==='core') return [group([...svgContours(traced.core.paths[1].d,traced.core.origin).map(c=>({ty:'sh',ks:fixed(c)})),fill('#fdfbfd')]),group([rect(100,100,30),fill('#5a2ad7')])];
  if(name==='qr') return sourceData.qrGrid.matrix.flatMap((row,y)=>row.flatMap((on,x)=>on?[group([rect(3,3,0,[(x-2)*4,(y-2)*4]),fill(override||'#fff')])]:[]));
  const item=traced[name];
  return item.paths.map(row=>group([...svgContours(row.d,item.origin).map(c=>({ty:'sh',ks:fixed(c)})),fill(override||row.fill)])).reverse();
}
function glow(w,h,hex,opacity=30) {
  const rgb=color(hex).slice(0,3);
  return group([ellipse(w,w),{ty:'gf',o:fixed(opacity),r:1,t:2,s:fixed([0,0]),e:fixed([w/2,0]),h:fixed(0),a:fixed(0),g:{p:2,k:fixed([0,...rgb,1,...rgb,0,1,.35,.5,1,0])}}],[0,0],0,[100,h/w*100]);
}
function tick() {return group([group([path([[-3,0],[-.6,2.4],[4,-2.6]]),stroke('#25313b',1.6)]),group([ellipse(15,15),fill('#fff')])],[16,-17]);}
// Positions measured from reference frames 30,45,60,75,90,105,120.
const specs=[
 {name:'qr',size:40,r:12,idle:'#ddd4fb',active:'#6128db',ink:'#493c94',at:39,points:[[735,212],[773,220],[803,229],[819,244],[820,264],[804,285],[716,330]]},
 {name:'question',size:46,r:14,idle:'#d5e8ff',active:'#3685ef',ink:'#2f5483',at:56,points:[[835,264],[799,290],[767,313],[722,333],[671,350],[617,363],[522,361]]},
 {name:'search',size:49,r:15,idle:'#d6ecda',active:'#16a34a',ink:'#105d5d',at:73,points:[[662,359],[605,365],[554,369],[511,368],[479,359],[461,345],[490,298]]},
 {name:'payment',size:40,r:12,idle:'#fcd7e1',active:'#dd4798',ink:'#643c7f',at:91,points:[[470,358],[460,341],[460,321],[478,299],[510,276],[554,255],[666,228]]},
 {name:'bill',size:34,r:11,idle:'#f4dcda',active:'#f58718',ink:'#926b8e',at:108,points:[[532,275],[562,251],[614,233],[668,223],[720,217],[765,218],[805,248]]},
];
// Opening dots, followed by the tilted N, are separate phases in the video.
for(const [i,t] of [0,2,4].entries()) layer(`Opening dot ${i+1}`,[group([ellipse(5,5),fill(i===1?C.purple:C.dark)])],[620+i*20,294+i*4-4],{op:13,ks:{o:frames([[0,0],[t+3,100],[10,100],[13,0]])}});
for(const spec of specs) {
  const {name,size,r,idle,active,ink,at,points}=spec;
  const p=frames([[20,[640,294,0]],[25,[(points[0][0]+640)/2,(points[0][1]+294)/2,0]],...points.map((p,i)=>[30+i*15,[...p,0]]),[126,[640,294,0]]]);
  const ks={p,o:appear(20,29),s:frames([[20,[0,0,100]],[29,[100,100,100]],[120,[100,100,100]],[126,[0,0,100]]])};
  const idleSymbol=source(name,ink);
  const activeSymbol=source(name,'#fff');
  layer(`${name} completed badge`,[tick()],[0,0],{ip:at,op:127,ks});
  layer(`${name} completed artwork`,[...activeSymbol,group([rect(size,size,r),fill(active)])],[0,0],{ip:at,op:127,ks});
  layer(`${name} original artwork`,[...idleSymbol,group([rect(size,size,r),fill(idle),stroke(ink,.7,40)])],[0,0],{ip:20,op:at,ks});
  layer(`${name} completion pulse`,[group([rect(size+18,size+18,r+7),stroke(active,1.2,65),fill(active,9)])],[0,0],{ip:at-3,op:at+10,ks:{...ks,o:frames([[at-3,0],[at,100],[at+10,0]])}});
  layer(`${name} soft shadow`,[glow(size*2,size*1.6,active,35)],[0,0],{ks});
}
const coreKs={s:frames([[0,[0,0,100]],[11,[0,0,100]],[15,[76,76,100]],[22,[98,98,100]],[30,[90,90,100]],[38,[100,100,100]],[60,[98,98,100]],[75,[100,100,100]],[90,[100,100,100]],[105,[94,94,100]],[120,[100,100,100]],[130,[142,142,100]],[135,[130,130,100]]]),r:frames([[11,-28],[20,-12],[27,0],[135,0]]),o:frames([[0,0],[11,0],[14,100],[135,100]])};
const coreShapes=source('core');
layer('Source N outline',[coreShapes[0]],[640,294],{ks:{...coreKs,o:frames([[0,0],[11,0],[14,100],[125,100],[130,35],[135,75]])}});
layer('Core rounded tile',[coreShapes[1]],[640,294],{ks:coreKs});
layer('Core violet glow',[glow(230,230,C.purple,40)],[640,310],{ks:{o:frames([[0,0],[15,30],[30,85],[120,85],[130,100]])}});
for(const [start,w,end] of [[11,640,36],[15,500,39],[125,490,135]]) layer(`Expanding ring ${start}`,[group([ellipse(w,w),stroke(C.purple,start===125?2.5:1.4,start===125?80:45)])],[640,294],{ip:start,op:end,ks:{s:frames([[start,[0,0,100]],[end,[100,100,100]]]),o:frames([[start,65],[end-6,40],[end,0]])}});
// Source has two oblique orbits, not a permanent circular third orbit.
const orbitKs={o:appear(20,29),s:frames([[20,[0,0,100]],[30,[100,100,100]],[119,[100,100,100]],[126,[0,0,100]]])};
const gradientStroke={ty:'gs',o:fixed(100),w:fixed(1.8),lc:2,lj:2,t:1,s:fixed([-190,0]),e:fixed([190,0]),g:{p:3,k:fixed([0,.35,.13,.85,.5,.22,.42,.98,1,.86,.12,.51])}};
layer('Main blue violet pink orbit',[group([ellipse(380,120),gradientStroke],[0,0],-16)],[640,294],{ks:orbitKs});
layer('Dotted tilted orbit',[group([ellipse(510,120),{...stroke('#8655d8',.8,80,true),d:[{n:'d',v:fixed(1.5)},{n:'g',v:fixed(7)}]}],[0,0],20)],[640,294],{ks:orbitKs});
for(let n=0;n<20;n++) {
  const positions=[];
  for(let f=24;f<=120;f+=3){const a=n*Math.PI*2/20+(f-45)*.012,rot=20*Math.PI/180,x=255*Math.cos(a),y=60*Math.sin(a);positions.push([f,[640+x*Math.cos(rot)-y*Math.sin(rot),294+x*Math.sin(rot)+y*Math.cos(rot),0]]);}
  positions.push([126,[640,294,0]]);
  layer(`Colored orbit particle ${n}`,[group([ellipse(n%3===0?6:4,n%3===0?6:4),fill(['#9260e5','#e879ae','#f8b84e','#73bdf3','#75c98b'][n%5])])],[0,0],{ks:{...orbitKs,p:frames(positions,true)}});
}
// Bright short arcs travel along the main orbit.
for(let n=0;n<3;n++)layer(`Traveling highlight ${n}`,[group([ellipse(380,120),stroke('#fff',1.6,95),{ty:'tm',s:frames([[25,n*33],[120,n*33+90]],true),e:frames([[25,n*33+4],[120,n*33+94]],true),o:fixed(0),m:1}],[0,0],-16)],[640,294],{ks:orbitKs});
layer('Source NovaBank wordmark',source('wordmark'),[640,494],{ks:{o:frames([[26,0],[34,100],[126,100],[131,0]]),p:frames([[26,[640,535,0]],[35,[640,494,0]],[135,[640,494,0]]])}});
const progressKeys=[[26,0],[30,5],[45,24],[60,42],[75,60],[90,80],[105,93],[112,100]];
function progress(f){for(let i=1;i<progressKeys.length;i++){const [a,x]=progressKeys[i-1],[b,y]=progressKeys[i];if(f<=b)return Math.round(x+(y-x)*(f-a)/(b-a));}return 100;}
const markerKeys=progressKeys.map(([f,p])=>[f,[455+370*p/100,579,0]]).concat([[116,[825,579,0]],[120,[640,579,0]],[126,[640,494,0]]]);
for(let f=26;f<127;f++) {
  const percent=progress(f),x=f<=116?455+370*percent/100:f<=120?825-(f-116)*185/4:640,y=f<=120?554:554-(f-120)*85/6;
  layer(`Source progress ${percent}% at ${f}`,[glyph(`p${percent}`,C.dark),group([rect(34,21,8),fill('#fff')])],[x,y],{ip:f,op:f+1,ks:{o:frames([[26,0],[33,100],[123,100],[127,0]])}});
}
for(const [start,end,status] of [[26,39,'securing'],[39,55,'loading'],[55,71,'syncing'],[71,87,'indexing'],[87,101,'balances'],[101,115,'reminders'],[115,130,'ready']])layer(`Source status ${status}`,[group([glyph(status,'#666172')],[0,0],0,[120,100])],[640,604],{ip:start,op:end,ks:{o:frames([[start,0],[start+2,100],[end-1,100],[end,0]])}});
layer('Progress white marker',[group([ellipse(15,15),fill('#fff'),stroke(C.purple,2.6)])],[0,0],{ip:26,op:127,ks:{p:frames(markerKeys,true),o:frames([[26,0],[33,100],[123,100],[127,0]])}});
layer('Progress moving aura',[glow(85,28,C.purple,65)],[0,0],{ip:26,op:127,ks:{p:frames(markerKeys,true),o:appear(26,33)}});
for(const [n,x] of [528,603,677,752,800].entries()) {
 const t=Array.from({length:87},(_,i)=>i+26).find(f=>455+progress(f)*3.7>=x)??112;
 layer(`Progress checkpoint ${n}`,[group([ellipse(5,5),fill(C.dark)])],[x,579],{ip:t,op:125});
 layer(`Progress idle checkpoint ${n}`,[group([ellipse(4,4),fill('#fff'),stroke('#c7bddc',.7)])],[x,579],{ip:26,op:t});
}
layer('Progress fill',[group([rect(370,2.5,1,[185,0]),fill(C.purple)])],[455,579],{ip:26,op:127,ks:{s:frames(progressKeys.map(([f,p])=>[f,[p,100,100]]).concat([[116,[100,100,100]],[126,[0,100,100]]]),true),p:frames([[26,[455,579,0]],[116,[455,579,0]],[126,[640,579,0]]]),o:appear(26,33)}});
layer('Progress track',[group([rect(370,3,1.5),fill('#ddd6e9')])],[640,579],{ip:26,op:127,ks:{o:appear(26,33),s:frames([[26,[100,100,100]],[116,[100,100,100]],[126,[0,100,100]]])}});
layer('Atmosphere',[glow(1100,1000,'#9773de',36)],[640,330]);
for(let i=0;i<50;i++)layer(`Quiet grain ${i}`,[group([ellipse(1.2,1.2),fill('#a897bd',22)])],[18+(i*157)%1250,4+(i*97)%710]);
layer('Paper',[group([rect(1280,720),fill('#f8f7fc')])],[640,360]);
// Highlights sit over the colored orbital stroke.
const highlights=layers.filter(l=>l.nm.startsWith('Traveling highlight'));
for(const l of highlights)layers.splice(layers.indexOf(l),1);
layers.splice(layers.findIndex(l=>l.nm==='Main blue violet pink orbit'),0,...highlights);
const animation={v:'5.13.0',fr:30,ip:0,op:135,w:1280,h:720,nm:'Nova v11 source-traced vectors and reconstructed motion',ddd:0,assets:[],layers,markers:[{tm:26,cm:'loading',dr:0}]};
mkdirSync(output,{recursive:true});
const json=JSON.stringify(animation);writeFileSync(new URL('animation.json',output),json);
console.log(`${layers.length} vector layers; no image assets; ${(Buffer.byteLength(json)/1024).toFixed(1)} KiB; 4.5 seconds`);
