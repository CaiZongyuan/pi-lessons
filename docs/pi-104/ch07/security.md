---
title: "安全模型"
originalPage: 174
---

<div class="section-kicker">7.2 / EXPERIMENTAL & OPERATIONS</div>

# 安全模型

---

Pi 使用你的账户权限运行每一次工具调用，不会请求批准。项目信任决定一个文件夹中的哪些文件可以配置 Pi；它并不决定 Pi 启动后模型可以做什么。



你今天早上克隆的一个仓库里包含 `.pi/extensions/`、一个 `AGENTS.md` 和一个测试脚本。在其中启动 Pi，可能运行三种代码：扩展、模型读取 `AGENTS.md` 后决定运行的内容，以及模型调用的脚本。本节展示 Pi 会对这三者中的哪些设置关卡，以及具体如何实施。它引用 Pi 自己的安全立场，沿着代码追踪项目信任的决策过程，比较文档提供的隔离方案，并列出各个组件内部的控制措施。

## 安全立场



随软件提供的指南开篇就确立了一条规则：“应将模型生成的命令和代码视为不可信。Pi 可以使用启动它的账户权限读取、修改和执行文件，而且不会在每次工具调用之前请求批准”，见 `CA/docs/security.md`。扩展、软件包安装器、语言服务器及其他子进程“以相同的权限运行，除非操作系统或虚拟化边界限制了它们”。指南也点明哪些东西不构成边界：“查看对话记录、使用项目信任以及审查变更，都不会形成安全边界。”



仓库的 `SECURITY.md` 在同一处划定了漏洞报告范围：“Pi 将本地用户账户及该账户可写的文件，视为与 Pi 进程本身处于同一信任边界之内”，见 `SECURITY.md`。用指南的话说，提示注入、没有内置沙箱，以及用户安装的扩展的行为，“通常不属于安全边界内的问题，除非报告证明存在权限边界绕过，或取得了本地用户原本不具备的访问权限”，见 `CA/docs/security.md` 的“报告安全问题”一节。报告应发送至 `security@earendil.com`，或通过私密 GitHub 安全公告提交，见 `SECURITY.md`。



工作文件夹也不限制访问范围：它“控制资源发现和工具的默认位置，但不会阻止命令访问 Pi 进程能够访问的其他路径”，见 `CA/docs/security.md`。

## 项目信任



项目信任是启动时针对配置设置的关卡。如果一个文件夹的 `.pi/` 下包含八项内容中的任意一项，就需要作出信任决定：`settings.json`、`mcp.json`、`extensions`、`skills`、`prompts`、`themes`、`SYSTEM.md`、`APPEND_SYSTEM.md`，见 `CA/src/core/trust-manager.ts:30`；该文件夹或任一祖先目录中存在 `.agents/skills` 目录时也一样。`~/.agents/skills` 本身属于用户资源，不会触发这个决定，见 `CA/src/core/trust-manager.ts:186`。仅有 `.pi` 目录本身不需要作出决定。



<BookFigure id="7.5" />

> 第一个给出答复的行决定结果；所有未得到答复的路径最终都被视为不可信。顺序来自 `resolveProjectTrusted()`，见 `CA/src/core/project-trust.ts:46`。命令行覆盖项在资源扫描之前检查，因此即使文件夹中没有需要保护的内容，`--no-approve` 也会生效。只有存在受保护资源时，才会执行第3至6行。
> 
> 



第3行在加载任何项目代码之前执行。`loadProjectTrustExtensions()` 强制将项目视为不可信，并加载用户、全局和命令行扩展以及 SDK 工厂，因此项目本地扩展无法对自身是否可信投票，见 `CA/src/core/resource-loader.ts:501`。内置扩展要等到最后一轮才加载，因为“项目设置可能禁用它们，而已加载的扩展无法卸载”，见 `CA/src/core/resource-loader.ts:683`。处理器循环返回第一个 `"yes"` 或 `"no"`；抛出异常的处理器会被报告并跳过，见 `CA/src/core/extensions/runner.ts:295`。



信任存储是智能体目录中的 `trust.json`，见 `CA/src/core/trust-manager.ts:214`，它是一个把规范化目录路径映射为 `true` 或 `false` 的 JSON 对象。查找从当前文件夹向上遍历到根目录，并采用遇到的第一个显式值，见 `CA/src/core/trust-manager.ts:45`。读取和写入都会持有 `trust.json.lock` 上的 `proper-lockfile` 锁。交互式提示显示“Trust project folder?”（是否信任项目文件夹？），并提供五个选项：



|<strong>选项</strong>|<strong>决定</strong>|<strong>写入 `trust.json` 的内容</strong>|
|---|---|---|
|信任（Trust）|可信|此文件夹 → `true`|
|信任父文件夹（Trust parent folder \(\.\.\.\)）|可信|父文件夹 → `true`；删除此文件夹自身的条目|
|信任，仅本次会话（Trust \(this session only\)）|可信|无|
|不信任（Do not trust）|不可信|此文件夹 → `false`|
|不信任，仅本次会话（Do not trust \(this session only\)）|不可信|无|



五个选项中有两个不会留下记录。来源：`getProjectTrustOptions()`，`CA/src/core/trust-manager.ts:67`。也可以稍后在会话中通过 `/trust` 保存决定，见 `CA/src/core/slash-commands.ts:36`。



Print、JSON 和 RPC 模式没有信任提示。如果没有覆盖项、扩展答复或已保存的决定，它们只会在 `defaultProjectTrust: "always"` 下加载受保护资源，见 `CA/src/core/project-trust.ts:86`。自动化中应使用 `--approve` 或 `--no-approve`。



授予信任会加载项目设置、项目 MCP 服务器、`.pi` 下的扩展、技能、提示模板、主题和系统提示文件，以及项目软件包。拒绝信任还会禁止软件包管理器访问项目软件包存储：“Project is not trusted; refusing to access project package storage”（项目不可信；拒绝访问项目软件包存储），见 `CA/src/core/package-manager.ts:1777`。`.pi` 下的 `npm` 和 `git` 目录也在该检查范围内，但仅仅存在这些目录不会触发信任决定。



有两类内容绕过了这道关卡。上下文文件，包括 `AGENTS.override.md`、`AGENTS.md`、`CLAUDE.md` 及其大写变体，无须信任检查就会加载；只有 `--no-context-files` 能阻止它们，见 `CA/src/core/resource-loader.ts:642`。此外，会话目录在信任决定完成之前就会选定，优先级依次为 `--session-dir`、`PI_CODING_AGENT_SESSION_DIR`，以及启动设置管理器读取的 `sessionDir` 设置，见 `CA/src/main.ts:688`。因此，即使项目被拒绝信任，它的 `.pi/settings.json` 仍然可以改变会话文件的写入位置；`CA/docs/security.md` 记录了这一缺口。



> <strong>FOOTGUN</strong> <!-- pdf-restored-label -->
>
> 拒绝信任并不会阻止一个文件夹引导模型。`AGENTS.md` 和 `CLAUDE.md` 仍然会进入系统提示，模型也仍然使用你的权限运行工具。应将不可信仓库中的指令视为输入；如果尚未读过这些指令，就使用 `-nc` 启动 Pi；如果必须在那里运行模型，就隔离整个进程。



> <strong>文档 ≠ 代码</strong> <!-- pdf-restored-label -->
>
> 示例扩展 `CA/examples/extensions/project-trust.ts` 写道：“可以在包含 `.pi`、`AGENTS.md/CLAUDE.md` 或 `.agents/skills` 的项目中试用。”仅有 `.pi`、`AGENTS.md` 或 `CLAUDE.md` 并不会触发 `project_trust`：只有存在上述八项 `.pi` 内容之一，或项目中的 `.agents/skills` 时，该事件才会运行，见 `CA/src/core/trust-manager.ts:186`。

## 隔离选项



由于 Pi 没有自己的沙箱，隔离意味着让它或它的部分工具在别处运行。`CA/docs/containerization.md` 比较了四种方法，示例扩展又补充了两种。



<BookFigure id="7.6" />

> 只有整个进程的隔离才能将扩展也约束在内。工具级方法把选定的工具移出宿主进程，却将 Pi、其他工具及其环境变量留在原处。各行来自 `CA/docs/containerization.md` 和 `CA/examples/extensions/{gondolin,sandbox,permission-gate.ts,protected-paths.ts}`；此图为示意图。
> 
> 



|<strong>方法</strong>|<strong>做法</strong>|<strong>注意事项</strong>|
|---|---|---|
|普通 Docker|`FROM node:24-bookworm-slim`，`npm install -g --ignore-scripts @earendil-works/pi-coding-agent`；运行时使用 `-v "$PWD:/workspace"`，并为 `/root/.pi/agent` 配置一个命名卷|通过 `-e` 传入的环境变量在容器内可见；挂载宿主机的 `~/.pi/agent` 会暴露其中的凭据|
|Docker Sandboxes|`sbx run --kit "docker.io/sbx/pi-kit:latest" pi`|代理将占位符替换为真实的提供商密钥；在沙箱内运行 `/login` 会把真实凭据写入沙箱|
|NVIDIA OpenShell|`openshell sandbox create --name pi-sandbox --from pi -- pi`|提供文件系统、进程、网络、凭据和推理策略；远程网关不会挂载你的文件夹|
|gondolin（示例）|`pi -e ~/.pi/agent/extensions/gondolin`；QEMU 微型虚拟机，Node ≥ 23\.6|“虚拟机中的命令继承宿主进程的环境”，所以它并不构成凭据边界|
|sandbox（示例）|`@anthropic-ai/sandbox-runtime 0.0.26` 替换 `bash`；macOS 上使用 `sandbox-exec`，Linux 上使用 `bubblewrap`|配置位于 `~/.pi/agent/extensions/sandbox.json` 和 `.pi/sandbox.json`；其他工具未被沙箱化|
|`tool_call` 关卡（示例）|`permission-gate.ts` 在 `rm -rf`、`sudo` 和 `chmod/chown 777` 前询问，没有 UI 时会阻止它们；`protected-paths.ts` 会阻止对包含 `.env`、`.git/` 或 `node_modules/` 的路径调用 `write` 和 `edit`|依赖正则表达式和子串规则；通过 `bash` 写入 `.env` 的命令，或模式未匹配到的危险命令，仍会通过|



这六种方法都能缩小错误操作的影响范围。命令复制自 `28dcce2` 版本的 `CA/docs/containerization.md` 和示例扩展。指南将整个进程隔离称为“通常是最强的实用选项”，见 `CA/docs/security.md`。

## 组件内部的控制措施



下面各组件都实施了一条范围较窄的规则。它们都不能把 Pi 变成沙箱，但各自堵住了一个具体缺口：

- <strong>凭据：</strong>`auth.json` 以 `0600` 模式写入，其目录以 `0700` 模式创建；“该模式只在创建时应用，因此管理员管理的权限模式和 ACL 会保持不变”，见 `CA/src/core/auth-storage.ts:24`。每次读取—修改—写入都会持有 `proper-lockfile` 锁。`mcp-auth.json` 使用相同后端，见 `CA/src/extensions/mcp/oauth.ts:144`。已经开始的 OAuth 刷新会忽略取消：“提供商可能已经轮换了刷新令牌，因此刷新及其持久化会忽略 `signal`，只受超时限制”，见 `ai/src/auth/resolve.ts:105`。

- <strong>MCP 配置：</strong> 项目的 `.pi/mcp.json` 只在项目信任时加载，而且不能设置 `auth`：“`auth` 只允许出现在全局 `mcp.json` 中”，因此“仓库不能决定凭据的去向”，见 `CA/src/extensions/mcp/config.ts:133`。设置了 `auth.provider` 的服务器必须使用 `https`，或在 `localhost`、`127.0.0.1`、`[::1]` 上使用 `http`，见 `CA/src/core/mcp-servers.ts:285`。`oauth.callbackUrl` 必须是 `http` 回环 URI，见 `CA/src/core/mcp-servers.ts:178`；`oauth.authServerMetadataUrl` 必须使用 `https` 或回环 `http`，见 `CA/src/core/mcp-servers.ts:201`。

- <strong>MCP OAuth：</strong> 对于不是 `https` 的非回环端点，该流程会抛出 `OAuthInsecureEndpointError`，见 `mcp/src/oauth/flow.ts:121`；当返回的 `iss` 与元数据中的颁发者不同时，会抛出 `OAuthIssuerMismatchError`，见 `mcp/src/oauth/flow.ts:373`。

- <strong>MCP 进程：</strong> stdio 服务器通过 `cross-spawn` 启动，不经过 shell；除 Windows 外，在所有平台上都会分离到各自独立的进程组中，因此关闭时会终止整个进程组，见 `mcp/src/transports/stdio.ts:101`。`env` 和 `headers` 中的值会经过 `resolveConfigValue`，其中开头的 `!` 会让余下内容作为 shell 命令运行，见 `CA/src/core/resolve-config-value.ts:140`。因此，受信任的配置可以在服务器连接时执行代码。

- <strong>Codemode：</strong> 脚本在编译为 WebAssembly 的 QuickJS 中运行，“唯一的能力是调用注入的工具”，见 `codemode/README.md`。前置代码会先冻结内置对象，见 `codemode/src/runtime/prelude-source.ts:28`；编码智能体将 VM 内存上限设为 256 MiB，见 `CA/src/extensions/codemode/execute.ts:55`；工作进程设置 QuickJS 的最大栈大小，见 `codemode/src/runtime/worker.ts:59`；宿主在 `terminate()` 之前设置中断标志，见 `codemode/src/runtime/host.ts:323`。嵌套调用是通过 `ctx.executeTool` 发出的真实调用，所以会应用 `tool_call` 钩子和权限检查，见 `CA/src/extensions/codemode/tool.ts:7`；而且“故障发生前已经执行的调用不会被撤销”，见 `CA/docs/codemode.md`。

- <strong>实验性技术栈：</strong> 没有声明 `replay: "safe"` 的持久化工具，崩溃后绝不会重新运行。`pi-env` 使用固定别名锁定主机密钥，关闭所有转发，每次启动前重新验证守护进程的 SHA\-256，并在静默 30 s 后终止远程进程组。`pi server` 在自己拥有的 `0700` 目录中绑定一个 `0600` 套接字，而且只有持有凭据时才会连接 Radius 中继，见“实验性技术栈”（原书第166页）。

## 供应链



仓库的 `AGENTS.md` 为贡献者和智能体设定了规则：“将 npm 依赖和锁文件的变更作为代码审查。直接外部依赖保持锁定到精确版本。”安装时使用 `--ignore-scripts`，而且“带有生命周期脚本的新依赖必须经过审查，并在 `scripts/generate-coding-agent-install-lock.mjs` 中添加明确的允许列表条目”，见 `AGENTS.md` 的“依赖与安装安全”一节。在 `28dcce2` 版本中，该允许列表有三个条目：`@google/genai@2.21.0`、`esbuild@0.28.2` 和 `protobufjs@7.6.6`，每个都附有一行理由，见 `scripts/generate-coding-agent-install-lock.mjs:17`。`scripts/check-pinned-deps.mjs` 强制要求精确版本；除非设置了 `PI_ALLOW_LOCKFILE_CHANGE`，否则提交前检查会阻止锁文件提交，见 `scripts/check-lockfile-commit.mjs:5`。上面的 Docker 配方在安装 Pi 时也使用 `--ignore-scripts`。



> <strong>这对你意味着什么：</strong>
> 
> - 对每个仓库分别决定是否信任，并记住，被拒绝信任的项目仍然会提供 `AGENTS.md`。
> 
> - 在 CI 中传入 `--approve` 或 `--no-approve`；非交互模式永远不会弹出询问。
> 
> - 当仓库或任务不属于你时，在容器或虚拟机中运行 Pi；工具级隔离会把扩展留在宿主机上。
> 
> - 不要将提供商凭据放入任何被隔离程序的环境中；也可以改用 Docker Sandboxes 代理。
> 
> - 加载扩展之前先审查它：它会在 Pi 进程中，以你的权限运行。
> 
> 



> 来源：`CA/docs/security.md`；`CA/docs/containerization.md`；`SECURITY.md`；`AGENTS.md` 的“依赖与安装安全”一节；`CA/src/core/project-trust.ts`（`resolveProjectTrusted`）；`CA/src/core/trust-manager.ts`（`TRUST_REQUIRING_PROJECT_CONFIG_RESOURCES`、`hasTrustRequiringProjectResources`、`getProjectTrustOptions`、`ProjectTrustStore`）；`CA/src/core/resource-loader.ts`（`loadProjectTrustExtensions`、`loadCurrentExtensionSet`、`loadProjectContextFiles`）；`CA/src/core/extensions/runner.ts`（`emitProjectTrustEvent`）；`CA/src/main.ts`（`sessionDir`）；`CA/src/core/package-manager.ts`（`assertProjectTrustedForScope`）；`CA/examples/extensions/{project-trust.ts, permission-gate.ts, protected-paths.ts, gondolin/, sandbox/}`；`CA/src/core/auth-storage.ts`；`ai/src/auth/resolve.ts`（`refreshStoredOAuthCredential`）；`CA/src/extensions/mcp/config.ts`、`oauth.ts`；`CA/src/core/mcp-servers.ts`（`validateOAuth`、`auth` 检查）；`mcp/src/oauth/flow.ts`；`mcp/src/transports/stdio.ts`；`CA/src/core/resolve-config-value.ts`；`codemode/README.md`；`codemode/src/runtime/{prelude-source,worker,host}.ts`；`CA/src/extensions/codemode/execute.ts`、`tool.ts`；`CA/docs/codemode.md`；`scripts/generate-coding-agent-install-lock.mjs`；`scripts/check-pinned-deps.mjs`；`scripts/check-lockfile-commit.mjs`。
> 
>
