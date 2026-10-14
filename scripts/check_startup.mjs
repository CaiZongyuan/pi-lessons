/** Optional local smoke test: does not execute any book examples. */
import {spawn} from 'node:child_process'
import http from 'node:http'
const npm=process.platform==='win32'?'npm.cmd':'npm'
async function check(command,port,route){
 const child=spawn(npm,['run',command],{cwd:process.cwd(),shell:process.platform==='win32',stdio:['ignore','pipe','pipe'],detached:process.platform!=='win32'})
 let log='';child.stdout.on('data',b=>log+=b);child.stderr.on('data',b=>log+=b)
 try{
  const deadline=Date.now()+30000;let ok=false,last=''
  while(Date.now()<deadline){
   if(child.exitCode!==null)throw Error(`${command} exited ${child.exitCode}: ${log}`)
   try{await new Promise((resolve,reject)=>{const req=http.get(`http://127.0.0.1:${port}${route}`,res=>{let text='';res.on('data',b=>text+=b);res.on('end',()=>res.statusCode===200&&(text.includes('Pi')||(command==='dev'&&text.includes('/@vite/client')))?resolve():reject(Error(`HTTP ${res.statusCode}`)))});req.on('error',reject);req.setTimeout(2000,()=>req.destroy(Error('request timed out')))});ok=true;break}catch(e){last=e.message}
   await new Promise(resolve=>setTimeout(resolve,200))
  }
  if(!ok)throw Error(`${command}: ${last}; ${log}`)
  console.log(`PASS npm run ${command}: HTTP 200 at ${route}, port ${port}`)
 }finally{if(process.platform==='win32')child.kill();else{try{process.kill(-child.pid,'SIGTERM')}catch{}}}
}
await check('preview',4173,'/pi-durable/')
await check('dev',5173,'/pi-durable/ch01/section-01')
