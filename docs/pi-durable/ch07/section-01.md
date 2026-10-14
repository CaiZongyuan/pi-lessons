---
title: "扩展与注册表"
---

<div class="section-kicker">PI DURABLE / 7.1 · P. 103</div>

# 扩展与注册表

---

> 你的代码存在于进程内的注册表中；存储中只记录对话需要的扩展名称。
> 
> 

智能体需要工具、系统提示词和一些防护措施。你还希望不用停止智能体就能发布针对其中某项的修复，并在崩溃后重启而不丢失任何内容。<strong>Pi Durable 通过将全部代码保留在内存中、只存储名称，同时做到这两点。</strong>读完本节，你就能将代码打包为扩展，安装和替换它，并说明重启需要什么。

## 扩展包



扩展是一个有名称的代码包。它是普通对象，带有 name 和最多五个列表。`defineExtension()` 只为对象提供类型，不做任何检查，见 `src/harness/define.ts`。每个列表都通过字符串名称与系统的其余部分匹配，绝不依赖对象身份。



注册表是扩展与 Harness 对接的地方。`createRegistry()` 返回一个由你的应用拥有的对象。它已经包含三个内置任务定义：`pi.generation`、`pi.tool` 和 `pi.compaction`，这三者不能移除或替换。`Harness.open()` 会拒绝缺少它们的注册表，因此应始终从 `createRegistry()` 开始，见 `src/harness/registry.ts` 和 `src/harness/harness.ts`。



三个扩展，一个注册表，来源：README §Extensions · 规范 §7\.1

```js
import { createRegistry, defineExtension, hook, section, ToolTask }
    from "@earendil-works/pi-durable";
import { CodingTools } from "@earendil-works/pi-durable/tools";

const Coding = defineExtension({
    name: "coding",
    sections: [
    section("preamble", () => "You are a concise coding assistant.", { tag: false }),
    section("cwd", (input) => input.env?.cwd),
    ],
});

const Permissions = defineExtension({
    name: "permissions",
    hooks: [hook(ToolTask, {
    beforeTool: (call) => (isDangerous(call) ? { block: "Needs approval" } : undefined),
    })],
});

const registry = createRegistry();
registry.install(CodingTools); // "coding-tools"：read、write、edit、bash
registry.install(Coding);
registry.install(Permissions);
```



安装顺序很重要。默认情况下，每个对话都按安装顺序使用全部已安装扩展，因此 coding\-tools 的工具排在 coding 添加的任何内容之前。

|<strong>字段</strong>|<strong>包含什么</strong>|<strong>按什么匹配</strong>|<strong>章节</strong>|
|---|---|---|---|
|`tools`|模型可调用的工具|工具名|7\.4（原书第112页）|
|`sections`|系统提示词的组成区段|区段键|7\.5（原书第115页）|
|`hooks`|内置任务调用的处理函数|任务名|7\.3（原书第109页）|
|`wraps`|针对另一个扩展的工具或区段的装饰器|工具名或区段键|7\.2（原书第106页）|
|`tasks`|你自己的持久化任务定义|任务名|5\.4（原书第73页）|



`Extension` 接口，见 `src/harness/types.ts`。

## 名称在存储中，代码在内存中



注册表中的内容一律不会写入磁盘。用规范的话说，注册表“是进程本地的，生命周期可以长于 Harness，而且不会持久化”，见规范 §7\.1。对话在其 `pi.agent` 文档中，用一个名称列表记录它需要哪些扩展（每个对话的智能体，原书第106页）。每当 Harness 需要代码时，就到注册表中查找这些名称。



<BookFigure id="D.7.1" :show-caption="false" />

> 代码位于进程注册表中；对话只存储名称。对话 1 没有存储选择配置，使用宿主默认值。对话 7 指定了三个扩展；skills 没有安装在这个进程中，因此被跳过，但存储的列表保持不变。前三个扩展来自上面的代码示例；reviewer 和 skills 扩展来自规范 §7\.1。
> 
> 



这种分离让重启的代价很低。在一轮已回答对话的数据库采集记录中，根对话的智能体仅存储为 `{"model": {"provider": "faux", "modelId": "faux-1"}}`，除此之外没有别的内容：没有工具代码，也没有提示词代码，见 `research/capture/sqlite-rows.txt`，文档 6。新进程安装自己的扩展，打开同一个存储，而每个已存储名称都会绑定到当前使用这个名称的代码。如果某个名称没有对应的已安装扩展，就跳过它，不算错误；“再次安装后，它会重新生效”，见规范 §2\.2。



任务定义也按同样方式工作。存储的任务以名称记录其 kind。如果没有任何已安装扩展定义这个名称，任务就会阻塞：它会等待，而不会失败。之后安装扩展就能解除阻塞（调度器，原书第73页）。不过，仍应在 `open()` 之前安装全部扩展，让恢复的工作立即继续。

## 安装、替换、卸载



注册表有两个操作。`install(extension)` 把新名称添加到末尾；如果已有同名扩展，则在原位置替换它。`uninstall(extension)` 移除当前占用该名称的扩展。每次变更立即生效，而且“扩展是重新加载的单位”，见规范 §7\.1。



<BookFigure id="D.7.2" :show-caption="false" />

> 同名安装会原位替换；卸载后再安装，会将扩展移到末尾。操作与订阅者日志 `["a", "a,b", "a,b", "b", "b,a"]` 来自 `test/harness-registry.test.ts` 中的一个用例。最后一行是同一文件中的另一个用例：声明了两次 read 的扩展会被拒绝。卸载不存在的名称和被拒绝的安装都不会发布任何内容。
> 
> 



位置就是优先级。当两个扩展定义同名工具时，后面的扩展胜出；后面的钩子也会后执行（钩子，原书第109页）。由于替换会保留位置，重新加载扩展绝不会改变谁胜出。



如果一次安装会让注册表无效，它就会抛出异常，并且不改变任何内容。工具名和区段键在一个扩展内必须唯一；跨扩展重复使用工具名，则是一个扩展覆盖另一个扩展的方式。区段键使用小写（`^[a-z][a-z0-9 -]*$`），而且不能使用保留名称 instructions。任务名在整个注册表中必须唯一。已经运行的工作不会在执行途中看到注册表变化（运行期间重新加载，原书第118页）。



> <strong>这对你意味着什么：</strong>
> 
> - 在 `Harness.open()` 之前，按你想要的优先顺序安装所有扩展
> 
> - 不要重命名对话已经在使用的扩展、工具或任务：存储的名称将不再匹配
> 
> - 发布修复时，用相同名称安装新对象。install 和 uninstall 都不会调用清理代码，因此你需要自行释放共享资源，而且只能在旧调用结束之后释放，见规范 §12
> 
>
