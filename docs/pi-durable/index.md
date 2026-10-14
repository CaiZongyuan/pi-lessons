---
title: Pi Durable
outline: false
---

<div class="section-kicker">PI / TECHNICAL SERIES · 02</div>

# Pi Durable

<div class="book-lede">从原子提交到崩溃恢复，读懂持久化智能体运行框架。</div>

Pi Durable 1.0.3 · 工程版 · 2026.10。完整收录 10 章、7 节参考资料及开篇内容。

[如何阅读本书与第一个可运行的对话 →](/pi-durable/preface)

> **版本说明**
> 本书对应提交 `5b6c792`（2026 年 10 月 5 日）。Pi Durable 为实验性软件；本阅读版保留书中版本与技术语义，示例不会自动更新到后续版本。

## 01 · 模型

- [1.1 Pi Durable 的用途](/pi-durable/ch01/section-01) · 原书第 10 页
- [1.2 一页看懂架构](/pi-durable/ch01/section-02) · 原书第 13 页
- [1.3 核心规则及其不变量](/pi-durable/ch01/section-03) · 原书第 16 页
- [1.4 一次输入得到回答的全过程](/pi-durable/ch01/section-04) · 原书第 19 页

## 02 · 会话与提交

- [2.1 记录与 ID](/pi-durable/ch02/section-01) · 原书第 25 页
- [2.2 提交与变更串行队列](/pi-durable/ch02/section-02) · 原书第 29 页
- [2.3 提交失败时会怎样](/pi-durable/ch02/section-03) · 原书第 33 页

## 03 · 对话与上下文

- [3.1 条目与内置种类](/pi-durable/ch03/section-01) · 原书第 37 页
- [3.2 从对话记录到模型上下文](/pi-durable/ch03/section-02) · 原书第 40 页
- [3.3 分叉与有所有者的对话](/pi-durable/ch03/section-03) · 原书第 43 页
- [3.4 重置、交接与头指针](/pi-durable/ch03/section-04) · 原书第 46 页

## 04 · 文档

- [4.1 定义文档](/pi-durable/ch04/section-01) · 原书第 50 页
- [4.2 访问、创建与生命周期](/pi-durable/ch04/section-02) · 原书第 53 页
- [4.3 基值、增量与迁移](/pi-durable/ch04/section-03) · 原书第 56 页
- [4.4 内置文档](/pi-durable/ch04/section-04) · 原书第 60 页

## 05 · 任务

- [5.1 作为状态机的任务](/pi-durable/ch05/section-01) · 原书第 63 页
- [5.2 阶段、步骤与进展](/pi-durable/ch05/section-02) · 原书第 67 页
- [5.3 副作用三明治](/pi-durable/ch05/section-03) · 原书第 70 页
- [5.4 调度器](/pi-durable/ch05/section-04) · 原书第 73 页
- [5.5 所有权与结构化并发](/pi-durable/ch05/section-05) · 原书第 76 页
- [5.6 中止、故障与孤立](/pi-durable/ch05/section-06) · 原书第 80 页

## 06 · 运行

- [6.1 提交请求与收件箱](/pi-durable/ch06/section-01) · 原书第 84 页
- [6.2 运行控制与实时文档](/pi-durable/ch06/section-02) · 原书第 88 页
- [6.3 生成](/pi-durable/ch06/section-03) · 原书第 91 页
- [6.4 工具调用与重放](/pi-durable/ch06/section-04) · 原书第 94 页
- [6.5 压缩](/pi-durable/ch06/section-05) · 原书第 97 页
- [6.6 用量与费用](/pi-durable/ch06/section-06) · 原书第 100 页

## 07 · 扩展与智能体

- [7.1 扩展与注册表](/pi-durable/ch07/section-01) · 原书第 103 页
- [7.2 每个对话的智能体](/pi-durable/ch07/section-02) · 原书第 106 页
- [7.3 钩子](/pi-durable/ch07/section-03) · 原书第 109 页
- [7.4 定义工具](/pi-durable/ch07/section-04) · 原书第 112 页
- [7.5 系统提示词](/pi-durable/ch07/section-05) · 原书第 115 页
- [7.6 运行期间重新加载](/pi-durable/ch07/section-06) · 原书第 118 页
- [7.7 子智能体](/pi-durable/ch07/section-07) · 原书第 121 页

## 08 · 观察

- [8.1 Chord 与文档状态](/pi-durable/ch08/section-01) · 原书第 125 页
- [8.2 对话视图与 watch()](/pi-durable/ch08/section-02) · 原书第 129 页
- [8.3 智能体事件](/pi-durable/ch08/section-03) · 原书第 133 页
- [8.4 任务图与 inspect()](/pi-durable/ch08/section-04) · 原书第 137 页

## 09 · 存储与环境

- [9.1 存储契约](/pi-durable/ch09/section-01) · 原书第 141 页
- [9.2 SQLite](/pi-durable/ch09/section-02) · 原书第 144 页
- [9.3 JSONL](/pi-durable/ch09/section-03) · 原书第 148 页
- [9.4 内存、一致性与可移植性](/pi-durable/ch09/section-04) · 原书第 152 页
- [9.5 执行环境](/pi-durable/ch09/section-05) · 原书第 155 页

## 10 · 实践

- [10.1 构建编码智能体](/pi-durable/ch10/section-01) · 原书第 159 页
- [10.2 容易踩坑的契约](/pi-durable/ch10/section-02) · 原书第 163 页
- [10.3 限制与非目标](/pi-durable/ch10/section-03) · 原书第 168 页

## R · 参考

- [R.1 Harness 与 Conversation API](/pi-durable/reference/section-01) · 原书第 172 页
- [R.2 内置种类](/pi-durable/reference/section-02) · 原书第 179 页
- [R.3 设置与默认值](/pi-durable/reference/section-03) · 原书第 180 页
- [R.4 错误与原因](/pi-durable/reference/section-04) · 原书第 183 页
- [R.5 术语表](/pi-durable/reference/section-05) · 原书第 185 页
- [R.6 来源](/pi-durable/reference/section-06) · 原书第 187 页
- [R.7 图表索引](/pi-durable/reference/section-07) · 原书第 189 页

---

[返回技术文库 →](/)
