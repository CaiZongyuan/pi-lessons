<div align="center">

# Pi Lessons

**Pi 的中文教程**

把英文技术手册翻译成可在线阅读的中文版，保留原版结构、图表与代码格式。

[在线阅读](https://caizongyuan.github.io/pi-lessons/) · [Pi 技术手册](https://caizongyuan.github.io/pi-lessons/#pi-manual) · [Pi Durable 技术手册](https://caizongyuan.github.io/pi-lessons/#pi-durable)

</div>

---

## 教程

### 📘 [Pi 技术手册](https://caizongyuan.github.io/pi-lessons/)

> 原文：[Pi Technical Manual](https://x.com/calebfahlgren/status/2107199330926899652) · 221 页 · 8 部分

从模型调用到智能体循环，读懂 Pi 的核心设计与扩展点。

| 部分 | 内容 |
|---|---|
| 1 · 模型 | Pi 要解决什么、单仓库一页纸、一次提示词的一生 |
| 2 · 供应商层 | 供应商与模型、流式事件协议、跨供应商转交、鉴权与成本 |
| 3 · 智能体循环 | 循环本体、智能体事件、`AgentSession` 接线、从 `prompt()` 到 `agent_settled` |
| 4 · 编码智能体 | 系统提示词构建、内置工具、JSONL 会话树、压缩与分支摘要 |
| 5 · 配置与扩展性 | 配置与鉴权、上下文文件与技能、扩展加载与 API、扩展事件、运行模式、RPC 与 SDK |
| 6 · 集成与界面 | MCP、Codemode、`pi-tui` 终端界面框架 |
| 7 · 实验特性与运维 | 实验特性栈、安全模型、遥测与评测 |
| 附录 | 环境变量、CLI 参考、斜杠命令、设置参考、源码索引、术语表 |

**状态**：已完译。

### 📗 [Pi Durable 技术手册](https://caizongyuan.github.io/pi-lessons/)

> 原文：[Pi Durable Technical Manual](https://x.com/lucataco/status/2107230736403013653) · 190 页 · 11 部分 · **已完译**

Pi Durable 是 Pi 的会话与提交内核：让智能体每一个可见步骤都成为已存储的提交。

| 部分 | 内容 |
|---|---|
| 1 · 模型 | 核心规则与八条不变式 |
| 2 · Session 与提交 | 变更线、原子提交、`Seal`/`Notify`/`Join`/`Settle` |
| 3 · 会话与上下文 | 条目、内置种类、分叉与交接 |
| 4 · 文档 | 存储契约、作用域、化身与存续期 |
| 5 · 任务 | 任务即状态机、阶段与进度、调度器、结构化并发、中止与孤儿 |
| 6 · 运行 | 收件箱、生成与压缩、工具轮 |
| 7 · 扩展与 Agent | 注册表、七种钩子、边运行边重载 |
| 8 · 观察 | Chord、视图状态、智能体事件流、任务图 |
| 9 · 存储与环境 | 存储契约、SQLite、JSONL、执行环境 |
| 10 · 实践 | 构建真实智能体、会咬人的契约、刻意不做的事 |
| 附录 | Harness 与会话 API、内置 kind、设置默认值、错误与原因、术语表 |

<div align="center">

[开始阅读 Pi 手册 →](https://caizongyuan.github.io/pi-lessons/#pi-manual)

</div>

---

## 原文来源

两本手册的原始 PDF 由作者公开发布，本仓库只提供中文翻译：

- **Pi Technical Manual** — <https://x.com/calebfahlgren/status/2107199330926899652>
- **Pi Durable Technical Manual** — <https://x.com/lucataco/status/2107230736403013653>

原 PDF 不随本仓库分发。翻译内容版权归原作者所有，此处仅作学习交流。

---

## 参与翻译

译文以 Markdown 为单位维护在 `books/<书名>/md/parts/`，每部分一个文件，原文在上、
译文在下逐段对照。术语表见 `books/pi-manual/GLOSSARY.md` 与
`books/pi-durable/GLOSSARY.md` —— 新增章节请先对照它保持术语一致：`Session`、
`Harness`、`Chord` 这类代码里的类名保留英文，`pending`、`running` 这类状态值不译。

Pi Durable 的译文源是 `books/pi-durable/ir/*.json`，由 `tools/ir2md.py` 转成 Markdown
供网站使用；修改译文请改 IR，不要改生成出来的 Markdown。

## 本地运行

网站用 Astro + Starlight 构建，依赖 `books/` 里的内容：

```bash
pip install pymupdf requests        # 只在需要重跑 PDF 抽取时装
python tools/ir2md.py books/pi-durable/ir --out books/pi-durable/md/parts
python tools/docs.py sync           # 生成 docs/src/content/docs/ 下的页面

cd docs
npm install
npm run dev                         # http://localhost:4321/pi-lessons/
```

校验：

```bash
python tools/check.py               # 译文完整性
python tools/check_md.py            # Markdown 与英文原文的结构一致性
python tools/verify_site.py docs/dist
```

`books/` 是内容的唯一来源，`docs/src/content/docs/{pi-manual,pi-durable}/` 与
`docs/dist/` 都是生成产物，不入库。

## 许可

本仓库的翻译与编排代码遵循 MIT；原手册内容遵循原作者的许可。