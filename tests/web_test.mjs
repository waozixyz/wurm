// Exercise only a private Chromium/profile and this game's HTTP server.
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,writeFile,mkdir,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {setTimeout as delay} from 'node:timers/promises';
const root=resolve(import.meta.dirname,'..'), out=join(root,'build/web-test');
await mkdir(out,{recursive:true});
const profile=await mkdtemp(join(tmpdir(),'wurm-web-'));
const env={...process.env,YUE_DESKTOP_RECOVERY:'0'};
for(const key of ['DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','DBUS_SESSION_BUS_ADDRESS','SESSION_MANAGER'])delete env[key];
let server,browser,socket,serial=0,stderr='';const pending=new Map(),errors=[];
const command=(method,params={})=>new Promise((resolve,reject)=>{const id=++serial;const timer=setTimeout(()=>{pending.delete(id);reject(new Error(method+' timed out'));},15000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});
const evaluate=async expression=>{const r=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
const until=async(expression,timeout=20000)=>{const start=Date.now();while(Date.now()-start<timeout){if(await evaluate(expression))return;await delay(100);}throw new Error('Timed out: '+expression);};
const key=async(name,code)=>{await command('Input.dispatchKeyEvent',{type:'keyDown',key:name,code:name==='Enter'?'Enter':name===' '?'Space':name,windowsVirtualKeyCode:code,nativeVirtualKeyCode:code});await command('Input.dispatchKeyEvent',{type:'keyUp',key:name,windowsVirtualKeyCode:code,nativeVirtualKeyCode:code});await delay(180);};
const capture=async name=>{const r=await command('Page.captureScreenshot',{format:'png'});await writeFile(join(out,name+'.png'),Buffer.from(r.data,'base64'));};
const stop=p=>{if(p&&p.exitCode===null){try{process.kill(-p.pid,'SIGTERM');}catch{}}};
try{
 let url=process.env.WURM_TEST_URL;
 if(!url){server=spawn('python3',['-u','-m','http.server','0','--bind','127.0.0.1','--directory',join(root,'build/web')],{env,detached:true,stdio:['ignore','pipe','pipe']});let line='';server.stdout.on('data',d=>line+=d);for(let i=0;i<100&&!line.includes('port ');i++)await delay(50);const port=line.match(/port (\d+)/)?.[1];if(!port)throw new Error('HTTP server did not start');url='http://127.0.0.1:'+port+'/';}
 browser=spawn('xvfb-run',['-a',process.env.CHROMIUM||'chromium','--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--no-default-browser-check','--disable-background-networking','--mute-audio','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{env,detached:true,stdio:['ignore','ignore','pipe']});browser.stderr.on('data',d=>stderr=(stderr+d).slice(-4000));
 let port;for(let i=0;i<800;i++){try{port=(await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];break;}catch{}if(browser.exitCode!==null)throw new Error('Private Chromium exited with '+browser.exitCode+': '+stderr);await delay(50);}if(!port)throw new Error('Private Chromium did not publish its debugging port within 40 seconds: '+stderr);
 const targets=await(await fetch('http://127.0.0.1:'+port+'/json/list')).json();socket=new WebSocket(targets.find(x=>x.type==='page').webSocketDebuggerUrl);await new Promise((r,j)=>{socket.onopen=r;socket.onerror=j;});socket.onmessage=e=>{const m=JSON.parse(e.data);if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails);const p=pending.get(m.id);if(!p)return;pending.delete(m.id);clearTimeout(p.timer);m.error?p.reject(new Error(JSON.stringify(m.error))):p.resolve(m.result);};
 await command('Runtime.enable');await command('Page.enable');
 // Observe real HTML audio in this disposable browser without adding app hooks.
 await command('Page.addScriptToEvaluateOnNewDocument',{source:"window.__wurmAudio=[];window.__wurmAudioErrors=[];window.Audio=new Proxy(window.Audio,{construct(target,args){const audio=Reflect.construct(target,args),play=audio.play.bind(audio);audio.play=()=>{const p=play();p.catch(e=>window.__wurmAudioErrors.push({src:audio.src,error:String(e)}));return p};window.__wurmAudio.push(audio);return audio;}});"});
 await command('Emulation.setDeviceMetricsOverride',{width:1100,height:900,deviceScaleFactor:1,mobile:false});await command('Page.navigate',{url});
 const click=async(x,y)=>{await command('Input.dispatchMouseEvent',{type:'mouseMoved',x,y});await delay(80);await command('Input.dispatchMouseEvent',{type:'mousePressed',x,y,button:'left',clickCount:1});await delay(80);await command('Input.dispatchMouseEvent',{type:'mouseReleased',x,y,button:'left',clickCount:1});await delay(180);};
 await until("typeof Module!=='undefined' && Module.FS && document.getElementById('loading').hidden");await until("(()=>{try{return Module.FS.stat('/kryon-apps').mode>0}catch{return false}})()");await delay(1800);await capture('title');
 const colorful=await evaluate("(()=>{const c=document.getElementById('canvas'),p=c.getContext('2d').getImageData(0,0,c.width,c.height).data,s=new Set();for(let i=0;i<p.length;i+=80)s.add(p[i]+','+p[i+1]+','+p[i+2]);return s.size})()");if(colorful<200)throw new Error('Title artwork did not render: '+colorful);
 await click(1018,34);await delay(400);await capture('profile');await click(48,30);await delay(200);
 await click(1066,34);await delay(200);await capture('settings');await key('Escape',27);
 await key('Enter',13);await delay(200);await capture('controls');await key('1',49);await until("(()=>{try{return Module.FS.readFile('/kryon-apps/wurm/controls.dat')[0]===0}catch{return false}})()");await delay(300);await capture('level-1');
 await key('ArrowRight',39);await delay(150);await key(' ',32);await capture('playing');
 // Run a real recording quickly to its end. The next must start before the
 // old one stops, with complementary gains, then finish the fade on its own.
 await until("window.__wurmAudio.length===7 && window.__wurmAudio.slice(4).some(a=>!a.paused && a.currentTime>0 && Number.isFinite(a.duration))");
 await evaluate("(()=>{window.__outgoing=window.__wurmAudio.slice(4).find(a=>!a.paused);window.__outgoing.playbackRate=16;return true})()");
 await until("window.__wurmAudio.slice(4).filter(a=>!a.paused).length===2");
 await evaluate("window.__outgoing.playbackRate=1");await delay(750);
 if(!await evaluate("(()=>{const playing=window.__wurmAudio.slice(4).filter(a=>!a.paused);return playing.length===2 && playing.every(a=>a.volume>0 && a.volume<0.4) && Math.abs(playing.reduce((s,a)=>s+a.volume,0)-0.4)<0.001})()"))throw new Error('Music did not blend the two real recordings');
 await until("window.__outgoing.paused && window.__wurmAudio.slice(4).filter(a=>!a.paused).length===1");
 await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await delay(400);await capture('portrait');
 await command('Page.reload');await until("typeof Module!=='undefined' && Module.FS && document.getElementById('loading').hidden");await delay(1200);await until("(()=>{try{return Module.FS.readFile('/kryon-apps/wurm/controls.dat')[0]===0}catch{return false}})()");await key('Enter',13);await delay(300);await capture('playing-portrait');
 // The real touch path paints Kryon's feedback above the board, then removes
 // it on release. Read the same spot to avoid counting moving game pieces.
 const pixel=async(x,y)=>evaluate(`(()=>{const c=document.getElementById('canvas'),b=c.getBoundingClientRect();return Array.from(c.getContext('2d').getImageData(Math.round((${x}-b.left)*c.width/b.width),Math.round((${y}-b.top)*c.height/b.height),1,1).data).slice(0,3)})()`);
 const beforeTouch=await pixel(219,480);
 await command('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:195,y:480}]});await delay(80);
 await command('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:225,y:480}]});await delay(80);
 const duringTouch=await pixel(219,480);await capture('swipe-feedback');
 if(duringTouch.reduce((a,b)=>a+b,0)<beforeTouch.reduce((a,b)=>a+b,0)+80)throw new Error('Touch feedback did not appear above the board');
 await command('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await delay(100);
 const afterTouch=await pixel(219,480);
 if(duringTouch.reduce((a,b)=>a+b,0)<afterTouch.reduce((a,b)=>a+b,0)+80)throw new Error('Touch feedback stayed after release');
 await capture('swipe-released');
 // Import an old run, persist it through IndexedDB, then use the real title
 // buttons. Only this test's private browser profile contains these records.
 await evaluate("new Promise((resolve,reject)=>{Module.FS.writeFile('/kryon-apps/wurm/run.dat',new Uint8Array([57,6,120,0,0,0]));try{Module.FS.unlink('/kryon-apps/wurm/unlocked.dat')}catch{}Module.FS.syncfs(false,e=>e?reject(e):resolve(true))})");
 await command('Page.reload');await until("typeof Module!=='undefined' && Module.FS && document.getElementById('loading').hidden");await delay(1500);await until("(()=>{try{return Module.FS.readFile('/kryon-apps/wurm/unlocked.dat')[0]===57}catch{return false}})()");await capture('continue-title');
 await click(195,700);await until("JSON.stringify(Array.from(Module.FS.readFile('/kryon-apps/wurm/run.dat')))==='[57,3,0,0,0,0]'");await capture('continued-level-58');
 await key(' ',32);await key('q',81);await click(195,774);await until("JSON.stringify(Array.from(Module.FS.readFile('/kryon-apps/wurm/run.dat')))==='[0,3,0,0,0,0]'");
 if(!await evaluate("Module.FS.readFile('/kryon-apps/wurm/unlocked.dat')[0]===57"))throw new Error('Play erased unlocked progress');
 await delay(500);await command('Page.reload');await until("typeof Module!=='undefined' && Module.FS && document.getElementById('loading').hidden");await delay(1500);await key('c',67);await until("JSON.stringify(Array.from(Module.FS.readFile('/kryon-apps/wurm/run.dat')))==='[57,3,0,0,0,0]'");
 await key(' ',32);await key('q',81);await key('l',76);await capture('level-selector');
 const gridFingerprint=()=>evaluate("(()=>{const c=document.getElementById('canvas'),p=c.getContext('2d').getImageData(0,132,c.width,c.height-132).data;let h=0;for(let i=0;i<p.length;i+=20)h=(Math.imul(h,31)+p[i]+p[i+1]*3+p[i+2]*7)>>>0;return h})()");
 const beforeScroll=await gridFingerprint();
 await command('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:195,y:700}]});
 for(const y of [650,600,550,500,450]){await command('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:195,y}]});await delay(70);}
 await command('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await delay(350);
 if(await gridFingerprint()===beforeScroll)throw new Error('Browser selector did not scroll under touch drag');
 if(!await evaluate("Module.FS.readFile('/kryon-apps/wurm/run.dat')[0]===57"))throw new Error('Dragging the selector started a level');
 await capture('level-selector-scrolled');
 await click(354,96);await click(90,238); // Future Pinewood shows only locks.
 if(!await evaluate("Module.FS.readFile('/kryon-apps/wurm/run.dat')[0]===57"))throw new Error('A locked browser level started');
 await capture('locked-levels');await click(36,96);await click(90,238);
 await until("JSON.stringify(Array.from(Module.FS.readFile('/kryon-apps/wurm/run.dat')))==='[40,3,0,0,0,0]'");
 if(!await evaluate("Module.FS.readFile('/kryon-apps/wurm/unlocked.dat')[0]===57"))throw new Error('Level selection erased progress');
 await key(' ',32);await key('q',81);await key('l',76);await key('Escape',27);await key('c',67);
 await until("Module.FS.readFile('/kryon-apps/wurm/run.dat')[0]===57");
 // Only this disposable browser's records change. Both orientations use the
 // same library placement and retain a visible press highlight.
 await evaluate("new Promise((resolve,reject)=>{Module.FS.writeFile('/kryon-apps/wurm/controls.dat',new Uint8Array([1]));Module.FS.writeFile('/kryon-apps/wurm/unlocked.dat',new Uint8Array([0]));Module.FS.writeFile('/kryon-apps/wurm/run.dat',new Uint8Array([0,3,0,0,0,0]));Module.FS.syncfs(false,e=>e?reject(e):resolve(true))})");
 for(const [width,height] of [[390,844],[844,390]]){
  await command('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:true});
  await command('Page.reload');await until("typeof Module!=='undefined' && Module.FS && document.getElementById('loading').hidden");await delay(1200);await key('Enter',13);
  const playHeight=height-(width<520?104:72),short=Math.min(width,playHeight),margin=Math.max(24,Math.min(32,short*.06)),side=Math.max(168,Math.min(216,short*.44));
  const x=Math.round(margin+side/6),y=Math.round(height-margin-side/2);
  const rest=await pixel(x-10,y+9);
  await command('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});await delay(80);
  const held=await pixel(x-10,y+9);await capture(`pad-${width}x${height}`);
  if(Math.abs(held.reduce((a,b)=>a+b,0)-rest.reduce((a,b)=>a+b,0))<10)throw new Error('Direction pad did not highlight the held arm at '+width+'x'+height);
  await command('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
 }
 if(errors.length)throw new Error(JSON.stringify(errors));
 await writeFile(join(out,'result.json'),JSON.stringify({passed:true,url,behaviors:['shared touch feedback and release','mobile pad placement and held highlight in both orientations','rendered title artwork','control choice','straight into level 1','keyboard steering','pause','portrait resize','durable saves after reload','old run migration','Continue highest level with fresh stats','Play from start preserves unlocks','Continue after browser reload','landscape level selector','touch scrolling without starting a level','locked levels show only locks','unlocked level selection starts fresh','selector keyboard back'],colorful,errors},null,2)+'\n');
 console.log('Browser local test: touch feedback and release, mobile pad placement and highlight, controls, play, portrait, durable progress and unlocked-level selection passed.');
}catch(error){
 try{await writeFile(join(out,'audio-failure.json'),JSON.stringify(await evaluate("({audio:(window.__wurmAudio||[]).map(a=>({src:a.src,paused:a.paused,time:a.currentTime,duration:a.duration,volume:a.volume,ready:a.readyState,error:a.error?.code})),errors:window.__wurmAudioErrors})"),null,2));await capture('failure');}catch{}
 await writeFile(join(out,'failure.txt'),String(error)+'\n'+stderr);throw error;
}finally{socket?.close();stop(browser);stop(server);await delay(300);await rm(profile,{recursive:true,force:true});}
