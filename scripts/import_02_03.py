#!/usr/bin/env python3
"""Reproducibly import authoritative chapters 2–3 without modifying supplied sources.

PDF and all 15 images were visually inspected. Source Markdown governs prose/code;
PDF pp.24–73 verifies figure IDs, titles, relationships and callout classification.
Fenced code bodies remain byte-for-byte unchanged. No heading regex runs in fences.
"""
from pathlib import Path
from urllib.parse import unquote
import hashlib, html, json, re, shutil

ROOT = Path(__file__).resolve().parents[1]
CONFIG = {
    2: dict(folder='2.提供商层', english='THE PROVIDER LAYER', sections=[
        ('providers-models', '提供商与模型', [24,29]),
        ('streaming-events', '流式事件协议', [30,35]),
        ('wire-apis', '传输 API 与跨提供商交接', [36,40]),
        ('auth-cost-retries', '身份验证、费用、重试与模型目录', [41,47])],
        images={'image 2.png':'2.1','image 6.png':'2.2','image 3.png':'2.3','image 5.png':'2.4','image.png':'2.5','image 4.png':'2.6','image 1.png':'2.7'}),
    3: dict(folder='3.智能体循环', english='THE AGENT LOOP', sections=[
        ('agent-loop','智能体循环',[49,56]),
        ('agent-events','智能体事件与 Agent 类',[57,60]),
        ('agent-session','AgentSession：组装运行时',[61,66]),
        ('prompt-lifecycle','从 prompt() 到 agent_settled',[67,73])],
        images={'image 4.png':'3.1','image 2.png':'3.2','image 1.png':'3.3','image 5.png':'3.4','image 7.png':'3.5','image.png':'3.6','image 3.png':'3.7','image 6.png':'3.8'})
}
FIGURES = {2:[],3:[]}

def node(id, x, y, w, h, label, detail='', tone='purple'):
    return dict(id=id,x=x,y=y,w=w,h=h,label=label,detail=detail or label.replace('\n',' · '),tone=tone)

def edge(start, end, label=None, points=None, dashed=False):
    d=dict(from_=start,to=end)
    d['from']=d.pop('from_')
    if label: d['label']=label
    if points is not None: d['points']=points
    if dashed: d['dashed']=True
    return d

def figure(id, title, page, width, height, nodes, edges, notes=None):
    ch=int(id.split('.')[0]); cfg=CONFIG[ch]
    filename=next(k for k,v in cfg['images'].items() if v==id)
    f=dict(id=id,title=title,label='FIG. '+id,source=f'Pi Technical Manual · 图片和附件/{filename}',page=page,image=f'/figures/ch{ch:02d}/'+filename,caption='',kind='diagram',width=width,height=height,nodes=nodes,edges=edges)
    if notes:f['notes']=notes
    FIGURES[ch].append(f)
    return f

def flow(id,title,page,items,width=1200,height=290):
    # Original figures are horizontal ordered cards, never decision diamonds.
    gap=32; margin=20; w=(width-2*margin-gap*(len(items)-1))/len(items)
    ns=[]
    for i,(label,detail,tone) in enumerate(items):ns.append(node(f'{id}-step-{i}',margin+i*(w+gap),35,w,height-70,label,detail,tone))
    return figure(id,title,page,width,height,ns,[edge(ns[i]['id'],ns[i+1]['id']) for i in range(len(ns)-1)])

# 2.1: the six API boxes are peers, not a chain.
ns=[node('2.1-caller',25,20,1150,70,'caller\nContext {systemPrompt, messages, tools}','agent loop, SDK, extensions — passes a Context {systemPrompt, messages, tools}','gray'),
    node('2.1-models',25,160,1150,85,'Models · createModels()\nnormalizeContext → lazyStream → requireChatProvider → applyAuth → header merge','normalizeContext() → lazyStream() → requireChatProvider → applyAuth (credential store, then ambient env) → header merge'),
    node('2.1-provider',25,315,1150,75,'Provider · createProvider({ id, auth, models, api })\none runtime unit per vendor or gateway; dispatches on model.api'),
    node('2.1-vendor',25,645,1150,60,'vendor endpoint','HTTP · SSE · WebSocket','gray')]
es=[edge('2.1-caller','2.1-models','models.stream(model, context, options)'),edge('2.1-models','2.1-provider','provider.stream(requestModel, transcript, requestOptions)')]
for i,label in enumerate(['anthropic-\nmessages','openai-\ncompletions','openai-\nresponses','google-*','bedrock-\nconverse-stream','… 10 chat\nAPIs']):
    ident=f'2.1-api-{i}';x=25+i*195
    ns.append(node(ident,x,475,175,85,label,'lazyApi: import api/<api-id>.ts on first use; '+label.replace('\n','')))
    es.extend([edge('2.1-provider',ident,points=[[x+87.5,390],[x+87.5,475]]),edge(ident,'2.1-vendor',points=[[x+87.5,560],[x+87.5,645]])])
figure('2.1','PI-AI IN ONE PAGE',24,1200,730,ns,es,['Provider → APIs：lazyApi 在首次使用时导入 api/<api-id>.ts。','APIs → vendor endpoint：HTTP · SSE · WebSocket。'])

# 2.2: comparison rows retain the exact counts and sequence of source messages.
ns=[]
rows=[('TRANSCRIPT AFTER A TOOL IS ADDED MID-SESSION',[
    ('system · leading\nprompt + sections\n+ tools [read, bash]','purple'),('user','blue'),('assistant','blue'),('system · later\ntoolsAdded [grep]','purple'),('user','blue')]),
    ('supportsMidConvoSystemMessages: true — sent as stored',[
    ('system\nunchanged head:\ncache hit','purple'),('user','blue'),('assistant','blue'),('system\nUpdated system prompt\nsection … / tool addition','purple'),('user','blue')]),
    ('false (Google, most models) — collapseSystemMessages()',[
    ('system\nreplayed: prompt +\nsections + [read, bash, grep]','rose'),('user','blue'),('assistant','blue'),('user','blue')])]
for r,(title,items) in enumerate(rows):
    y=20+r*160
    ns.append(dict(node(f'2.2-heading-{r}',20,y,1160,40,title,title,'gray'),shape='label'))
    w=(1160-16*(len(items)-1))/len(items)
    for i,(label,tone) in enumerate(items):ns.append(node(f'2.2-r{r}-{i}',20+i*(w+16),y+55,w,88,label,label,tone))
figure('2.2','ONE TRANSCRIPT, TWO RENDERINGS',29,1200,495,ns,[],['三行是同一对话记录的比较，不是三段连续对话。','第一、二行各五条消息；折叠后四条，后续 system 已并入首条。'])

# 2.3: an arbitrary number of content blocks precedes exactly one terminal event.
ns=[node('2.3-setup',20,35,180,320,'setup\nauth · lazy import\nprovider lookup','lazyStream: auth, lazy import, provider lookup','gray'),
    node('2.3-start',240,35,180,320,'start\nonce\nstopReason pending'),
    node('2.3-text',465,35,385,80,'text_start → text_delta* → text_end'),
    node('2.3-thinking',465,135,385,95,'thinking_start → thinking_delta*\n→ thinking_end'),
    node('2.3-tool',465,250,385,105,'toolcall_start → toolcall_delta*\n→ toolcall_end'),
    node('2.3-done',900,35,280,145,'done\nstop · length · toolUse\n· deferred'),
    node('2.3-error',900,210,280,145,'error\nerror · aborted',tone='rose'),
    node('2.3-failed',20,425,400,90,'setup fails',tone='gray'),
    node('2.3-no-start',465,425,715,90,'error, with no start\nmissing auth · unknown provider · module load failure · empty faux queue',tone='rose')]
es=[edge('2.3-setup','2.3-start'),edge('2.3-failed','2.3-no-start')]
# Shared branch lines convey a grammar group, not a mandatory text/thinking/tool sequence.
es += [edge('2.3-start','2.3-text',points=[[420,195],[443,195],[443,75],[465,75]]),edge('2.3-start','2.3-thinking',points=[[420,195],[443,195],[443,182.5],[465,182.5]]),edge('2.3-start','2.3-tool',points=[[420,195],[443,195],[443,302.5],[465,302.5]])]
for ident,y in [('2.3-text',75),('2.3-thinking',182.5),('2.3-tool',302.5)]:
    es.extend([edge(ident,'2.3-done',points=[[850,y],[875,y],[875,107.5],[900,107.5]]),edge(ident,'2.3-error',points=[[850,y],[875,y],[875,282.5],[900,282.5]])])
figure('2.3','THE EVENT GRAMMAR',31,1200,545,ns,es,['zero or more blocks, in content order; contentIndex = position in content[]','start 之后也允许没有内容块，直接 done / error；各内容块可以按内容顺序重复。'])

# Sequence reconstruction uses explicit x/y routes. Each lane is its source participant.
def sequence(id,title,page,lanes,events,width=1200,notes=None):
    margin=30;step=(width-2*margin)/len(lanes);xs=[margin+step*(i+.5) for i in range(len(lanes))]
    ns=[node(f'{id}-lane-{i}',xs[i]-step*.43,20,step*.86,75,label,detail,tone) for i,(label,detail,tone) in enumerate(lanes)]
    height=145+75*len(events)
    es=[]
    for i,x in enumerate(xs):
        es.append(dict(edge(f'{id}-lane-{i}',f'{id}-lane-{i}',points=[[x,95],[x,height-20]],dashed=True),arrow=False,color='#b7bdbe',width=1))
        relevant=[label.replace('\n',' · ') for a,b,label,*_ in events if i in (a,b)]
        ns[i]['detail']+='。本泳道中的调用与事件（自上而下）：'+' → '.join(relevant)
    phases={'2.4':[0,4,7,10],'3.2':[0,4,7],'3.8':[0,4,6,11]}.get(id,[])
    for number,event_index in enumerate(phases,1):
        ns.append(dict(node(f'{id}-phase-{number}',0,128+event_index*75,40,38,str(number),f'原图阶段 {number}','gray'),shape='label',align='center'))
    for i,event in enumerate(events):
        a,b,label,dashed=event[:4];y=145+i*75
        points=[[xs[a],y],[xs[b],y]] if a!=b else [[xs[a],y],[xs[a]+32,y],[xs[a]+32,y+22],[xs[a],y+22]]
        event_edge=edge(f'{id}-lane-{a}',f'{id}-lane-{b}',label,points,dashed)
        event_edge['labelX']=(xs[a]+xs[b])/2 if a!=b else xs[a]+150
        event_edge['labelY']=y-12-(17 if '\n' in label else 0)
        if 'error, no start' in label:event_edge['color']='#a33d60'
        if label=='events · result()':event_edge['color']='#835981';event_edge['emphasis']=True
        if label=='agent_settled':event_edge['color']='#5666a6';event_edge['emphasis']=True
        if label.startswith('start · *_start'):event_edge['dash']='dotted'
        es.append(event_edge)
    return figure(id,title,page,width,height,ns,es,notes or ['从上到下阅读时序；虚线为原图中的事件或返回箭头，实线为调用。原始泳道关系和事件顺序保持不变。'])

sequence('2.4','ONE CALL TO MODELS.STREAM()',34,[
    ('CALLER\nagent loop','caller','amber'),('MODELS\ncreateModels()','Models','purple'),('LAZY\nlazyStream','lazyStream','purple'),('PROVIDER\ncreateProvider','createProvider','purple'),('ADAPTER\napi/<id>.ts','adapter','purple'),('VENDOR\nHTTP · SSE','vendor','gray')],[
    (0,1,'stream(model, context, options)',False),
    (1,1,'normalizeContext(context)\nContext → TranscriptContext',False),
    (1,2,'lazyStream(model, setup)',False),
    (2,0,'AssistantMessageEventStream\nreturned before any await',True),
    (2,1,'setup(): requireChatProvider · applyAuth\ngetAuth, header merge',False),
    (1,3,'provider.stream(requestModel, transcript, requestOptions)',False),
    (3,4,'streams for model.api\nlazyApi: import on first use',False),
    (4,5,'request (retryProviderRequest)',False),
    (5,4,'headers, then events',True),
    (4,2,'start · *_start/_delta/_end · done\nforwarded event by event',True),
    (2,0,'events · result()',False),
    (2,0,'error, no start\nif setup throws',True)],1280)

flow('2.5','WHAT TRANSFORMMESSAGES DOES TO HISTORY',38,[
    ('0 · images\nuser · toolResult','model has no image input → one "(image omitted: …)" text per run of images','gray'),
    ('1 · thinking\nassistant','same provider + api + model: keep, with signatures; else plain text, no tags; redacted and empty dropped','purple'),
    ('2 · signatures\nassistant','other model: textSignature and thoughtSignature removed','purple'),
    ('3 · tool-call ids\nassistant · toolResult',"other model: adapter’s normaliser; results remapped to match",'purple'),
    ('4 · failed turns\nsecond pass','stopReason error or aborted: message skipped','rose'),
    ('5 · orphans\nsecond pass','call with no result → synthetic "No result provided", isError','rose')])
FIGURES[2][-1]['notes']=['原书图注：历史记录针对目标模型重写。“同一模型”要求 provider、api、model 三者全部匹配。','原书第38页：步骤0–3逐消息进行首遍处理；步骤4–5位于第二遍，也会暂存调用与其结果之间的 system 消息，直到结果输出。']
flow('2.6',"WHERE A REQUEST’S CREDENTIAL COMES FROM",43,[
    ('1 · explicit apiKey\nfirst match wins','options.apiKey set and provider has apiKey auth → apiKey.resolve(override)','purple'),
    ('2 · stored oauth','stored type "oauth" and provider has oauth → refresh if expiring, then oauth.toAuth()','purple'),
    ('3 · stored api_key','stored type "api_key" and provider has apiKey → apiKey.resolve(stored)','purple'),
    ('4 · type mismatch\nno env fallback','something is stored, no matching handler → undefined','rose'),
    ('5 · ambient','nothing stored → apiKey.resolve() reads env vars, AWS, ADC','gray')])
flow('2.7','FROM REMOTE CATALOGS TO BUILTINMODELS()',46,[
    ('1 · fetch\nnetwork, at build','models.dev/api.json, OpenRouter /api/v1/models, Vercel AI Gateway, Radius, NVIDIA','gray'),
    ('2 · generate\n3,726 lines','scripts/generate-models.ts adds hand-kept entries, compat, thinking maps and price fixes','purple'),
    ('3 · data\nschemaVersion 6\ngitignored','src/providers/data/.json + .manifest.json','teal'),
    ('4 · wrap\n42 files, generated','.models.ts: flattenChatModelCatalog() and image, classifier twins','purple'),
    ('5 · index\ndo not edit','models.generated.ts: MODELS, IMAGE_MODELS, CLASSIFIER_MODELS','purple'),
    ('6 · register\n42 factories','providers/all.ts: builtinProviders(), builtinModels()','purple')])

# 3.1: original loop, exits and two return routes.
labels=[
 ('runAgentLoop · :102\nagent_start · turn_start · prompt messages','gray'),
 ('poll steering · :176\nuser may have typed while waiting','amber'),
 ('prepareNextTurn · :186\nre-poll steering if empty (:204) · turn_start','amber'),
 ('inject pending · :211\ndeclareToolChanges · message_start/end each','amber'),
 ('prepareRequest · :219\nmay replace context, model, thinking level','amber'),
 ('streamAssistantResponse · :242\ntransformContext → convertToLlm → streamFn','purple'),
 ('tool calls · :263\nexecute; on stopReason length, fail them all','green'),
 ('finishTurn · :286 → turn_end\ncontinue, end, or nothing','amber'),
 ('poll steering · :295\nafter every turn_end','amber'),
 ('poll follow-ups · :302\nonly when the inner loop would exit','amber')]
ns=[node(f'3.1-step-{i}',310,25+i*105,525,74,label,label,tone) for i,(label,tone) in enumerate(labels)]
ns.append(node('3.1-end',965,970,270,85,'agent_end\nreturn newMessages',tone='amber'))
es=[edge(f'3.1-step-{i}',f'3.1-step-{i+1}') for i in range(9)]
es += [edge('3.1-step-1','3.1-step-3','first turn skips it',[[835,167],[915,167],[915,377],[835,377]]),
 edge('3.1-step-5','3.1-end','stopReason error | aborted',[[835,587],[1170,587],[1170,970]]),
 edge('3.1-step-7','3.1-end','{action: "end"}',[[835,797],[1045,797],[1045,970]]),
 edge('3.1-step-8','3.1-step-2','tool results not terminated · steering',[[310,902],[195,902],[195,272],[310,272]]),
 edge('3.1-step-9','3.1-step-2','follow-ups · finishTurn continue',[[310,1007],[95,1007],[95,272],[310,272]]),
 edge('3.1-step-9','3.1-end','nothing',[[835,1007],[965,1007]])]
for e in es:
    if e.get('label')=='first turn skips it':e.update(label='first turn\nskips it',labelX=975,labelY=245)
    elif e.get('label')=='stopReason error | aborted':e.update(label='stopReason error | aborted',labelX=1025,labelY=572,color='#a33d60')
    elif e.get('label')=='{action: "end"}':e.update(labelX=935,labelY=782)
    elif e.get('label')=='tool results not terminated · steering':e.update(label='tool results\nnot terminated\n· steering',labelX=170,labelY=560,color='#94671f',emphasis=True)
    elif e.get('label')=='follow-ups · finishTurn continue':e.update(label='follow-ups\n· finishTurn continue',labelX=145,labelY=1048,color='#94671f',emphasis=True)
    elif e.get('label')=='nothing':e.update(labelX=885,labelY=995)
    elif e['from']=='3.1-step-8' and e['to']=='3.1-step-9':e.update(label='neither',labelX=650,labelY=960)
figure('3.1','RUNLOOP',51,1260,1090,ns,es,['poll steering :295 → poll follow-ups :302：neither。','首次进入跳过 prepareNextTurn；返回路径都回到 prepareNextTurn。','玫瑰色 stopReason 错误出口跳过队列；finishTurn 仍会运行，但其决定被忽略。'])

sequence('3.2','A PARALLEL BATCH OF TWO CALLS',55,[
    ('LOOP\nexecuteToolCallsParallel','loop','amber'),('PREP\nprepareToolCall','find · prepareArguments · validate · beforeToolCall','amber'),('TOOLS\nslow 40 ms · fast 5 ms','tools','green'),('LISTENERS\nsubscribers','listeners','blue')],[
    (0,3,'tool_execution_start A (slow)',True),(0,1,'prepare A',False),
    (0,3,'tool_execution_start B (fast)',True),(0,1,'prepare B',False),
    (0,2,'Promise.all(execute A, execute B)',False),
    (2,3,'tool_execution_end B\ncompletion order: fast first',True),
    (2,3,'tool_execution_end A',True),
    (0,3,'message_start/end toolResult A\nassistant source order',True),
    (0,3,'message_start/end toolResult B',True),
    (0,3,'turn_end toolResults=[A, B]',True)])

# 3.3: source event tree. Connectors show lifecycle containment, never causal calls.
events=[
(0,'agent_start','once, opening the run','amber'),
(1,'turn_start · turn 1','first turn','amber'),
(2,'message_start · message_end · system','prompt sections + toolsAdded','blue'),
(2,'message_start · message_end · user','"What does hello.txt say?"','blue'),
(2,'message_start · assistant','first assistant message','purple'),
(3,'message_update ×6','text_start · text_delta · text_end · toolcall_start · toolcall_delta · toolcall_end','purple'),
(2,'message_end · assistant','stopReason toolUse','purple'),
(2,'tool_execution_start · read','read begins','green'),
(2,'tool_execution_end · read','read completes','green'),
(2,'message_start · message_end · toolResult','tool result message','blue'),
(1,'turn_end · assistant','toolResults: [call_1]','amber'),
(1,'turn_start · turn 2','second turn','amber'),
(2,'message_start · assistant','second assistant message','purple'),
(3,'message_update ×4','text_start · text_delta ×2 · text_end','purple'),
(2,'message_end · assistant','stopReason stop','purple'),
(1,'turn_end · assistant','second turn ends','amber'),
(0,'agent_end','28 AgentEvents complete','amber'),
(0,'agent_settled','AgentSession only, after the run','blue')]
ns=[];es=[]
for i,(depth,label,detail,tone) in enumerate(events):
    ns.append(node(f'3.3-event-{i}',20+depth*64,20+i*66,980-depth*64,50,label,detail,tone))
# Match printed indentation; terminal peers are not treated as nested children.
for a,children in [(0,[1,10,11,15]),(1,[2,3,4,6,7,8,9]),(4,[5]),(11,[12,14]),(12,[13])]:
    for b in children:
        ax=ns[a]['x']+20;ay=ns[a]['y']+50;bx=ns[b]['x'];by=ns[b]['y']+25
        es.append(edge(f'3.3-event-{a}',f'3.3-event-{b}',points=[[ax,ay],[ax,by],[bx,by]]))
for e in es:e['arrow']=False
figure('3.3','ONE PROMPT, ONE TOOL CALL, 29 EVENTS',58,1020,1210,ns,es,['按原图生命周期缩进：28 个 AgentEvent，加上 AgentSession 的 agent_settled。','点选节点可查看原图侧注与 message_update 内包含的完整块事件列表。','read 没有报告部分结果，所以本例没有 tool_execution_update。'])

flow('3.4','ONE RUN OF THE AGENT CLASS',59,[
    ('1 · runWithLifecycle\n:507','activeRun set · isStreaming = true','amber'),
    ('2 · runAgentLoop\n:437','or runAgentLoopContinue','amber'),
    ('3 · processEvents\n:565','reduce state, then await each listener','blue'),
    ('4 · handleRunFailure\n:532','only if the run threw; catch emits closing events','rose'),
    ('5 · finishRun\n:550','isStreaming = false · resolve waitForIdle; finally','amber')])

pairs=[
 ('subscribe(_handleAgentEvent)\n:501','listener\npersistence · queue mirrors · extension dispatch','teal'),
 ('_installAgentToolHooks\n:640','beforeToolCall · afterToolCall\nextension tool_call; tool_result, then image resize','purple'),
 ('_installAgentNextTurnRefresh\n:886','prepareNextTurn\ncompaction · prompt patch · tool loadout · model + thinking','amber'),
 ('_installAgentRequestProjection\n:775','prepareRequest\ncontext.messages := buildSessionProjection().messages\nvirtual-model routing','teal'),
 ('_installAgentBoundaryHooks\n:874','finishTurn\nextension turn_end boundary; may ask for one more request','purple'),
 ('_installHiddenDeclarationsProjection\n:1753','transformContext, chained\nstrip tool declarations hidden by prepareLoadout hooks','purple'),
 ('_installAgentForcedPromptProjection\n:1773','transformContext, chained\nbefore_agent_start systemPrompt replaces head, unrecorded','purple')]
ns=[];es=[]
for i,(left,right,tone) in enumerate(pairs):
    y=20+i*115;ns.extend([node(f'3.5-left-{i}',20,y,540,95,left,tone='amber'),node(f'3.5-right-{i}',620,y,620,95,right,tone=tone)])
    es.append(edge(f'3.5-left-{i}',f'3.5-right-{i}'))
figure('3.5','WHAT AGENTSESSION PLUGS INTO THE AGENT',64,1260,825,ns,es,['原图共有七行：一次 subscribe，加上六个钩子安装器。','prepareRequest 从会话文件投影替换消息，是图中高亮的不变量。'])
flow('3.6','ONE EVENT THROUGH _HANDLEAGENTEVENT',65,[
    ('1 · nested calls\n:1092','toolResult start: attach nestedCalls, add their usage','green'),
    ('2 · queue mirrors\n:1106','user start: drop text from steering/follow-up lists, queue_update','amber'),
    ('3 · extensions\n:1127','awaited; message_end may replace the message','purple'),
    ('4 · listeners\n:1128','agent_end gains willRetry','blue'),
    ('5 · persist\n:1131','message_end: appendMessage or appendCustomMessageEntry','teal'),
    ('6 · flush\n:1179','turn_end: deferred custom messages','teal')])

checks=[
 ('text starts with / and matches an extension command\nrun the command handler','"handled"','amber','blue'),
 ('manual compaction in progress','throw\nCannot submit a prompt while compaction is in progress…','amber','rose'),
 ('extension input event\ncontinue · transform text and images · handled','"handled"','purple','blue'),
 ('expand /skill:name, then prompt templates','no exit','green','gray'),
 ('agent is streaming\nstreamingBehavior: steer → agent.steer; followUp → agent.followUp','"queued"\nor throw if streamingBehavior is missing','amber','blue'),
 ('flush deferred bash and custom messages','no exit','teal','gray'),
 ('model selected and auth configured','throw\nno model · no API key · OAuth expired','purple','rose'),
 ('_checkCompaction(last assistant, false)\nmay compact before the prompt is sent','no exit','teal','gray'),
 ('extension before_agent_start\nedit systemPromptOptions · inject messages · force a system prompt','no exit','purple','gray'),
 ('normalise images · build messages\n[prompt patch?, user, nextTurn messages, extension messages]','_runAgentPrompt\n"started"','blue','amber')]
ns=[];es=[]
for i,(a,b,ta,tb) in enumerate(checks):
    y=20+i*106;ns.extend([node(f'3.7-check-{i}',20,y,760,86,f'{i+1} · '+a,tone=ta),node(f'3.7-outcome-{i}',840,y,400,86,b,tone=tb)])
    es.append(edge(f'3.7-check-{i}',f'3.7-outcome-{i}'))
figure('3.7','PROMPT() BEFORE THE LOOP STARTS',68,1260,1080,ns,es,['自上而下，first match wins；no exit 行继续检查。','保留原图第7行原文“model selected and auth configured”；右侧 throw 列出相应失败状态。'])
sequence('3.8','AGENT_END IS NOT THE END',70,[
    ('SESSION\n_runAgentPrompt','session','amber'),('AGENT\nAgent · runLoop','agent','amber'),('MODEL\nprovider','model','purple'),('LISTENER\nsubscriber','listener','blue')],[
    (0,1,'agent.prompt(messages)',False),
    (1,2,'request 1',False),
    (2,1,'stopReason error, retryable',True),
    (1,3,'agent_end willRetry=true',True),
    (0,3,'auto_retry_start attempt 1 · delayMs 2000',True),
    (0,0,'context_edit hides attempt · sleep',False),
    (0,1,'agent.continue()',False),
    (1,2,'request 2',False),
    (2,1,'stopReason stop',True),
    (0,3,'auto_retry_end success=true\non the assistant message_end',True),
    (1,3,'agent_end willRetry=false',True),
    (0,3,'agent_settled',False)])

# Original PNG/PDF palette, audited per node. Never reinterpret extension purple as model plum.
SOURCE_TONE_CORRECTIONS = {
    'plum': [
        '2.1-models', '2.1-provider', *[f'2.1-api-{i}' for i in range(6)],
        '2.2-r0-0', '2.2-r0-3', '2.2-r1-0', '2.2-r1-3',
        '2.3-start', '2.3-text', '2.3-thinking', '2.3-tool', '2.3-done',
        *[f'2.4-lane-{i}' for i in range(1,5)],
        *[f'2.5-step-{i}' for i in range(1,4)],
        *[f'2.6-step-{i}' for i in range(3)],
        '2.7-step-1', '2.7-step-3', '2.7-step-4', '2.7-step-5',
        '3.1-step-5', '3.3-event-4', '3.3-event-6', '3.3-event-12', '3.3-event-14',
        '3.7-check-6', '3.8-lane-2',
    ],
    'indigo': ['3.2-lane-3', '3.3-event-17', '3.4-step-2', '3.6-step-3',
               '3.7-outcome-0', '3.7-outcome-2', '3.7-outcome-4', '3.8-lane-3'],
    'config': ['3.7-check-3'],
    'gray': ['3.3-event-5', '3.3-event-13'],
}
_all_nodes={n['id']:n for fs in FIGURES.values() for f in fs for n in f['nodes']}
for tone, ids in SOURCE_TONE_CORRECTIONS.items():
    for id in ids:
        assert id in _all_nodes, id
        _all_nodes[id]['tone']=tone

FENCE_LANGS={'TypeScript':'ts','JavaScript':'js','JSON':'json','Plain Text':'text','Shell':'sh'}
IMAGE_PATTERN=re.compile(r'!\[[^\]]*\]\(([^)]+)\)')

def split_sections(text):
    parts=[];current=[];fence=None;seen_title=False
    for line in text.splitlines():
        m=re.match(r'^\s*(`{3,}|~{3,})(.*)$',line)
        if m:
            if fence is None:fence=m[1][0]
            elif m[1][0]==fence:fence=None
        if fence is None and line.startswith('# '):
            if not seen_title:seen_title=True;continue
            if current:parts.append('\n'.join(current));current=[]
        if seen_title and (current or line.startswith('# ')):current.append(line)
    if current:parts.append('\n'.join(current))
    assert fence is None,'Unclosed source code fence'
    return parts

def plain(s):
    s=re.sub(r'<strong>(.*?)</strong>',r'\1',s)
    s=s.replace('****','').replace('**','').replace('`','')
    s=re.sub(r'\\+([.\-()\[\]{}!+_|<>*])',r'\1',s)
    return s

def normalize_line(line):
    # Repairs export-only paired strong delimiters without touching code bodies.
    line=line.replace('****','')
    pieces=re.split(r'(`+[^`]*`+)',line)
    opened=False
    for i in range(0,len(pieces),2):
        piece=pieces[i]
        piece=re.sub(r'\\+([.\-()\[\]{}!+_])',r'\1',piece)
        piece=re.sub(r'\\+\|',r'\|',piece)
        bits=piece.split('**');value=bits[0]
        for bit in bits[1:]:
            value+=('</strong>' if opened else '<strong>')+bit;opened=not opened
        pieces[i]=value
    assert not opened, 'Unbalanced strong marker: '+line
    # A pipe in a table's inline code must be escaped before markdown-it table splitting.
    if line.lstrip().startswith('|'):
        for i in range(1,len(pieces),2):pieces[i]=re.sub(r'(?<!\\)\|',r'\|',pieces[i])
    return ''.join(pieces)

FIGURE_25_CAPTION_PREFIX = '历史记录始终为目标模型重写，而不是为源模型重写。'

def figure_25_caption(text):
    matches=[line for line in text.splitlines() if line.startswith(FIGURE_25_CAPTION_PREFIX)]
    assert len(matches)==1, 'Expected exactly one authoritative Fig.2.5 caption paragraph'
    return matches[0]

def repair_figure_25_position(part, cfg):
    if FIGURE_25_CAPTION_PREFIX not in part:return part
    caption=figure_25_caption(part)
    lines=part.splitlines();lines.remove(caption)
    image_index=next(i for i,line in enumerate(lines) if (m:=IMAGE_PATTERN.search(line)) and cfg['images'].get(unquote(m[1]).split('/')[-1])=='2.5')
    # PDF p.38 puts this exact paragraph immediately below Fig.2.5.
    lines[image_index+1:image_index+1]=['', '> '+caption, '']
    intro=next(i for i,line in enumerate(lines) if line.startswith('> 图 2\\.5：'))
    # The supplied quote is a capture introduction, not the original figure caption.
    while intro<len(lines) and lines[intro].startswith('>'):
        lines[intro]=lines[intro][1:].lstrip();intro+=1
    return '\n'.join(lines)

def normalize_part(part, cfg):
    part=repair_figure_25_position(part,cfg)
    lines=[];fence=None
    for line in part.splitlines():
        m=re.match(r'^(\s*)(`{3,}|~{3,})(.*)$',line)
        if m:
            if fence is None:
                fence=m[2][0];lang=m[3].strip();line=m[1]+m[2]+FENCE_LANGS.get(lang,lang)
            elif m[2][0]==fence:fence=None
            lines.append(line);continue
        if fence is not None:lines.append(line);continue
        def replace_image(m):
            name=unquote(m[1]).split('/')[-1]
            assert name in cfg['images'],name
            return '<BookFigure id="'+cfg['images'][name]+'" />'
        line=IMAGE_PATTERN.sub(replace_image,line)
        # Technical ephemeral endpoint, not an actual navigation destination.
        line=line.replace('它在 http://localhost:0 注册模型', '它在 `http://localhost:0` 注册模型')
        lines.append(normalize_line(line))
    return '\n'.join(lines).strip()+'\n'

def code_bodies(s):
    blocks=[];current=None;fence=None
    for line in s.splitlines():
        m=re.match(r'^\s*(`{3,}|~{3,})(.*)$',line)
        if m:
            if fence is None:fence=m[1][0];current=[]
            elif m[1][0]==fence:blocks.append('\n'.join(current));current=None;fence=None
        elif current is not None:current.append(line)
    return blocks

def prose_canonical(s):
    # Independent coverage comparison removes only known presentation syntax.
    s=IMAGE_PATTERN.sub('',s)
    s=re.sub(r'^> ?', '', s, flags=re.M)
    s=re.sub(r'<BookFigure id="[^"]+" />','',s)
    s=re.sub(r'^```(?:TypeScript|JavaScript|JSON|Plain Text|Shell|ts|js|json|text|sh)?$', '```',s,flags=re.M)
    s=plain(s)
    return re.sub(r'\s+','',s)

def table_counts(s):
    rows=0;tables=0;inside=False;fence=None
    for l in s.splitlines():
        if re.match(r'^\s*(`{3,}|~{3,})',l):fence=None if fence else True;continue
        if fence:continue
        row=l.lstrip().startswith('|')
        if row and not inside:tables+=1
        if row:rows+=1
        inside=row
    return tables,rows

def extract_captions(source,cfg):
    lines=source.splitlines();out={}
    for i,line in enumerate(lines):
        m=IMAGE_PATTERN.search(line)
        if not m:continue
        id=cfg['images'][unquote(m[1]).split('/')[-1]]
        j=i+1
        while j<len(lines) and not lines[j].strip():j+=1
        caption=[]
        while j<len(lines) and lines[j].startswith('>'):
            caption.append(lines[j][1:].strip());j+=1
        out[id]=plain(' '.join(caption)).strip()
        assert out[id],f'Missing supplied caption {id}'
    return out


def main():
    report=[];nav=[];hashes={};coverage=[]
    for ch,cfg in CONFIG.items():
        source_path=ROOT/'sources/full'/cfg['folder']/(cfg['folder']+'.md')
        source=source_path.read_text();hashes[str(source_path.relative_to(ROOT))]=hashlib.sha256(source_path.read_bytes()).hexdigest()
        parts=split_sections(source);assert len(parts)==4,(ch,len(parts))
        target=ROOT/f'docs/pi-104/ch{ch:02d}';target.mkdir(parents=True,exist_ok=True)
        captions=extract_captions(source,cfg)
        stats=dict(chapter=ch,sections=4,figures=len(cfg['images']),tables=0,table_rows=0,code_blocks=0,code_lines=0,prose_code_coverage='PASS')
        for i,(part,(slug,title,pages)) in enumerate(zip(parts,cfg['sections']),1):
            converted=normalize_part(part,cfg)
            assert plain(part.splitlines()[0][2:])==title
            assert code_bodies(part)==code_bodies(converted),(ch,slug,'code body mismatch')
            before,after=prose_canonical(part),prose_canonical(converted)
            if ch==2 and slug=='wire-apis':
                moved=prose_canonical(figure_25_caption(part))
                assert before.count(moved)==after.count(moved)==1
                # Only this PDF-verified paragraph may move; every other character stays in order.
                before=before.replace(moved,'',1);after=after.replace(moved,'',1)
            assert before==after,(ch,slug,'normalized prose mismatch')
            content='---\n'+f'title: "{title}"\ndescription: "Pi 1.0.4 · {ch}.{i} · 原书第 {pages[0]}–{pages[1]} 页"\n'+'---\n\n'
            content+=f'<div class="section-kicker">{ch}.{i} / {cfg["english"]}</div>\n\n'+converted
            (target/(slug+'.md')).write_text(content)
            nav.append(dict(chapter=ch,section=f'{ch}.{i}',title=title,route=f'/pi-104/ch{ch:02d}/{slug}',pageRange=pages,source=str(source_path.relative_to(ROOT))))
            tables,rows=table_counts(part);blocks=code_bodies(part)
            stats['tables']+=tables;stats['table_rows']+=rows;stats['code_blocks']+=len(blocks);stats['code_lines']+=sum(len(b.splitlines()) for b in blocks)
        dest=ROOT/f'docs/public/figures/ch{ch:02d}';dest.mkdir(parents=True,exist_ok=True)
        for name,id in cfg['images'].items():
            src=source_path.parent/'图片和附件'/name
            shutil.copy2(src,dest/name)
            assert hashlib.sha256(src.read_bytes()).digest()==hashlib.sha256((dest/name).read_bytes()).digest()
            hashes[str(src.relative_to(ROOT))]=hashlib.sha256(src.read_bytes()).hexdigest()
        for f in FIGURES[ch]:
            f['caption']=plain(figure_25_caption(source)) if f['id']=='2.5' else re.sub(r'^图 \d+\.\d+：', '', captions[f['id']])
            ids={n['id'] for n in f['nodes']};assert len(ids)==len(f['nodes'])
            assert all(e['from'] in ids and e['to'] in ids for e in f['edges'])
            assert all(n['x']>=0 and n['y']>=0 and n['x']+n['w']<=f['width'] and n['y']+n['h']<=f['height'] for n in f['nodes']),f['id']
        figures_path=ROOT/f'docs/.vitepress/theme/figures/book-{ch:02d}.json';figures_path.parent.mkdir(parents=True,exist_ok=True)
        figures_path.write_text(json.dumps(FIGURES[ch],ensure_ascii=False,indent=2)+'\n')
        coverage.append(stats)
    reports=ROOT/'sources/reports';reports.mkdir(parents=True,exist_ok=True)
    (reports/'navigation-02-03.json').write_text(json.dumps(nav,ensure_ascii=False,indent=2)+'\n')
    lines=['# Chapters 02–03 import and verification','','## Scope and authority','',
    '- Text authority: supplied Chinese Markdown, unchanged. Original PDF pp.24–73 and all 15 supplied PNGs visually inspected before authoring.',
    '- Eight reading pages, four per chapter. Navigation: `navigation-02-03.json`.',
    '- All 15 source figures reconstructed with native nodes/edges and exact original figure IDs/titles; source PNGs copied without recompression for expandable inspection.',
    '- All original caption text retained in the body pending the shared central callout pass. Figure JSON captions reproduce supplied authoritative wording. Fig.2.5 uses its PDF-verified caption paragraph, relocated intact from its erroneous export position; the capture introduction remains separate prose.',
    '- No shared theme/config/CSS changes and no publication, push, or global build.','',
    '## Reproducible validation','',
    'Run `python3 scripts/import_02_03.py`. The importer asserts all code bodies match byte-for-byte, independently compares normalized prose/code, preserves table and image counts, verifies image hashes, and validates figure geometry and edge targets.','',
    'Independent verification: all eight pages parsed through VitePress createMarkdownRenderer and Vue compileTemplate successfully; every rendered table row has the same cell count as its header. All node labels fit their boxes under the shared 13px monospace layout estimate, and positioned edge labels remain within their viewboxes. No global build or browser run by this worker.','',
    '```json',json.dumps(coverage,ensure_ascii=False,indent=2),'```','',
    '## Export repairs (presentation only)','',
    '- Parse sections using a fence-aware line scanner. A `#` inside a captured code example cannot create a reading page.',
    '- Collapse exporter-only `****` seams and convert paired `**` emphasis into explicit strong tags so punctuation-adjacent CJK emphasis renders consistently. No code body is changed.',
    '- Normalize escaped ordinary punctuation outside code spans: dots, hyphens, parentheses, brackets, braces, exclamation/plus signs and underscores; collapse multiply escaped prose pipes to one Markdown escape.',
    '- Escape pipes inside inline-code spans only when inside a table row, preventing TypeScript unions such as `Partial<Record<level, string | null>>` from creating phantom columns.',
    '- Normalize fence labels: TypeScript→ts, JavaScript→js, JSON→json, Plain Text→text, Shell→sh. Preserve fenced body whitespace and content.',
    '- Replace source image tags with BookFigure references; preserve caption wording. One PDF-verified Fig.2.5 paragraph relocation restores the original figure association (documented below).',
    '- Wrap the literal faux endpoint `http://localhost:0` in inline code, preserving visible text while preventing VitePress from interpreting an ephemeral test endpoint as a navigable/dead local link.',
    '- Leave pre-existing ellipses, missing-data annotations, suspicious sample values, mixed English/Chinese caption text, source citations, and code indentation exactly as supplied.','',
    '## Source issues retained (not silently repaired)','',
    '- §2.2 core rule contains two `［原文缺失事件名］` placeholders. Original PDF p.31 reads `error` for the first, `done` for the second, and explicitly says direct `streamSimple()` calls. These PDF-confirmed readings are recorded here, but authoritative Chinese prose remains unchanged.',
    '- §3.1 states its source citation was truncated as `agent/agent-`. The reference continues on original PDF p.51 as `loop.ts:163`. The supplied note remains unchanged.',
    '- Figure 2.5 caption relocation (PDF p.38 verified): move the exact source paragraph beginning `历史记录始终为目标模型重写，而不是为源模型重写。` from before Anthropic OAuth to immediately below BookFigure 2.5. It is now the catalog caption and body caption. The supplied `图 2.5：transformMessages 如何处理历史记录。采集工具…` paragraph retains its exact wording but is restored to ordinary capture-introduction prose. Coverage asserts the moved paragraph occurs exactly once on each side, then compares all remaining text in its original order. No source words or code changed.',
    '- The supplied chapter2 groq JSON prose example spells `lama-3.1-8b-instant`; PDF p.46 spells `llama-3.1-8b-instant`. Source spelling is retained.',
    '- §2.4 captured cost examples and §3.3/3.4 excerpts remain source snapshots; no current-library claims or external corrections were introduced.','',
    '## PDF-verified callout classifications for central pass','',
    '- p.26 WHY IT MATTERS: paragraph beginning `导入 @earendil-works/pi-ai 的扩展并不会得到根入口` is plain prose in the Markdown export.',
    '- p.31 CORE RULE: quoted paragraph beginning `成功的流在任何局部更新之前发出 start` under `核心规则`.',
    '- pp.32,45,52,60,64 FOOTGUN: source blockquotes titled `易踩的坑`.',
    '- pp.39,65 DOC ≠ CODE: source blockquotes titled `文档 ≠ 代码` (including mixed typography if present).',
    '- p.71 RULE OF THUMB: paragraph beginning `如果客户端需要知道“模型已完成回答”` is plain prose in the Markdown export.',
    '- pp.29,35,39,47,56,60,65,73 WHAT THIS MEANS FOR YOU: source blockquotes beginning `这对你意味着什么`.',
    '- Source/citation blocks remain raw `>` blocks, separate from figure captions and callouts.','',
    '## PDF-verified table-caption paragraph prefixes','',
    'These exact normalized source paragraph prefixes identify the complete paragraph to style, without inventing new text. Retain their inline formatting and source references.','',
    '- p.25 / ch02/providers-models: `24 个方法，只有一条路由规则`',
    '- p.27 / ch02/providers-models: `助手内容由文本、思考和工具调用构成`',
    '- p.28 / ch02/providers-models: `限制、价格和特殊行为都随模型一起传递`',
    '- p.30 / ch02/streaming-events: `三种内容块 × start、delta、end`',
    '- p.37 / ch02/wire-apis: `每种协议一个文件，每个文件可服务多个提供商`',
    '- p.37 / ch02/wire-apis: `签名只对写入它的 API 有意义`',
    '- p.43 / ch02/auth-cost-retries: `42 个提供商中，有 40 个具有 API 密钥变量`',
    '- p.44 / ch02/auth-cost-retries: `每个 OAuth 流程最终都得到同一种 OAuthCredential`',
    '- p.49 / ch03/agent-loop: `整个运行时集中在三个文件中`',
    '- p.50 / ch03/agent-loop: `除 convertToLlm 外，每个钩子都是可选的`',
    '- p.53 / ch03/agent-loop: `Steering等待当前轮次的工具完成`',
    '- p.57 / ch03/agent-events: `只有助手消息以流式方式传递`',
    '- p.59 / ch03/agent-events: `不带选项构建的 Agent 没有模型`',
    '- p.60 / ch03/agent-events: `状态在监听器运行之前更新`',
    '- p.63 / ch03/agent-session: `编码智能体的每种角色，要么以用户消息的形式传达给模型`',
    '- p.73 / ch03/prompt-lifecycle: `十种智能体事件之上，还有十二种会话事件`',
    '- p.71 retry-settings following paragraph is preserved as source prose; no caption wrapper inferred.','',
    '## Native diagram decisions','',
    '- Figures 2.4, 3.2 and 3.8 keep source participants, direction, chronology and solid/dashed event distinction. Dashed, non-arrow lifelines retain the participant lanes; numbered phase labels and explicit routes preserve the original messages.',
    '- Figure 2.2 uses three unconnected comparison rows; it does not imply transitions between the scenarios.',
    '- Figure 2.3 shows the three content-block grammars as peers and records zero-or-more semantics in notes, rather than implying an obligatory text/thinking/tool order.',
    '- Figure 3.1 retains first-turn bypass, all three stops, and both loop-back paths. Notes preserve the special error-path finishTurn behavior.',
    '- Figure 3.3 retains printed lifecycle indentation; node details contain the source annotations and full block-event sequences.',
    '- Figures with compact cards move the original card explanatory text into the selectable node detail, preserving it verbatim or as a directly matched Chinese note. Original images are available alongside every native version.','',
    '## Source-palette reconciliation (tone-only)','',
    '- Audited against all supplied images and PDF figure pages. Chapter 2 provider/model transport, transcript, auth and catalog nodes are plum; chapter 3 model/assistant nodes are plum. Extension hooks and event nodes retain purple.',
    '- Listener/UI state nodes and handled/queued dispositions are indigo. The skill/template settings row in Fig.3.7 is config. The two neutral message_update rows in Fig.3.3 are gray, matching the original tree text.',
    '- Exact per-node corrections below: 38 purple→plum, 8 blue→indigo, 1 green→config, and 2 purple→gray. No text, caption, geometry, edge or source-image change.',
    '```json',json.dumps(SOURCE_TONE_CORRECTIONS,ensure_ascii=False,indent=2),'```','',
    '## Immutable source SHA-256','', '```json',json.dumps(hashes,ensure_ascii=False,indent=2),'```','']
    (reports/'chapters-02-03.md').write_text('\n'.join(lines))
    print(json.dumps(coverage,ensure_ascii=False,indent=2))
    print('Created 8 reading pages, 15 native figures, 15 verified original images; normalized source coverage PASS.')

if __name__=='__main__':main()
