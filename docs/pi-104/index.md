---
title: Pi 1.04
outline: false
---

<div class="section-kicker">PI / TECHNICAL MANUAL · 1.0.4</div>

# Pi 1.04

<div class="book-lede">从一个提示一直追踪到 JSONL 中的一行，理解这个极简智能体运行框架。</div>

[如何阅读本书 · 来源、约定与插图颜色 →](./preface)


<div class="chapter-title"><span>01</span><h2>模型</h2></div>

<div class="chapter-contents">
<a href="/pi-104/ch01/what-pi-is-for"><span>1.1</span><strong>Pi 的用途</strong><small>P. 7</small><b>→</b></a>
<a href="/pi-104/ch01/monorepo"><span>1.2</span><strong>一页看懂 monorepo</strong><small>P. 11</small><b>→</b></a>
<a href="/pi-104/ch01/prompt-lifecycle"><span>1.3</span><strong>一个提示的生命周期</strong><small>P. 15</small><b>→</b></a>
</div>


<div class="chapter-title"><span>02</span><h2>提供商层</h2></div>

<div class="chapter-contents">
<a href="/pi-104/ch02/providers-models"><span>2.1</span><strong>提供商与模型</strong><small>P. 24</small><b>→</b></a>
<a href="/pi-104/ch02/streaming-events"><span>2.2</span><strong>流式事件协议</strong><small>P. 30</small><b>→</b></a>
<a href="/pi-104/ch02/wire-apis"><span>2.3</span><strong>传输 API 与跨提供商交接</strong><small>P. 36</small><b>→</b></a>
<a href="/pi-104/ch02/auth-cost-retries"><span>2.4</span><strong>身份验证、费用、重试与模型目录</strong><small>P. 41</small><b>→</b></a>
</div>


<div class="chapter-title"><span>03</span><h2>智能体循环</h2></div>

<div class="chapter-contents">
<a href="/pi-104/ch03/agent-loop"><span>3.1</span><strong>智能体循环</strong><small>P. 49</small><b>→</b></a>
<a href="/pi-104/ch03/agent-events"><span>3.2</span><strong>智能体事件与 Agent 类</strong><small>P. 57</small><b>→</b></a>
<a href="/pi-104/ch03/agent-session"><span>3.3</span><strong>AgentSession：组装运行时</strong><small>P. 61</small><b>→</b></a>
<a href="/pi-104/ch03/prompt-lifecycle"><span>3.4</span><strong>从 prompt() 到 agent_settled</strong><small>P. 67</small><b>→</b></a>
</div>


<div class="chapter-title"><span>04</span><h2>编码智能体</h2></div>

<div class="chapter-contents">
<a href="/pi-104/system-prompt"><span>4.1</span><strong>系统提示词构建</strong><small>P. 75</small><b>→</b></a>
<a href="/pi-104/tools"><span>4.2</span><strong>内置工具</strong><small>P. 81</small><b>→</b></a>
<a href="/pi-104/sessions"><span>4.3</span><strong>会话：JSONL 树</strong><small>P. 86</small><b>→</b></a>
<a href="/pi-104/compaction"><span>4.4</span><strong>压缩与分支摘要</strong><small>P. 92</small><b>→</b></a>
</div>


<div class="chapter-title"><span>05</span><h2>配置与扩展</h2></div>

<div class="chapter-contents">
<a href="/pi-104/ch05/configuration-models-auth"><span>5.1</span><strong>配置、模型与身份验证</strong><small>P. 99</small><b>→</b></a>
<a href="/pi-104/ch05/resources"><span>5.2</span><strong>上下文文件、技能、模板、主题与包</strong><small>P. 106</small><b>→</b></a>
<a href="/pi-104/ch05/extensions-loading-api"><span>5.3</span><strong>扩展：加载与 API</strong><small>P. 113</small><b>→</b></a>
<a href="/pi-104/ch05/extension-events-contexts"><span>5.4</span><strong>扩展事件与上下文</strong><small>P. 120</small><b>→</b></a>
<a href="/pi-104/ch05/run-modes"><span>5.5</span><strong>运行模式：交互式、print 与 JSON</strong><small>P. 127</small><b>→</b></a>
<a href="/pi-104/ch05/rpc-sdk"><span>5.6</span><strong>RPC 模式与 SDK</strong><small>P. 133</small><b>→</b></a>
</div>


<div class="chapter-title"><span>06</span><h2>集成与界面</h2></div>

<div class="chapter-contents">
<a href="/pi-104/ch06/mcp"><span>6.1</span><strong>MCP：从 mcp.json 到工具调用</strong><small>P. 144</small><b>→</b></a>
<a href="/pi-104/ch06/codemode"><span>6.2</span><strong>Codemode：调用工具的脚本</strong><small>P. 151</small><b>→</b></a>
<a href="/pi-104/ch06/tui"><span>6.3</span><strong>pi-tui：终端 UI 框架</strong><small>P. 158</small><b>→</b></a>
</div>


<div class="chapter-title"><span>07</span><h2>实验性功能与运维</h2></div>

<div class="chapter-contents">
<a href="/pi-104/ch07/experimental-stack"><span>7.1</span><strong>实验性技术栈</strong><small>P. 166</small><b>→</b></a>
<a href="/pi-104/ch07/security"><span>7.2</span><strong>安全模型</strong><small>P. 174</small><b>→</b></a>
<a href="/pi-104/ch07/telemetry-evals"><span>7.3</span><strong>遥测与评测</strong><small>P. 179</small><b>→</b></a>
</div>


<div class="chapter-title"><span>R</span><h2>参考资料</h2></div>

<div class="chapter-contents">
<a href="/pi-104/reference/environment"><span>R.1</span><strong>环境变量</strong><small>P. 185</small><b>→</b></a>
<a href="/pi-104/reference/cli"><span>R.2</span><strong>CLI 参考</strong><small>P. 191</small><b>→</b></a>
<a href="/pi-104/reference/commands"><span>R.3</span><strong>斜杠命令与快捷键</strong><small>P. 197</small><b>→</b></a>
<a href="/pi-104/reference/settings"><span>R.4</span><strong>设置参考</strong><small>P. 202</small><b>→</b></a>
<a href="/pi-104/reference/source-index"><span>R.5</span><strong>源文件索引</strong><small>P. 208</small><b>→</b></a>
<a href="/pi-104/reference/doc-code"><span>R.6</span><strong>文档与代码的差异</strong><small>P. 213</small><b>→</b></a>
<a href="/pi-104/reference/glossary"><span>R.7</span><strong>术语表</strong><small>P. 216</small><b>→</b></a>
<a href="/pi-104/reference/sources"><span>R.8</span><strong>来源与版本</strong><small>P. 218</small><b>→</b></a>
<a href="/pi-104/reference/figures"><span>R.9</span><strong>插图索引</strong><small>P. 220</small><b>→</b></a>
</div>

<p class="edition-note">依据所提供的中文书稿与原版 PDF 整理。页码对应原书；图示保留原图对照，核对中发现的源文差异会明确标注。</p>
