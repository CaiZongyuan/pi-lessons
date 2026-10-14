"""Coordinate transcription of the supplied cover's 29-event timeline (PDF p1)."""
def front_figure():
 ns=[];es=[]
 def n(id,x,y,w,h,label,detail='',tone='gray',shape='label',**kw):
  item=dict(id=id,x=x,y=y,w=w,h=h,label=label,detail=detail or label,tone=tone,shape=shape,**kw);ns.append(item);return item
 def line(id,points,color='#3b4858',dash=False,width=1,from_=None,to=None):es.append({'from':from_ or id,'to':to or id,'points':points,'color':color,'dashed':dash,'width':width,'arrow':False})
 for id,label,y,tone in [('user','USER',35,'gray'),('loop','AGENT LOOP · PI-AGENT-CORE',151,'amber'),('model','MODEL · PI-AI STREAM',263,'plum'),('tool','TOOL',375,'green'),('disk','SESSION FILE · JSONL',487,'teal')]:
  n(id,16,y,520,34,label,tone=tone);line(id,[[20,y+48],[1028,y+48]])
 n('prompt',178,62,520,35,'prompt("What does hello.txt say?")','用户提示，从 AgentSessionEvent 第1项开始。')
 n('answer',565,94,475,35,'"It says: Hello from the capture kit."','最终文本回答。')
 n('turn1',210,178,505,39,'turn 1 · tool use','原图第一轮的绘制区间；请求模型并执行 read。','amber','rect')
 n('turn2',745,178,208,39,'turn 2 · answer','原图第二轮的绘制区间；模型返回最终答案。','amber','rect')
 line('turn1',[[179,197],[982,197]],'#deb16b',False,2,from_='turn1',to='turn2')
 n('settled',1001,185,24,24,'','agent_settled：整个会话运行收束，原图位于第29个事件。','amber','circle')
 n('settled-label',881,222,165,30,'agent_settled','最后一个事件为 agent_settled。','amber')
 n('stream1',358,290,209,39,'text + toolCall','第一轮模型输出文本及 read 工具调用。','plum','rect')
 n('stream2',774,290,149,39,'text','第二轮模型输出最终文本。','plum','rect')
 n('deltas',510,330,210,35,'*_delta events','流式增量事件；这里只保留原图标记，不产生模拟计数。','plum')
 for x in [417,506,834,864]:line('stream1' if x<700 else 'stream2',[[x,334],[x,347]],'#b598bd',False,2)
 n('read-mark',595,405,30,36,'','read 工具执行。','green','rect')
 n('read',638,404,260,40,'read hello.txt','实际工具读取 hello.txt，结果成为第7行记录。','green')
 rows=[('session','header · version 3'),('model_change','faux / faux-1'),('thinking_level_change','off'),('message · system','preamble, tools, rules, docs…'),('message · user','the prompt'),('message · assistant','text + toolCall read'),('message · toolResult','hello.txt contents'),('message · assistant','the answer')]
 # Positions copied from original; 1–3 are before the event axis, at construction.
 centers=[50,86,123,269,329,566,685,923]
 for i,((name,detail),x) in enumerate(zip(rows,centers),1):
  n('row'+str(i),x-16,519,32,32,str(i),f'会话文件第{i}行：{name}；{detail}。'+('文件头，不是树条目。' if i==1 else ''),'teal','circle',align='center')
  n('key-circle'+str(i),1102,81+(i-1)*64,28,28,str(i),f'会话文件第{i}行：{name}。','teal','circle',align='center')
  n('key'+str(i),1137,73+(i-1)*64,230,58,name+'\n'+detail,f'对应左侧第{i}条会话记录。','gray')
 n('construction',16,558,300,35,'at createAgentSession','第1–3条元数据在 createAgentSession 中生成；不是三个模型消息。','teal')
 n('persist',355,558,365,35,'one line per message_end','每条完成的消息在 message_end 处对应一行 JSONL。','teal')
 for id,x,y in [('row4',269,217),('row5',329,217),('row6',566,329),('row7',685,443),('row8',923,329)]:line(id,[[x,y],[x,519]],'#81bfc2',True,1.2)
 line('answer',[[923,127],[923,290]],'#9ba6b5',True,1)
 line('disk',[[1077,18],[1077,603]],'#3b4858',False,2)
 n('key-title',1100,14,255,61,'KEY · THE SESSION\nFILE, LINE BY LINE','右侧逐行解释；不是额外的事件流。')
 # Exact ordinal event ticks from the original graphic, not elapsed-time metrics.
 line('axis-title',[[179,625],[1013,625]],'#8d99a9',False,1.3)
 for event in [1,5,10,15,20,25,29]:
  x=179+(event-1)*(834/28);line('axis-title',[[x,618],[x,633]],'#8d99a9',False,1.3);n('tick'+str(event),x-15,639,30,26,str(event),f'按发出顺序排列的第 {event} 个 AgentSessionEvent。',align='center')
 n('axis-title',330,669,605,29,'AgentSessionEvent number, in emission order · 29 events','横轴是事件序号，不是时间；轴与写入对齐保留原图坐标。',align='center')
 return dict(id='front-run',title='一次真实运行：从提示到 JSONL',label='FIG. 1 · 开篇',page=1,image='/figures/front/image.png',source='research/out/one-turn.txt · 原书封面',caption='使用 faux 提供商实际运行一次 AgentSession。脚本化模型要求读取文件，read 工具执行，随后模型回答。每条完成的消息成为一行 JSONL，其 parentId 指向上一行。',kind='diagram',theme='dark',width=1380,height=710,nodes=ns,edges=es,notes=['横轴保留原图的 1 / 5 / 10 / 15 / 20 / 25 / 29 事件序号。第1–3条记录在 createAgentSession 处；系统、用户、助手、工具结果与最终助手消息的写入位置按原图对齐。','文件头不是树条目；图中不添加原书没有的 parentId 箭头。'])
