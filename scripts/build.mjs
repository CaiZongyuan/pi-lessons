import {spawnSync} from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import {fileURLToPath} from 'node:url'
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..')
const stage=path.join(root,'docs/.vitepress/staging'),dest=path.join(root,'docs/.vitepress/dist')
const verify=spawnSync(process.execPath,[path.join(root,'scripts/verify_assets.mjs')],{cwd:root,stdio:'inherit'});if(verify.status!==0)process.exit(verify.status||1)
fs.rmSync(stage,{recursive:true,force:true})
const p=spawnSync(process.execPath,[path.join(root,'node_modules/vitepress/bin/vitepress.js'),'build','docs'],{cwd:root,stdio:'inherit',env:{...process.env,PI_BUILD_DIR:stage}})
if(p.status!==0)process.exit(p.status||1)
// Keep the live directory inode stable for the already-running preview server.
// Install assets before documents; older hashed assets remain valid for open tabs.
fs.mkdirSync(dest,{recursive:true})
function files(dir){return fs.readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()?files(path.join(dir,e.name)):[path.join(dir,e.name)])}
const list=files(stage).sort((a,b)=>Number(a.endsWith('.html'))-Number(b.endsWith('.html')))
for(const f of list){const out=path.join(dest,path.relative(stage,f));fs.mkdirSync(path.dirname(out),{recursive:true});const temp=out+'.new';fs.copyFileSync(f,temp);fs.renameSync(temp,out)}
fs.rmSync(stage,{recursive:true,force:true})
for(const f of files(path.join(dest,'figures'))){if(f.endsWith('.png')&&fs.existsSync(f.slice(0,-4)+'.webp'))fs.unlinkSync(f)}
console.log('Verified build installed; local preview remains available.')
