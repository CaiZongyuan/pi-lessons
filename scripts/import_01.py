#!/usr/bin/env python3
"""Faithful, reproducible chapter 1 import. Run with --check to validate only.

No networking. Does not execute book commands. Sources are immutable. Figures
were visually checked against all PDF pages 7–22 and the five supplied PNGs.
"""
from pathlib import Path
from urllib.parse import unquote
import argparse
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'sources/full/1.模型/1.模型.md'
IMAGES = SOURCE.parent / '图片和附件'
OUT = ROOT / 'docs/pi-104/ch01'
PUBLIC = ROOT / 'docs/public/figures/ch01'
CATALOG = ROOT / 'docs/.vitepress/theme/figures/book-01.json'
REPORT = ROOT / 'sources/reports/chapter-01.md'
NAV = ROOT / 'sources/reports/navigation-01.json'
SECTIONS = [('what-pi-is-for', 'Pi 的用途', 7), ('monorepo', '一页看懂 monorepo', 11), ('prompt-lifecycle', '一个提示的生命周期', 15)]
IMAGE_MAP = {'image.png': '1.1', 'image 1.png': '1.2', 'image 3.png': '1.3', 'image 2.png': '1.4', 'image 4.png': '1.5'}
TABLE_CAPTION = '<p class="table-caption" data-figure="1.6">FIG. 1.6 · 一个回答完成的提示，逐事件查看 · 原书第 20 页</p>'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def node(id, x, y, w, h, label, tone='blue', detail=None, **extra):
    return dict(id=id, x=x, y=y, w=w, h=h, label=label, detail=detail or label.replace('\n', ' · '), tone=tone, **extra)


def label(id, x, y, w, h, text, **extra):
    return node(id, x, y, w, h, text, 'gray', shape='label', **extra)


def figure(id, title, source, page, width, height, caption, nodes=None, edges=None, **extra):
    filename = next(name for name, fid in IMAGE_MAP.items() if fid == id)
    return dict(id=id, title=title, label=f'FIG. {id}', source=source, page=page,
                image='/figures/ch01/' + filename.replace(' ', '-'), caption=caption,
                kind='diagram', width=width, height=height, nodes=nodes or [], edges=edges or [], **extra)


def catalog():
    # Exact source column membership, ordering, English labels and explanatory text.
    n = [label('core-heading', 18, 5, 456, 35, 'CORE · ALWAYS LOADED'),
         label('builtin-heading', 492, 5, 364, 35, 'BUILT-IN EXTENSIONS'),
         label('omitted-heading', 874, 5, 457, 35, 'LEFT TO EXTENSIONS')]
    core = [
        ('pi-ai', 'pi-ai\n10 wire APIs · 42 providers', 'plum'),
        ('loop', 'agent loop · AgentSession\nturns, queues, retries', 'amber'),
        ('tools', 'read · bash · edit · write\n+ powershell · grep · find · ls', 'green'),
        ('jsonl', 'JSONL session tree\nappend-only · compaction on by default', 'teal'),
        ('modes', 'TUI · print/JSON · RPC · SDK', 'indigo')]
    for i, (id, txt, tone) in enumerate(core):
        n.append(node(id, 18, 55 + i * 94, 456, 78, txt, tone))
    builtins = [('mcp', 'mcp\nreplaceable'), ('codemode', 'codemode\nQuickJS sandbox · replaceable'),
                ('tool-search', 'tool-search\nregistered inactive · replaceable'),
                ('llama', 'llama.cpp\nlocal model provider')]
    for i, (id, txt) in enumerate(builtins):
        n.append(node(id, 492, 55 + i * 118, 364, 103, txt, 'purple'))
    omissions = [('subagents', 'sub-agents\nexamples/extensions/subagent/'),
                 ('plan', 'plan mode\nexamples/extensions/plan-mode/'),
                 ('permissions', 'permission popups\nexamples/extensions/permission-gate.ts'),
                 ('todos', 'to-dos\nexamples/extensions/todo.ts'),
                 ('background', 'background bash\nno example · “Use tmux”')]
    for i, (id, txt) in enumerate(omissions):
        n.append(node(id, 874, 55 + i * 94, 457, 78, txt, 'rose' if id == 'background' else 'purple', hatch=id == 'background'))
    f1 = figure('1.1', 'Pi 核心、内置扩展和有意留给扩展实现的功能',
                 'Pi Technical Manual p9 · CA/src/extensions/index.ts:7 · CA/examples/extensions/ · pi.dev', 9, 1350, 525,
                 '五项未内置功能中的四项有仓库内的参考扩展；后台 bash 没有。三列保留核心、内置扩展、留给扩展实现的边界。', n,
                 notes=['原图无连接箭头；三列是分类边界，不是依赖关系。', '原始 Markdown 正文写作 lama.cpp；原书及此图写作 llama.cpp。正文按供应文本保留，未静默订正。'])
    # Pixel-space transcription of the supplied chart. These lengths are visual
    # evidence, not a scale inferred from the numeric values. Antialiased edges
    # were checked against the original PNG; heights/row spacing remain fixed.
    bars = [
        ('pi-coding-agent', 77340, 644, 133, 'rose', '48.6% of the repository'),
        ('pi-ai', 23581, 298, 169, 'blue', ''),
        ('pi-durable', 18338, 232, 205, 'gray', 'experimental'),
        ('pi-tui', 17134, 218, 242, 'blue', ''),
        ('chord', 8136, 103, 278, 'gray', ''),
        ('pi-mcp', 2907, 38, 314, 'blue', ''),
        ('pi-agent-core', 2281, 30, 350, 'blue', 'the loop'),
        ('pi-env', 1928, 25, 387, 'gray', ''),
        ('pi-server', 1800, 23, 423, 'gray', 'experimental'),
        ('pi-codemode', 1696, 21, 460, 'blue', ''),
        ('pi-evals', 1345, 17, 496, 'gray', 'private'),
        ('pi-client', 1046, 13, 532, 'gray', 'experimental'),
        ('pi-telemetry', 826, 11, 569, 'blue', ''),
        ('pi-protocol', 790, 11, 605, 'gray', 'experimental')]
    n = [label('exclusions', 33, 5, 1300, 32,
               'NON-BLANK LINES UNDER SRC/ · TESTS, .D.TS AND GENERATED CATALOGUES EXCLUDED')]
    fills = {'rose':'#ce7f94', 'blue':'#6f9cc5', 'gray':'#a8a59e'}
    for name, value, width, center_y, tone, note in bars:
        y = center_y - 65
        detail = (f'{name}：{value:,} lines' + (f' · {note}' if note else '') +
                  '。条长仅按原图转录，不能据此推导统一线性比例；精确数据以标签为准。')
        n.append(label(name+'-name', 55, y-18, 292, 36, name, align='right', detail=detail))
        n.append(node(name+'-bar', 366, y-14, width, 28, '', tone, detail=detail,
                      fill=fills[tone], stroke='none', ariaLabel=f'{name}: {value:,} lines',
                      dataValue=value, visualWidth=width))
        n.append(label(name+'-value', 366+width+10, y-18, 147, 36,
                       f'{value:,} lines', detail=detail))
        if note:
            n.append(label(name+'-note', 366+width+161, y-18,
                           196 if name == 'pi-coding-agent' else 240, 36, note, detail=detail))
    f2 = figure('1.2', '各包代码量：CLI 大于其全部依赖包的总和',
                 'Pi Technical Manual p12 · research/out/stats.txt §package-lines', 12, 1373, 580,
                 'CLI 的体量比它依赖的全部包加起来还大。蓝色：稳定版 pi 命令导入的包。灰色：仅供实验性技术栈或评测运行框架使用的包。', n,
                 notes=['图形转录说明：条形位置和长度忠实转录原图，未按标签数值重新计算。原书未给出统一比例尺；例如 77,340 与 23,581 的条长之比不等于数值之比。因此这不是重新标定的定量比例图，请以精确数值标签及前表为准。',
                        '可选择包名、条形或数值查看该包的精确行数；原始图片保留在下方供对照。'])
    n = [label('top-label', 15, 35, 95, 45, 'TOP'), label('l3-label', 15, 127, 95, 45, 'L3'),
         label('l2-label', 15, 219, 95, 45, 'L2'), label('l1-label', 15, 311, 95, 45, 'L1'),
         label('leaf-label', 15, 423, 95, 45, 'LEAF'), label('aside-label', 15, 570, 95, 45, 'ASIDE'),
         node('coding-agent', 155, 15, 864, 78, 'pi-coding-agent\n→ chord · pi-agent-core · pi-ai · pi-codemode · pi-mcp · pi-tui'),
         node('dev-only', 1038, 15, 315, 78, 'dev only\n→ pi-client · pi-protocol · pi-server', 'gray', hatch=True),
         node('env', 155, 107, 1198, 79, 'pi-env\n→ chord · pi-durable · no consumer in the repo', 'gray', hatch=True),
         node('agent-core', 155, 199, 287, 79, 'pi-agent-core\n→ pi-ai'),
         node('durable', 460, 199, 286, 79, 'pi-durable\n→ chord · pi-ai', 'gray', hatch=True),
         node('server', 764, 199, 284, 79, 'pi-server\n→ chord · pi-protocol', 'gray', hatch=True),
         node('client', 1067, 199, 286, 79, 'pi-client\n→ chord · pi-protocol', 'gray', hatch=True),
         node('ai', 155, 291, 589, 79, 'pi-ai\n→ pi-telemetry'),
         node('protocol', 763, 291, 590, 79, 'pi-protocol\n→ chord', 'gray', hatch=True),
         node('telemetry', 155, 383, 227, 125, 'pi-telemetry'),
         node('tui', 400, 383, 223, 125, 'pi-tui'),
         node('mcp', 641, 383, 226, 125, 'pi-mcp'),
         node('codemode', 885, 383, 224, 125, 'pi-codemode'),
         node('chord', 1127, 383, 226, 125, 'chord\ndeclared by the CLI ·\nimported only under\nsrc/experimental/', 'gray'),
         node('evals', 155, 523, 589, 134, 'pi-evals (private)\ndevDependencies → pi-ai · pi-coding-agent', 'gray', hatch=True),
         node('experimental', 763, 523, 590, 134, 'CA/src/experimental/\nimports pi-durable without declaring it · resolved through npm\nworkspaces', 'gray', hatch=True)]
    f3 = figure('1.3', 'monorepo 的五层依赖图',
                 'Pi Technical Manual p13 · fourteen package.json dependencies / devDependencies at 28dcce2', 13, 1370, 680,
                 '稳定版 CLI 依赖一条由三个包组成的主链：pi-coding-agent → pi-agent-core → pi-ai。逐层保留运行时依赖、仅开发依赖以及未声明导入的区别。', n,
                 notes=['原图以每个矩形内的 → 依赖列表表达边，不绘制跨层连接线；此处沿用这种布局，避免添加未声明的关系。', '灰色标明实验性、开发依赖或私有评测路径；chord 虽被 CLI 声明为运行时依赖，实际仅由 src/experimental/ 导入。'])

    # Fixed-coordinate sequence diagrams preserve direction, arrow style, lane order,
    # step order, first-write timing, and post-agent_end settlement. No invented graph.
    lanes4 = [('tui', 227, 'TUI\neditor', 'indigo'), ('session', 394, 'SESSION\nAgentSession', 'amber'),
              ('ext', 560, 'EXT\nextensions', 'purple'), ('loop', 727, 'LOOP\nAgent · runLoop', 'amber'),
              ('models', 894, 'MODELS\nModelRuntime', 'plum'), ('api', 1061, 'API\nprovider', 'plum'),
              ('jsonl', 1228, 'JSONL\nSessionManager', 'teal')]
    n = [node(id, x-72, 20, 144, 70, txt, tone, align='center') for id, x, txt, tone in lanes4]
    e = [dict(from_=id, to=id, points=[[x, 92], [x, 1260]], arrow=False, dashed=True) for id, x, _, _ in lanes4]
    e = [{('from' if k == 'from_' else k): v for k, v in edge.items()} for edge in e]
    xpos = {id: x for id, x, _, _ in lanes4}
    steps = [
        ('tui', 'session', 'prompt(text)\nonSubmit → getUserInput()', None),
        ('session', 'ext', 'input · before_agent_start\nmay handle, rewrite or add', None),
        ('session', 'loop', 'agent.prompt([system, user])', None),
        ('loop', 'session', 'agent_start · turn_start · message_end ×2', 'dotted'),
        ('session', 'jsonl', 'appendMessage ×2\nfile created: lines 1–5', None),
        ('loop', 'session', 'prepareRequest\ncontext = session projection', None),
        ('loop', 'ext', 'context\ntransformContext', None),
        ('loop', 'models', 'streamSimple(model, context)', None),
        ('models', 'api', 'provider.streamSimple\nauth resolved first', None),
        ('api', 'loop', 'AssistantMessageEvent stream', 'dashed'),
        ('loop', 'session', 'message_start · update · end', 'dotted'),
        ('session', 'jsonl', 'appendMessage(assistant)\nline 6', None)]
    for i, (a, b, txt, dash) in enumerate(steps, 1):
        y = 160 + (i-1)*94
        n.append(label(f'step-{i}', 35, y-19, 55, 38, str(i), detail=f'{a.upper()} → {b.upper()} · ' + txt.replace('\n', ' · ')))
        edge = dict(**{'from':a, 'to':b}, points=[[xpos[a], y], [xpos[b], y]], label=txt)
        if dash: edge.update(dashed=True, dash=dash)
        edge['color'] = {2:'#72548e', 3:'#8c6428', 5:'#245f67', 7:'#72548e', 8:'#835981', 9:'#835981', 10:'#835981', 12:'#245f67'}.get(i, '#232a34')
        if i == 5: edge.update(width=3, emphasis=True)
        e.append(edge)
    f4 = figure('1.4', '一个提示进入智能体循环的步骤 1–12',
                 'Pi Technical Manual p16 · CA/src/core/agent-session.ts · agent/agent-loop.ts · CA/src/core/model-runtime.ts at 28dcce2', 16, 1379, 1280,
                 '模型看到提示之前，提示已经写入磁盘。实线箭头表示调用，虚线箭头表示提供商流，点线箭头表示递交给 AgentSession 的智能体事件。', n, e)
    lanes5 = [('tui', 244, 'TUI\neditor', 'indigo'), ('session', 439, 'SESSION\nAgentSession', 'amber'),
              ('ext', 634, 'EXT\nextensions', 'purple'), ('loop', 828, 'LOOP\nAgent · runLoop', 'amber'),
              ('tools', 1023, 'TOOLS\nread · bash · …', 'green'), ('jsonl', 1218, 'JSONL\nSessionManager', 'teal')]
    n = [node(id, x-86, 20, 172, 71, txt, tone, align='center') for id, x, txt, tone in lanes5]
    e = [dict(**{'from':id, 'to':id}, points=[[x, 93], [x, 1080]], arrow=False, dashed=True) for id, x, _, _ in lanes5]
    xpos = {id: x for id, x, _, _ in lanes5}
    steps = [
        (13, 'loop', 'session', 'tool_execution_start', 'dotted'),
        (14, 'loop', 'ext', 'tool_call\nbeforeToolCall · may block', None),
        (15, 'loop', 'tools', 'execute(args)\nparallel by default', None),
        (16, 'loop', 'ext', 'tool_result\nafterToolCall · may rewrite', None),
        (17, 'loop', 'session', 'tool_execution_end · message_end', 'dotted'),
        (18, 'session', 'jsonl', 'appendMessage(toolResult)\nline 7', None),
        (19, 'loop', 'loop', 'turn_end · next turn\nsteps 6–12 again: line 8', None),
        (20, 'loop', 'session', 'agent_end\na turn with no tool calls', 'dotted'),
        (21, 'session', 'session', 'retry? compact? queued?\nthen agent_before_settle', None),
        (22, 'session', 'tui', 'agent_settled\nprompt() resolves', None)]
    for offset, (num, a, b, txt, dash) in enumerate(steps):
        y = 162 + offset * 94
        n.append(label(f'step-{num}', 35, y-19, 55, 38, str(num), detail=f'{a.upper()} → {b.upper()} · ' + txt.replace('\n', ' · ')))
        edge = dict(**{'from':a, 'to':b}, points=[[xpos[a], y], [xpos[b], y]], label=txt)
        if a == b:
            edge['points'] = [[xpos[a], y-16], [xpos[a]+48, y-16], [xpos[a]+48, y+14], [xpos[a], y+14]]
            del edge['label']
            n.append(label(f'note-{num}', xpos[a]+63, y-35, 325, 70, txt))
        if dash: edge.update(dashed=True, dash=dash)
        edge['color'] = {14:'#72548e', 15:'#456932', 16:'#72548e', 18:'#245f67', 19:'#8c6428', 21:'#8c6428', 22:'#485d96'}.get(num, '#232a34')
        if num == 22: edge.update(width=3, emphasis=True)
        e.append(edge)
    f5 = figure('1.5', '一个提示的工具执行与收束步骤 13–22',
                 'Pi Technical Manual p18 · agent/agent-loop.ts · CA/src/core/agent-session.ts:640 at 28dcce2', 18, 1382, 1100,
                 '一次运行在 agent_settled 时结束，而不是 agent_end。tool_call 与 tool_result 从调用 beforeToolCall / afterToolCall 的 LOOP 泳道指向 EXT；步骤 19 和 21 保留自调用回环。', n, e)
    return [f1, f2, f3, f4, f5]


def split_sections(s):
    parts, lines, fenced = [], [], False
    for line in s.splitlines():
        if re.match(r'^\s*```', line):
            fenced = not fenced
        if not fenced and line.startswith('# ') and line != '# 1\\.模型':
            if lines: parts.append('\n'.join(lines))
            lines = [line]
        elif lines:
            lines.append(line)
    if lines: parts.append('\n'.join(lines))
    assert not fenced, 'Unclosed source code fence'
    assert len(parts) == len(SECTIONS), 'Unexpected section count'
    return parts


def repair_formatting(part):
    # Remove paired strong close/open export artifacts; only outside code fences.
    fixed, fenced = [], False
    for line in part.splitlines():
        if line.startswith('```'):
            fenced = not fenced
            fixed.append({'```TypeScript':'```ts', '```JSON':'```json'}.get(line, line))
            continue
        if not fenced:
            line = line.replace('****', '')
            chunks = re.split(r'(`[^`]*`)', line)
            opened = False
            for i in range(0, len(chunks), 2):
                bits = chunks[i].split('**')
                new = bits[0]
                for bit in bits[1:]:
                    new += ('</strong>' if opened else '<strong>') + bit
                    opened = not opened
                chunks[i] = new
            assert not opened, f'Unbalanced source bold: {line}'
            # Escaping only table-cell code pipes leaves ordinary prose/code unchanged.
            if line.startswith('|'):
                for i in range(1, len(chunks), 2):
                    chunks[i] = re.sub(r'(?<!\\)\|', r'\\|', chunks[i])
            line = ''.join(chunks)
        fixed.append(line)
    return '\n'.join(fixed)


def transform(part, i):
    part = repair_formatting(part)
    def image_ref(m):
        filename = unquote(m[1]).split('/')[-1]
        return f'<BookFigure id="{IMAGE_MAP[filename]}" />'
    part = re.sub(r'!\[[^\]]*\]\(([^)]+)\)', image_ref, part)
    if i == 2:
        target = '|<strong>序号</strong>|<strong>毫秒</strong>|<strong>事件</strong>|<strong>详情</strong>|<strong>磁盘上的状态</strong>|<strong>步骤</strong>|'
        assert part.count(target) == 1
        part = part.replace(target, TABLE_CAPTION + '\n\n' + target)
    slug, title, page = SECTIONS[i]
    assert part.splitlines()[0] == '# ' + title
    part = part.replace('# ' + title, f'<div class="section-kicker">1.{i+1} / MODEL</div>\n\n# {title}', 1)
    return f'---\ntitle: {title}\n---\n\n' + part.strip() + '\n'


def canonical(s):
    s = re.sub(r'^---\ntitle: [^\n]+\n---\n', '', s, flags=re.M)
    s = re.sub(r'<div class="section-kicker">.*?</div>', '', s)
    s = s.replace(TABLE_CAPTION, '')
    s = re.sub(r'^# 1\\\.模型\s*', '', s)
    s = re.sub(r'!\[[^\]]*\]\(([^)]+)\)', lambda m: f'[figure:{IMAGE_MAP[unquote(m[1]).split("/")[-1]]}]', s)
    s = re.sub(r'<BookFigure id="([^"]+)" />', r'[figure:\1]', s)
    s = s.replace('****', '').replace('**', '').replace('<strong>', '').replace('</strong>', '')
    s = s.replace('```TypeScript', '```ts').replace('```JSON', '```json').replace('\\|', '|')
    return re.sub(r'\s+', '', s)


def code_bodies(s):
    result, current, fenced = [], [], False
    for line in s.splitlines():
        if line.startswith('```'):
            if fenced:
                result.append('\n'.join(current)); current = []
            fenced = not fenced
        elif fenced:
            current.append(line)
    assert not fenced
    return result


def table_shapes(s):
    result, current = [], []
    for line in s.splitlines() + ['']:
        if line.startswith('|'):
            line = re.sub(r'`[^`]*`', lambda m: m[0].replace('|', '\ue001'), line)
            current.append(len(re.split(r'(?<!\\)\|', line)) - 2)
        elif current:
            assert len(set(current)) == 1, current
            result.append((len(current)-2, current[0])); current = []
    return result


def validation(source, generated, figs, source_bytes):
    # Regression: H1-looking text within a fence must not become a reading page.
    probe = source.replace('```TypeScript\n', '```TypeScript\n# fenced heading sentinel\n', 1)
    assert len(split_sections(probe)) == len(SECTIONS), 'Heading split entered code fence'
    combined = '\n'.join(generated)
    assert canonical(source) == canonical(combined), 'Normalized full-text mismatch'
    assert code_bodies(source) == code_bodies(combined), 'Code body changed'
    assert table_shapes(source) == table_shapes(combined), 'Table data or column structure changed'
    assert set(re.findall(r'<BookFigure id="([^"]+)"', combined)) == set(IMAGE_MAP.values())
    assert len(re.findall(r'<BookFigure id=', combined)) == 5
    assert SOURCE.read_bytes() == source_bytes, 'Source mutation'
    for f in figs:
        ids = [n['id'] for n in f['nodes']]
        assert len(set(ids)) == len(ids)
        for n in f['nodes']:
            assert n['x'] >= 0 and n['y'] >= 0 and n['x'] + n['w'] <= f['width'] and n['y'] + n['h'] <= f['height'], (f['id'], n)
        for edge in f['edges']:
            assert edge['from'] in ids and edge['to'] in ids, (f['id'], edge)
            for x, y in edge.get('points', []):
                assert 0 <= x <= f['width'] and 0 <= y <= f['height']
    chart_bars = [n for n in figs[1]['nodes'] if n['id'].endswith('-bar')]
    assert len(chart_bars) == 14
    assert [n['dataValue'] for n in chart_bars] == [77340,23581,18338,17134,8136,2907,2281,1928,1800,1696,1345,1046,826,790]
    assert [n['w'] for n in chart_bars] == [644,298,232,218,103,38,30,25,23,21,17,13,11,11]
    assert all(n['x'] == 366 and n['h'] == 28 and n['ariaLabel'] for n in chart_bars)
    assert len(figs[3]['edges']) == 7 + 12
    assert len(figs[4]['edges']) == 6 + 10
    assert [e['dash'] for e in figs[3]['edges'] if e.get('dash')] == ['dotted', 'dashed', 'dotted']
    assert len([e for e in figs[4]['edges'] if e['from'] == e['to'] and e.get('arrow') is not False]) == 2
    return dict(normalized_chars=len(canonical(source)), code_blocks=len(code_bodies(source)),
                code_lines=sum(len(s.splitlines()) for s in code_bodies(source)),
                tables=table_shapes(source), source_sha256=sha(source_bytes))


def report(metrics, source, figs):
    table_rows = '\n'.join(f'| {name} | {sha((IMAGES / name).read_bytes())} |' for name in IMAGE_MAP)
    nav_rows = '\n'.join(f'| 1.{i+1} {title} | {page} | /pi-104/ch01/{slug} |' for i,(slug,title,page) in enumerate(SECTIONS))
    table_shapes_text = ', '.join(f'{rows} data rows × {cols} columns' for rows, cols in metrics['tables'])
    return f'''# Chapter 1 import evidence

## Result and scope
- Three complete reading pages; five native interactive figures; five immutable source PNGs copied verbatim for comparison. FIG.1.2 transcribes original drawn bar lengths without inventing a common numeric scale.
- Restored the missing FIG. 1.6 caption on the existing event table. This is a table in PDF p20, not a sixth missing image.
- Sources: `sources/full/1.模型/1.模型.md` and its five PNG attachments. PDF authority: Pi Technical Manual, printed/PDF pages 7–22. No claims based on executing the book's commands or fetching repository code.
- Import/validation: `python scripts/import_01.py` and `python scripts/import_01.py --check`.

| Reading page | Original first page | Route |
| --- | --- | --- |
{nav_rows}

## Coverage checks (passed)
- Normalized full text: {metrics['normalized_chars']:,} non-whitespace characters, exactly equal in source order after removing only documented formatting wrappers and the newly restored figure-table caption.
- Fenced code: {metrics['code_blocks']} blocks / {metrics['code_lines']} body lines; every code body compared byte-for-byte (line endings excluded). A regression test injects an H1-looking line inside a code fence and verifies that the section splitter still returns exactly three pages.
- Markdown tables: {len(metrics['tables'])}, preserving {table_shapes_text}; all rows and columns unchanged.
- Every source image appears exactly once and maps to its verified original figure ID.
- Source SHA-256: `{metrics['source_sha256']}`.
- Native FIG.1.2 chart checks: exactly 14 bars, each original drawn width and each stated numeric value locked independently; shared baseline x=366, 28px bar height, and meaningful bar accessible names. No formula maps values to widths.
- Native graph checks: unique node IDs; every edge resolves; nodes and explicit edge points stay within the viewBox; FIG.1.4 has 7 lifelines + 12 numbered steps; FIG.1.5 has 6 lifelines + 10 numbered steps including 2 self-loops.
- Reproducibility: --check compares every generated Markdown page, navigation JSON, figure catalog, report, and copied PNG against the in-memory regeneration without writing.

## Visual reference audit
All sixteen PDF pages 7–22 were rendered and visually inspected, including all source lists, callouts, code panels, figure/table captions, and all five supplied images at native size.

| Figure | PDF page | Supplied image | Fidelity decision |
| --- | --- | --- | --- |
| 1.1 | 9 | image.png | Native three-column classification, 14 boxes; original membership, ordering and detail retained. No invented arrows. |
| 1.2 | 12 | image 1.png | Native chart faithfully transcribes 14 original drawn bars, package/value labels, color classes and annotations. Explicit caveat: visual transcription, not recalculated quantitative scale. Original comparison retained. |
| 1.3 | 13 | image 3.png | Native five-layer dependency layout plus aside. In-box → lists preserve the original dependency encoding and dev-only/undeclared-import exceptions. |
| 1.4 | 16 | image 2.png | Native seven-lane sequence, exact 12-step arrow directions, dotted events versus dashed provider stream, and first write before model call. |
| 1.5 | 18 | image 4.png | Native six-lane sequence, exact ten steps, LOOP→EXT hooks, two self-loops, and agent_settled after agent_end. |
| 1.6 | 20 | Markdown event table | Native table; caption restored from “ONE ANSWERED PROMPT, EVENT BY EVENT”. All event groups 1–29 retained. |

### Other table/caption verification
- p7 core-surfaces table: seven data rows; its seven-surfaces caption remains verbatim in supplied Chinese.
- p11 package table: fourteen packages plus total row; all file/line counts retained, including 670 and 159,148. Exclusions and 48.6% / 1.4% caption remain.
- p20 event table: eighteen grouped rows represent all 29 events; the two turns / four writes / 5 ms caveat remains.
- p21 JSONL table: eight data rows; parent IDs, write events and caption remain.
- Existing explanatory captions, source lists and blockquotes remain in the Markdown. No callout content was rewritten.

## Precise mechanical repairs
- Removed {source.count('****')} `****` export-artifact boundaries outside fenced code; converted {source.replace('****','').count('**') // 2} balanced bold spans to explicit strong tags to avoid CommonMark CJK punctuation ambiguities. No text removed.
- Canonicalized only the two fence-language labels: TypeScript→ts and JSON→json. Body text remains exact.
- Figure image references replaced by BookFigure IDs in the same positions; source filename URLs percent-decoded for lookup, copies use hyphens for spaces.
- Source chapter-title wrapper replaced by section kickers and frontmatter; all three actual reading headings and lower headings retained. Heading splitting is fence-aware.
- A safeguard escapes bare pipes only inside inline code in Markdown table cells; this chapter requires no such pipe repair.
- Added the verified p20 caption `FIG. 1.6 · 一个回答完成的提示，逐事件查看 · 原书第 20 页` immediately before its table.

## Explicit unresolved/source discrepancies
1. The supplied prose says `lama.cpp`; PDF p7 and FIG.1.1 say `llama.cpp`. The prose is preserved as supplied, and the native figure preserves the original spelling. A visible note in FIG.1.1 discloses the discrepancy. No speculative code correction.
2. FIG.1.2: 77,340 vs 23,581 do not have proportional displayed bar lengths, and the original does not disclose a transformation. Exact numeric labels/table are authoritative; native positions and lengths transcribe the original visual with an explicit caveat, without computing a replacement scale. The original is retained for comparison.
3. The JSON example intentionally contains `"usage": {{ ... }}` and is an abbreviated excerpt, not executable JSON. Its existing explanation remains; no fabricated usage values are introduced.
4. This chapter's normalized text does not re-verify the book's source-code claims against an external repository; it faithfully preserves the supplied snapshot at commit 28dcce2.

## Immutable attachment hashes
| Source file | SHA-256 |
| --- | --- |
{table_rows}

## Static compiler check
All three generated pages were rendered through VitePress createMarkdownRenderer and compiled with @vue/compiler-sfc compileTemplate without errors. This is an isolated template check, not a global site build or browser inspection.

## Integration boundary
No shared theme/config/style changes, browser work, global build, commit, remote push or publishing were performed by this chapter importer. Parent integration owns final production rendering and accessibility checks. The native sequence renderer must honor explicit points, shape:label, arrow:false, dashed, dash:dotted, and multiline labels.
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Validate generated files without changing them')
    args = parser.parse_args()
    source_bytes = SOURCE.read_bytes()
    source = source_bytes.decode()
    parts = split_sections(source)
    pages = [transform(part, i) for i, part in enumerate(parts)]
    figs = catalog()
    metrics = validation(source, pages, figs, source_bytes)
    outputs = {OUT / f'{slug}.md': text for (slug, _, _), text in zip(SECTIONS, pages)}
    outputs[CATALOG] = json.dumps(figs, ensure_ascii=False, indent=2) + '\n'
    nav = [dict(title=title, link=f'/pi-104/ch01/{slug}', page=page, chapter='1', chapterTitle='模型') for slug, title, page in SECTIONS]
    outputs[NAV] = json.dumps(nav, ensure_ascii=False, indent=2) + '\n'
    outputs[REPORT] = report(metrics, source, figs)
    for path, content in outputs.items():
        if args.check:
            assert path.read_text() == content, f'Generated file differs: {path.relative_to(ROOT)}'
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    for filename in IMAGE_MAP:
        path = PUBLIC / filename.replace(' ', '-')
        data = (IMAGES / filename).read_bytes()
        if args.check:
            assert path.read_bytes() == data, f'Image differs: {filename}'
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    assert SOURCE.read_bytes() == source_bytes
    print(json.dumps(dict(status='checked' if args.check else 'imported', sections=len(pages), figures=len(figs), native_figures=5, **metrics), ensure_ascii=False))


if __name__ == '__main__':
    main()
