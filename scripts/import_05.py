#!/usr/bin/env python3
"""Rebuild chapter 5 without changing the immutable translated Markdown.

Text: supplied Chinese Markdown. Diagrams, captions and diagram-specific labels:
Pi Technical Manual pp. 99–142 and all twelve supplied PNGs. No network required.
Run from anywhere: python3 scripts/import_05.py
"""
from pathlib import Path
from urllib.parse import unquote
from collections import Counter
import hashlib, json, re, shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'sources/full/5 配置与扩展/5 配置与扩展.md'
OUT = ROOT / 'docs/pi-104/ch05'
FIGOUT = ROOT / 'docs/public/figures/ch05'
REPORT = ROOT / 'sources/reports/chapter-05.md'
NAV = ROOT / 'sources/reports/navigation-05.json'
DATA = ROOT / 'docs/.vitepress/theme/figures/book-05.json'
SECTIONS = [
 ('configuration-models-auth', '配置、模型与身份验证', 99),
 ('resources', '上下文文件、技能、模板、主题与包', 106),
 ('extensions-loading-api', '扩展：加载与 API', 113),
 ('extension-events-contexts', '扩展事件与上下文', 120),
 ('run-modes', '运行模式：交互式、print 与 JSON', 127),
 ('rpc-sdk', 'RPC 模式与 SDK', 133),
]
MAP = {'image 5.png':'5.1','image 2.png':'5.2','image 8.png':'5.3','image 10.png':'5.4',
       'image 1.png':'5.5','image 6.png':'5.6','image 7.png':'5.7','image 9.png':'5.8',
       'image.png':'5.9','image 4.png':'5.10','image 11.png':'5.11','image 3.png':'5.12'}
PAGES = [100,101,104,105,107,107,114,116,123,127,129,134]
TITLES = ['Pi 的文件位置','设置优先级','API 密钥解析','初始模型','DefaultResourceLoader.reload()',
          '项目是否受信任？','扩展加载顺序','/reload 热重载','被阻止的工具调用','从 argv 到运行模式','四种模式，三个标准流','一次 RPC 对话']
SOURCES = ['config.ts · auth-storage.ts:25 · session-manager.ts:592 · package-manager.ts:232 · trust-manager.ts:30',
 'settings-manager.ts:195, 225, 1023, 1100, 1176 · main.ts:594',
 'provider-composer.ts:457 · runtime-credentials.ts:24 · docs/models.md',
 'main.ts:475, 499 · sdk.ts:214 · model-resolver.ts:676, 691',
 'resource-loader.ts:509–674, 747', 'extensions/runner.ts:295 · trust-manager.ts:45 · project-trust.ts:46',
 'resource-loader.ts:573 · research/out/resources-precedence.txt (§extensions)',
 'agent-session.ts:3646–3684', 'extensions/runner.ts:1242 · agent-session.ts:646–669 · agent/agent-loop.ts:724–775',
 'CA/src/main.ts:582–986', 'CA/src/main.ts:651–655 · core/output-guard.ts · modes/print-mode.ts · modes/rpc/rpc-mode.ts',
 'research/out/rpc-exchange.txt · research/capture/rpc-and-sdk-exchange.mjs']
TRUST_CAPTION = '返回“未决定”的处理器会把问题传给优先级链的下一环。第一个匹配项胜出。处理器顺序就是扩展加载顺序，见 `CA/src/core/extensions/runner.ts:295`。步骤 4 使用 `findNearestTrustEntry()`，因此信任一个父文件夹就会覆盖它下面的所有文件夹，见 `CA/src/core/trust-manager.ts:45`。'
FIG7_CAPTION = '命令行指定的扩展最先加载。事件处理器、工具渲染器以及首次注册查找都遵循这个顺序。`research/out/resources-precedence.txt`（§extensions）验证了这一点，其中通过 `-e` 指定的扩展先于两个自动发现的扩展加载。'

def plain(s):
    return s.replace('****','').replace('**','').replace('`','').replace('\\.', '.').strip()

def figure_caption(src, image_name):
    if MAP[image_name] == '5.6': return plain(TRUST_CAPTION)
    if MAP[image_name] == '5.7': return plain(FIG7_CAPTION)
    marker = next(m for m in re.finditer(r'!\[[^\]]*\]\(([^)]+)\)',src) if unquote(m.group(1)).split('/')[-1] == image_name)
    after = src[marker.end():]
    # Fig. 5.1's supplied source includes a verbatim directory transcription first.
    if MAP[image_name] == '5.1': after = after[after.index('```',after.index('```')+3)+3:]
    lines=[]; started=False
    for line in after.splitlines():
        if line.startswith('> '):
            started=True
            if line[2:].strip(): lines.append(line[2:])
        elif started: break
    return plain(' '.join(lines))

def node(id,x,y,w,h,label,detail='',tone='teal',shape=None):
    a=dict(id=id,x=x,y=y,w=w,h=h,label=label,detail=detail or label.replace('\n',' '),tone=tone)
    if shape: a['shape']=shape
    return a

def edge(a,b,points=None,label=None,dashed=False,arrow=True):
    d=dict(from_=a,to=b)
    d['from']=d.pop('from_')
    if points is not None: d['points']=points
    if label: d['label']=label
    if dashed: d['dashed']=True
    if not arrow:d['arrow']=False
    return d

def chain(fig, rows, vertical=False, width=200,height=220):
    gap=42
    fig['nodes']=[];fig['edges']=[]
    for i,(label,detail,tone) in enumerate(rows):
        x=20 if vertical else 20+i*(width+gap)
        y=20+i*(height+gap) if vertical else 20
        fig['nodes'].append(node(f'n{i+1}',x,y,width,height,f'{i+1} · {label}',detail,tone))
        if i:fig['edges'].append(edge(f'n{i}',f'n{i+1}'))
    fig['width']=width+40 if vertical else len(rows)*(width+gap)-gap+40
    fig['height']=len(rows)*(height+gap)-gap+40 if vertical else height+40

def sequence(fig, participants, events, stages, height):
    # Original column order and directional message/return routes, not a card flow.
    centers={p[0]:140+i*240 for i,p in enumerate(participants)}
    fig['width']=140+(len(participants)-1)*240+140;fig['height']=height
    fig['nodes']=[node(pid,centers[pid]-100,20,200,68,label,detail,tone) for pid,label,detail,tone in participants]
    for participant in fig['nodes']: participant['align']='center'
    fig['edges']=[edge(pid,pid,[[centers[pid],88],[centers[pid],height-25]],dashed=True,arrow=False) for pid,_,_,_ in participants]
    for i,(a,b,y,text,sub,dashed,tone) in enumerate(events,1):
        xa,xb=centers[a],centers[b]
        if a==b:
            pts=[[xa,y],[xa+48,y],[xa+48,y+26],[xa,y+26]]
            x=xa+58;w=520;ly=y-8
        else:
            pts=[[xa,y],[xb,y]];w=max(abs(xb-xa)+110,450);x=(xa+xb-w)/2;ly=y-40
        fig['edges'].append(edge(a,b,pts,dashed=dashed))
        fig['edges'][-1]['color']={'rose':'#a23d5b','purple':'#76609b','green':'#6c8e70'}.get(tone,'#596471')
        if ' events:' in text: fig['edges'][-1]['dash']='dotted'
        fig['nodes'].append(node(f'event-{i}',x,ly,w,36,text,(text+'\n'+sub).strip(),tone,'label'))
        if a != b: fig['nodes'][-1]['align']='center'
        if sub:
            fig['nodes'].append(node(f'note-{i}',x,y+10 if a!=b else y+30,w,32,sub,sub,'gray','label'))
            if a != b: fig['nodes'][-1]['align']='center'
    for num,y in stages:
        fig['nodes'].append(node(f'stage-{num}',4,y-20,28,40,str(num),f'原图阶段 {num}','gray','label'))
        fig['nodes'][-1]['align']='center'


def make_figures(src):
    figs=[]
    for i in range(1,13):
        name=next(name for name,id in MAP.items() if id==f'5.{i}')
        figs.append(dict(id=f'5.{i}',title=TITLES[i-1],label=f'FIG. 5.{i}',source=SOURCES[i-1],page=PAGES[i-1],
            image='/figures/ch05/'+name,caption=figure_caption(src,name),kind='diagram',width=960,height=400,nodes=[],edges=[]))
    f=figs[0]
    f['width']=1680;f['height']=1220
    f['nodes']=[node('user-root',42,20,785,72,'~/.pi/agent/\n用户作用域 · 始终加载','用户作用域的智能体目录；下方十五项都直属此目录。','green','label')]
    user_paths=[
      ('settings','settings.json\n严格 JSON；使用文件锁','严格 JSON；使用文件锁。','gray'),
      ('keybindings','keybindings.json','按键绑定配置文件。','gray'),
      ('models','models.json\n自定义提供商与模型；允许注释','自定义提供商与模型，允许注释。','gray'),
      ('models-store','models-store.json\n动态模型目录缓存','动态目录缓存。','gray'),
      ('auth','auth.json\n凭据；创建时文件 0600、目录 0700','文件权限 0600、目录权限 0700，仅在创建时设置。','teal'),
      ('mcp','mcp.json · mcp-auth.json · mcp.log\n日志超过 5 MB 时轮转为 mcp.log.1','同级的 MCP 配置、身份验证和日志文件；日志超过 5 MB 时轮转。','gray'),
      ('trust','trust.json\n项目信任决定','保存项目信任决定。','gray'),
      ('context','AGENTS.md | CLAUDE.md\n全局上下文文件','用户作用域全局上下文文件。','gray'),
      ('system','SYSTEM.md · APPEND_SYSTEM.md\n替换或追加系统提示词','分别替换或追加系统提示词。','gray'),
      ('resources','extensions/ skills/ prompts/ themes/\n自动发现','自动发现的扩展、技能、提示词模板和主题目录。','gray'),
      ('sessions','sessions/--<cwd>--/*.jsonl\n每个工作目录各有一个目录','使用原图及 PDF 的 *.jsonl 拼写；供稿代码中的 *.json 原样保留并另作差异说明。','teal'),
      ('packages','npm/node_modules/ · git/<host>/<path>\n用户作用域包','用户作用域 npm 和 git 包路径。','gray'),
      ('temp','tmp/extensions/\n一次性 -e 安装；权限 0700','一次性命令行扩展安装目录，权限 0700。','gray'),
      ('bin','bin/\n托管的 fd 和 rg','托管搜索工具 fd 和 rg。','gray'),
      ('crashes','crashes.json · pi-debug.log','崩溃记录与调试日志。','gray'),
    ]
    for i,(id,label,detail,tone) in enumerate(user_paths):
        y=108+i*64
        f['nodes'].append(node('user-'+id,96,y,735,58,label,detail,tone,'label'))
        f['edges'].append(edge('user-root','user-'+id,[[64,92],[64,y+29],[92,y+29]],arrow=False))
    f['nodes'].append(node('user-agent-skills',42,1100,785,78,'~/.agents/skills/\nAgent Skills 标准 · 用户作用域','独立于 ~/.pi/agent 的用户作用域标准技能目录。','green','label'))
    f['nodes'].append(node('project-root',930,20,705,72,'<project>/.pi/\n仅在项目受信任时加载','项目作用域目录，下方三组资源直属此目录。','rose','label'))
    project_paths=[
      ('files','settings.json · mcp.json\nSYSTEM.md · APPEND_SYSTEM.md','项目设置、MCP 配置和替换/追加系统提示词文件。'),
      ('resources','extensions/ skills/ prompts/ themes/','项目扩展、技能、提示词模板和主题目录。'),
      ('packages','npm/ · git/\n项目作用域包','项目作用域 npm 和 git 包目录。'),
    ]
    for i,(id,label,detail) in enumerate(project_paths):
        y=108+i*122
        f['nodes'].append(node('project-'+id,986,y,650,96,label,detail,'gray','label'))
        f['edges'].append(edge('project-root','project-'+id,[[952,92],[952,y+48],[982,y+48]],arrow=False))
    f['nodes'].extend([
      node('project-agent-skills',930,540,705,105,'<project>/.agents/skills/\n从 cwd 向上直到 git 根目录 · 仅限受信任项目','项目标准技能目录。发现范围从工作目录向上直到 git 根目录；需要信任。','rose','label'),
      node('ancestor-context',930,748,705,116,'<every ancestor>/AGENTS.md | CLAUDE.md\n每一级祖先目录的上下文文件 · 无须信任','此项不属于 .pi 目录，也不受项目信任控制；因此不连接到项目目录树。','gray','label'),
    ])
    f['notes']=['按用户和项目作用域分列，保留原图每一条目录分支。树枝表示目录归属，不表示加载流程；独立的标准技能目录和祖先上下文文件不接到 .pi 树上。',
                '原图/PDF 的 sessions 路径为 *.jsonl；供稿 Markdown 代码为 *.json。原生图遵循原图，紧接其后的供稿代码原样保留。']
    f=figs[1];f['width']=1140;f['height']=385
    f['nodes']=[node('global',20,20,305,100,'~/.pi/agent/settings.json\n全局设置','用户作用域配置。','green'),
        node('project',20,135,305,100,'.pi/settings.json\n仅受信任项目；否则 {}','未经信任的项目提供空对象。','rose'),
        node('merge',395,20,330,215,'deepMergeSettings\n(global, project)\n对象递归合并\n数组和标量由项目替换\ndefaultTools 的 ±name 追加','只递归合并普通对象。defaultTools 完全由 +name / -name 组成时追加，修改继承选择。','green'),
        node('effective',795,20,325,215,'effective Settings\n生效设置','除下方四项外，项目值优先。','green'),
        node('global-only',20,275,510,90,'仅全局设置','此分支绕过合并。','green'),
        node('four-keys',605,275,515,90,'defaultProjectTrust · cacheWarming\nhttpProxy · deviceId\n始终从全局文件读取，不合并','项目文件即使填写这些键，也不会生效。','gray')]
    f['edges']=[edge('global','merge',[[325,70],[360,70],[360,126],[395,126]]),edge('project','merge',[[325,185],[360,185],[360,126],[395,126]]),edge('merge','effective'),edge('global-only','four-keys')]
    chain(figs[2],[
      ('--api-key\nRuntimeCredentials\n仅本进程','需要先确定模型。运行时凭据覆盖存储的凭据。','rose'),
      ('auth.json\n/login 或 pi auth\n持久化凭据','来自 /login 或 pi auth 的存储凭据，优先于配置密钥。','teal'),
      ('apiKey\n扩展 registerProvider\n否则 models.json','先使用扩展配置的 apiKey，否则使用 models.json。','purple'),
      ('内置解析器\n提供商环境变量\n云环境凭据','前面的来源都不适用时，使用提供商内置解析器。','gray')],width=245,height=185)
    figs[2]['notes']=['按原图从左到右，首个适用来源胜出；不是把多个密钥合并。']
    chain(figs[3],[
      ('--model / --provider\nresolveCliModel\n未知模型直接报错\nmain.ts:475','最高优先级的命令行覆盖。','purple'),
      ('scoped models\n范围内的保存默认值\n否则第一项\n恢复会话时跳过\nmain.ts:499','范围模型选择只用于非恢复启动。','purple'),
      ('session\n分支最后的 model_change\n需要已配置身份验证\nsdk.ts:214','恢复会话保留原模型。','teal'),
      ('settings default\ndefaultProvider +\ndefaultModel\n需要已配置身份验证\nmodel-resolver.ts:676','会话没有可用模型时，尝试设置中的默认模型。','green'),
      ('first available\n已知提供商的默认模型\n否则第一项\nmodel-resolver.ts:691','最低优先级的可用模型。','gray')],width=240,height=230)
    figs[3]['notes']=['首个匹配项胜出；完整模型选择分布在 buildSessionOptions、createAgentSession 和 findInitialModel 三个函数中。']
    chain(figs[4],[
      ('pre-trust pass\n用户与 CLI 扩展\n发出 project_trust\n仅当信任尚未确定','项目强制为不受信任；暂不加载内置扩展。','purple'),
      ('settings reload\n未受信任时项目设置 {}\nsettingsManager.reload()','先决定信任，再读取项目设置。','green'),
      ('packageManager.resolve()\n包、设置、约定目录\n内置扩展；按排名排序\n得到资源路径','汇集并按 resourcePrecedenceRank 排序。','green'),
      ('CLI -e sources\nresolveExtensionSources\n{ temporary: true }\n临时作用域','解析命令行指定的扩展来源。','green'),
      ('extensions\nCLI 优先，随后已解析路径\n导入；移除被替代的内置项\njiti','信任前加载的扩展被复用，不重复导入。','purple'),
      ('skills · prompts · themes\n-e 包副本 → 已解析资源\n→ --skill / --prompt-template\n/ --theme\n同名第一项胜出','保持原图的三类资源与内部优先级。','green'),
      ('context and prompt files\nAGENTS.md 链\nSYSTEM.md / APPEND_SYSTEM.md\n项目副本仅在受信任时','上下文文件本身无须信任；此处的项目信任限制适用于项目提示词副本。','green')],width=270,height=245)
    chain(figs[5],[
      ('--approve / --no-approve\n-a / -na\n仅本次运行\noverride','最高优先级，显式覆盖。','gray'),
      ('无需保护的资源\n没有任何需信任资源\n直接 trusted','hasTrustRequiringProjectResources 未找到资源。','green'),
      ('project_trust handler\n首个 yes / no 胜出\nremember: true 可保存\n扩展决定','返回 undecided 则继续沿优先级链判断；处理器顺序等于加载顺序。','purple'),
      ('trust.json\ncwd 或祖先目录的\n最近存储记录','findNearestTrustEntry：父目录的决定覆盖其子目录。','teal'),
      ('defaultProjectTrust\nalways → yes\nnever → no\nask → 继续判断\n全局设置','项目设置不能决定自己的信任状态。','green'),
      ('no UI\nprint、JSON、RPC 启动\n判为 untrusted','没有可交互界面时不能显示信任提示。','rose'),
      ('prompt\n信任 / 信任父文件夹\n仅此会话信任 / 不信任\n交给用户','仅此会话的选项不写入 trust.json。','gray')],width=250,height=230)
    figs[5]['notes']=['原图是“首个匹配项胜出”的判定阶梯。只有未决定时才沿箭头继续；不是七个必须执行的操作。']
    chain(figs[6],[
      ('-e <source>\nCLI · 临时作用域 · 也支持 builtin:','先加载命令行指定的扩展。','blue'),
      ('项目设置\n.pi/settings.json 的 extensions 条目 · rank 0','资源优先级 0。','purple'),
      ('.pi/extensions/\n仅受信任项目 · rank 1','资源优先级 1。','purple'),
      ('用户设置\n~/.pi/agent/settings.json 的 extensions 条目 · rank 2','资源优先级 2。','purple'),
      ('~/.pi/agent/extensions/\n始终加载 · rank 3','资源优先级 3。','purple'),
      ('packages\n先项目包，后用户包 · rank 4','资源优先级 4。','purple'),
      ('built-ins\nbuiltin:llama.cpp · codemode · tool-search · mcp · rank 5','保留原图中的 builtin:llama.cpp 拼写；供稿正文写作 builtin:lama.cpp，差异已记录。','gray'),
      ('内联工厂函数\nSDK extensionFactories · 最后','内联工厂函数保持原图最后一项。','gray')],vertical=True,width=800,height=86)
    figs[6]['notes']=['竖向顺序与原图一致。原图首项的 < 被裁失；按正文明确的 -e <source> 恢复完整占位符。']
    sequence(figs[7],[('user','USER','用户','gray'),('session','SESSION\nAgentSession','现有会话','amber'),('old','OLD\n旧运行器','原扩展运行时','purple'),('loader','LOADER\nresource loader','资源加载器','green'),('new','NEW\n新运行器','替换后的扩展运行时','purple')],[
      ('user','session',155,'/reload','',False,'gray'),
      ('session','old',245,'session_shutdown { reason: "reload" }','',False,'purple'),
      ('session','old',335,'invalidate()','所有旧 pi 和 ctx 从此抛出异常',False,'rose'),
      ('session','session',435,'settings reload · resetApiProviders()','',False,'gray'),
      ('session','loader',545,'reload()','缓存代次 +1；重新导入',False,'green'),
      ('session','new',645,'_buildRuntime()','携带活动工具名称和标志值',False,'purple'),
      ('session','new',745,'session_start { reason: "reload" }','',False,'purple'),
      ('session','new',835,'resources_discover { reason: "reload" }','',False,'purple')],[(1,155),(2,448),(3,645)],910)
    figs[7]['notes']=['最后两个事件仅在绑定 UI 或命令上下文时触发。原图的五条参与者生命线和八条调用路线均保留。']
    sequence(figs[8],[('loop','LOOP\nagent loop','智能体循环','amber'),('session','SESSION\nAgentSession','会话','amber'),('runner','RUNNER\nExtensionRunner','扩展运行器','purple'),('a','A\next A','扩展 A','purple'),('b','B\next B','扩展 B','purple')],[
      ('loop','loop',145,'validateToolArguments()','先进行 schema 检查',False,'gray'),
      ('loop','session',255,'beforeToolCall({ toolCall, args })','',False,'gray'),
      ('session','runner',345,'emitToolCall(event)','',False,'gray'),
      ('runner','a',435,'handler(event, ctx)','',False,'purple'),
      ('a','runner',525,'undefined','可能已经修改 event.input',True,'purple'),
      ('runner','b',625,'handler(event, ctx)','',False,'purple'),
      ('b','runner',715,'{ block: true, reason: "bash was not approved" }','',True,'rose'),
      ('runner','session',805,'result','后续处理器不会运行',True,'gray'),
      ('session','loop',895,'{ block: true, reason }','',True,'gray'),
      ('loop','loop',985,'createErrorToolResult(reason)','isError: true；跳过 execute()',False,'rose')],[(1,158),(2,435),(3,625),(4,895)],1090)
    figs[8]['notes']=['虚线表示返回值；B 的阻止结果短路后续处理器。异常分支的行为保留在原始图注中，未虚构额外调用。']
    chain(figs[9],[
      ('subcommand?\nauth · install/remove/update/list\nconfig · mcp\nmain.ts:582–618','子命令在标志解析前分发，可能提前退出。','gray'),
      ('parseArgs\n错误 → exit 1\n--version · --export\nmain.ts:620–649','解析参数并处理启动诊断、版本和导出。','green'),
      ('resolveAppMode\nrpc · json · print · interactive\nmain.ts:651','第 3 步确定模式，第 8 步才真正交接。','blue'),
      ('session manager\n--no-session · --fork · --session\n-r · -c · --session-id\nmain.ts:693','会话管理器选择使用的会话。','teal'),
      ('runtime\nservices → resource loader\n→ AgentSession\nmain.ts:863','四种模式共享运行时构建过程。','amber'),
      ('--help · --list-models\n打印并退出\nmain.ts:875–889','在扩展加载后生成帮助，以列出扩展标志。','green'),
      ('stdin · @files · theme\n管道 stdin 将 interactive\n降为 print\nmain.ts:891–906','输入处理与模式降级。','gray'),
      ('hand off\nrunRpcMode / InteractiveMode\n/ runPrintMode\nmain.ts:948–986','把同一运行时交给所选模式。','blue')],width=250,height=220)
    f=figs[10];f['width']=1280;f['height']=715
    rows=[('INTERACTIVE · InteractiveMode',['原始按键进入编辑器','TUI 帧','仅启动错误；警告显示在 TUI','TUI 对话框\nhasUI true']),
          ('PRINT · runPrintMode({ mode: "text" })',['管道文本，前置到首条提示词','最后一条助手消息的文本块','诊断；错误或中止 → exit 1','no-op\nhasUI false']),
          ('JSON · runPrintMode({ mode: "json" })',['管道文本，前置到首条提示词','会话头，随后每个事件一行','诊断信息','no-op\nhasUI false']),
          ('RPC · runRpcMode',['JSONL 命令与 UI 响应','响应、事件、UI 请求','诊断信息','转交客户端\nhasUI true'])]
    for r,(title,cells) in enumerate(rows):
        y=15+r*175
        f['nodes'].append(node(f'row-{r}',20,y,1240,36,title,title,'gray','label'))
        for c,(heading,tone,text) in enumerate(zip(['stdin','stdout','stderr','ctx.ui'],['gray','blue','rose','purple'],cells)):
            f['nodes'].append(node(f'cell-{r}-{c}',20+c*315,y+47,295,115,heading+'\n'+text,f'{title}：{heading}。{text}',tone))
    f['notes']=['四行对应四种模式，四列对应 stdin、stdout、stderr、ctx.ui。保留原图全部 16 个比较单元格，无流程箭头。print 和 JSON 的无 UI 行为以 no-op / hasUI false 明示。']
    sequence(figs[11],[('client','CLIENT\ntest harness','捕获工具包扮演客户端','gray'),('rpc','RPC\nrunRpcMode','RPC 模式','blue'),('session','SESSION\nAgentSession','会话','amber'),('ext','EXT\ninline extension','内联扩展','purple')],[
      ('client','rpc',155,'prompt · id 1','',False,'gray'),
      ('rpc','session',235,'session.prompt(preflightResult)','',False,'gray'),
      ('rpc','client',315,'response · disposition started','在 agent_start 之前',True,'gray'),
      ('rpc','client',405,'16 events: agent_start → tool_execution_start','',True,'gray'),
      ('session','ext',495,'tool_call read','',False,'purple'),
      ('ext','rpc',575,'ctx.ui.confirm()','',False,'purple'),
      ('rpc','client',655,'extension_ui_request · confirm','id 是 UUID',True,'purple'),
      ('client','rpc',745,'extension_ui_response · confirmed true','',False,'purple'),
      ('rpc','ext',825,'resolve(true)','',True,'purple'),
      ('rpc','client',905,'15 events: tool_execution_end → agent_settled','',True,'gray'),
      ('client','rpc',985,'get_last_assistant_text · id 2','',False,'gray'),
      ('rpc','client',1065,'response · data.text','',True,'gray'),
      ('client','rpc',1145,'{not json','',False,'gray'),
      ('rpc','client',1225,'response · command parse · success false','',True,'rose'),
      ('client','rpc',1305,'stdin closed','',False,'gray'),
      ('rpc','session',1385,'runtime.dispose() · exit 0','',False,'gray')],[(1,155),(2,495),(3,745),(4,985),(5,1145),(6,1305)],1450)
    figs[11]['notes']=['保留原图四条生命线、六个阶段、16 条消息路线及其方向；消息数是这次捕获记录的事实，不代表每次运行固定的事件数。']
    return figs


def split_sections(src):
    result=[];lines=[];fenced=False
    for line in src.splitlines():
        if line.startswith('```'): fenced=not fenced
        if not fenced and line.startswith('# ') and line!='# 5 配置与扩展':
            if lines: result.append('\n'.join(lines))
            lines=[line]
        elif lines: lines.append(line)
    if lines:result.append('\n'.join(lines))
    assert not fenced
    assert len(result)==6
    return result

LANGS={'TypeScript':'ts','JavaScript':'js','JSON':'json','Bash':'bash','Shell':'shell','Plain Text':'text'}
IMAGE_RE=re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
pipe_repairs=[];bold_repairs=[]
def transform(part):
    result=[];in_fence=False
    for line in part.splitlines():
        if line.startswith('```'):
            if not in_fence:line='```'+LANGS.get(line[3:],line[3:])
            in_fence=not in_fence;result.append(line);continue
        if in_fence:result.append(line);continue
        line=IMAGE_RE.sub(lambda m:f'<BookFigure id="{MAP[unquote(m.group(1)).split("/")[-1]]}" />',line)
        old=line
        line=line.replace('****','')
        if old!=line:bold_repairs.append(old)
        chunks=re.split(r'(`+[^`]*`+)',line)
        if line.startswith('|'):
            for ci in range(1,len(chunks),2):
                repaired=re.sub(r'(?<!\\)\|',r'\\|',chunks[ci])
                if repaired!=chunks[ci]:pipe_repairs.append(chunks[ci])
                chunks[ci]=repaired
        opened=False
        for ci in range(0,len(chunks),2):
            bits=chunks[ci].split('**');joined=bits[0]
            for bit in bits[1:]:
                joined+=('</strong>' if opened else '<strong>')+bit;opened=not opened
            chunks[ci]=joined
        assert not opened,('Unbalanced emphasis',line)
        result.append(''.join(chunks))
    assert not in_fence
    return '\n'.join(result)


def code_blocks(s):
    blocks=[];buf=[];inside=False
    for line in s.splitlines():
        if line.startswith('```'):
            if inside:blocks.append('\n'.join(buf));buf=[]
            inside=not inside
        elif inside:buf.append(line)
    assert not inside
    return blocks

def norm_line(s):
    s=IMAGE_RE.sub(lambda m:'FIGURE:'+MAP[unquote(m.group(1)).split('/')[-1]],s)
    s=re.sub(r'<BookFigure id="([^"]+)"\s*/>','FIGURE:'+r'\1',s)
    s=s.replace('<strong>','').replace('</strong>','').replace('**','').replace('\\|','|')
    if s.startswith('```'):s='```'
    s=re.sub(r'^> ?', '', s)
    return s.strip()

def normalized_lines(s):
    return [norm_line(line) for line in s.splitlines() if line.strip() and not line.startswith('<div class="section-kicker">')]

def sha(text):return hashlib.sha256(text.encode()).hexdigest()

def main():
    src=SOURCE.read_text();source_sha=sha(src)
    sections=split_sections(src)
    assert sections[1].count(TRUST_CAPTION)==1
    # PDF p.107 proves this paragraph is Fig.5.6's caption, not Fig.5.5's preface.
    sections[1]=sections[1].replace(TRUST_CAPTION,'',1)
    marker='![image\\.png](图片和附件/image%206.png)'
    assert marker in sections[1]
    sections[1]=sections[1].replace(marker,marker+'\n\n'+TRUST_CAPTION,1)
    # PDF p.141: this title belongs to the later JSDoc discrepancy, not the defaults-table caption.
    misplaced_title='> **文档 ≠ 代码**'
    assert sections[5].count(misplaced_title)==1
    sections[5]=sections[5].replace(misplaced_title+'\n> \n','',1)
    sdk_discrepancy=next(line for line in sections[5].splitlines() if line.startswith('`createAgentSession` 的 JSDoc'))
    sections[5]=sections[5].replace(sdk_discrepancy,misplaced_title+'\n> \n> '+sdk_discrepancy,1)
    for path in (OUT,FIGOUT,REPORT.parent,DATA.parent):path.mkdir(parents=True,exist_ok=True)
    nav=[];exported=[];coverage=[]
    for i,((slug,title,page),part) in enumerate(zip(SECTIONS,sections),1):
        assert part.splitlines()[0]=='# '+title
        text=transform(part)
        text=text.replace('# '+title,f'<div class="section-kicker">5.{i} / CONFIGURATION & EXTENSIONS</div>\n\n# {title}',1)
        (OUT/(slug+'.md')).write_text('---\ntitle: '+title+'\n---\n\n'+text.strip()+'\n')
        exported.append(text)
        nav.append(dict(title=title,link='/pi-104/ch05/'+slug,page=page,chapter='5',chapterTitle='配置与扩展'))
        before=Counter(normalized_lines(part));after=Counter(normalized_lines(text))
        assert before==after,(title,before-after,after-before)
        assert code_blocks(part)==code_blocks(text),f'Code changed in {title}'
        coverage.append((title,len(normalized_lines(part)),len(code_blocks(part)),len(re.findall(r'^\|',part,re.M)),len(IMAGE_RE.findall(part))))
    figures=make_figures(src)
    for fig in figures:
        ids={n['id'] for n in fig['nodes']}
        assert len(ids)==len(fig['nodes'])
        for n in fig['nodes']:
            assert 0<=n['x'] and 0<=n['y'] and n['x']+n['w']<=fig['width'] and n['y']+n['h']<=fig['height'], (fig['id'],n['id'])
        for e in fig['edges']:
            assert e['from'] in ids and e['to'] in ids
            for x,y in e.get('points',[]):assert 0<=x<=fig['width'] and 0<=y<=fig['height']
    for text in exported:
        columns=None;fenced=False
        for line in text.splitlines():
            if line.startswith('```'):fenced=not fenced
            if fenced:continue
            if line.startswith('|'):
                count=len(re.split(r'(?<!\\)\|',line))-2
                if columns is None:columns=count
                assert count==columns, ('Table column mismatch',line)
            elif line.strip():columns=None
    for old,id in MAP.items():shutil.copy2(SOURCE.parent/'图片和附件'/old,FIGOUT/old)
    DATA.write_text(json.dumps(figures,ensure_ascii=False,indent=2)+'\n')
    NAV.write_text(json.dumps(nav,ensure_ascii=False,indent=2)+'\n')
    # Global line-multiset check accounts only for the verified caption relocation.
    source_body='\n'.join(split_sections(src));out_body='\n'.join(exported)
    assert Counter(normalized_lines(source_body))==Counter(normalized_lines(out_body))
    assert code_blocks(source_body)==code_blocks(out_body)
    assert sha(SOURCE.read_text())==source_sha
    report='''# Chapter 5 import and source review

## Authority and inspection

- Text authority: `sources/full/5 配置与扩展/5 配置与扩展.md` (unchanged).
- Figure/caption/layout authority: original Pi Technical Manual, physical PDF pages 99–142 (printed pages agree).
- All 44 PDF pages visually inspected in page contact sheets; figure-bearing pages and their extracted text checked in detail. All twelve supplied images inspected individually at readable resolution.
- Rebuild: `python3 scripts/import_05.py`. This script writes only the six chapter pages, twelve copied chapter images, chapter figure JSON, chapter navigation manifest, and this report.
- Source SHA-256: `SOURCEHASH`

## Coverage

Six top-level sections preserved in order. The initial `# 5 配置与扩展` becomes the chapter navigation label; no prose is omitted. All source headings inside fenced code remain code. Markdown emphasis is rendered with strong tags to avoid CJK punctuation ambiguity; this changes markup only.

| Page | Normalized nonempty lines | Exact code blocks | Raw table rows | Original figures |
|---|---:|---:|---:|---:|
'''.replace('SOURCEHASH',source_sha)
    for title,lines,code,rows,imgs in coverage:report+=f'| {title} | {lines} | {code} | {rows} | {imgs} |\n'
    report+=f'''
- Normalized nonempty source-line multiset coverage: **100%** ({sum(x[1] for x in coverage)} lines). The normalization removes presentation-only strong markers, normalizes fenced-language labels, maps original image references to their BookFigure IDs, and unescapes table-only inline-code pipes, and ignores blockquote presentation markers.
- Fenced code: **{len(code_blocks(source_body))}/{len(code_blocks(source_body))} blocks byte-identical internally**, in original order; SHA-256 over concatenated code interiors: `{sha(chr(10).join(code_blocks(source_body)))}`.
- Table rows: **{sum(x[3] for x in coverage)}/{sum(x[3] for x in coverage)}** preserved; raw tables retained for central styling.
- Figures: **12/12** original references and **12/12** original PNGs retained; 12 faithful native coordinate-based diagrams, including the full directory tree.
- Inline-code pipe repairs: {len(pipe_repairs)} affected inline-code spans; pipe characters remain visible content rather than creating accidental table cells.
- Malformed adjacent strong delimiters: {len(bold_repairs)} lines repaired without text edits.
- All assertions run on every rebuild. Source bytes were rehashed after output and remained unchanged.

## Figure inventory

| Figure | PDF page | Supplied image | Representation |
|---|---:|---|---|
'''
    for f in figures:
        report+=f'| {f["id"]} | {f["page"]} | {f["image"].split("/")[-1]} | {"Native directory tree + complete source transcription" if f["id"]=="5.1" else "Coordinate-based diagram"} |\n'
    report+='''
### Geometry and semantic fidelity

- 5.1 is a native label-only directory tree with all 15 user-directory child rows, all three project-directory child groups, both independent Agent Skills roots, and the independent ancestor-context row. User/project scope columns use parent–child tree branches without arrowheads; no flow is invented. Every original permission, trust condition and side note is retained. The supplied code transcription stays below, and the high-resolution original remains available for comparison.
- 5.2 retains two merging inputs plus the separate global-only bypass and all four global-only keys.
- 5.3/5.4/5.6 preserve the original first-match ladders, each original choice and its exception conditions. The notes distinguish precedence from mandatory sequential execution.
- 5.5/5.7/5.10 preserve original horizontal/vertical direction, all original steps, and their internal ordering.
- 5.8, 5.9 and 5.12 preserve participant columns, dashed lifelines, directed calls, dashed returns, self-calls and stage numbers. Explicit edge coordinates remain independent of node bounds.
- 5.11 retains all four modes × four stream/UI columns (16 comparison cells), including no-op/hasUI false and print exit behavior. It contains no invented flow arrows.
- Every original image remains available to the shared component for comparison.

## Verified repairs

1. **Trust caption moved, wording unchanged.** In supplied Markdown, the paragraph starting “返回‘未决定’的处理器…” occurs before Fig.5.5. PDF p.107 places the equivalent paragraph immediately below Fig.5.6, referring to the trust ladder. The importer moves the exact paragraph immediately below Fig.5.6. Apart from the independently verified callout-heading move below, all other source body order remains unchanged. The following prompt-text quotation stays in place.
2. **Figure 5.7 placeholder restored.** The supplied PNG/PDF visually drops the opening `<` in the first `-e <source>` item. The explicit numbered Chinese source list confirms the complete spelling. The redraw uses `-e <source>`.
3. **Figure headings/captions recovered as metadata.** Figure IDs/titles are embedded in the original images and absent from Markdown figure alt text. All 12 IDs and titles are mapped against PDF pages; Chinese captions remain in the body as requested and are additionally available to the shared figure component.
4. **Inline-code table pipes escaped.** For example, `echo "..." | pi` stays one table cell instead of splitting the invocation and mode columns. All similar cases are repaired mechanically without altering displayed text.
5. **SDK table-caption/callout association repaired.** PDF p.141 shows the paragraph beginning “如果没有传入 sessionManager” as the defaults-table caption, without a DOC ≠ CODE heading. The supplied heading is moved, unchanged, to the later paragraph beginning “createAgentSession 的 JSDoc”, which is the actual DOC ≠ CODE callout in the PDF. The table caption stays in place and remains verbatim.
6. **Adjacent strong markers normalized.** The directory trust-resource sentence and RPC table's data-column heading contain `****` artifacts. Their visible text is preserved.

## Ambiguities retained rather than silently rewritten

- **Fig.5.1 sessions extension:** original image and PDF p.100 show `sessions/--<cwd>--/*.jsonl`; supplied Chinese Bash directory block says `*.json`. Markdown is the code authority, so its exact code is retained. Original image remains correct to the PDF. This is a documented discrepancy, not a claim both spellings are equivalent.
- **Fig.5.7 builtin spelling:** original image/PDF p.114 use `builtin:llama.cpp`; supplied Markdown prose/table/list use `builtin:lama.cpp`. The redraw follows the original figure, while body and code preserve the supplied text. No source version was invented.
- **Fig.5.10 source-line annotations:** the graphic uses positions such as runtime `main.ts:863`, whereas the accompanying prose discusses factory execution at `main.ts:730`. Both are preserved in their respective authorities; a graphic location label is not silently replaced with a prose citation.
- The full extension example appears before its introductory prose in supplied Markdown, while PDF p.113 places it later. This is not a caption association error, so the Markdown's body order is retained.
- Source spelling/casing such as `jsonL.ts` / `attachJsonLLineReader` is not corrected inside supplied code or prose. This import is not a code-version reconciliation.

## Validation boundary

Local source import and structural assertions completed. VitePress Markdown parsing and Vue template compilation of all six pages reported zero errors. The 21 tables parse as 200 header/data rows plus 21 delimiter rows, with consistent column counts. All figure nodes and explicit edge points fit their canvases, and all edge endpoints resolve. Two consecutive importer runs produced identical page, figure-data and navigation hashes. Global site build, browser review, deployment, remote pushes, shared table/callout styling and shared component rendering belong to the parent task and were not run here.
'''
    REPORT.write_text(report)
    print(f'Chapter 5 imported: 6 pages, 12 figures, {len(code_blocks(source_body))} unchanged code blocks, {sum(x[3] for x in coverage)} table rows. Coverage 100%.')

if __name__=='__main__':main()
