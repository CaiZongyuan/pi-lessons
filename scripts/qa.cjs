const {chromium}=require('playwright');
const fs=require('fs');
(async()=>{
 fs.mkdirSync('qa',{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1440,height:1050},deviceScaleFactor:1});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const routes=['/','/pi-104/','/pi-104/system-prompt','/pi-104/tools','/pi-104/sessions','/pi-104/compaction','/pi-durable/'];
 const results=[];
 for(const route of routes){
  const res=await page.goto('http://localhost:4173'+route);await page.waitForLoadState('networkidle');
  const stats=await page.evaluate(()=>({title:document.title,h1:document.querySelector('h1')?.innerText,overflow:document.documentElement.scrollWidth>innerWidth,tables:[...document.querySelectorAll('.vp-doc table')].map(t=>[...t.rows].map(r=>r.cells.length)),figures:document.querySelectorAll('.manual-figure').length}));
  if(res.status()!==200||stats.overflow)throw Error('Route failed '+route+JSON.stringify(stats));
  if(stats.tables.some(t=>new Set(t).size!==1))throw Error('Broken table '+route);
  results.push({route,status:res.status(),...stats});
 }
 await page.goto('http://localhost:4173/');await page.waitForLoadState('networkidle');await page.screenshot({path:'qa/desktop-library.png',fullPage:true});
 await page.goto('http://localhost:4173/pi-104/system-prompt');await page.waitForLoadState('networkidle');await page.screenshot({path:'qa/desktop-reading.png',fullPage:false});
 await page.getByRole('button',{name:'收起目录',exact:true}).click();
 if(!await page.locator('html').evaluate(el=>el.classList.contains('sidebar-hidden')))throw Error('Desktop sidebar hide failed');
 await page.getByRole('button',{name:'显示目录',exact:true}).click();
 await page.setViewportSize({width:390,height:844});
 for(const route of routes){await page.goto('http://localhost:4173'+route);await page.waitForLoadState('networkidle');if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile overflow '+route);}
 await page.goto('http://localhost:4173/');await page.waitForLoadState('networkidle');await page.screenshot({path:'qa/mobile-library.png',fullPage:true});
 await page.goto('http://localhost:4173/pi-104/system-prompt');await page.waitForLoadState('networkidle');await page.screenshot({path:'qa/mobile-reading.png',fullPage:true});
 await page.getByRole('button',{name:'书籍目录',exact:true}).click();
 if(!await page.locator('.VPSidebar.open').count())throw Error('Mobile sidebar not open');
 await page.screenshot({path:'qa/mobile-menu.png',fullPage:false});
 if(errors.length)throw Error(errors.join('\n'));
 fs.writeFileSync('qa/results.json',JSON.stringify({routes:results,consoleErrors:errors,desktopSidebar:true,mobileMenu:true,mobileOverflow:false},null,2));
 console.log('PASS: 7 routes, desktop/mobile overflow, 6 tables, desktop collapse, mobile menu, no page errors.');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
