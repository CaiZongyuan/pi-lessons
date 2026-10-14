---
title: "系统提示词"
---

<div class="section-kicker">PI DURABLE / 7.5 · P. 115</div>

# 系统提示词

---

> 提示词本身不会被单独存储；每个请求都从区段渲染它，只有发生变化的部分才会加入对话记录。
> 
> 

提供商会缓存提示词的开头，因此每个轮次都重写系统提示词会浪费金钱和时间。Pi Durable 用小型的命名区段构建提示词；某个区段变化时，只发送该区段。读完本节，你就能编写提示词区段，并维持对话提示词缓存的有效性。

## 区段



区段是系统提示词中有名称的一部分。`section(key, render)` 构建一个区段。render 返回字符串，或者返回 undefined 以省略该区段。默认情况下，文本用标签包裹，即 `<key>…</key>`；`{ tag: false }` 会原样发送文本。所选扩展的区段与智能体的 instructions 是提示词文本的唯一来源，见规范 §7\.4。



渲染函数接收解析后的 agent（包括本次请求提供的工具）、本次请求的 env（cwd 区段渲染 `input.env?.cwd`），以及用于读取已提交文档的 read。区段按扩展顺序排列，较后的同键区段会原位替换较早区段，随后应用 `wrapSection()` 装饰器，instructions 放在最后。示例 15 在两个对话上展示了全部这些行为。



<BookFigure id="D.7.6" :show-caption="false" />

> 区段按扩展顺序渲染，包装器会应用，未选中的扩展被排除，instructions 最后出现。渲染值来自 `research/runs/15-system-prompt.txt`；各标签内的换行显示为空格。
> 
> 



区段抛出异常不会让请求失败。它会保留上一次显示的文本（如果有），并报告错误。区段不应关心自己在哪里运行：“没有任何区段检查自己是否运行在子智能体中。”对话提示词的差异只来自其选择配置、指令、环境和文档，见规范 §7\.4。

## 只发送差异



对话记录保存模型看到过的内容，因此提示词也保存在其中。每次请求之前，generation 任务会重放先前的系统条目，了解模型已经拥有哪些内容。它渲染现在需要的区段，如果发现差异，就追加一个只包含变更的 `pi.system` 条目。该条目保存 sections 补丁以及 toolsAdded 和 toolsRemoved（条目与内置类型，原书第37页）。



第一次请求的基线，来源：`research/capture/sqlite-rows.txt`，条目 10

```json
{
    "model": [ {
    "role": "system",
    "content": "",
    "sections": { "preamble": "You are a terse assistant." },
    "toolsAdded": [
    { "name": "count", "description": "Count from 1 to n", ..., "parameters": {...} } ],
    "timestamp": 1791211974788
    } ],
    "kind": "pi.system",
    "id": 10,
    "conversationId": 1,
    "byTaskId": 9
}
```

> 对话的第一次请求写入完整基线：一个不带标签的 preamble 和 count 工具（声明已省略部分内容）。它跟在所回答的消息，也就是用户条目 7 之后。这份采集记录的 preamble 与示例 15 不同，本节两幅图使用的是示例 15。
> 
> 



重放按对话记录顺序应用系统条目。字符串会原位添加或替换区段，null 则移除区段。因此，cwd 改变之后，下一个请求会追加一个只有单个键的补丁，其余提示词仍保留原位置和缓存。



<BookFigure id="D.7.7" :show-caption="false" />

> 后续请求只会在对话记录中的相应位置追加发生变化的区段。图中是示例 15 的根对话；`research/runs/15-system-prompt.txt` 中，第二个 `pi.system` 条目为 `{ sections: { cwd: '<cwd>\n/repo/packages\n</cwd>' } }`。
> 
> 



示例 27 展示了工具也以相同方式改变。退出计划模式会追加 `sections: { plan_mode: null }`，添加 write、edit 和 bash，移除 submit\_plan，而 read 保持原位置，见运行记录 27。



Details

A er a compaction or reset — the old baseline may lie outside the active context, so the next request writes a fresh full baseline,

even if nothing changed\. The capture kit saw sections: \{\} written this way for a conversation with no sections

research/capture/NOTES\.md, note 18\.

Reordering — a patch cannot move a section\. When the desired order diﬀers, the Harness writes two entries: one removing

every section, one adding them all back in order src/harness/prompt\.ts\.

Missing tools — a request oﬀers only tools that resolve\. A tool whose extension disappeared is listed in toolsRemoved, and

added back once it resolves again spec §2\.2\.

History is authoritative — rendered text stored in old entries stays as it was, even if the renderer changes\.

WHAT THIS MEANS FOR YOU

Keep renderers deterministic: an embedded timestamp changes the text, appends a delta and breaks the provider’s cache spec

§7\.4\.

Give long\-lived conversations a stable extension list; the host default moves whenever you install something spec §12\.

Add tools later through a filter or control\.addTools: that appends one small delta and keeps the earlier prefix intact\.

Sources: src/harness/prompt\.ts; src/harness/define\.ts section\(\), wrapSection\(\); src/harness/generation\.ts; src/harness/types\.ts

\(PromptInput, PromptSection\); spec §7\.4, §2\.2, §12; README §System Prompt; ex 15, 27 and runs 15, 27; research/capture/sqlite\-

rows\.txt; research/capture/NOTES\.md
