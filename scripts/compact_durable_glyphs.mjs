/** Lossless authoring optimization: pool identical Type3 glyph outlines, never simplify geometry. */
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import {fileURLToPath} from 'node:url'
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),dir=path.join(root,'docs/.vitepress/theme/figures'),dictPath=path.join(root,'docs/.vitepress/theme/durable-glyphs.json')
const glyphs=fs.existsSync(dictPath)?JSON.parse(fs.readFileSync(dictPath,'utf8')):{}
let uses=0
for(const name of fs.readdirSync(dir).filter(n=>/^durable-.*\.json$/.test(n))){const p=path.join(dir,name),figs=JSON.parse(fs.readFileSync(p,'utf8'));for(const f of figs){for(const d of f.vectorDefs||[]){if(d.d){const key=crypto.createHash('sha256').update(d.d).digest('hex').slice(0,20);if(glyphs[key]&&glyphs[key]!==d.d)throw Error('Glyph hash collision');glyphs[key]=d.d;delete d.d;d.key=key;}if(!glyphs[d.key])throw Error('Missing pooled glyph');uses++}}fs.writeFileSync(p+'.tmp',JSON.stringify(figs)+'\n');fs.renameSync(p+'.tmp',p)}
fs.writeFileSync(dictPath,JSON.stringify(glyphs)+'\n');console.log(`Pooled ${uses} glyph definitions into ${Object.keys(glyphs).length} exact outlines.`)
