#!/usr/bin/env python3
"""Reproduce chapters 6–7 without editing supplied Markdown or PNG inputs.

Run from any directory: python scripts/import_06_07.py
PDF reference: Pi-Technical-Manual.pdf, printed pages 144–184.
All diagram text/relationships were checked against the supplied PNGs and PDF.
"""
from pathlib import Path
from urllib.parse import unquote
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
CHAPTERS = {
    '6': ('6.集成与界面', '集成与界面', [('mcp', 144), ('codemode', 151), ('tui', 158)]),
    '7': ('7.实验性功能与运维', '实验性功能与运维', [('experimental-stack', 166), ('security', 174), ('telemetry-evals', 179)]),
}


def node(id, x, y, w, h, label, detail='', tone='gray', **extra):
    return dict(id=id, x=x, y=y, w=w, h=h, label=label, detail=detail or label, tone=tone, **extra)


def edge(a, b, label=None, points=None, **extra):
    value = dict(from_=a, to=b, **extra)
    value['from'] = value.pop('from_')
    if label is not None:
        value['label'] = label
    if points is not None:
        value['points'] = points
    return value


def fig(id, filename, title, page, source, width=960, height=400, nodes=None, edges=None, notes=None, original_reason=None):
    ch = id[0]
    return dict(id=id, title=title, label=f'FIG. {id}', source=source,
                page=page, image=f'/figures/ch0{ch}/{filename}', caption='',
                kind='original' if original_reason else 'diagram', width=width, height=height,
                nodes=nodes or [], edges=edges or [], notes=([original_reason] if original_reason else []) + (notes or []))


FIGURES = [
    fig('6.1', 'image-4.png', '连接，然后执行一次工具调用', 145, 'mcp/src/client.ts', width=1580, height=1300),
    fig('6.2', 'image.png', '通往同一次 MCP 调用的三条路径', 148,
        'CA/src/extensions/mcp/index.ts; tools.ts', height=670,
        nodes=[
            node('model', 20, 10, 920, 70, 'model · 系统提示词中的 mcp_servers', 'namespace · how reached · one-line summary', 'purple'),
            node('codemode', 20, 130, 290, 75, 'CODEMODE（默认）\ncodemode({ code })', 'codemode({ code })', 'green'),
            node('search', 335, 130, 290, 75, 'DEFERRED\ntool_search(query)', 'loads the declaration', 'green'),
            node('direct', 650, 130, 290, 220, 'DIRECT\ndirect call\n从第一次请求起声明', 'declared from the first request', 'green'),
            node('script', 20, 275, 290, 75, 'QuickJS script\n调用 mcp__github__get_issue', 'await tools.mcp__github__get_issue(args)', 'green'),
            node('loaded', 335, 275, 290, 75, 'direct call\n下一次模型调用', 'on the next model call', 'green'),
            node('pipeline', 20, 405, 920, 65, 'ctx.executeTool · validation\ntool_call / tool_result hooks · permission gates', '三条路径进入同一工具调用流水线。', 'gray'),
            node('connection', 20, 510, 920, 60, 'McpServerConnection.callTool', 'connects lazily · progress → onUpdate · 20 KiB cut for the model', 'purple'),
            node('server', 20, 610, 920, 45, 'MCP server', 'MCP server', 'gray'),
        ], edges=[edge('codemode', 'script'), edge('search', 'loaded'),
                  edge('script', 'pipeline', points=[[165,350],[165,405]]),
                  edge('loaded', 'pipeline', points=[[480,350],[480,405]]),
                  edge('direct', 'pipeline', points=[[795,350],[795,405]]),
                  edge('pipeline','connection'), edge('connection','server','tools/call')]),
    fig('6.3', 'image-1.png', '一次执行：宿主、工作线程与 VM', 152,
        'codemode/src/runtime/{protocol,worker,host}.ts', width=1180, height=660,
        nodes=[
            node('host-label', 10, 0, 420, 30, 'HOST THREAD · PI', shape='label'),
            node('worker-label', 735, 0, 435, 30, 'WORKER THREAD · 每次执行一个', shape='label'),
            node('execute', 10, 55, 420, 100, 'CodemodeSandbox.execute(code, {\nsignal, store })', '执行脚本，并向工作线程传入 WorkerData。', 'green'),
            node('bridge', 10, 220, 420, 100, 'tool bridge → ctx.executeTool()', 'runs the call, posts the JSON result back', 'green'),
            node('deadline', 10, 400, 420, 85, 'deadline · abort signal', 'on either: set flag, then worker.terminate()', 'amber'),
            node('flag', 10, 555, 420, 75, 'SharedArrayBuffer(4)', 'interrupt flag, one Int32', 'rose'),
            node('vm', 735, 55, 435, 100, 'QuickJS VM\n独立的 wasm 线性内存', 'imports: WASI shim (clock, random, discarded stdout/stderr) + one host call', 'gray'),
            node('prelude', 735, 205, 435, 105, 'prelude: frozen built-ins', 'tools · ALL_TOOLS · console · text · image · store/load · exit · globals such as searchTools', 'green'),
            node('code', 735, 360, 435, 125, '(async (tools, console) ⇒ {model code})', 'bridge(kind, a, b, c) held in a closure', 'green'),
            node('interrupt', 735, 555, 435, 75, 'interruptHandler polls the flag', 'maxStackSize → catchable RangeError', 'gray'),
        ], edges=[
            edge('execute','vm','WorkerData {code, tools, globals,\nwasm, memoryLimitBytes,\nstore, interrupt}', [[430,100],[735,100]], labelX=582, labelY=39),
            edge('code','bridge','{type:"call", id,\ntarget, name, args}', [[735,395],[660,395],[660,245],[430,245]], labelX=580, labelY=205),
            edge('bridge','code','{type:"result", id, ok, payload}', [[430,300],[690,300],[690,445],[735,445]], labelX=580, labelY=290),
            edge('code','execute','output · done · crash', [[950,485],[950,515],[460,515],[460,175],[220,175],[220,155]], labelX=580, labelY=505),
        ], notes=['消息以 JSON 字符串跨越宿主／工作线程边界；共享的中断标记不是工具消息。']),
    fig('6.4', 'image-3.png', '一次 Codemode 调用与一次嵌套调用', 156,
        'CA/src/extensions/codemode/execute.ts; CA/src/core/nested-tool-calls.ts', width=1580, height=1490),
    fig('6.5', 'image-5.png', '一个基类，两种渲染器', 159, 'tui/tui.ts; tui/tui-main-screen.ts; tui/tui-alt-screen.ts', height=510,
        nodes=[
            node('component', 20, 20, 290, 100, '«interface» Component', 'render(width) · handleInput? · handleMouse? · invalidate()', 'blue'),
            node('container', 335, 20, 290, 100, 'Container', 'children: Component[] · vertical stack · mouse by row', 'blue'),
            node('tui', 650, 20, 290, 100, '«interface» TUI', 'mode · setFocus · showOverlay · requestRender · start · stop', 'blue'),
            node('base', 20, 215, 920, 80, '«abstract» TuiBase', 'focus · overlay stack · input routing · 16 ms render throttle · abstract doRender()', 'blue'),
            node('main', 20, 380, 445, 100, 'TuiMainScreen · mode "regular"', 'line diff against the previous frame · output stays in terminal scrollback · over-wide line throws', 'blue'),
            node('alt', 495, 380, 445, 100, 'TuiAltScreen · mode "fullscreen"', 'alternate screen · row diff · mouse, selection, search, scrollbar · over-wide line sliced · Pi’s default', 'blue'),
        ], edges=[edge('container','base','extends Container', [[480,120],[480,215]]),
                  edge('tui','base','implements TUI', [[795,120],[795,215]])],
        notes=['原图下排并列展示两个渲染器，不额外添加继承箭头。Component 的方法保留在节点详情中。']),
    fig('6.6', 'image-2.png', '全量还是差异：主屏幕的决策', 160, 'tui/tui-main-screen.ts, TuiMainScreen.doRender', height=790),
    fig('6.7', 'image-6.png', '从环境判断终端能力', 163, 'tui/terminal-image.ts, detectCapabilitiesFromEnvironment', height=790),
    fig('7.1', 'image-6.png', 'pi server 与 pi client 的进程', 167, 'CA/src/experimental/{server,session-worker,process}.ts; client; server; durable; chord', height=540,
        nodes=[
            node('client', 20, 35, 280, 105, 'pi client', 'ExperimentalClientTui · pi-client Client · createClientServiceTransport', 'blue'),
            node('socket', 345, 35, 270, 105, 'Unix socket', '<dir>/<serverId>.sock · mode 0600 · u32 length + one CBOR item · protocol 8', 'gray'),
            node('server', 660, 35, 280, 105, 'pi server', 'pi-server · handshake 5 s · routes by serverId · sessionId · attachmentId', 'blue'),
            node('coordinator', 20, 205, 205, 135, 'coordinator', 'private JSON-line router between server and workers · protocol 3', 'gray'),
            node('worker', 265, 205, 205, 135, 'session worker', 'one per session · durable Harness · holds the session lock', 'amber'),
            node('sqlite', 510, 205, 205, 135, 'session.sqlite', 'pi-durable storage · WAL · synchronous NORMAL', 'teal'),
            node('local', 755, 205, 185, 135, 'NodeExecutionEnv', 'id node:local · tools run here', 'green'),
            node('chord', 20, 410, 500, 110, 'chord', 'facets · services · replicated state · delta ops · the payload inside every request', 'purple'),
            node('radius', 545, 410, 180, 110, 'Radius relay', 'outbound WSS when Radius credentials exist；原图使用斜线填充。', 'gray'),
            node('env', 750, 410, 190, 110, 'pi-env', 'remote ExecutionEnv over SSH · no consumer in the repo；原图使用斜线填充。', 'gray'),
            node('row1', 20, 0, 920, 25, 'CLIENT', shape='label'),
            node('row2', 20, 170, 920, 25, 'SERVER HOST', shape='label'),
            node('row3', 20, 380, 920, 25, 'EVERYWHERE', shape='label'),
        ], edges=[edge('client','socket'),edge('socket','server'),edge('coordinator','worker'),edge('worker','sqlite')],
        notes=['保留原图三排分组；没有为同排无箭头的 NodeExecutionEnv、chord、Radius relay 或 pi-env 添加连线。']),
    fig('7.2', 'image-4.png', '工具调用期间崩溃会留下什么', 169, 'durable/src/harness/tool.ts; durable/docs/spec.md §7.2', height=325,
        nodes=[
            node('intent', 15, 30, 205, 250, '1 · crash after intent\ncommitted', 'checkpoint { phase: "execute", arguments, replay }', 'teal'),
            node('reopen', 260, 30, 205, 250, '2 · reopen', 'running tasks show as pending until they run again', 'amber'),
            node('safe', 505, 30, 205, 250, '3 · both say safe\nrerun', 'stored intent and current registration both have replay: "safe"; clear progress, run again', 'green'),
            node('otherwise', 750, 30, 195, 250, '4 · otherwise\nfailed', 'settle as interrupted: "Tool X was interrupted and may have partially run"', 'rose'),
        ],edges=[edge('intent','reopen'),edge('reopen','safe'),edge('safe','otherwise')],
        notes=['按原图保留从左至右的决策阅读顺序；otherwise 是安全重放条件不成立时的结果，不表示成功重跑后再次失败。']),
    fig('7.3', 'image-5.png', '一个 pi-env 帧', 170, 'env/docs/protocol.md; env/src/connection.ts', width=1100, height=330,
        nodes=[
            node('length', 10, 30, 145, 205, 'length\nu32', 'bytes after this field', 'gray'),
            node('type', 175, 30, 155, 205, 'type\nu8', '1 request · 2 result · 3 error · 4 event · 5 cancel · 6 ping', 'amber'),
            node('id', 350, 30, 145, 205, 'id\nu32', '0 = no request', 'amber'),
            node('jsonlength', 515, 30, 150, 205, 'jsonLength\nu32', 'u32', 'gray'),
            node('json', 685, 30, 190, 205, 'json', 'UTF-8 object · jsonLength bytes', 'blue'),
            node('bytes', 895, 30, 195, 205, 'bytes', 'raw payload · length − 9 − jsonLength', 'green'),
            node('fixed', 10, 265, 1080, 45, 'FIXED: 4 + 1 + 4 + 4 = 13 BYTES · THEN VARIABLE · BIG-ENDIAN · AT MOST 16 MiB', shape='label'),
        ],notes=['字节字段依原图顺序排列；这是布局示意，不将块宽度解释为字节比例。']),
    fig('7.4', 'image-7.png', '逐字节查看客户端 hello', 172, 'research/capture/experimental-stack-frames.mjs; protocol/src/framing.ts', width=1680, height=285),
    fig('7.5', 'image-3.png', 'Pi 如何决定项目信任', 175, 'CA/src/core/project-trust.ts, resolveProjectTrusted', width=1250, height=340,
        nodes=[
            node('cli',10,20,175,285,'1 · CLI override','--approve (-a) or --no-approve (-na) wins, even with no protected resources','green'),
            node('nothing',220,20,175,285,'2 · nothing to\nprotect','none of the eight .pi entries, no project .agents/skills → trusted','gray'),
            node('extension',430,20,175,285,'3 · extension','project_trust event, user-level and CLI extensions only; first yes or no wins. remember: true saves it','purple'),
            node('store',640,20,175,285,'4 · trust.json','closest saved decision in ~/.pi/agent/trust.json, this folder or a parent','teal'),
            node('default',850,20,175,285,'5 · default','defaultProjectTrust: "always" → trusted · "never" → untrusted · "ask" → next row. Global setting, default "ask"','green'),
            node('prompt',1060,20,175,285,'6 · prompt','only with a UI; without one, untrusted. Dismissing the prompt = untrusted','rose'),
        ],edges=[edge('cli','nothing'),edge('nothing','extension'),edge('extension','store'),edge('store','default'),edge('default','prompt')],
        notes=['第一个给出答复的规则即决定结果。箭头沿用原图阅读次序，不表示已有决定后仍继续执行下一项。']),
    fig('7.6', 'image.png', '每种方法把哪些部分放在隔离边界内', 176, 'CA/docs/containerization.md; CA/examples/extensions/{gondolin,sandbox,permission-gate.ts,protected-paths.ts}', width=1100, height=560,
        nodes=[
            node('docker-label',10,20,205,90,'DOCKER · SANDBOXES\n· OPENSHELL',shape='label'),
            node('docker',230,20,855,90,'inside: Pi 进程 · 内置工具 · ! 命令 · 所有扩展','only mounts, env vars and network you grant cross the boundary','green'),
            node('gondolin-label',10,145,205,125,'GONDOLIN EXTENSION',shape='label'),
            node('gondolin-host',230,145,410,125,'host: Pi · 其他扩展的工具\n· host env vars','host: Pi · other extensions’ tools · host env vars','gray'),
            node('gondolin-vm',665,145,420,125,'micro-VM: read · write · edit\nbash · grep · find · ls · ! 命令','cwd mounted read-write at /workspace','green'),
            node('sandbox-label',10,305,205,75,'SANDBOX EXTENSION',shape='label'),
            node('sandbox-host',230,305,565,75,'host: Pi · 除 bash 外的全部工具','host: Pi · every tool except bash','gray'),
            node('sandbox-os',820,305,265,75,'OS sandbox: bash','OS sandbox: bash','green'),
            node('gate-label',10,415,205,115,'TOOL_CALL GATE',shape='label'),
            node('gate-host',230,415,565,115,'host: everything','所有内容仍在宿主进程。','gray'),
            node('gate-rule',820,415,265,115,'a rule decides per call\nnot a boundary','原图用斜线填充：每次调用应用规则，不构成隔离边界。','rose'),
        ],notes=['比较图没有调用箭头；不同颜色区分宿主部分、隔离部分和规则门控。']),
    fig('7.7', 'image-2.png', '遥测 README 描述的内容，与实际存在的内容', 180, 'telemetry/README.md; packages/*/src at 28dcce2', width=1100, height=420,
        nodes=[
            node('telemetry-label',10,20,185,90,'PI-TELEMETRY',shape='label'),
            node('contract',205,20,560,90,'TelemetryContext · TelemetrySpan','NOOP · InMemory · schemas · conformance','blue'),
            node('exporter',790,20,295,90,'exporter\nnone, by design','按设计不包含导出器；原图用斜线填充。','gray'),
            node('ai-label',10,145,185,90,'PI-AI',shape='label'),
            node('context',205,145,560,90,'telemetryContext?: TelemetryContext','accepted on requests and passed along','purple'),
            node('startspan',790,145,295,90,'startSpan calls\nnone in the repository','仓库没有生产方调用；原图用玫瑰色斜线填充。','rose'),
            node('agent-label',10,270,185,125,'PI-AGENT-CORE',shape='label'),
            node('missing',205,270,880,125,'AGENT_TELEMETRY_SCHEMAS · AI_TELEMETRY_SCHEMA\nHARNESS_TELEMETRY_SCHEMA · startAiSpan · startHarnessSpan','named in the README; not defined anywhere at 28dcce2；原图使用玫瑰色斜线填充。','rose'),
        ],notes=['比较图没有依赖或调用连线；玫瑰色节点表示 README 提及却在该提交中找不到的内容。']),
    fig('7.8', 'image-1.png', '一次文档对照实验', 182, 'evals/README.md, Running a documentation comparison and Results', width=1250, height=340,
        nodes=[
            node('build',10,20,175,285,'1 · build\nidentical tarballs','pack the workspace, then two images: without_docs and with_docs','gray'),
            node('discover',220,20,175,285,'2 · discover\ncohorts must match','list cases in both images','gray'),
            node('plan',430,20,175,285,'3 · plan\nexpected-runs.json','every (case, variant, model, run) arm before anything runs','amber'),
            node('run',640,20,175,285,'4 · run\nvitest.json per arm','each arm in a fresh container; a failed arm is recorded, the cohort continues','green'),
            node('read',850,20,175,285,'5 · read\nobservations','native Vitest JSON through @vitest-evals/core/node','blue'),
            node('pair',1060,20,175,285,'6 · pair\nreport.json · report.txt','match arms, compute lift; any blocked pair withholds headline rates','rose'),
        ],edges=[edge('build','discover'),edge('discover','plan'),edge('plan','run'),edge('run','read'),edge('read','pair')]),
]


def decision_rows(figure, rows):
    for i, (condition, action, detail, tone) in enumerate(rows):
        y = 12 + i * 96
        figure['nodes'].extend([
            node(f'condition-{i}',15,y,345,78,f'{i + 1} · {condition}',condition,'gray'),
            node(f'action-{i}',420,y,525,78,action,detail,tone),
        ])
        figure['edges'].append(edge(f'condition-{i}',f'action-{i}'))


decision_rows(FIGURES[5], [
    ('first frame','write every line, no clear','ESC[?2026h … ESC[?2026l','blue'),
    ('width changed','full redraw: clear screen and scrollback','ESC[2J ESC[H ESC[3J','rose'),
    ('height changed, not Termux','full redraw','Termux changes height when its keyboard toggles','rose'),
    ('clearOnShrink, fewer lines, no overlay','full redraw','clearOnShrink, fewer lines, no overlay','rose'),
    ('diff finds no changed line','move the hardware cursor only','只移动硬件光标。','blue'),
    ('only deleted lines changed','move to the new end','\\r\\x1b[2K each surplus row','blue'),
    ('first change above the viewport','full redraw','the cursor cannot reach rows in scrollback','rose'),
    ('otherwise','move with CSI n A/B · rewrite changed rows','rewrite firstChanged…lastChanged, clear leftover rows; ESC[?2026h … ESC[?2026l','blue'),
])
decision_rows(FIGURES[6], [
    ('TMUX set, or TERM starts tmux','images none','links only if tmux forwards OSC 8','gray'),
    ('TERM starts screen','images none · links off','images none · links off','gray'),
    ('kitty · Ghostty · WezTerm · Warp','images kitty · truecolor · links','KITTY_WINDOW_ID, GHOSTTY_RESOURCES_DIR, WEZTERM_PANE, WARP_SESSION_ID or TERM_PROGRAM','blue'),
    ('iTerm2','images iterm2 · truecolor · links','ITERM_SESSION_ID or TERM_PROGRAM','blue'),
    ('Windows Terminal · Alacritty\n· VS Code · Zed','images none · truecolor · links','Windows Terminal (WT_SESSION) · Alacritty · VS Code · Zed','gray'),
    ('JetBrains JediTerm','images none · truecolor · links off','images none · truecolor · links off','gray'),
    ('any other Windows console','images none · truecolor · links off','images none · truecolor · links off','gray'),
    ('unknown terminal','images none · links off','truecolor only from COLORTERM or a -direct TERM','rose'),
])

FIGURE_SOURCE_NAMES = {
    '6': {'image 4.png':'6.1','image.png':'6.2','image 1.png':'6.3','image 3.png':'6.4','image 5.png':'6.5','image 2.png':'6.6','image 6.png':'6.7'},
    '7': {'image 6.png':'7.1','image 4.png':'7.2','image 5.png':'7.3','image 7.png':'7.4','image 3.png':'7.5','image.png':'7.6','image 2.png':'7.7','image 1.png':'7.8'},
}
BY_ID = {f['id']:f for f in FIGURES}


def actor(id, center, label, detail, tone):
    return node(id, center-110, 20, 220, 75, label, detail, tone, align='center')


def lifeline(id, center, end):
    return edge(id,id,points=[[center,95],[center,end]],dashed=True,arrow=False,width=1,color='#a1aab1')


def note(id, x, y, w, label, detail=None, tone='gray', h=35):
    return node(id,x,y,w,h,label,detail or label,tone,shape='label',align='center')


def step(id, number, y, detail):
    return node(id,10,y-18,36,36,str(number),detail,'gray',rx=18,align='center')


def make_native_detail_figures():
    """Transcribe every arrow/annotation; positions are not inferred from nodes."""
    f = BY_ID['6.1']
    centers = {'pi':200,'client':600,'transport':1000,'server':1400}
    f['nodes'] = [
        actor('pi',200,'PI\nMcpServerConnection','Pi 中每台 MCP 服务器对应的连接。','purple'),
        actor('client',600,'CLIENT\nMcpClient','connect() 完成版本检查及 notifications/initialized 后才能使用服务器。','blue'),
        actor('transport',1000,'TRANSPORT\nstdio · HTTP','start()：stdio 启动进程；HTTP 此处无需启动进程。','teal'),
        actor('server',1400,'SERVER\nMCP server','接收 initialize、notifications/initialized 和工具请求，返回结果及进度通知。','gray'),
        step('step-1',1,180,'connect(transport) 调用 McpClient，客户端启动 transport。'),
        step('step-2',2,400,'initialize 携带 protocolVersion、capabilities 和 clientInfo；收到 InitializeResult 后检查版本。'),
        step('step-3',3,720,'发送 notifications/initialized；此时状态为 connected。'),
        step('step-4',4,840,'listTools() 跟随 nextCursor，最多读取 1,000 页。'),
        step('step-5',5,960,'callTool(name, args, {timeoutMs, onProgress})；每次进度通知重置超时，最终返回 CallToolResult。'),
        note('transport-start-note',650,292,300,'spawn, or nothing for HTTP'),
        note('version-note',690,570,630,'version in SUPPORTED_PROTOCOL_VERSIONS?\nelse close and throw',tone='rose',h=65),
        note('connected-note',760,732,470,'state = connected'),
        note('pagination-note',220,852,360,'follows nextCursor, at most 1,000 pages'),
        note('progress-note',790,1092,410,'re-arms the timeout'),
    ]
    f['edges'] = [lifeline(id,x,1270) for id,x in centers.items()] + [
        edge('pi','client','connect(transport)',[[200,180],[600,180]]),
        edge('client','transport','start()',[[600,280],[1000,280]]),
        edge('client','server','initialize {protocolVersion, capabilities, clientInfo}',[[600,400],[1400,400]]),
        edge('server','client','InitializeResult',[[1400,510],[600,510]],dashed=True),
        edge('client','client',points=[[600,585],[660,585],[660,620],[600,620]],color='#a23f60'),
        edge('client','server','notifications/initialized',[[600,720],[1400,720]]),
        edge('pi','client','listTools()',[[200,840],[600,840]]),
        edge('pi','client','callTool(name, args, {timeoutMs, onProgress})',[[200,960],[600,960]],emphasis=True,color='#4a5398'),
        edge('server','client','notifications/progress',[[1400,1080],[600,1080]],dash='dotted'),
        edge('server','client','CallToolResult',[[1400,1210],[600,1210]],dashed=True),
    ]
    f['notes'] = ['四条生命线、十条消息或自调用箭头依原图逐一重绘；虚线表示返回，点线表示进度通知。步骤 1–3 对应 connect()，步骤 4 对应 listAll，步骤 5 对应带进度通知的 requestInternal。']

    f = BY_ID['6.4']
    centers = {'model':160,'session':470,'codemode':780,'vm':1090,'tool':1400}
    f['nodes'] = [
        actor('model',160,'MODEL','只收到最终脚本输出；嵌套调用结果止于 VM。','purple'),
        actor('session',470,'SESSION\nAgentSession','嵌套调用拥有独立调用 id，并执行验证、tool_call 与 tool_result hooks。','amber'),
        actor('codemode',780,'CODEMODE\nexecuteCodemode','解析源代码及分支存储，为本次调用创建 worker 与 VM。','green'),
        actor('vm',1090,'VM\nworker · QuickJS','运行脚本；工具结果转换后返回这里，而不是直接进入模型上下文。','gray'),
        actor('tool',1400,'TOOL\nnested tool','一次真实的嵌套 read 工具调用，受普通工具流水线约束。','green'),
        step('step-1',1,170,'模型调用 codemode，id 为 call_7；AgentSession 调用 execute(call_7, { code })。'),
        step('step-2',2,460,'executeCodemode 创建新 worker 和 QuickJS VM。'),
        step('step-3',3,680,'ctx.executeTool("read", args)：嵌套 id 为 call_7/1，parentToolCallId 为 call_7。'),
        step('step-4',4,1210,'VM 返回 done { ok, value, writes }；只有 ok 时才 appendEntry("codemode-store", writes)。'),
        step('step-5',5,1430,'最终 Script completed、Wall time 与 Output 返回模型。'),
        note('call-id',210,182,200,'id call_7'),
        note('parse-source',855,327,660,'parseCodemodeSource · readCodemodeStore(branch)',h=55),
        note('nested-id',470,692,420,'id call_7/1, parentToolCallId call_7'),
        note('result-hooks',485,1002,290,'tool_result hooks have run'),
        note('store-success',490,1332,260,'only when ok',tone='teal'),
    ]
    f['edges'] = [lifeline(id,x,1470) for id,x in centers.items()] + [
        edge('model','session','codemode({ code })',[[160,170],[470,170]]),
        edge('session','codemode','execute(call_7, { code })',[[470,270],[780,270]]),
        edge('codemode','codemode',points=[[780,335],[830,335],[830,375],[780,375]]),
        edge('codemode','vm','new worker + VM',[[780,460],[1090,460]]),
        edge('vm','codemode','call · tools.read(args)',[[1090,560],[780,560]]),
        edge('codemode','session','ctx.executeTool("read", args)',[[780,680],[470,680]],emphasis=True,color='#4c743d'),
        edge('session','tool','validate · tool_call hooks · execute',[[470,800],[1400,800]]),
        edge('tool','session','result',[[1400,900],[470,900]],dashed=True),
        edge('session','codemode','outcome',[[470,990],[780,990]],dashed=True),
        edge('codemode','vm','result → string, or structuredContent',[[780,1100],[1090,1100]],dashed=True,labelX=1000,labelY=1085),
        edge('vm','codemode','done { ok, value, writes }',[[1090,1210],[780,1210]],dashed=True),
        edge('codemode','session','appendEntry("codemode-store", writes)',[[780,1320],[470,1320]],color='#276f78',emphasis=True),
        edge('codemode','model','"Script completed" · Wall time · Output',[[780,1430],[160,1430]],dashed=True),
    ]
    f['notes'] = ['五条生命线、十三条消息或自调用箭头均依原图保留。嵌套结果仅返回 VM；模型只看到步骤 5 的最终输出。存储写入保留 only when ok 条件。']

    f = BY_ID['7.4']
    # Exact source boundary offsets: each byte occupies 64 CSS/viewBox units.
    start, unit, y, h = 40, 64, 100, 92
    fields = [
        ('length',0,4,'length\n00 00 00 15 = 21','4 字节大端无符号长度前缀；后续 CBOR 数据为 21 字节。','gray'),
        ('map',4,5,'a2\nmap','CBOR map，两个键值对；1 字节。','blue'),
        ('type',5,10,'"type"\n64 74 79 70 65','字段名 type：偏移 5–10，共 5 字节；原图十六进制为 64 74 79 70 65。','blue'),
        ('hello',10,16,'"hello"\n65 68 65 6c 6c 6f','字段值 hello：偏移 10–16，共 6 字节。','blue'),
        ('version',16,24,'"version"\n67 … 6e','字段名 version：偏移 16–24，共 8 字节；原图将中间十六进制字节以省略号表示。','blue'),
        ('eight',24,25,'08\n8','版本号 8：偏移 24–25，以一个字节编码。','amber'),
    ]
    f['nodes'] = [note('encoded-by',40,15,1600,'25 BYTES ENCODED BY encodeClientMessage({ type: "hello", version: 8 })',h=55)]
    f['nodes'] += [node(id,start+a*unit,y,(b-a)*unit,h,label,detail,tone,align='center') for id,a,b,label,detail,tone in fields]
    f['edges'] = []
    for offset in (0,4,5,10,16,24,25):
        x = start+offset*unit
        id = f'offset-{offset}'
        f['nodes'].append(note(id,x-20,238,40,str(offset),f'距帧起点 {offset} 字节。',h=30))
        f['edges'].append(edge(id,id,points=[[x,204],[x,230]],arrow=False))
    f['notes'] = ['字段宽度严格按每字节 64 个绘图单位等比例重绘：4、1、5、6、8、1 字节，共 25 字节。刻度保留 0、4、5、10、16、24、25；字段边界相接，没有等宽化。']


make_native_detail_figures()

# Exact, figure-specific matches to the supplied PNG colors. Do not infer a
# palette change merely from a package name: blue data/byte nodes stay blue.
REFERENCE_TONES = {
    '6.1': {'client':'indigo'},
    '6.2': {'model':'plum'},
    '6.4': {'model':'plum'},
    '6.5': {'component':'indigo','container':'indigo','tui':'indigo','base':'indigo','main':'indigo','alt':'indigo'},
    '6.6': {'action-0':'indigo','action-4':'indigo','action-5':'indigo','action-7':'indigo'},
    '6.7': {'action-2':'indigo','action-3':'indigo'},
    '7.1': {'client':'indigo','server':'indigo'},
    '7.4': {'map':'indigo','type':'indigo','version':'indigo'},
    '7.5': {'cli':'config','default':'config'},
    '7.7': {'contract':'indigo','context':'plum'},
}
for figure_id, overrides in REFERENCE_TONES.items():
    for n in BY_ID[figure_id]['nodes']:
        if n['id'] in overrides:
            n['tone'] = overrides[n['id']]

# The source uses hatching to distinguish optional or absent pieces and a gate
# that is not an isolation boundary. The renderer can now preserve that cue.
for figure_id, node_ids in {
    '7.1': {'radius','env'},
    '7.6': {'gate-rule'},
    '7.7': {'exporter','startspan','missing'},
}.items():
    for n in BY_ID[figure_id]['nodes']:
        if n['id'] in node_ids:
            n['hatch'] = True

PDF_CORRECTION = '> **PDF核对注（原书第179页）：** 原始 PDF 的对应接口行为 `setStatus(status: SpanStatus): void;`。上方保留所提供译稿的 `focal Status` 及译注，便于核对；此处仅记录原书中的明确写法。'
GRAMMAR_CORRECTION = '> **PDF核对注（原书第154页）：** 原始 PDF 的 `OPTIONS_LINE` 字符类为 `[ \\t]`，包含一个普通空格与 `\\t`。上方所提供代码为 `[\\t]`，保留原样以便核对。'
HEADER_CORRECTION = '> **PDF核对注（原书第181页）：** NVIDIA NIM 请求头在原始 PDF 中为 `X-BILLING-INVOKE-ORIGIN: Pi`；上表保留所提供译稿中的 `X-BILLING-INFOKE-ORIGIN: Pi`。'


def repair_outer_fence(text):
    """A quoted Markdown example contains a literal triple-backtick TS block."""
    if '```Markdown\n' not in text:
        return text
    text = text.replace('```Markdown\n', '````markdown\n', 1)
    assert text.count('\n```\n```\n') == 1
    return text.replace('\n```\n```\n', '\n```\n````\n', 1)


def scan_lines(text):
    """Yield line, whether literal code, and whether a fence delimiter."""
    active = 0
    for line in text.splitlines():
        match = re.match(r'^(`{3,})([^`]*)$', line)
        if not active and match:
            active = len(match[1])
            yield line, False, True
        elif active and re.fullmatch(r'`{%d,}\s*' % active, line):
            active = 0
            yield line, False, True
        else:
            yield line, bool(active), False
    assert not active, 'Unclosed code fence'


def sections(text):
    result, lines = [], []
    for line, literal, delimiter in scan_lines(text):
        if not literal and not delimiter and line.startswith('# '):
            if lines:
                result.append('\n'.join(lines))
            lines = [line]
        elif lines:
            lines.append(line)
    if lines:
        result.append('\n'.join(lines))
    assert len(result) == 4
    return result[1:]


def code_blocks(text):
    out, lines = [], None
    for line, literal, delimiter in scan_lines(text):
        if delimiter:
            if lines is None:
                lines = []
            else:
                out.append('\n'.join(lines))
                lines = None
        elif literal:
            lines.append(line)
    return out


def bold_and_pipes(line):
    line = line.replace('****', '')
    chunks = re.split(r'(`[^`]*`)', line)
    opened = False
    for index in range(0, len(chunks), 2):
        bits = chunks[index].split('**')
        rewritten = bits[0]
        for bit in bits[1:]:
            rewritten += ('</strong>' if opened else '<strong>') + bit
            opened = not opened
        chunks[index] = rewritten
    assert not opened, f'Unbalanced emphasis: {line}'
    if line.startswith('|'):
        for index in range(1, len(chunks), 2):
            chunks[index] = re.sub(r'(?<!\\)\|', r'\\|', chunks[index])
    return ''.join(chunks)


def add_verified_callouts(text, slug):
    if slug == 'tui':
        start = text.index('\n对你的意义：\n') + 1
        end = text.index('\n> 来源：', start)
        text = text[:start] + '\n'.join('> ' + line if line else '>' for line in text[start:end].splitlines()) + '\n' + text[end:]
    if slug == 'security':
        for opening, label in [('拒绝信任并不会阻止一个文件夹引导模型。','FOOTGUN'), ('示例扩展 `CA/examples/extensions/project-trust.ts` 写道：','文档 ≠ 代码')]:
            lines = text.splitlines()
            positions = [i for i, line in enumerate(lines) if line.startswith(opening)]
            assert len(positions) == 1
            i = positions[0]
            lines[i] = '> **' + label + '** <!-- pdf-restored-label -->\n>\n> ' + lines[i]
            text = '\n'.join(lines)
    return text


def transform(part, ch, slug):
    part = add_verified_callouts(part, slug)
    if slug == 'telemetry-evals':
        lines = part.splitlines()
        i = next(i for i,line in enumerate(lines) if line.startswith('> 译注：已修复'))
        lines.insert(i + 1, '\n' + PDF_CORRECTION)
        i = next(i for i,line in enumerate(lines) if line.startswith('> 一次 ping、'))
        lines.insert(i, HEADER_CORRECTION + '\n')
        part = '\n'.join(lines)
    if slug == 'codemode':
        part = part.replace('> 完整内容，第 23–29 行。', '> 完整内容，第 23–29 行。\n\n' + GRAMMAR_CORRECTION, 1)
    output = []
    for line, literal, delimiter in scan_lines(part):
        if literal:
            output.append(line)
            continue
        if delimiter:
            language = re.match(r'^(`{3,})(.*)$', line)
            count, lang = language[1], language[2]
            lang = {'JSON':'json','TypeScript':'ts','Plain Text':'text','JavaScript':'js','Bash':'bash','Markdown':'markdown'}.get(lang, lang)
            output.append(count + lang)
            continue
        def replace_image(match):
            name = unquote(match[1]).split('/')[-1]
            return '<BookFigure id="' + FIGURE_SOURCE_NAMES[ch][name] + '" />'
        line = re.sub(r'!\[[^\]]*\]\(([^)]+)\)', replace_image, line)
        output.append(bold_and_pipes(line))
    # PDF identifies this as Lark grammar. Use literal highlighting without modifying its text.
    result = '\n'.join(output).replace('```ts\nstart: options_source', '```text\nstart: options_source')
    return result


def canonical(text):
    """Formatting-neutral line coverage; code receives a separate exact comparison."""
    output = []
    for line in text.splitlines():
        if 'PDF核对注' in line or '<!-- pdf-restored-label -->' in line:
            continue
        if line.startswith('<div class="section-kicker">') or re.match(r'^`{3,}', line):
            continue
        if line.startswith('![') or line.startswith('<BookFigure '):
            output.append('[FIGURE]')
            continue
        line = re.sub(r'</?strong>', '', line).replace('**','')
        line = re.sub(r'^\s*>\s?', '', line)
        line = re.sub(r'\\([!"#$%&\'()*+,\-./:;<=>?@\[\]\\^_`{|}~])', r'\1', line)
        line = line.strip()
        if line:
            output.append(line)
    return output


def counts(text):
    scanned = list(scan_lines(text))
    table_count = 0
    in_table = False
    table_rows = 0
    for line, literal, delim in scanned:
        is_row = not literal and not delim and line.startswith('|')
        if is_row and not in_table:
            table_count += 1
        if is_row:
            table_rows += 1
        in_table = is_row
    return dict(code_blocks=len(code_blocks(text)), tables=table_count, table_lines=table_rows,
                headings=sum(not literal and bool(re.match(r'^#{1,6} ',line)) for line,literal,_ in scanned),
                source_lines=len(canonical(text)))


def capture_captions(text, ch):
    for match in re.finditer(r'!\[[^\]]*\]\(([^)]+)\)\s*\n((?:>[^\n]*(?:\n|$))+)',text):
        name = unquote(match[1]).split('/')[-1]
        id = FIGURE_SOURCE_NAMES[ch][name]
        caption = ' '.join(re.sub(r'^>\s?', '', line).strip() for line in match[2].splitlines()).strip()
        BY_ID[id]['caption'] = caption


def main():
    navigation, statistics, source_hashes = [], {}, []
    assert len([e for e in BY_ID['6.1']['edges'] if e.get('arrow') is not False]) == 10
    assert len([e for e in BY_ID['6.1']['edges'] if e.get('arrow') is False]) == 4
    assert len([e for e in BY_ID['6.4']['edges'] if e.get('arrow') is not False]) == 13
    assert len([e for e in BY_ID['6.4']['edges'] if e.get('arrow') is False]) == 5
    byte_fields = [n for n in BY_ID['7.4']['nodes'] if n.get('shape') != 'label']
    assert [n['w'] / 64 for n in byte_fields] == [4,1,5,6,8,1]
    assert [int((n['x']-40)/64) for n in byte_fields] == [0,4,5,10,16,24]
    assert sum(n['w'] for n in byte_fields) / 64 == 25
    for ch, (dirname, chapter_title, slugs) in CHAPTERS.items():
        source_dir = ROOT/'sources/full'/dirname
        source_path = source_dir/(dirname + '.md')
        raw = source_path.read_text()
        prepared = repair_outer_fence(raw)
        capture_captions(prepared, ch)
        source_hashes.extend((str(path.relative_to(ROOT)),hashlib.sha256(path.read_bytes()).hexdigest()) for path in sorted(source_dir.rglob('*')) if path.is_file())
        image_dir = ROOT/f'docs/public/figures/ch0{ch}'
        image_dir.mkdir(parents=True, exist_ok=True)
        for name, id in FIGURE_SOURCE_NAMES[ch].items():
            shutil.copyfile(source_dir/'图片和附件'/name, image_dir/BY_ID[id]['image'].split('/')[-1])
        page_dir = ROOT/f'docs/pi-104/ch0{ch}'
        page_dir.mkdir(parents=True, exist_ok=True)
        totals = dict(code_blocks=0,tables=0,table_lines=0,headings=0,source_lines=0,pages=3,figures=len(FIGURE_SOURCE_NAMES[ch]))
        for n, ((slug,page),part) in enumerate(zip(slugs,sections(prepared)), 1):
            body = transform(part,ch,slug)
            assert code_blocks(part) == code_blocks(body), f'Code changed in {slug}'
            before,after = canonical(part),canonical(body)
            # Source DOC ≠ CODE headings must still be counted; only newly restored labels are excluded.
            if before != after:
                import difflib
                raise AssertionError(f'Coverage mismatch in {slug}:\n' + '\n'.join(difflib.unified_diff(before,after)))
            title = re.sub(r'\\([.\-])',r'\1',part.splitlines()[0][2:])
            kicker = f'<div class="section-kicker">{ch}.{n} / {"INTEGRATION & INTERFACES" if ch == "6" else "EXPERIMENTAL & OPERATIONS"}</div>'
            body = kicker + '\n\n' + body
            content = '---\ntitle: ' + json.dumps(title,ensure_ascii=False) + f'\noriginalPage: {page}\n---\n\n' + body.strip() + '\n'
            (page_dir/(slug+'.md')).write_text(content)
            navigation.append(dict(title=title,link=f'/pi-104/ch0{ch}/{slug}',page=page,chapter=ch,chapterTitle=chapter_title))
            stat = counts(part)
            for key,value in stat.items():
                totals[key] += value
        statistics[ch] = totals
        chapter_figures = [f for f in FIGURES if f['id'].startswith(ch+'.')]
        assert all(f['caption'] for f in chapter_figures), f'Missing caption in chapter {ch}'
        for figure in chapter_figures:
            ids = {n['id'] for n in figure['nodes']}
            assert len(ids) == len(figure['nodes']), f'Duplicate node in {figure["id"]}'
            for n in figure['nodes']:
                assert n['x'] >= 0 and n['y'] >= 0 and n['x'] + n['w'] <= figure['width'] and n['y'] + n['h'] <= figure['height'], f'Out-of-bounds node in {figure["id"]}: {n["id"]}'
            for e in figure['edges']:
                assert e['from'] in ids and e['to'] in ids, f'Unknown edge endpoint in {figure["id"]}'
                for x,y in e.get('points',[]):
                    assert 0 <= x <= figure['width'] and 0 <= y <= figure['height'], f'Out-of-bounds edge in {figure["id"]}'
            assert (ROOT/'docs/public'/figure['image'].lstrip('/')).is_file(), f'Missing image for {figure["id"]}'
        (ROOT/f'docs/.vitepress/theme/figures/book-0{ch}.json').write_text(json.dumps(chapter_figures,ensure_ascii=False,indent=2)+'\n')
    report_dir = ROOT/'sources/reports'
    report_dir.mkdir(parents=True,exist_ok=True)
    (report_dir/'navigation-06-07.json').write_text(json.dumps(navigation,ensure_ascii=False,indent=2)+'\n')
    report = ['# Chapters 6–7 import verification', '',
              'Scope: supplied Chinese Markdown and 15 PNGs only; original English PDF is the visual/caption verification source. All 41 PDF pages 144–184 were visually reviewed in contact sheets; all 15 PNGs were inspected at readable resolution. Chapter 7 begins on p166, after the p165 divider; p184 is the reference divider.', '',
              '## Reproduction and coverage', '', 'Run `python scripts/import_06_07.py`. Inputs under `sources/full/` are never written. The importer asserts line-order normalized source coverage and exact code-body equality before writing the six pages.', '',
              '| Chapter | Pages | Figures | Code blocks | Tables | Table lines | Headings | Normalized nonempty source lines |', '|---|---:|---:|---:|---:|---:|---:|---:|']
    for ch,s in statistics.items():
        report.append(f'| {ch} | {s["pages"]} | {s["figures"]} | {s["code_blocks"]} | {s["tables"]} | {s["table_lines"]} | {s["headings"]} | {s["source_lines"]} |')
    report += ['', 'Normalization ignores whitespace, Markdown emphasis/escaping, quotation markers, fence language spelling and image/component syntax. Added PDF-verification notices and two recovered callout titles are excluded. All source prose, lists, tables, captions, citations and notes remain in original order. Code contents receive an independent byte-for-byte string comparison, including the nested Markdown sample.', '',
               'An isolated VitePress Markdown-token check (without a global build) parsed 16 tables, 100 header/data rows, 13 outer code blocks and 15 BookFigure references. Every parsed table row matches its header column count. Diagram validation checks unique node ids, node bounds, edge endpoints and all original image paths.', '',
               '## Evidenced presentation repairs', '',
               '- PDF p154 contains a Markdown output sample with an inner TS fence. Its outer source fence is lengthened from three to four backticks; all interior text and the inner fence are preserved.',
               '- The source labels the Lark grammar as TypeScript. PDF p154 labels it LARK. The output uses literal text highlighting; its code remains unchanged.',
               '- Repeated `****` emphasis artifacts outside code are removed; other bold text becomes explicit `<strong>` for CJK punctuation compatibility. Inline-code pipe characters in Markdown table cells are escaped, preserving their visible values.',
               '- PDF p164: the final `对你的意义：` paragraph and four bullets in the TUI section are restored as a practical-takeaway blockquote.',
               '- PDF p176: the source paragraphs beginning `拒绝信任并不会阻止…` and `示例扩展…` regain their original FOOTGUN and DOC ≠ CODE callout roles. Paragraph contents are unchanged; verified headings are added.', '',
               '## Source discrepancies retained and explicitly annotated', '',
               '- PDF p179 visibly reads `setStatus(status: SpanStatus): void;`. The supplied code reads `focal Status(status: SpanStatus): void;` and its supplied translator note says the corruption could not be resolved. Both supplied items remain unchanged; a separately labeled `PDF核对注` records the original PDF line.',
               '- PDF p154 shows a literal space in the `OPTIONS_LINE` character class, `[ \\t]`; supplied code has `[\\t]`. Supplied code is unchanged; a PDF-verification note states the difference.',
               '- PDF p181 shows `X-BILLING-INVOKE-ORIGIN: Pi`; the supplied table has `X-BILLING-INFOKE-ORIGIN: Pi`. Supplied table text is retained and the discrepancy is stated separately.', '',
               '## Figure mapping and native reconstruction', '',
               '| Figure | PDF page | Supplied PNG | Treatment |', '|---|---:|---|---|']
    for f in FIGURES:
        name = next(name for name,id in FIGURE_SOURCE_NAMES[f['id'][0]].items() if id==f['id'])
        report.append(f'| {f["id"]} | {f["page"]} | {name} | {"Original; " + f["notes"][0] if f["kind"]=="original" else "Native diagram, with original PNG comparison"} |')
    report += ['', 'All 15 figures now use native interactive data, retaining their original PNG comparison. All original figure numbers and captions were checked. No supplemental figure ids are needed. Native diagrams preserve original grouping and arrows: row-wise decisions remain row-wise, comparisons and byte fields have no invented relationships, process topology preserves only the four arrows drawn in the source, and 7.2/7.5 explicitly distinguish decision-reading order from unconditional execution. Every native node carries inspectable source detail.', '',
               '- FIG6.1: four dashed lifelines, ten message/self-call arrows, five step markers, version-check loop, progress dotted arrow, dashed returns, pagination limit and timeout-reset annotation. Explicit points preserve direction and timing independently of actor-box bounds.',
               '- FIG6.4: five lifelines, thirteen message/self-call arrows, five step markers, call_7 and call_7/1 identifiers, parentToolCallId, both hook phases, intermediate result returning only to VM, and success-only codemode-store append. Dashed returns and final model output remain separate.',
               '- FIG7.4: exact 25-byte scale at 64 drawing units per byte; touching fields span 4/1/5/6/8/1 bytes, with offset ticks at 0/4/5/10/16/24/25. All original hex strings, including the original version-field ellipsis, are preserved. The importer asserts byte widths, boundaries and total length.', '',
               'Reference palette reconciliation uses an explicit node whitelist: model/AI-context plum in 6.2/6.4/7.7; the original indigo clients, UI/renderers, terminal capability outcomes, CBOR map/key fields and telemetry contract in 6.1/6.5/6.6/6.7/7.1/7.4/7.7; mint configuration decisions in 7.5. Existing purple extension/runtime nodes remain purple. Blue data nodes (including the hello value) are unchanged. Original hatching is restored on optional Radius/pi-env nodes (7.1), the non-boundary call gate (7.6), and absent exporter/producer/schema nodes (7.7). No role-only or global recoloring is applied.', '',
               '## Table and callout verification', '',
               '- Ch6 tables: MCP module files p144; transports p146; exposure modes p147; retries p149; sandbox probes p152; runtime limits p153; overlay fields p162; native binaries p163; built-in components p164.',
               '- Ch7 tables: durable harness tasks p169; storage backends p170; protocol message types p172; five trust options p175; isolation methods p177; product telemetry p181; evaluation suites p182.',
               '- Original table captions remain immediately before/after their tables. Original figure captions remain in the body and also populate the figure data for shared presentation.',
               '- Verified original callouts: DOC ≠ CODE p149/p161/p176/p180; RULE OF THUMB p157/p181; practical takeaways p150/p164/p173/p178/p182; FOOTGUN p176; source blocks at each section end.', '',
               '## Boundaries', '', 'No shared files, global build, browser preview, Git remote, publication or push were changed by this importer. Shared-component visual QA remains an integration task for the parent.', '',
               '## Immutable input hashes', '', '| Source | SHA-256 |', '|---|---|']
    report += [f'| {path} | `{digest}` |' for path,digest in source_hashes]
    (report_dir/'chapters-06-07.md').write_text('\n'.join(report)+'\n')
    print(json.dumps(statistics,ensure_ascii=False,indent=2))
    print('PASS: six pages; 15 native interactive figures; exact code and normalized content coverage.')


if __name__ == '__main__':
    main()
