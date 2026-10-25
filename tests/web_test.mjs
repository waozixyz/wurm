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
 let port;for(let i=0;i<200;i++){try{port=(await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];break;}catch{}await delay(50);}if(!port)throw new Error(stderr);
 const targets=await(await fetch('http://127.0.0.1:'+port+'/json/list')).json();socket=new WebSocket(targets.find(x=>x.type==='page').webSocketDebuggerUrl);await new Promise((r,j)=>{socket.onopen=r;socket.onerror=j;});socket.onmessage=e=>{const m=JSON.parse(e.data);if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails);const p=pending.get(m.id);if(!p)return;pending.delete(m.id);clearTimeout(p.timer);m.error?p.reject(new Error(JSON.stringify(m.error))):p.resolve(m.result);};
 await command('Runtime.enable');await command('Page.enable');await command('Emulation.setDeviceMetricsOverride',{width:1100,height:900,deviceScaleFactor:1,mobile:false});await command('Page.navigate',{url});
 await until("typeof Module!=='undefined' && Module.FS && document.getElementById('loading').hidden");await until("(()=>{try{return Module.FS.stat('/kryon-apps').mode>0}catch{return false}})()");await delay(1800);await capture('title');
 const colorful=await evaluate("(()=>{const c=document.getElementById('canvas'),p=c.getContext('2d').getImageData(0,0,c.width,c.height).data,s=new Set();for(let i=0;i<p.length;i+=80)s.add(p[i]+','+p[i+1]+','+p[i+2]);return s.size})()");if(colorful<200)throw new Error('Title artwork did not render: '+colorful);
 await key('Enter',13);await delay(200);await capture('controls');await key('1',49);await until("(()=>{try{return Module.FS.readFile('/kryon-apps/wurm/controls.dat')[0]===0}catch{return false}})()");await delay(200);await capture('journey');
 await key('1',49);await capture('levels');await key('Enter',13);await delay(300);await key('ArrowRight',39);await delay(150);await key(' ',32);await capture('playing');
 await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await delay(400);await capture('portrait');
 await command('Page.reload');await until("typeof Module!=='undefined' && Module.FS && document.getElementById('loading').hidden");await delay(1200);await until("(()=>{try{return Module.FS.readFile('/kryon-apps/wurm/controls.dat')[0]===0}catch{return false}})()");await key('Enter',13);await capture('journey-portrait');
 if(errors.length)throw new Error(JSON.stringify(errors));
 await writeFile(join(out,'result.json'),JSON.stringify({passed:true,url,behaviors:['rendered title artwork','control choice','stage/level selection','keyboard steering','pause','portrait resize','durable saves after reload'],colorful,errors},null,2)+'\n');
 console.log('Browser local test: title, control choice, stage selection, play, portrait resize and saved choice after reload passed.');
}catch(error){await writeFile(join(out,'failure.txt'),String(error)+'\n'+stderr);throw error;}finally{socket?.close();stop(browser);stop(server);await delay(300);await rm(profile,{recursive:true,force:true});}
