// Run with CHROME_BIN=/path/to/chromium and a local preview server.
// Uses Node's standard library; no browser automation package is required.
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const baseUrl = (process.env.PORTFOLIO_BASE_URL || 'http://127.0.0.1:8765/').replace(/\/?$/, '/');
const reviewDir = process.env.PORTFOLIO_REVIEW_DIR || path.join(os.tmpdir(), 'portfolio-interaction-review');
fs.mkdirSync(reviewDir, {recursive: true});
const resultFile = path.join(reviewDir, 'results.json');
fs.writeFileSync(resultFile, JSON.stringify({status: 'running'}));
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'portfolio-chrome-'));
const chrome = spawn(process.env.CHROME_BIN || 'chromium', [
  '--headless', '--no-sandbox', '--disable-dev-shm-usage',
  '--disable-background-networking', '--no-first-run', '--remote-debugging-pipe',
  '--user-data-dir=' + profile
], {stdio: ['ignore', 'ignore', 'pipe', 'pipe', 'pipe']});
let buffer = '', sequence = 0;
const pending = new Map(), errors = [], loaded = new Set();
function rejectPending(error) {
  for (const request of pending.values()) request.reject(error);
  pending.clear();
}
chrome.on('error', error => rejectPending(new Error('Cannot launch Chromium. Set CHROME_BIN. ' + error.message)));
chrome.stdio[3].on('error', rejectPending);
chrome.stderr.on('data', data => fs.appendFileSync(path.join(reviewDir, 'chrome.log'), data));
chrome.once('close', () => {
  rejectPending(new Error('Chromium closed before the command completed'));
  fs.rmSync(profile, {recursive: true, force: true, maxRetries: 3, retryDelay: 100});
});
chrome.stdio[4].on('data', data => {
  buffer += data;
  let boundary;
  while ((boundary = buffer.indexOf('\0')) >= 0) {
    const message = JSON.parse(buffer.slice(0, boundary));
    buffer = buffer.slice(boundary + 1);
    if (message.id) {
      const request = pending.get(message.id);
      if (request) {
        pending.delete(message.id);
        message.error ? request.reject(message.error) : request.resolve(message.result);
      }
    } else if (message.method === 'Page.lifecycleEvent' && message.params.name === 'load') {
      loaded.add(message.params.loaderId);
    } else if (message.method === 'Runtime.exceptionThrown' ||
               (message.method === 'Log.entryAdded' && message.params.entry.level === 'error')) {
      errors.push(message);
    }
  }
});
function send(method, params = {}, sessionId) {
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error('Timeout: ' + method));
    }, 15000);
    pending.set(id, {
      resolve: result => { clearTimeout(timer); resolve(result); },
      reject: error => { clearTimeout(timer); reject(error); }
    });
    chrome.stdio[3].write(JSON.stringify({id, method, params, ...(sessionId ? {sessionId} : {})}) + '\0');
  });
}
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function main() {
  const version = await send('Browser.getVersion');
  const {targetId} = await send('Target.createTarget', {url: 'about:blank'});
  const {sessionId} = await send('Target.attachToTarget', {targetId, flatten: true});
  const cmd = (method, params) => send(method, params, sessionId);
  const evaluate = async expression => {
    const response = await cmd('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true});
    if (response.exceptionDetails) throw new Error(JSON.stringify(response.exceptionDetails));
    return response.result.value;
  };
  await cmd('Page.enable');
  await cmd('Page.setLifecycleEventsEnabled', {enabled: true});
  await cmd('Runtime.enable');
  await cmd('Log.enable');
  const viewport = width => cmd('Emulation.setDeviceMetricsOverride', {
    width, height: 1000, deviceScaleFactor: 1, mobile: false
  });
  const go = async route => {
    const url = new URL(route, baseUrl).href;
    const navigation = await cmd('Page.navigate', {url});
    if (navigation.errorText) throw new Error('Cannot open ' + url + ': ' + navigation.errorText + '. Start the preview server first.');
    let ready = false;
    for (let attempt = 0; attempt < 80; attempt++) {
      await sleep(100);
      if (loaded.has(navigation.loaderId) && await evaluate("document.readyState === 'complete' && location.href === " + JSON.stringify(url))) {
        ready = true;
        break;
      }
    }
    if (!ready) throw new Error('Navigation did not complete: ' + url);
    await evaluate('document.fonts.ready.then(() => true)');
    await sleep(80);
  };
  const click = async selector => {
    const point = await evaluate(`(async () => {
      const element = document.querySelector(${JSON.stringify(selector)});
      if (!element) throw new Error('Missing ' + ${JSON.stringify(selector)});
      element.scrollIntoView({block: 'center', behavior: 'instant'});
      await new Promise(requestAnimationFrame);
      await new Promise(requestAnimationFrame);
      const bounds = element.getBoundingClientRect();
      return {x: bounds.x + bounds.width / 2, y: bounds.y + bounds.height / 2};
    })()`);
    await cmd('Input.dispatchMouseEvent', {type: 'mousePressed', button: 'left', clickCount: 1, ...point});
    await cmd('Input.dispatchMouseEvent', {type: 'mouseReleased', button: 'left', clickCount: 1, ...point});
    await sleep(80);
  };
  const key = async (key, code = key) => {
    const windowsVirtualKeyCode = {Escape: 27, Enter: 13, ' ': 32, ArrowRight: 39, ArrowLeft: 37, ArrowDown: 40, ArrowUp: 38, Home: 36, End: 35}[key];
    await cmd('Input.dispatchKeyEvent', {type: 'keyDown', key, code, windowsVirtualKeyCode, ...(key === 'Enter' ? {text: '\r', unmodifiedText: '\r'} : {})});
    await cmd('Input.dispatchKeyEvent', {type: 'keyUp', key, code, windowsVirtualKeyCode});
    await sleep(100);
  };
  const shot = async name => {
    await evaluate("window.scrollTo({top: 0, behavior: 'instant'})");
    await sleep(100);
    const {data} = await cmd('Page.captureScreenshot', {format: 'png'});
    fs.writeFileSync(path.join(reviewDir, name + '.png'), Buffer.from(data, 'base64'));
  };
 const results=[];const assert=(name,value)=>{results.push({name,pass:!!value});if(!value)console.log('FAIL',name);};
 const routes=['','work/','about/','library/','work/eeg-platform/','work/medipredict/','work/eeg-benchmark/','work/local-retrieval/','work/tempo/','work/nand2tetris/'];
 for(const width of [1440,768,390,320]){await viewport(width);for(const path of routes){await go(path);const a=await evaluate(`({width:innerWidth,scroll:document.documentElement.scrollWidth,badImages:[...document.images].filter(i=>i.loading!=='lazy'&&(!i.complete||!i.naturalWidth)).length,h1:document.querySelectorAll('h1').length,enhanced:[...document.querySelectorAll('[data-enhance]')].every(e=>!e.hidden)})`);assert(`${width} ${path||'home'} layout/assets`,a.scroll<=a.width&&a.badImages===0&&a.h1===1);if(a.scroll>a.width)console.log('OVERFLOW',width,path,await evaluate("[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).slice(0,10).map(e=>({tag:e.tagName,cls:e.className,right:e.getBoundingClientRect().right}))"));if((width===1440&&['','work/','work/eeg-platform/','library/'].includes(path))||(width===390&&['','about/','work/medipredict/','library/'].includes(path)))await shot((path||'home').replaceAll('/','-')+width);}}
 await viewport(1440);await go('work/');
 for(const [filter,n] of [['Backend & data',2],['ML & retrieval',3],['Developer tools',3],['Systems',1],['all',9]]){await click('[data-filter="'+filter+'"]');assert('filter '+filter,await evaluate(`document.querySelectorAll('.work-entry:not([hidden])').length===${n} && document.querySelector('[data-filter-count]').textContent.startsWith('${n} ')`));}
 await go('');await click('#theme-toggle');await go('about/');assert('theme persists',await evaluate("document.documentElement.dataset.theme==='dark'&&document.querySelector('#theme-toggle').getAttribute('aria-pressed')==='true'"));await shot('about-dark');await click('#theme-toggle');
 await go('');await evaluate("document.querySelector('.portrait').focus()");await key('Enter');assert('portrait keyboard reveal',await evaluate("document.querySelector('.portrait').getAttribute('aria-pressed')==='true'"));await key(' ','Space');assert('portrait keyboard restore',await evaluate("document.querySelector('.portrait').getAttribute('aria-pressed')==='false'"));await sleep(250);assert('keyboard portrait reset changes the visible image',await evaluate("getComputedStyle(document.querySelector('.portrait__colour')).opacity==='0'"));
 await click('.latest-writing summary');assert('latest dispatch expands',await evaluate("document.querySelector('.latest-writing').open&&document.querySelectorAll('.latest-writing article').length>0"));
 await go('work/eeg-platform/');await evaluate("document.querySelector('#window-start').focus()");await key('ArrowRight');assert('window keyboard updates',await evaluate("document.querySelector('#window-value').value==='9–25 s'&&document.querySelector('[data-window-region]').getAttribute('x')==='90'"));await click('[data-demo="window"] [data-reset]');assert('window reset',await evaluate("document.querySelector('#window-value').value==='8–24 s'"));
 await click('[data-expand-figure]');assert('figure modal and unique ids',await evaluate("document.querySelector('dialog').open&&new Set([...document.querySelectorAll('[id]')].map(e=>e.id)).size===document.querySelectorAll('[id]').length"));const padding=await evaluate("(()=>{const r=document.querySelector('.figure-dialog').getBoundingClientRect();return{x:r.left+5,y:r.top+5};})()");await cmd('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...padding});await cmd('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...padding});assert('clicking dialog padding keeps it open',await evaluate("document.querySelector('.figure-dialog').open"));
 const backdrop=await evaluate("(()=>{const r=document.querySelector('.figure-dialog').getBoundingClientRect();return{x:r.left-8,y:r.top+20};})()");await cmd('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...backdrop});await cmd('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...backdrop});await sleep(80);assert('clicking backdrop closes the dialog',await evaluate("!document.querySelector('.figure-dialog').open&&document.activeElement.matches('[data-expand-figure]')"));await click('[data-expand-figure]');
 await key('Escape');assert('figure Escape and focus restore',await evaluate("!document.querySelector('dialog').open&&document.activeElement.matches('[data-expand-figure]')"));
 await click('.case-contents a[href="#measurements"]');await sleep(600);assert('anchor clears sticky navigation',await evaluate("document.querySelector('#measurements').getBoundingClientRect().top>=document.querySelector('.site-nav').getBoundingClientRect().bottom"));
 await go('work/medipredict/');await click('input[value="leaked"]');assert('leakage comparison',await evaluate("document.querySelector('[data-ablation-score]').value==='0.925'&&document.querySelector('[data-ablation-bar]').getAttribute('width')==='555'"));await click('input[value="honest"]');assert('quote-time comparison',await evaluate("document.querySelector('[data-ablation-score]').value==='~0.15'"));
 await viewport(390);await go('work/eeg-platform/');await click('[data-expand-figure]');assert('mobile figure modal',await evaluate("document.querySelector('dialog').open&&document.querySelector('dialog').getBoundingClientRect().right<=innerWidth"));await click('[data-close-figure]');assert('mobile close',await evaluate("!document.querySelector('dialog').open"));
 await cmd('Emulation.setScriptExecutionDisabled',{value:true});await go('work/');assert('no JS work complete',await evaluate("document.querySelectorAll('.work-entry').length===9&&document.querySelector('.work-filters').hidden"));await go('work/local-retrieval/');assert('no JS case readable',await evaluate("document.querySelector('#measurements').textContent.length>100&&document.querySelector('.fusion-results li:first-child output').value==='0.032522'&&[...document.querySelectorAll('[data-enhance]')].every(e=>e.hidden)"));await cmd('Emulation.setScriptExecutionDisabled',{value:false});
 await cmd('Emulation.setTouchEmulationEnabled',{enabled:true});await go('');
 const touch=async selector=>{const p=await evaluate(`(async()=>{const e=document.querySelector(${JSON.stringify(selector)});e.scrollIntoView({block:'center',behavior:'instant'});await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()`);await cmd('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[p]});await cmd('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await sleep(150);};
 await touch('.portrait');assert('touch portrait reveal',await evaluate("document.querySelector('.portrait').getAttribute('aria-pressed')==='true'"));await touch('.portrait');assert('touch portrait restore',await evaluate("document.querySelector('.portrait').getAttribute('aria-pressed')==='false'"));await sleep(250);assert('touch portrait reset clears sticky hover',await evaluate("getComputedStyle(document.querySelector('.portrait__colour')).opacity==='0'"));
 const detailShot=async(name,selector)=>{await evaluate(`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({block:'start',behavior:'instant'})`);await sleep(200);const {data}=await cmd('Page.captureScreenshot',{format:'png'});fs.writeFileSync(reviewDir+'/' +name+'.png',Buffer.from(data,'base64'));};
 await detailShot('home-selected-mobile','.front-work');await go('work/medipredict/');await detailShot('leakage-mobile','#explore');await go('about/');await detailShot('about-personal-mobile','#outside');
 await viewport(1440);await go('work/eeg-platform/');await detailShot('window-desktop','#explore');
 for(const path of ['work/eeg-platform/','work/medipredict/','work/eeg-benchmark/','work/local-retrieval/']){await go(path);await click('[data-expand-figure]');assert(path+' figure expanded',await evaluate("document.querySelector('dialog').open&&!!document.querySelector('[data-figure-content] svg')"));const {data}=await cmd('Page.captureScreenshot',{format:'png'});fs.writeFileSync(reviewDir+'/figure-expanded.png',Buffer.from(data,'base64'));await key('Escape');}
 // Exercise the new exploration controls through browser input.
 await cmd('Emulation.setTouchEmulationEnabled',{enabled:false});
 await viewport(1440);await go('');
 assert('project map starts closed',await evaluate("!document.querySelector('.map-disclosure').open"));
 await click('.map-disclosure > summary');
 await evaluate("document.querySelector('[data-project=\"eeg-platform\"]').focus()");await key('ArrowDown');
 assert('map arrow navigation selects retrieval',await evaluate("document.querySelector('[data-project=\"local-retrieval\"]').getAttribute('aria-pressed')==='true'&&document.querySelector('#map-detail a').getAttribute('href')==='work/local-retrieval/'"));
 await click('[data-project="premiere-assist"]');
 assert('map private project retains summary link',await evaluate("document.querySelector('#map-detail a').getAttribute('href')==='work/#project-premiere-assist'&&document.querySelectorAll('.map-lines .is-connected').length===2"));
 await click('[data-open-find]');
 assert('find opens and focuses input',await evaluate("document.querySelector('#find-dialog').open&&document.activeElement.id==='site-query'"));
 await cmd('Input.insertText',{text:'Premiere Assist'});
 assert('find includes private summary',await evaluate("document.querySelector('#find-results a').getAttribute('href')==='work/#project-premiere-assist'"));
 await evaluate("document.querySelector('#site-query').select()");await cmd('Input.insertText',{text:'zzznomatch987'});
 assert('find has an empty state',await evaluate("!document.querySelector('[data-find-empty]').hidden&&document.querySelectorAll('#find-results a').length===0"));
 await key('Escape');
 assert('find Escape restores focus',await evaluate("!document.querySelector('#find-dialog').open&&document.activeElement.matches('[data-open-find]')"));
 await cmd('Input.dispatchKeyEvent',{type:'keyDown',key:'k',code:'KeyK',modifiers:2});await cmd('Input.dispatchKeyEvent',{type:'keyUp',key:'k',code:'KeyK'});await sleep(100);
 assert('Ctrl K opens find',await evaluate("document.querySelector('#find-dialog').open"));
 await cmd('Input.insertText',{text:'Tempo'});await key('ArrowDown');
 assert('find keyboard reaches result',await evaluate("document.activeElement.matches('#find-results a')&&document.activeElement.getAttribute('href')==='work/tempo/'"));
 await key('Enter');await sleep(400);
 assert('find result navigates',await evaluate("location.pathname==='/work/tempo/'"));
 await go('');await click('[data-open-print]');
 for(let i=0;i<50;i++){if(await evaluate("!document.querySelector('[data-print-canvas]').hidden"))break;await sleep(100);}
 assert('print renders the portrait',await evaluate("document.querySelector('#print-dialog').open&&!document.querySelector('[data-print-canvas]').hidden"));
 await evaluate("window.__printBefore=document.querySelector('[data-print-canvas]').toDataURL();document.querySelector('#print-spacing').focus()");await key('ArrowRight');
 assert('spacing changes actual canvas pixels',await evaluate("document.querySelector('#print-spacing').value==='9'&&document.querySelector('[data-print-canvas]').toDataURL()!==window.__printBefore"));
 await cmd('Input.dispatchKeyEvent',{type:'keyDown',key:'k',code:'KeyK',modifiers:2});await cmd('Input.dispatchKeyEvent',{type:'keyUp',key:'k',code:'KeyK'});await sleep(80);
 assert('search shortcut does not open a second modal',await evaluate("document.querySelector('#print-dialog').open&&!document.querySelector('#find-dialog').open&&document.querySelector('#print-dialog').contains(document.activeElement)"));
 await click('input[name="print-ink"][value="red"]');
 assert('red ink updates accessible description',await evaluate("document.querySelector('[data-print-canvas]').getAttribute('aria-label').startsWith('Red ink')"));
 {const {data}=await cmd('Page.captureScreenshot',{format:'png'});fs.writeFileSync(reviewDir+'/printing-press.png',Buffer.from(data,'base64'));}
 await click('[data-print-photo]');assert('photo mode disables print settings',await evaluate("document.querySelector('[data-print-photo]').getAttribute('aria-pressed')==='true'&&document.querySelector('#print-spacing').disabled"));
 await click('[data-print-reset]');assert('print reset returns to default',await evaluate("document.querySelector('#print-spacing').value==='8'&&!document.querySelector('#print-spacing').disabled&&document.querySelector('input[name=\"print-ink\"][value=\"black\"]').checked"));
 const downloadPath=reviewDir+'/download-'+Date.now();fs.mkdirSync(downloadPath);
 await send('Browser.setDownloadBehavior',{behavior:'allow',downloadPath});await click('[data-print-save]');
 for(let i=0;i<40&&!fs.existsSync(downloadPath+'/sukalyan-roy-halftone.png');i++)await sleep(100);
 const png=fs.existsSync(downloadPath+'/sukalyan-roy-halftone.png')?fs.readFileSync(downloadPath+'/sukalyan-roy-halftone.png'):null;
 assert('save produces a 440px PNG',png&&png.subarray(1,4).toString()==='PNG'&&png.readUInt32BE(16)===440&&png.readUInt32BE(20)===440);
 await key('Escape');assert('print focus returns to trigger',await evaluate("document.activeElement.matches('[data-open-print]')&&!document.querySelector('#print-dialog').open"));
 await click('.map-disclosure > summary');
 await detailShot('project-map-desktop','.project-atlas');
 await go('work/local-retrieval/');
 const defaultScores=['0.032522','0.032266','0.031754','0.031498'];
 assert('fusion default matches hand calculations',JSON.stringify(await evaluate("[...document.querySelectorAll('.fusion-results output')].map(e=>e.value)"))===JSON.stringify(defaultScores));
 await click('[data-ranking="dense"] [data-move-up="window"]');
 assert('promoting a document recalculates fusion',await evaluate("document.querySelector('[data-ranking=\"dense\"] li').dataset.doc==='window'&&document.querySelector('.fusion-results output').value==='0.032787'"));
 await click('[data-retriever="dense"]');
 assert('single retriever preserves its ranking',await evaluate("document.querySelector('.fusion-results li').dataset.result==='window'&&document.querySelector('.fusion-results output').value==='0.016393'"));
 await click('[data-retriever="sparse"]');assert('no retrievers has empty state',await evaluate("document.querySelector('.fusion-results').hidden&&!document.querySelector('[data-fusion-empty]').hidden"));
 await click('[data-retriever="dense"]');assert('restoring results avoids animating from hidden coordinates',await evaluate("[...document.querySelectorAll('[data-result]')].every(row=>row.getAnimations().length===0)"));
 await click('[data-fusion-reset]');
 assert('fusion reset restores both lists and scores',JSON.stringify(await evaluate("[...document.querySelectorAll('.fusion-results output')].map(e=>e.value)"))===JSON.stringify(defaultScores));
 await evaluate("document.querySelector('[data-ranking=\"dense\"] [data-move-up=\"header\"]').focus()");await key('Enter');
 assert('rank movement works from the keyboard',await evaluate("document.querySelectorAll('[data-ranking=\"dense\"] li')[2].dataset.doc==='header'&&document.activeElement.dataset.moveUp==='header'"));
 await click('[data-fusion-reset]');
 await evaluate("document.querySelector('.retriever-pair').scrollIntoView({block:'center',behavior:'instant'})");
 const drag=await evaluate("(()=>{const c=id=>{const r=document.querySelector('[data-ranking=\"dense\"] [data-doc=\"'+id+'\"]').getBoundingClientRect();return {x:r.x+r.width*.4,y:r.y+r.height/2};};return {from:c('header'),to:c('cancel')};})()");
 await cmd('Input.dispatchMouseEvent',{type:'mouseMoved',...drag.from});await cmd('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',buttons:1,clickCount:1,...drag.from});
 await sleep(120);for(let i=1;i<=12;i++){await cmd('Input.dispatchMouseEvent',{type:'mouseMoved',button:'left',buttons:1,x:drag.from.x+(drag.to.x-drag.from.x)*i/12,y:drag.from.y+(drag.to.y-drag.from.y)*i/12});await sleep(35);}
 await sleep(500);await cmd('Input.dispatchMouseEvent',{type:'mouseMoved',button:'left',buttons:1,...drag.to});await sleep(100);await cmd('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...drag.to});await sleep(250);
 assert('native mouse drag reorders ranking',await evaluate("document.querySelector('[data-ranking=\"dense\"] li').dataset.doc==='header'"));
 await detailShot('fusion-desktop','#explore');
 await go('library/');await evaluate("document.querySelector('#books-track').scrollIntoView({block:'center',behavior:'instant'})");await sleep(700);
 assert('book covers load locally',await evaluate("[...document.querySelectorAll('#books-track img')].slice(0,3).every(i=>i.complete&&i.naturalWidth>0&&new URL(i.src).origin===location.origin)"));
 await click('[data-shelf] [data-shelf-next]');await sleep(700);
 assert('book carousel advances',await evaluate("document.querySelector('#books-track').scrollLeft>0&&!document.querySelector('[data-shelf] [data-shelf-prev]').disabled"));
 await evaluate("document.querySelector('#film-kind').focus()");await key('End');await key('Enter');
 assert('film filter shows 10 series',await evaluate("document.querySelector('#film-kind').value==='series'&&document.querySelectorAll('#films-track > li:not([hidden])').length===10"));
 await evaluate("document.querySelector('#film-kind').focus()");await key('Home');await key('Enter');
 assert('film filter restores all 84 recommendations',await evaluate("document.querySelectorAll('#films-track > li:not([hidden])').length===84"));
 await evaluate("window.__random=Math.random;Math.random=()=>.75");await click('[data-shelf-surprise]');await sleep(700);await evaluate("Math.random=window.__random");
 assert('surprise browses elsewhere in the film shelf',await evaluate("document.querySelector('#films-track').scrollLeft>0"));
 await detailShot('book-shelf-desktop','.personal-shelf');
 await detailShot('film-shelf-desktop','#films-heading');
 await viewport(390);await go('library/');await evaluate("document.querySelector('#books-track').scrollIntoView({block:'center',behavior:'instant'})");await sleep(300);
 await cmd('Emulation.setTouchEmulationEnabled',{enabled:true});
 const swipe=await evaluate("(()=>{const r=document.querySelector('#books-track').getBoundingClientRect();return {x:r.right-30,y:r.top+110,scroll:scrollY};})()");
 await cmd('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:swipe.x,y:swipe.y}]});
 for(let i=1;i<=8;i++){await cmd('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:swipe.x-i*28,y:swipe.y}]});await sleep(35);}
 await cmd('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await sleep(700);
 assert('mobile touch swipes the book shelf',await evaluate("document.querySelector('#books-track').scrollLeft>30"));
 await detailShot('book-shelf-mobile','#books-heading');
 await cmd('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});await go('');await click('.map-disclosure > summary');
 assert('map respects reduced motion',await evaluate("getComputedStyle(document.querySelector('.map-lines .is-connected')).animationName==='none'"));
 await cmd('Emulation.setScriptExecutionDisabled',{value:true});await go('library/');
 assert('personal shelves work without JS',await evaluate("document.querySelectorAll('#films-track a').length===84&&document.querySelectorAll('#books-track a').length===11&&document.querySelectorAll('.personal-essays article').length===2&&[...document.querySelectorAll('[data-enhance]')].every(e=>e.hidden)"));
 await cmd('Emulation.setScriptExecutionDisabled',{value:false});
 await cmd('Emulation.setDeviceMetricsOverride',{width:390,height:700,deviceScaleFactor:1,mobile:true});await go('');await touch('[data-open-print]');await sleep(150);
 assert('small phone print dialog fits',await evaluate("(()=>{const d=document.querySelector('#print-dialog');const r=d.getBoundingClientRect();return d.open&&r.right<=innerWidth&&r.bottom<=innerHeight&&r.top>=0;})()"));
 await evaluate("document.querySelector('#print-spacing').focus()");await key('End');
 assert('small phone print controls work',await evaluate("document.querySelector('#print-spacing').value==='20'&&document.querySelector('[data-print-canvas]').getAttribute('aria-label').includes('20 pixel')"));
 {const {data}=await cmd('Page.captureScreenshot',{format:'png'});fs.writeFileSync(reviewDir+'/printing-press-mobile.png',Buffer.from(data,'base64'));}
 await key('Escape');assert('small phone print closes',await evaluate("!document.querySelector('#print-dialog').open&&document.activeElement.matches('[data-open-print]')"));
 await cmd('Emulation.setTouchEmulationEnabled',{enabled:false});
 await cmd('Emulation.setEmulatedMedia',{features:[]});
 const blogRoot=path.resolve(__dirname,'../../blog');
 const blogRoutes=[];
 const collect=folder=>{for(const entry of fs.readdirSync(folder,{withFileTypes:true})){const location=path.join(folder,entry.name);if(entry.isDirectory()&&entry.name!=='assets')collect(location);else if(entry.isFile()&&entry.name==='index.html')blogRoutes.push('blog/'+path.relative(blogRoot,folder).split(path.sep).filter(Boolean).join('/')+(folder===blogRoot?'':'/'));}};
 collect(blogRoot);
 for(const width of [1440,390]){await viewport(width);for(const route of blogRoutes){await go(route);assert(width+' '+route+' blog layout',await evaluate("document.documentElement.scrollWidth<=innerWidth&&document.querySelectorAll('h1').length===1&&!!document.querySelector('main')"));}}
 await go('blog/');
 const blogQuery=await evaluate("!!document.querySelector('#finder-q')");
 if(blogQuery){await evaluate("document.querySelector('#finder-q').focus()");await cmd('Input.insertText',{text:'rank fusion'});await sleep(500);assert('blog search returns the retrieval article',await evaluate("!document.querySelector('[data-finder-results]').hidden&&document.querySelector('[data-finder-results]').textContent.includes('Rank Fusion')"));}
 assert('no browser errors',errors.length===0);fs.writeFileSync(reviewDir+'/results.json',JSON.stringify({status:results.every(item=>item.pass)?'passed':'failed',browser:version.product,results,errors},null,2));console.log(JSON.stringify({passed:results.filter(x=>x.pass).length,total:results.length,errors:errors.length}));if(results.some(x=>!x.pass))process.exitCode=1;
}
main().catch(error => {
  console.error(error);
  fs.writeFileSync(resultFile, JSON.stringify({status:'failed', error:String(error)}, null, 2));
  process.exitCode = 1;
}).finally(() => { chrome.kill(); });
