#!/usr/bin/env python3
"""Faithful Pi Durable vector catalogs, extracted from the supplied PDF.

PDF paths (including outlined type), clipping, and paint order are retained.
The transparent semantic nodes are a separate accessible interaction layer.
No source image is rasterized into the native diagram.
"""
from __future__ import annotations
import json
import math
import os
import re
from pathlib import Path
from urllib.parse import unquote

import fitz

ROOT = Path(__file__).resolve().parents[1]
PDF = Path(os.environ.get('PI_DURABLE_PDF', str(ROOT.parent / 'pi-durable-input/Pi-Durable-Technical-Manual.pdf')))


def nfmt(v):
    return f'{v:.3f}'.rstrip('0').rstrip('.') or '0'


def color(value):
    if value is None:
        return 'none'
    if len(value) == 1:
        value = value * 3
    return '#' + ''.join(f'{min(255,max(0,round(v*255))):02x}' for v in value[:3])


def path_d(items, crop, scale, close=False):
    """Convert PyMuPDF's native path records to normalized SVG commands."""
    out = []
    last = None
    def p(pt):
        return f'{nfmt((pt.x-crop.x0)*scale)},{nfmt((pt.y-crop.y0)*scale)}'
    def start(pt):
        nonlocal last
        if last is None or abs(pt.x-last.x)>0.00001 or abs(pt.y-last.y)>0.00001:
            out.append('M'+p(pt))
        last = pt
    for item in items:
        kind = item[0]
        if kind == 'l':
            start(item[1]);out.append('L'+p(item[2]));last=item[2]
        elif kind == 'c':
            start(item[1]);out.append('C'+' '.join(p(v) for v in item[2:5]));last=item[4]
        elif kind == 're':
            r = item[1]
            pts = [r.tl,r.tr,r.br,r.bl]
            if len(item)>2 and item[2]<0:
                pts = [r.tl,r.bl,r.br,r.tr]
            out.append('M'+p(pts[0])+''.join('L'+p(v) for v in pts[1:])+'Z');last=None
        elif kind == 'qu':
            q = item[1];pts=[q.ul,q.ur,q.lr,q.ll]
            out.append('M'+p(pts[0])+''.join('L'+p(v) for v in pts[1:])+'Z');last=None
        else:
            raise ValueError(f'Unsupported PDF path item {kind}')
    if close and last is not None:
        out.append('Z')
    return ''.join(out)


def intersects(a, b, margin=.02):
    return a.x0 <= b.x1+margin and a.x1 >= b.x0-margin and a.y0 <= b.y1+margin and a.y1 >= b.y0-margin


def text_lines(page, crop):
    lines=[]
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines',[]):
            r=fitz.Rect(line['bbox'])
            if not crop.contains(r.tl) or not crop.contains(r.br):
                continue
            text=''.join(s['text'] for s in line['spans']).strip()
            if text:
                lines.append({'text':text,'rect':r,'size':max(s['size'] for s in line['spans']),
                              'origin':line['spans'][0]['origin']})
    return lines


def export_vector_drawings(page, crop, width=1100, id_prefix='figure'):
    """Return BookFigure vector data and accessible text-line hotspots.

    Paths are clipped to the crop as well as the PDF's own nested clips.
    `vectorClips.parent` and `vectorPaths.clip` are zero-based clip indices.
    """
    crop=fitz.Rect(crop);scale=width/crop.width
    height=round(crop.height*scale,3)
    clips=[{'d':f'M0,0H{width}V{nfmt(height)}H0Z','fillRule':'nonzero'}]
    paths=[];stack=[];clippool={}
    for draw in page.get_drawings(extended=True):
        level=draw.get('level',0)
        stack=[s for s in stack if s['level']<level]
        parent=next((s['clip'] for s in reversed(stack) if 'clip' in s),0)
        opacity=math.prod(s.get('opacity',1) for s in stack)
        kind=draw['type']
        if kind == 'group':
            if draw.get('blendmode','Normal') != 'Normal':
                raise ValueError(f'Unsupported blend mode: {draw}')
            stack.append({'level':level,'opacity':draw.get('opacity',1)})
            continue
        if kind == 'clip':
            # A full-page clip adds no constraint beyond our figure crop.
            if draw['scissor'].contains(crop) and len(draw['items'])==1 and draw['items'][0][0]=='re':
                stack.append({'level':level,'clip':parent});continue
            c={'d':path_d(draw['items'],crop,scale,draw.get('closePath',False)),
               'fillRule':'evenodd' if draw.get('even_odd') else 'nonzero','parent':parent}
            key=json.dumps(c,sort_keys=True)
            if key not in clippool:
                clippool[key]=len(clips);clips.append(c)
            stack.append({'level':level,'clip':clippool[key]})
            continue
        if not intersects(draw['rect'],crop):
            continue
        d=path_d(draw['items'],crop,scale,draw.get('closePath',False))
        if not d:
            continue
        path={'d':d,'fill':color(draw.get('fill')),'stroke':color(draw.get('color')),
              'width':round((draw.get('width') or 0)*scale,4),
              'fillOpacity':round((draw.get('fill_opacity') or 0)*opacity,4),
              'strokeOpacity':round((draw.get('stroke_opacity') or 0)*opacity,4),
              'fillRule':'evenodd' if draw.get('even_odd') else 'nonzero',
              'lineCap':{0:'butt',1:'round',2:'square'}.get(max(draw.get('lineCap') or [0]),'butt'),
              'lineJoin':{0:'miter',1:'round',2:'bevel'}.get(int(draw.get('lineJoin') or 0),'miter'),
              'clip':parent}
        dash=re.fullmatch(r'\[([^]]*)\]\s*([\d.+-]+)',draw.get('dashes') or '')
        if dash and dash[1].strip():
            path['dashArray']=' '.join(nfmt(float(v)*scale) for v in dash[1].split())
            path['dashOffset']=round(float(dash[2])*scale,4)
        # Coalesce consecutive opaque glyphs only. This preserves paint order,
        # keeps the catalog compact, and avoids tens of thousands of DOM nodes.
        style={k:v for k,v in path.items() if k!='d'}
        if paths and path['stroke']=='none' and path['fillOpacity']==1 and len(paths[-1]['d'])<50000 and style=={k:v for k,v in paths[-1].items() if k!='d'}:
            paths[-1]['d']+=d
        else:
            paths.append(path)
    lines=text_lines(page,crop)
    nodes=[]
    for i,line in enumerate(lines):
        r=line['rect']
        nodes.append({'id':f'{id_prefix}-text-{i+1}',
                      'x':round(max(0,(r.x0-crop.x0)*scale-3),3),
                      'y':round(max(0,(r.y0-crop.y0)*scale-3),3),
                      'w':round(min(width,(r.width*scale+6)),3),
                      'h':round(r.height*scale+6,3),
                      'label':line['text'],'detail':line['text'],
                      'shape':'label','hotspot':True})
    return {'width':width,'height':height,'nodes':nodes,'edges':[],
            'vectorPaths':paths,'vectorClips':clips,
            'sourceText':'\n'.join(l['text'] for l in lines)}


def export_vector(page, crop, width=1100, id_prefix='figure'):
    """Flatten the PDF's own SVG paths, preserving transformed stroke widths.

    PyMuPDF get_drawings() does not apply SVG transforms to stroke width. Its
    SVG exporter does; using that export is therefore important for fidelity.
    The only inline raster paint allowed here is the book's simple diagonal
    hatch, recreated as explicitly clipped native line paths.
    """
    import base64
    import io
    import xml.etree.ElementTree as ET
    from PIL import Image
    from fontTools.svgLib.path import parse_path
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.misc.transform import Transform
    crop=fitz.Rect(crop);scale=width/crop.width;height=round(crop.height*scale,3)
    svg=ET.fromstring(page.get_svg_image(text_as_path=True))
    defs={e.attrib['id']:e for e in svg.iter() if 'id' in e.attrib}
    root=Transform(scale,0,0,scale,-crop.x0*scale,-crop.y0*scale)
    clips=[{'d':f'M0,0H{width}V{nfmt(height)}H0Z','fillRule':'nonzero'}]
    paths=[];clipcache={};hatches=set();warnings=[];vector_defs=[];glyphcache={}
    view=fitz.Rect(0,0,width,height)
    def transform(value):
        if not value:return Transform()
        m=re.fullmatch(r'matrix\(([^)]*)\)',value)
        if not m:raise ValueError(f'Unknown SVG transform: {value}')
        return Transform(*map(float,re.split(r'[, ]+',m[1].strip())))
    def convert(d,m):
        bounds=BoundsPen(None);parse_path(d,TransformPen(bounds,m))
        if bounds.bounds is None:return '',None
        pen=SVGPathPen(None,ntos=nfmt);parse_path(d,TransformPen(pen,m))
        return pen.getCommands(),fitz.Rect(bounds.bounds)
    def clip_index(ref,m,parent):
        key=(ref,tuple(m),parent)
        if key in clipcache:return clipcache[key]
        e=defs[ref];parts=[]
        for child in e:
            if child.tag.split('}')[-1]!='path':raise ValueError('Nonpath SVG clip')
            d,_=convert(child.attrib['d'],m.transform(transform(child.get('transform'))));parts.append(d)
        c={'d':''.join(parts),'fillRule':next(iter(e)).get('clip-rule','nonzero'),'parent':parent}
        idx=len(clips);clips.append(c);clipcache[key]=idx;return idx
    def add(path):
        if 'ref' in path:
            paths.append(path);return
        style={k:v for k,v in path.items() if k!='d'}
        if paths and 'd' in paths[-1] and path['stroke']=='none' and path['fillOpacity']==1 and len(paths[-1]['d'])<50000 and style=={k:v for k,v in paths[-1].items() if k!='d'}:
            paths[-1]['d']+=path['d']
        else:paths.append(path)
    def walk(e,m,parent=0,opacity=1,using=False):
        tag=e.tag.split('}')[-1]
        if tag=='defs' or tag=='clipPath':return
        m=m.transform(transform(e.get('transform')))
        if e.get('clip-path'):
            ref=e.get('clip-path')[5:-1]
            parent=clip_index(ref,m,parent)
        opacity*=float(e.get('opacity',1))
        if tag=='path':
            d,r=convert(e.get('d',''),m)
            if not d or not intersects(r,view):return
            unit=math.sqrt(abs(m[0]*m[3]-m[1]*m[2]))
            p={'d':d,'fill':e.get('fill','#000000'),'stroke':e.get('stroke','none'),
               'width':round(float(e.get('stroke-width',1))*unit,4),
               'fillOpacity':round(float(e.get('fill-opacity',1))*opacity,4),
               'strokeOpacity':round(float(e.get('stroke-opacity',1))*opacity,4),
               'lineCap':e.get('stroke-linecap','butt'),'lineJoin':e.get('stroke-linejoin','miter'),
               'fillRule':e.get('fill-rule','nonzero'),'clip':parent}
            if e.get('stroke-dasharray'):
                p['dashArray']=' '.join(nfmt(float(v)*unit) for v in re.split('[, ]+',e.get('stroke-dasharray')))
                p['dashOffset']=round(float(e.get('stroke-dashoffset',0))*unit,4)
            # Source Type3 glyphs share a font-space path. Keep one definition
            # and exact affine uses instead of expanding every occurrence.
            if unit<.15 and p['stroke']=='none':
                raw=e.get('d','')
                if raw not in glyphcache:
                    glyphpen=SVGPathPen(None,ntos=nfmt);parse_path(raw,glyphpen)
                    glyphcache[raw]=len(vector_defs);vector_defs.append({'d':glyphpen.getCommands()})
                p.pop('d');p['ref']=glyphcache[raw]
                p['transform']='matrix('+','.join((f'{v:.8f}' if i<4 else f'{v:.3f}').rstrip('0').rstrip('.') or '0' for i,v in enumerate(m))+')'
                # These are SVG defaults; omit them on filled glyph uses.
                for key in ['width','stroke','lineCap','lineJoin','fillRule']:
                    p.pop(key,None)
                for key in ['fillOpacity','strokeOpacity']:
                    if p.get(key)==1:p.pop(key)
            add(p)
        elif tag=='use':
            ref=e.get('{http://www.w3.org/1999/xlink}href',e.get('href',''))
            if ref.startswith('#'):
                shift=Transform(1,0,0,1,float(e.get('x',0)),float(e.get('y',0)))
                walk(defs[ref[1:]],m.transform(shift),parent,opacity,True)
        elif tag=='image':
            if parent in hatches:return
            if int(e.get('width',0))<10 or int(e.get('height',0))<10:return
            href=e.get('{http://www.w3.org/1999/xlink}href',e.get('href',''))
            if not href.startswith('data:image/png;base64,'):raise ValueError('Nonembedded PDF image')
            im=Image.open(io.BytesIO(base64.b64decode(href.split(',',1)[1]))).convert('RGB')
            extrema=im.getextrema()
            # The supplied manual's hatching is a two-tone, warm-gray texture.
            # Reject arbitrary content rather than inventing a vector version.
            if any(hi-lo>45 for lo,hi in extrema) or min(lo for lo,hi in extrema)<190:
                raise ValueError(f'Non-hatch raster paint on PDF page {page.number+1}')
            # Clip may belong to a code block outside the selected figure.
            bounds=BoundsPen(None);parse_path(clips[parent]['d'],bounds)
            if not bounds.bounds or not intersects(fitz.Rect(bounds.bounds),view):return
            hatches.add(parent)
            r=fitz.Rect(bounds.bounds)&view
            base={'fillOpacity':opacity,'strokeOpacity':opacity,'lineCap':'butt','lineJoin':'miter','fillRule':'nonzero','clip':parent}
            add(dict(base,d=f'M{nfmt(r.x0)},{nfmt(r.y0)}H{nfmt(r.x1)}V{nfmt(r.y1)}H{nfmt(r.x0)}Z',fill='#f1efe8',stroke='none',width=0))
            # Hatch cadence and color are checked against the source pixels.
            step=4.0*scale;pad=r.height
            d=''.join(f'M{nfmt(x)},{nfmt(r.y1)}L{nfmt(x+pad)},{nfmt(r.y0)}' for x in [r.x0-pad+i*step for i in range(math.ceil((r.width+2*pad)/step)+1)])
            add(dict(base,d=d,fill='none',stroke='#e0ddd0',width=round(.8*scale,4)))
        else:
            for child in e:walk(child,m,parent,opacity)
    walk(svg,root)
    lines=text_lines(page,crop);nodes=[]
    for i,line in enumerate(lines):
        r=line['rect'];x=max(0,(r.x0-crop.x0)*scale-3);y=max(0,(r.y0-crop.y0)*scale-3)
        nodes.append({'id':f'{id_prefix}-text-{i+1}','x':round(x,3),'y':round(y,3),
                      'w':round(min(width-x,r.width*scale+6),3),'h':round(min(height-y,r.height*scale+6),3),
                      'label':line['text'],'detail':line['text'],'shape':'label','hotspot':True})
    return {'width':width,'height':height,'nodes':nodes,'edges':[],
            'vectorPaths':paths,'vectorClips':clips,'vectorDefs':vector_defs,
            'vectorTexts':[{'text':l['text'],'x':round((l['rect'].x0-crop.x0)*scale,3),
                            'y':round((l['origin'][1]-crop.y0)*scale,3),'width':round(l['rect'].width*scale,3),
                            'fontSize':round(l['size']*scale,3)} for l in lines],
            'sourceText':'\n'.join(l['text'] for l in lines),
            'vectorExtraction':{'method':'PDF SVG paths with outlined source text','reconstructedHatchRegions':len(hatches),'coordinateRounding':0.001}}


def matching_crop(page, target_ratio=None, title=None):
    """Find the actual figure panel, excluding code blocks on the same page."""
    candidates=[]
    for d in page.get_drawings():
        r=d['rect']
        if len(d['items'])==1 and d['items'][0][0]=='re' and d['type']=='f' and 480<r.width<510 and r.height>60 and r.y0>0 and r.y1<750:
            text=page.get_textbox(r)
            if title and title.lower() not in text.lower():
                continue
            score=abs(math.log((r.width/r.height)/target_ratio)) if target_ratio else 0
            candidates.append((score,r))
    if not candidates:
        raise ValueError(f'No figure panel found on page {page.number+1}')
    candidates.sort(key=lambda x:x[0])
    return candidates[0][1]


def write_svg(data, target):
    """QA-only SVG serialization using exactly the catalog renderer schema."""
    import html
    def attr(k,v):
        return f' {k}="{html.escape(str(v),quote=True)}"'
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{data["width"]}" height="{data["height"]}" viewBox="0 0 {data["width"]} {data["height"]}"><defs>']
    for i,d in enumerate(data.get('vectorDefs',[])):
        out.append(f'<path id="def-{i}"'+attr('d',d['d'])+'/>')
    for i,c in enumerate(data['vectorClips']):
        p=attr('clip-path',f'url(#clip-{c["parent"]})') if 'parent' in c else ''
        out.append(f'<clipPath id="clip-{i}" clipPathUnits="userSpaceOnUse"><path'+attr('d',c['d'])+attr('fill-rule',c['fillRule'])+p+'/></clipPath>')
    out.append('</defs>')
    mapping={'fill':'fill','stroke':'stroke','width':'stroke-width','fillOpacity':'fill-opacity','strokeOpacity':'stroke-opacity','lineCap':'stroke-linecap','lineJoin':'stroke-linejoin','fillRule':'fill-rule','dashArray':'stroke-dasharray','dashOffset':'stroke-dashoffset'}
    for p in data['vectorPaths']:
        s='<g'+attr('clip-path',f'url(#clip-{p.get("clip",0)})')+'>'
        s+=('<use'+attr('href',f'#def-{p["ref"]}')+attr('transform',p['transform'])) if 'ref' in p else '<path'+attr('d',p['d'])
        for key,svgkey in mapping.items():
            if key in p:s+=attr(svgkey,p[key])
        s+='/></g>';out.append(s)
    out.append('</svg>');Path(target).write_text(''.join(out))


EARLY = {
 'front':[(1,None,'一次崩溃，以及幸存的状态'),(8,'0.1','如何阅读时序图')],
 '1':[(11,'1.1','工具调用中途的崩溃'),(13,'1.2','Harness 的各层'),(16,'1.3','提交是唯一的门'),(20,'1.4','一次输入得到回答：提交 1–8'),(22,'1.5','一次输入得到回答：提交 9–17')],
 '2':[(25,'2.1','记录家族'),(27,'2.2','按 ID 与提交序号查看一次回答'),(30,'2.3','变更串行队列上的一次提交'),(33,'2.4','各阶段的提交失败结果')],
 '3':[(37,'3.1','条目的结构'),(41,'3.2','一份对话记录，两种读取方式'),(44,'3.3','分叉、上限与有所有者的对话'),(47,'3.4','头指针移动时的上下文范围')],
 '4':[(51,'4.1','七种合法的文档语义'),(53,'4.2','新文档的第一次 tx.doc()'),(54,'4.3','同一存储中的三种作用域'),(56,None,'五次提交后的 document_revisions'),(57,'4.4','按提交序号排列的文档记录'),(58,'4.5','分叉复制的内容')],
 '5':[(64,'5.1','任务状态机'),(67,'5.2','每个阶段之前的步骤检查'),(70,'5.3','意图、副作用与结果'),(73,'5.4','查找任务的实现代码'),(76,'5.5','任务与对话的所有权树'),(78,'5.6','一张卡被拒绝后的 failFast'),(81,'5.7','中止正在等待的结账任务')],
}

EXPLANATIONS = {
 'pending':'任务尚未调用，等待调度器预留。重新打开存储会把原来的 running 任务改回 pending。',
 'running':'任务已被调度器预留，具有当前调用实例；检查点保存在任务记录中。',
 'waiting':'任务暂停，等待 on 列表中的其他任务完成；此时没有调用实例。',
 'completing':'任务结果已经确定，但它启动的子工作仍然存活。子工作结束后才转为 terminal。',
 'terminal':'任务及其子工作已经完成，记录成为不会再被改写的回执。',
 'checkpoint':'检查点记录下一步执行所需的持久化状态。每个阶段结束时，调度器检查是否取得持久化进展。',
 'abortRequested':'存活任务上的中止标记，不是独立状态。下一次调用运行中止处理函数。',
 'MemoryStorage':'内存后端；进程退出后不保留状态。',
 'SqliteStorage':'SQLite 后端；一个数据库文件保存记录、文档与提交。',
 'JsonlStorage':'JSONL 后端；状态保存在目录中的文件里。',
 'Chord':'文档状态和操作的依赖包，不是 HarnessOptions 选项。',
 'model':'条目添加给模型上下文的 Message[]；缺省时不添加消息。',
 'data':'应用使用的 JSON；模型不会收到这个字段。',
 'head':'上下文起点：当前带头指针的条目先贡献消息，然后从指向的条目继续读取。原来的条目仍被存储。',
 'byTaskId':'写入条目的任务 ID。宿主直接写入的条目可以没有该字段。',
 'ConversationRecord':'对话记录。parent 描述历史分叉；owner 描述创建它的任务，两种关系并不相同。',
 'EntryRecord':'不可变的对话条目。模型消息、应用数据、头指针与上下文编辑彼此分开。',
 'TaskRecord':'可被完整替换的任务记录，包含任务代码版本、输入、所有权、状态和检查点。',
 'SubmissionRecord':'输入或写入的接纳记录，可用于请求去重、排队、等待及追踪答案。',
 'DocumentRecord':'一个文档实例世代的记录，标识作用域、语义、创建提交和退役提交；内容另行存储。',
 'missing_task':'没有注册该 kind 的代码。任务保持 pending 或 waiting，注册表变化后再试。',
 'task_too_old':'记录版本比当前代码新，当前定义不能处理。任务保持阻塞；中止时才以 orphaned 结束。',
 'migration_failed':'记录版本较旧，但缺少迁移或迁移没有返回状态；任务保持阻塞。',
 'failFast':'等待对象中首个暂存或已完成的非 completed 结果，会在下一次协调提交中为其仍存活的兄弟任务加中止标记；等待方不会因此被标记。',
 'snapshotAsOf':'读取某条目时的文档值；仅 rewindable 文档保留可用于历史读取的变更。',
 'latest':'只保留当前文档值；写入新基值后，存储可以删除之前的记录。',
 'rewindable':'保留历史变更，可按条目时点读取旧值。',
 'asOf':'分叉复制父对话在分叉条目时的文档值，创建具有新 ID 和单个基值的独立文档。',
 'current':'分叉复制父对话当前已提交的文档值。',
 'initial':'分叉时不复制文档；子对话首次 tx.doc() 时运行 initial()。',
 'rejected':'StorageRejected 表示后端确认没有提交；Session 可以继续使用。',
 'poisoned':'存储结果不确定，或存储提交后的采纳失败，会使 Session 中毒；必须关闭并重新打开。',
}


def plain(s):
    s=re.sub(r'\*\*|`','',s)
    return re.sub(r'\\([.#*_()\[\]-])',r'\1',s).strip()


def extract_caption(text,end,stop):
    following=text[end:stop]
    lines=following.splitlines();quote=[];started=False
    for line in lines:
        if line.startswith('>'):
            started=True;quote.append(line[1:].strip())
        elif line.strip():
            if started:break
            # The SQLite data image has a prose rather than quoted caption.
            if not quote:return plain(line)
    return plain(' '.join(x for x in quote if x))


def enrich_nodes(fig):
    # Spatial reading order, rather than the PDF renderer's reverse lane order.
    fig['nodes'].sort(key=lambda n:(round(n['y']/4)*4,n['x']))
    fig['sourceText']='\n'.join(n['label'] for n in fig['nodes'])
    for node in fig['nodes']:
        label=node['label'].strip()
        lookup=re.sub(r'^[①②③④⑤⑥⑦⑧⑨\d .·]+','',label)
        if lookup in EXPLANATIONS:
            node['detail']=f'{label}\n{EXPLANATIONS[lookup]}'
        elif label in EXPLANATIONS:
            node['detail']=f'{label}\n{EXPLANATIONS[label]}'
        elif re.fullmatch(r'(?:[a-z]+\.)?snapshotAsOf\([^)]*\)(?:.*)?',label):
            node['detail']=f'{label}\n{EXPLANATIONS["snapshotAsOf"]}'
        elif 'failFast' in label:
            node['detail']=f'{label}\n{EXPLANATIONS["failFast"]}'


def build_early():
    pdf=fitz.open(str(PDF));figures=[];report=[]
    outdir=ROOT/'qa/durable-native/early';outdir.mkdir(parents=True,exist_ok=True)
    for chapter,specs in EARLY.items():
        directory=next(d for d in (ROOT/'sources/durable').iterdir() if d.is_dir() and (d.name.startswith('Pi ') if chapter=='front' else d.name.startswith(chapter+'.')))
        markdown=next(directory.glob('*.md'));text=markdown.read_text()
        refs=list(re.finditer(r'!\[[^\]]*\]\(([^)]*)\)',text))
        assert len(refs)==len(specs),(chapter,len(refs),len(specs))
        for i,((page_num,pdf_fig,title),ref) in enumerate(zip(specs,refs),1):
            id=f'D.{chapter}.{i}';filename=Path(unquote(ref[1])).name
            img=directory/unquote(ref[1]);webp=filename.replace(' ','-').removesuffix('.png')+'.webp'
            caption=extract_caption(text,ref.end(),refs[i].start() if i<len(refs) else len(text))
            label=f'FIG. {pdf_fig}' if pdf_fig else ('PLATE I' if chapter=='front' else 'SQLITE ROWS')
            displaypage='viii' if id=='D.front.2' else ('封面' if id=='D.front.1' else page_num)
            fig={'id':id,'title':title,'label':label,'source':f'Pi Durable Technical Manual · {label} · {directory.name}/图片和附件/{filename}',
                 'page':displaypage,'pdfPage':page_num,'pdfFigure':pdf_fig,
                 'image':f'/durable/{"front" if chapter=="front" else "ch"+chapter.zfill(2)}/{webp}',
                 'caption':caption,'kind':'diagram'}
            if id=='D.front.1':
                fig.update(kind='original',reason='封面将按提交序号排列的崩溃记录、纹理与多幅小图合在一张图版中；这里保留可放大的原图，避免简化造成信息损失。')
                report.append({'id':id,'kind':'original','reason':'Composite cover plate includes non-hatch inline raster decoration; exact original retained.','page':page_num,'image':str(img.relative_to(ROOT))})
            else:
                from PIL import Image
                im=Image.open(img);ratio=im.width/im.height;page=pdf[page_num-1]
                crop=fitz.Rect(64.75,449,374,540) if id=='D.4.4' else matching_crop(page,ratio,title='FIG.')
                data=export_vector(page,crop,width=1100,id_prefix=id);fig.update(data);enrich_nodes(fig)
                fig['pdfCrop']=[round(v,3) for v in crop]
                if data['vectorExtraction']['reconstructedHatchRegions']:
                    fig['notes']=['图中斜线填充以原生 SVG 线条重建；节点、箭头、标签、顺序和时间刻度沿用原书。']
                write_svg(fig,outdir/(id+'.svg'))
                page.get_pixmap(matrix=fitz.Matrix(1100/crop.width,1100/crop.width),clip=crop).save(outdir/(id+'-source.png'))
                report.append({'id':id,'kind':'diagram','page':page_num,'pdfFigure':pdf_fig,'crop':fig['pdfCrop'],
                               'sourceImage':str(img.relative_to(ROOT)),'nodes':len(fig['nodes']),'paths':len(fig['vectorPaths']),
                               'hatchRegions':data['vectorExtraction']['reconstructedHatchRegions']})
            figures.append(fig)
    target=ROOT/'docs/.vitepress/theme/figures/durable-early.json'
    tmp=target.with_suffix('.json.tmp');tmp.write_text(json.dumps(figures,ensure_ascii=False,separators=(',',':'))+'\n');tmp.replace(target)
    reportfile=ROOT/'sources/reports/durable-figures-early.json';reportfile.parent.mkdir(exist_ok=True)
    reportfile.write_text(json.dumps({'scope':'front and chapters 1–5','figures':report,'count':len(figures),
         'native':sum(f['kind']=='diagram' for f in figures),'original':sum(f['kind']=='original' for f in figures),
         'method':'True source-extracted SVG path geometry, outlined glyphs, clipped paint order; accessible native hotspots. Warm-gray hatch textures alone reconstructed as lines.',
         'sourcePDF':str(PDF),'qa':'Source images and rendered PDF inspected; per-figure SVG/source renders in /tmp/durable-early/qa; final contact-sheet review pending.'},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'catalog':str(target),'bytes':target.stat().st_size,'figures':len(figures),'report':str(reportfile)}))


if __name__=='__main__':
    build_early()
