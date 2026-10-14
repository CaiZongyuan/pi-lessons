import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import {fileURLToPath} from 'node:url'
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..')
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')
const reports=[['sources/reports/webp-conversion.json',r=>r.files.map(f=>[f.public_webp,f.webp_sha256])],['sources/reports/durable-import.json',r=>r.images.map(f=>[f.output,f.webp_sha256])]]
let count=0
for(const [name,rows] of reports){const p=path.join(root,name);if(!fs.existsSync(p)){if(name.includes('durable'))continue;throw Error(`Missing asset manifest: ${name}`)}for(const [file,expected] of rows(JSON.parse(fs.readFileSync(p,'utf8')))){if(sha(path.join(root,file))!==expected)throw Error(`Asset hash mismatch: ${file}`);count++}}
console.log(`Verified ${count} committed WebP assets using Node.js; no Python needed.`)
