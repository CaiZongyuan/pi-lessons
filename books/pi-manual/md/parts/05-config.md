Files on disk decide the model, the context and the tools; extensions can intercept nearly everything else.

磁盘上的文件决定模型、上下文和工具；扩展几乎可以拦截其余的一切。

![](images/8e4327e610837fdee54058a79abb5dad9c7ae9a7d806e261fda13349a4284251.jpg)

## 5.1 Configuration, models and auth

## 5.1 配置、模型与鉴权

Pi reads its configuration from two directories, one per user and one per project. The project directory counts only after the folder is trusted, and four settings never come from it at all.

Pi 从两个目录读取配置，一个属于用户，一个属于项目。项目目录只有在文件夹被信任之后才起作用，而且有四个设置项永远不从它那里来。

Before Pi sends a single request it has to settle four questions: where its files live, which settings apply, which model to call, and which credential to send. Each answer comes from files on disk, in a fixed order. This section maps the agent directory, shows how user and project settings merge, reads the models.json schema field by field, and gives the resolution order for API keys and for the initial model.

在 Pi 发出第一个请求之前，它必须先定下四件事：文件放在哪里、哪些设置生效、要调用哪个模型、要发送哪份凭据。每一个答案都来自磁盘上的文件，且顺序固定。本节梳理 agent 目录，说明用户设置与项目设置如何合并，逐字段解读 models.json 的 schema，并给出 API key 与初始模型的解析顺序。

## Two directories

## 两个目录

The agent directory is the root of everything Pi stores per user. getAgentDir() returns \$PI_CODING_AGENT_DIR when it is set and \~/.pi/agent otherwise CA/src/config.ts:605. Neither name is hard-coded. CONFIG_DIR_NAME comes from piConfig.config Dir in package.json and defaults to .pi; APP_NAME comes from piConfig.name and defaults to pi CA/src/config.ts:579. The environment variable is built from the app name, so a rebranded fork named tau reads TAU_CODING_AGENT_DIR CA/src/config.ts:585.

agent 目录是 Pi 按用户存储一切内容的根。getAgentDir() 在 \$PI_CODING_AGENT_DIR 已设置时返回它，否则返回 \~/.pi/agent CA/src/config.ts:605。这两个名字都不是硬编码的。CONFIG_DIR_NAME 来自 package.json 里的 piConfig.config Dir，默认值是 .pi；APP_NAME 来自 piConfig.name，默认值是 pi CA/src/config.ts:579。环境变量由应用名拼成，所以一个改名为 tau 的分支会读取 TAU_CODING_AGENT_DIR CA/src/config.ts:585。

```txt
FIG. 5.1 WHERE PI KEEPS ITS FILES
~/.pi/agent/ user scope · always loaded
| settings.json strict JSON, file-locked
| keybindings.json
| models.json custom providers and models · comments allowed
| models-store.json dynamic catalogue cache
| auth.json credentials · created 0600, directory 0700
| mcp.json · mcp-auth.json · mcp.log log rotates to mcp.log.1 past 5 MB
| trust.json project trust decisions
| AGENTS.md | CLAUDE.md global context file
| SYSTEM.md · APPEND_SYSTEM.md replace or append the system prompt
| extensions/skills/prompts/themes/auto-discovered
| sessions/--<cwd>--/*.json one directory per working directory
| npm/node_modules/ · git/<host>/<path> user-scope packages
| tmp/extensions/ one-off-e installs·0700
| bin/ managed fd and rg
| crashes.json · pi-debug.log
~/.agents/skills/ Agent Skills standard · user scope
<project>/.pi/ only when the project is trusted
| settings.json · mcp.json · SYSTEM.md · APPEND_SYSTEM.md
| extensions/skills/prompts/themes/
| npm/ · git/ project-scope packages
<project>/.agents/skills/ cwd up to the git root · trusted only
<every ancestor>/AGENTS.md | CLAUDE.md no trust required
```

One directory always loads; the other waits for trust. Paths at the pinned commit. The session directory name is the working directory with its leading slash removed and every /, \ and : turned into -, wrapped in -- CA/src/core/session-manager.ts:592. From config.ts, auth-storage.ts:25, extensions/mcp/log.ts:10, package-manager.ts:232 and trust-manager.ts:30

一个目录始终加载；另一个要等信任。路径以锁定的提交为准。会话目录名是去掉前导斜杠、并把每个 /、\ 和 : 换成 - 之后的工作目录，外面包上 -- CA/src/core/session-manager.ts:592。取自 config.ts、auth-storage.ts:25、extensions/mcp/log.ts:10、package-manager.ts:232 和 trust-manager.ts:30

The rose entries are the ones hasTrustRequiringProjectResources() checks: any of settings.json, mcp.json, extensions, skills, prompts, themes, SYSTEM.md or APPEND_SYSTEM.md under <cwd>/.pi, or an .agents/skills directory in the working directory or any ancestor CA/src/core/trust-manager.ts:186. When none exists, the project counts as trusted without a prompt. How the decision is made when one does exist is in context files, skills, templates, themes and packages (p. 106).

图中标为 rose 的条目就是 hasTrustRequiringProjectResources() 要检查的东西：<cwd>/.pi 下的 settings.json、mcp.json、extensions、skills、prompts、themes、SYSTEM.md 或 APPEND_SYSTEM.md 任意一个，或者工作目录及其任一祖先目录里的 .agents/skills 目录 CA/src/core/trust-manager.ts:186。一个都不存在时，项目无需提示即视为受信任。真的存在时判定方式如何，见上下文文件、技能、模板、主题与包 (p. 106)。

auth.json is created with mode 0600 inside a directory created with 0700. The mode applies only on creation, so permissions an administrator set later are left alone CA/src/core/auth-storage.ts:24. Every read and write of auth.json, settings.json and trust.json takes a proper-lockfile lock, retried up to 10 times at 20 ms intervals CA/src/core/auth-storage.ts:69.

auth.json 以 0600 模式创建，外层目录以 0700 模式创建。该模式只在创建时生效，因此管理员之后设置的权限不会被改动 CA/src/core/auth-storage.ts:24。对 auth.json、settings.json 和 trust.json 的每一次读写都会获取 proper-lockfile 锁，最多重试 10 次、间隔 20 ms CA/src/core/auth-storage.ts:69。

#### Settings: two files, one merge

#### 设置：两个文件，一次合并

SettingsManager reads \~/.pi/agent/settings.json and <cwd>/.pi/settings.json and merges them with deepMergeSettings(global, project) CA/src/core/settings-manager.ts:250. An untrusted project contributes {} CA/src/core/settings-manager.ts:474. Both files are strict JSON: JSON.parse after a BOM strip, with no comment stripping CA/src/core/settings-manager.ts:487.

SettingsManager 读取 \~/.pi/agent/settings.json 和 <cwd>/.pi/settings.json，用 deepMergeSettings(global, project) 把两者合并 CA/src/core/settings-manager.ts:250。未受信任的项目贡献 {} CA/src/core/settings-manager.ts:474。两个文件都是严格 JSON：先去掉 BOM 再 JSON.parse，不剥离注释 CA/src/core/settings-manager.ts:487。

![](images/f8685fd91162dafd9c34c78554898f055bd412ced2ec20be6500b6f072c960a8.jpg)
The project wins every collision except four. Schematic. Merge rules from deepMergeObjects and mergeDefaultTools CA/src/core/settingsmanager.ts:195; global-only reads at settings-manager.ts:1023, :1100, :1176 and main.ts:594.

除了四个键，每一次冲突都由项目一方胜出。示意图。合并规则来自 deepMergeObjects 和 mergeDefaultTools CA/src/core/settingsmanager.ts:195；仅全局的读取位于 settings-manager.ts:1023、:1100、:1176 和 main.ts:594。

The merge recurses only into plain objects. Arrays and scalars from the project replace the global value outright. default Tools is the one exception: a project list made only of +name and -name entries is appended to the global list, so it edits the inherited selection instead of replacing it CA/src/core/settings-manager.ts:225. The base selection is read, bash, edit, write CA/src/core/settings-manager.ts:215.

合并只递归进入普通对象。项目方的数组和标量直接替换全局值。default Tools 是唯一的例外：只含 +name 和 -name 条目的项目列表会追加到全局列表之后，因此它是在编辑继承而来的选择，而不是替换 CA/src/core/settings-manager.ts:225。基础选择是 read、bash、edit、write CA/src/core/settings-manager.ts:215。

Four keys are read from the global file only:

有四个键只从全局文件读取：

<table><tr><td>键</td><td>默认值</td><td>为何只放全局</td><td>参见</td></tr><tr><td>defaultProjectTrust</td><td>&quot;ask&quot;</td><td>项目不能自行决定自己的信任</td><td>settings-manager.ts:1100</td></tr><tr><td>cache Warming</td><td>&quot;streaming&quot;</td><td>&quot;每次刷新都要花钱&quot;</td><td>settings-manager.ts:1023</td></tr><tr><td>http Proxy</td><td>unset</td><td>以 HTTP_PROXY 和 HTTPS_PROXY 形式应用</td><td>main.ts:594</td></tr><tr><td>deviceId</td><td>首次使用时创建（登录对话框）</td><td>本次安装的稳定 UUID</td><td>settings-manager.ts:1176</td></tr></table>

A project file can set these keys; Pi ignores them. The comment on cache Warming is quoted from settings-manager.ts:182.

项目文件可以设置这些键；Pi 会忽略它们。关于 cache Warming 的注释引自 settings-manager.ts:182。

The resource arrays packages, extensions, skills, prompts and themes do pass through the merge, but nothing reads the merged value. The package manager reads the global and project files separately and loads both CA/src/core/packagemanager.ts:920; context files, skills, templates, themes and packages (p. 106) gives the order. On load, old keys are migrated in memory: queue Mode becomes steering Mode, the boolean websockets becomes transport: "websocket" or "sse", an object-form skills becomes an array, and retry.maxDelayMs becomes retry.provider.maxRetryDelayMs CA/src/core/settings-manager.ts:504. settings reference (p. 202) lists every key.

资源数组 packages、extensions、skills、prompts 和 themes 确实会经过合并，但没有任何东西读取合并后的值。包管理器分别读取全局文件和项目文件，并把两者都加载 CA/src/core/packagemanager.ts:920；顺序见上下文文件、技能、模板、主题与包 (p. 106)。加载时，旧键会在内存中迁移：queue Mode 变成 steering Mode，布尔值 websockets 变成 transport: "websocket" 或 "sse"，对象形式的 skills 变成数组，retry.maxDelayMs 变成 retry.provider.maxRetryDelayMs CA/src/core/settings-manager.ts:504。每个键都列在设置参考 (p. 202) 里。

## models.json

## models.json

\~/.pi/agent/models.json adds providers and models or patches built-in ones. Unlike settings.json it may contain comments: ModelConfig.load() runs stripJsonComments before JSON.parse, then validates the result against a TypeBox schema CA/src/core/model-config.ts:310. A parse or schema error does not stop Pi. The config loads empty and the error is shown, for example as models.json error: … in the TUI. The file is read again on every catalogue refresh CA/src/core/modelruntime.ts:840, and opening the /model selector starts one in the background.

\~/.pi/agent/models.json 用来添加供应商和模型，或者给内置的那些打补丁。与 settings.json 不同，它可以包含注释：ModelConfig.load() 先跑 stripJsonComments 再 JSON.parse，然后按 TypeBox schema 校验结果 CA/src/core/model-config.ts:310。解析错误或 schema 错误不会让 Pi 停下。配置会按空加载，错误则被显示出来，例如在 TUI 里显示 models.json error: …。每次刷新目录都会重新读取该文件 CA/src/core/modelruntime.ts:840，而打开 /model 选择器会在后台触发一次刷新。

```typescript const ProviderConfigSchema = Type.Object({
    name: Type.Optional(Type.String({ min Length: 1 }),
    base Url: Type.Optional(Type.String({ min Length: 1 }),
    api Key: Type.Optional(Type.String({ min Length: 1 }),
    api: Type.Optional(Type.String({ min Length: 1 }),
    oauth: Type.Optional(Type.Literal("radius")),
    headers: Type.Optional(Type.Record(Type.String(), Type.String()))
    compat: Type.Optional(ProviderCompatSchema),
    auth Header: Type.Optional(Type.Boolean()),
    models: Type.Optional(Type.Array(ModelDefinitionSchema)),
    model Overrides: Type.Optional(Type.Record(Type.String(), ModelOverrideSchema)),
});

const ModelsConfigSchema = Type.Object({
    providers: Type.Record(Type.String(), ProviderConfigSchema),
});
```

Lines 242–257, uncut. ProviderCompatSchema is a union of the OpenAI Completions, OpenAI Responses and Anthropic Messages compat objects.

第 242–257 行，未删节。ProviderCompatSchema 是 OpenAI Completions、OpenAI Responses 和 Anthropic Messages 三种 compat 对象的联合。

base Url, api: the endpoint and wire API. A custom model needs both, at model or provider level, or inherited from a built-in model of the same provider. Otherwise loading fails with no "api" specified or "base Url" is required when defining custom models CA/src/core/provider-composer.ts:216.

base Url、api：端点与通信 API。自定义模型两者都需要，可以写在模型级或供应商级，也可以从同一供应商的内置模型继承。否则加载失败并报 no "api" specified 或 "baseUrl" is required when defining custom models CA/src/core/provider-composer.ts:216。

api Key, headers: values in the syntax described below.

api Key、headers：取值语法见下文。

auth Header: when true, adds Authorization: Bearer <key> with the resolved key. With no key it fails with auth Header requires a resolved API key CA/src/core/provider-composer.ts:382.

auth Header：为 true 时，用解析出的 key 加上 Authorization: Bearer <key>。没有 key 时失败并报 auth Header requires a resolved API key CA/src/core/provider-composer.ts:382。

oauth: "radius": the only OAuth value the schema accepts. It requires base Url CA/src/core/provider-composer.ts:306.

oauth: "radius"：schema 唯一接受的 OAuth 取值。它需要 base Url CA/src/core/provider-composer.ts:306。

models: full definitions. A definition whose id matches a built-in chat model of that provider replaces it in place; otherwise it is appended CA/src/core/provider-composer.ts:331.

models：完整定义。id 与该供应商某个内置对话模型匹配的定义会就地替换它；否则追加到末尾 CA/src/core/provider-composer.ts:331。

model Overrides: partial patches keyed by model id. They accept every definition field except id, api and base Url.

model Overrides：以模型 id 为键的部分补丁。除 id、api 和 base Url 之外，定义里的所有字段都可以写。

A provider entry that sets none of base Url, headers, compat, model Overrides, models, api Key, oauth or auth Header is rejected CA/src/core/provider-composer.ts:310. A new model takes these defaults when fields are omitted CA/src/core/provider-composer.ts:236:

base Url、headers、compat、model Overrides、models、api Key、oauth、auth Header 一个都没设置的供应商条目会被拒绝 CA/src/core/provider-composer.ts:310。新模型在字段缺省时采用这些默认值 CA/src/core/provider-composer.ts:236：

<table><tr><td>字段</td><td>默认值</td></tr><tr><td>name</td><td>与 id 相同</td></tr><tr><td>reasoning</td><td>false</td></tr><tr><td>input</td><td>[&quot;text&quot;]</td></tr><tr><td>cost</td><td>{ input: 0, output: 0, cache Read: 0, cache Write: 0 }</td></tr><tr><td>context Window</td><td>128000</td></tr><tr><td>max Tokens</td><td>16384</td></tr></table>

An unpriced local model costs nothing in Pi’s accounting. From modelFromJson(). context Window and max Tokens must be positive when set.

在 Pi 的记账里，没有定价的本地模型不计费用。取自 modelFromJson()。context Window 和 max Tokens 设置时必须为正数。

A local lama.cpp or vLLM server that speaks the OpenAI Chat Completions API needs one provider entry. Every field in this example is in the schema at the pinned commit, including the qwen-chat-template thinking format CA/src/core/modelconfig.ts:105:

一个说 OpenAI Chat Completions API 的本地 llama.cpp 或 vLLM 服务器只需要一个供应商条目。这个例子里的每个字段都在锁定提交的 schema 中，包括 qwen-chat-template 这个 thinking 格式 CA/src/core/modelconfig.ts:105：

```json
a local OpenAI-compatible endpoint ~/.pi/agent/models.json JSON
{
    "providers": {
    "local": {
    "base Url": "http://127.0.0.1:8080/v1",
    "api": "openai-completions",
    "api Key": "none",
    "compat": { "supportsDeveloperRole": false, "thinking Format": "qwen-chat-template" },
    "models": [{ "id": "qwen3-coder", "reasoning": true, "context Window": 262144 }]
    }
    }
}
```

Illustrative configuration checked against ModelsConfigSchema. The dummy api Key makes the model available; auth, cost, retries and the catalog (p. 41) explains why a model without resolvable credentials stays out of /model.

这是示意性配置，已按 ModelsConfigSchema 校验。dummy 的 api Key 让这个模型可用；鉴权、成本、重试与目录 (p. 41) 解释了为什么解析不出凭据的模型不会出现在 /model 里。

## Value syntax

## 取值语法

api Key and every header value go through the same resolver CA/src/core/resolve-config-value.ts:145. A value that starts with ! is a shell command; its trimmed stdout is the value, and the command has a 10-second timeout CA/src/core/resolve-configvalue.ts:189. Any other value is a template: \$NAME and \${NAME} interpolate environment variables, \$\$ is a literal \$ and \$! a literal !. If any referenced variable is unset, the whole value is unresolved, and resolving a key then fails with Failed to resolve API key for provider "<id>" from environment variable: NAME CA/src/core/resolve-configvalue.ts:243.

api Key 和每个 header 取值都走同一个解析器 CA/src/core/resolve-config-value.ts:145。以 ! 开头的取值是一条 shell 命令，其 trim 过的 stdout 就是取值，命令有 10 秒超时 CA/src/core/resolve-configvalue.ts:189。其他取值都是模板：\$NAME 和 \${NAME} 插值环境变量，\$\$ 是字面的 \$，\$! 是字面的 !。若引用的任何变量未设置，整个取值视为未解析，此时解析一个 key 会失败并报 Failed to resolve API key for provider "<id>" from environment variable: NAME CA/src/core/resolve-configvalue.ts:243。

The comment on resolveConfigValue() says command output is cached for the life of the process. The key and header path does not use it: composeApiKeyAuth() calls resolveConfigValueOrThrow(), which runs the uncached variant CA/src/core/providercomposer.ts:467. A ! command in models.json runs at every credential resolution, so keep it fast. CA/docs/models.md states the uncached behaviour correctly.

resolveConfigValue() 上的注释说命令输出在进程生命周期内缓存。key 和 header 这条路径不用它：composeApiKeyAuth() 调用的是 resolveConfigValueOrThrow()，它跑的是不缓存的版本 CA/src/core/providercomposer.ts:467。models.json 里的 ! 命令在每次解析凭据时都会运行，所以要让它足够快。CA/docs/models.md 对不缓存行为的表述是正确的。

## API key resolution

## API key 解析

When several credential sources exist for one provider, the composed ApiKeyAuth.resolve() picks the first that applies CA/src/core/provider-composer.ts:457:

当一个供应商存在多个凭据来源时，组合出的 ApiKeyAuth.resolve()挑第一个适用的 CA/src/core/provider-composer.ts:457：

![](images/26c84150e6e56521d972a6914caea90ae97ccf7e7ab82104675704b325afc190.jpg)
A stored login beats a configured key. First match wins. Step 1 is a credential that RuntimeCredentials.read() returns ahead of the store CA/src/core/runtime-credentials.ts:24, so it lands in the same branch as step 2. Steps 2–4 are the three branches of resolve(). The same order is stated in CA/docs/models.md.

已存下的登录凭据胜过配置的 key。最先匹配者胜出。步骤 1 是 RuntimeCredentials.read() 在存储之前返回的凭据 CA/src/core/runtime-credentials.ts:24，因此它落在与步骤 2 相同的分支里。步骤 2–4 是 resolve() 的三个分支。CA/docs/models.md 里也是这个顺序。

--api-key is set only after the model is known. Without one, startup reports --api-key requires a model to be specified via --model, --provider/--model, or --models CA/src/main.ts:832. In step 3 an extension’s api Key takes precedence over the models.json value for the same provider CA/src/core/provider-composer.ts:392; the same holds for auth Header and for headers with the same name.

--api-key 只在模型确定之后才被读取。没有它时，启动会报告 --api-key requires a model to be specified via --model, --provider/--model, or --models CA/src/main.ts:832。在步骤 3 里，扩展的 api Key 优先于同一供应商在 models.json 里的取值 CA/src/core/provider-composer.ts:392；auth Header 以及同名的 headers 同理。

Step 2 outranks step 3. After /login stores a key for a provider, editing api Key in models.json changes nothing until /logout removes the stored credential. /logout touches only what /login saved; environment variables and models.json are left as they are.

步骤 2 高于步骤 3。在 /login 为某个供应商存下 key 之后，改 models.json 里的 api Key 不会有任何效果，直到 /logout 删掉那份已存凭据。/logout 只动 /login 保存过的内容；环境变量和 models.json 原样不动。

## Choosing the model

## 选择模型

A model reference is provider/id or a bare id, with an optional :level thinking sufix. parseModelPattern() first tries the whole string as a model. Only when that fails does it split on the last : and treat the sufix as a thinking level, if it names one CA/src/core/model-resolver.ts:204. OpenRouter ids such as …:exacto therefore resolve as ids. An exact match is caseinsensitive. A partial match prefers aliases, ids without a -YYYYMMDD sufix or ending in -latest, over dated ids CA/src/core/model-resolver.ts:74. Glob patterns in --models and enabled Models match case-insensitively CA/src/core/model-resolver.ts:318.

模型引用是 provider/id 或一个裸 id，可带可选的 :level thinking 后缀。parseModelPattern() 先把整个字符串当作模型来试。只有失败时，它才按最后一个 : 切开，并在后缀恰好是一个 thinking level 时这样处理 CA/src/core/model-resolver.ts:204。因此像 …:exacto 这样的 OpenRouter id 会按 id 解析。精确匹配不区分大小写。部分匹配时，优先别名、没有 -YYYYMMDD 后缀或以 -latest 结尾的 id，而不是带日期的 id CA/src/core/model-resolver.ts:74。--models 和启用的 Models 里的 glob 模式不区分大小写 CA/src/core/model-resolver.ts:318。

The model a session starts with comes from a ladder spread over three functions:

会话起始时用的模型来自一条分布在三个函数里的阶梯：

![](images/668ee44e1063cab203f823853ed06d1f53de54319a2f829e05a84aa9a14a4ace.jpg)

A resumed session keeps its model unless the command line overrides it. First match wins. Steps 1–2 run in buildSessionOptions(), step 3 in createAgentSession(), steps 4–5 in findInitialModel().

恢复的会话会保留它的模型，除非命令行覆盖它。最先匹配者胜出。步骤 1–2 在 buildSessionOptions() 中，步骤 3 在 createAgentSession() 中，步骤 4–5 在 findInitialModel() 中。

## D O C ≠ C O D E

## 文 档 ≠ 代 码

The comment above findInitialModel() lists five steps, the third being “Restored from session (if continuing/resuming)” CA/src/core/model-resolver.ts:618. The function has no session step. Session restore happens before it is called, in createAgentSession() CA/src/core/sdk.ts:213, and the function’s own inline comments number the settings default as step 3.

findInitialModel() 上方的注释列了五个步骤，第三个是「Restored from session (if continuing/resuming)」CA/src/core/model-resolver.ts:618。这个函数里没有会话步骤。会话恢复发生在它被调用之前，在 createAgentSession() 里 CA/src/core/sdk.ts:213，而这个函数自己的内联注释把设置里的默认值编为第3 步。

## Virtual models

## 虚拟模型

A virtual model is a catalogue entry that picks a physical model per request. An extension registers one with pi.registerVirtualModel({ provider, id, name, route }) CA/src/core/extensions/types.ts:1872. Pi calls route(request, ctx) before each request with request.reason set to user, continuation, retry or direct; the router returns a physical model, a thinking level and optional state CA/src/core/virtual-models.ts:50. The selection, ctx.model and model_change entries name the virtual model; assistant messages record the physical one. Router state is stored on the session branch as a custom entry with custom Type: "pi.virtual-model-state" CA/src/core/virtual-models.ts:8. CA/docs/virtual-models.md documents the full contract.

虚拟模型是一个目录条目，它为每次请求挑选一个物理模型。扩展用 pi.registerVirtualModel({ provider, id, name, route }) 注册一个 CA/src/core/extensions/types.ts:1872。Pi 在每次请求前调用 route(request, ctx)，其中 request.reason 设为 user、continuation、retry 或 direct；路由返回一个物理模型、一个 thinking level 以及可选的状态 CA/src/core/virtual-models.ts:50。选择记录、ctx.model 和 model_change 条目里写的是虚拟模型名；assistant 消息记录的是物理模型。路由状态以自定义条目的形式存在会话分支上，customType 为 "pi.virtual-model-state" CA/src/core/virtual-models.ts:8。完整契约见 CA/docs/virtual-models.md。

## W H A T T H I S M E A N S F O R Y O U

## 这 对 你 意 味 着 什 么

Put credentials in auth.json with /login, or in models.json as \$VAR references; never commit literal keys to a project.

用 /login 把凭据放进 auth.json，或在 models.json 里写成 \$VAR 引用；绝不要把字面的 key 提交进项目。

Keep settings.json free of comments. Only models.json strips them.

settings.json 里不要写注释。只有 models.json 会剥离注释。

Set defaultProjectTrust, cache Warming and http Proxy in the global file; a project file cannot change them.

把 defaultProjectTrust、cache Warming 和 http Proxy 设到全局文件里；项目文件改不了它们。

Pin a model for scripts with --model provider/id:level; a resumed session otherwise keeps its last model.

脚本用 --model provider/id:level 固定模型；否则恢复的会话会保留上一个模型。

Sources: CA/src/config.ts (getAgentDir, CONFIG_DIR_NAME, ENV_AGENT_DIR); CA/src/core/trust-manager.ts (TRUST_REQUIRING_PROJECT_CONFIG_RESOURCES, hasTrustRequiringProjectResources); CA/src/core/auth-storage.ts (FileAuthStorageBackend); CA/src/core/session-manager.ts:592; CA/src/core/settings-manager.ts (deepMergeObjects, mergeDefaultTools, deepMergeSettings, migrate Settings, global-only getters) CA/src/main.ts (buildSessionOptions, -apikey check, applyHttpProxySettings); CA/src/core/model-config.ts (ModelConfig.load, schemas); CA/src/core/providercomposer.ts (modelFromJson, applyModelsJson, composeApiKeyAuth, withConfiguredAuth); CA/src/core/resolve-config-value.ts; CA/src/core/runtime-credentials.ts; CA/src/core/model-resolver.ts (isAlias, parseModelPattern, resolveModelScopeFromModels, findInitialModel); CA/src/core/sdk.ts (createAgentSession); CA/src/core/virtual-models.ts; CA/docs/models.md; CA/docs/virtual-models.md

来源：CA/src/config.ts（getAgentDir、CONFIG_DIR_NAME、ENV_AGENT_DIR）；CA/src/core/trust-manager.ts（TRUST_REQUIRING_PROJECT_CONFIG_RESOURCES、hasTrustRequiringProjectResources）；CA/src/core/auth-storage.ts（FileAuthStorageBackend）；CA/src/core/session-manager.ts:592；CA/src/core/settings-manager.ts（deepMergeObjects、mergeDefaultTools、deepMergeSettings、migrate Settings、仅全局的 getter）CA/src/main.ts（buildSessionOptions、-apikey 检查、applyHttpProxySettings）；CA/src/core/model-config.ts（ModelConfig.load、schemas）；CA/src/core/providercomposer.ts（modelFromJson、applyModelsJson、composeApiKeyAuth、withConfiguredAuth）；CA/src/core/resolve-config-value.ts；CA/src/core/runtime-credentials.ts；CA/src/core/model-resolver.ts（isAlias、parseModelPattern、resolveModelScopeFromModels、findInitialModel）；CA/src/core/sdk.ts（createAgentSession）；CA/src/core/virtual-models.ts；CA/docs/models.md；CA/docs/virtual-models.md

# 5.2 Context files, skills, templates, themes, packages

# 5.2 上下文文件、技能、模板、主题、包

Every resource Pi loads goes through one function,

Pi 加载的每一种资源都经过同一个函数，

\`DefaultResourceLoader.reload()\`. It settles trust, collects paths from five

它先确定信任，再从五类来源里收集路径，

kinds ofsource, and lets thefirst copy ofa name win, so the order it collects in decides everything.

并让同名资源的第一份拷贝胜出，所以收集顺序决定了一切。

A project can ship its own skills, prompt templates, themes and extensions, and so can the user, a package or the command line. When two of them use the same name, one is silently dropped. This section follows reload() from the trust decision to the last theme. It gives the precedence rank that settles collisions, with a capture that puts one skill name in seven places. It then covers each resource kind and the package manager that ships them.

项目可以携带自己的技能、提示词模板、主题和扩展，用户、包和命令行同样可以。当其中两个用了同一个名字时，其中一个会被静默丢弃。本节沿着 reload() 从信任判定一直走到最后一个主题，给出决定冲突的优先级排名，并附上把同一个技能名放进七个位置的实测。随后逐一说明各类资源以及分发它们的包管理器。

## Context files

## 上下文文件

Context files are the AGENTS.md and CLAUDE.md files whose text enters the system prompt as project context (system prompt construction (p. 75)). In each directory Pi takes the first file that exists among AGENTS.override.md, AGENTS.md, AGENTS.MD, CLAUDE.md and CLAUDE.MD CA/src/core/resource-loader.ts:185. Only one file per directory is read.

上下文文件就是 AGENTS.md 和 CLAUDE.md 文件，它们的文本会作为项目上下文进入系统提示词（系统提示词的构造 (p. 75)）。在每个目录里，Pi 从 AGENTS.override.md、AGENTS.md、AGENTS.MD、CLAUDE.md 和 CLAUDE.MD 中取第一个存在的文件 CA/src/core/resource-loader.ts:185。每个目录只读一个文件。

loadProjectContextFiles() reads the agent directory first, then walks from the working directory up to the filesystem root and emits the ancestors root-first, skipping any path already seen CA/src/core/resource-loader.ts:232. In a git linked worktree nested inside its main repository, the main repository’s copy of the same file is skipped, because both cover the same logical repository CA/src/core/resource-loader.ts:214. --no-context-files (-nc) turns loading of.

loadProjectContextFiles() 先读 agent 目录，然后从工作目录一路向上走到文件系统根，并按从根到下的顺序输出各级祖先，跳过任何已见过的路径 CA/src/core/resource-loader.ts:232。在嵌套于主仓库内部的 git linked worktree 中，同一文件在主仓库里的那份拷贝会被跳过，因为两者覆盖的是同一个逻辑仓库 CA/src/core/resource-loader.ts:214。--no-context-files (-nc) 会关闭这项加载。

## F O O T G U N

## 警 告

Context files need no trust. The walk in loadProjectContextFiles() has no trust check, so the AGENTS.md of a freshly cloned, untrusted repository and of every directory above it reaches the model. Trust gates .pi/ and .agents/skills, not context files. Use - nc when the text of a checkout should not reach the model.

上下文文件不需要信任。loadProjectContextFiles() 里的遍历没有信任检查，因此一个刚clone 下来、尚未受信任的仓库及其上层每个目录的 AGENTS.md 都会到达模型。信任把守的是 .pi/ 和 .agents/skills，不是上下文文件。当某个 checkout 的文本不该到达模型时，用 -nc。

## The loading pipeline

## 加载流水线

reload() runs at startup and on /reload CA/src/core/resource-loader.ts:509. Trust is settled first, because it decides whether the project half of the configuration exists at all.

reload() 在启动时和 /reload 时运行 CA/src/core/resource-loader.ts:509。信任最先确定，因为它决定了配置中项目那一半是否存在。

A handler that returns “undecided” passes the question down the ladder. First match wins. Handler order is extension load order CA/src/core/extensions/runner.ts:295. Step 4 uses findNearestTrustEntry(), so trusting a parent folder covers every folder below it CA/src/core/trust-manager.ts:45.

![](images/028092b3a1a35ea25864656441d62b5f74c88ae9bc6ca06c507166f2b4c2d271.jpg)
Trust is decided before anything project-local is read. Steps in source order, resource-loader.ts:509–674. Extensions loaded in the pre-trust pass are reused in step 5, not imported twice CA/src/core/resource-loader.ts:747.

信任在任何项目本地内容被读取之前就决定好。步骤按源码顺序排列，resource-loader.ts:509–674。信任前那一轮加载的扩展会在第 5 步被复用，不会导入两次 CA/src/core/resource-loader.ts:747。

## The trust decision

## 信任判定

The pre-trust pass forces the project to untrusted and loads only user-scope and command-line extensions; built-in extensions wait for the final pass because a loaded extension cannot be unloaded CA/src/core/resource-loader.ts:501. Those extensions can answer the project_trust event. resolveProjectTrusted() then walks a first-match ladder CA/src/core/projecttrust.ts:46:

信任前那一轮强制把项目视为 untrusted，并且只加载用户级和命令行的扩展；内置扩展要等最后那一轮，因为已加载的扩展无法卸载 CA/src/core/resource-loader.ts:501。这些扩展可以回答 project_trust 事件。随后 resolveProjectTrusted() 走一条最先匹配的阶梯 CA/src/core/projecttrust.ts:46：

![](images/4f9332bfe8d9119fe66ceca89518229afc7289d37ca294c95963e0c16bc31caa.jpg)

The prompt reads “Trust project folder? … This allows pi to load .pi settings and resources, install missing project packages, and execute project extensions.” CA/src/core/project-trust.ts:24. Choosing a “this session only” option writes nothing to trust.json.

提示语是「Trust project folder? … This allows pi to load .pi settings and resources, install missing project packages, and execute project extensions.」CA/src/core/project-trust.ts:24。选择「this session only」选项不会向 trust.json 写入任何东西。

## F O O T G U N
## 警 告
The two halves of .agents/skills handling disagree about how far up to look. hasTrustRequiringProjectResources() checks every ancestor up to the filesystem root CA/src/core/trust-manager.ts:196. Skill discovery stops at the git root CA/src/core/package-manager.ts:468. An .agents/skills directory above the repository root makes Pi ask for trust, and after you grant it, none of its skills load.

.agents/skills 处理的两半对「要向上查到多远」意见不一致。hasTrustRequiringProjectResources() 会检查一路到文件系统根的每个祖先 CA/src/core/trust-manager.ts:196，而技能发现止于 git 根 CA/src/core/package-manager.ts:468。仓库根之上的 .agents/skills 目录会让 Pi 询问是否信任，而一旦你授予信任，它的技能又一个都加载不了。

#### Collisions: the precedence rank

#### 冲突：优先级排名

package Manager.resolve() collects resources into one map per kind, then sorts them by resourcePrecedenceRank() CA/src/core/package-manager.ts:192. Lower ranks sort first, and the first copy of a name wins.

package Manager.resolve() 把资源按类别收进各自的映射表，然后按 resourcePrecedenceRank() 排序 CA/src/core/package-manager.ts:192。排名靠前的排在前面，同名的第一份拷贝胜出。

<table><tr><td>排名</td><td>来源</td><td>例子</td></tr><tr><td>0</td><td>项目设置条目</td><td>.pi/settings.json 里的 skills: [&quot;/tools/skills&quot;]</td></tr><tr><td>1</td><td>项目，自动发现</td><td>.pi/skills/，然后是从 cwd 向上到 git 根的 .agents/skills/</td></tr><tr><td>2</td><td>用户设置条目</td><td>~/.pi/agent/settings.json 里的 skills</td></tr><tr><td>3</td><td>用户，自动发现</td><td>~/.pi/agent/skills/，然后是 ~/.agents/skills/</td></tr><tr><td>4</td><td>包资源</td><td>包贡献的任何东西，项目包先于用户包</td></tr><tr><td>5</td><td>内置</td><td>builtin:mcp、builtin:codemode……（仅扩展）</td></tr></table>

A settings entry outranks the conventional directory of the same scope. From resourcePrecedenceRank() and the insertion order of addAutoDiscoveredResources() CA/src/core/package-manager.ts:2413. JavaScript’s sort is stable, so equal ranks keep insertion order.

设置条目的排名高于同一作用域的约定目录。取自 resourcePrecedenceRank() 以及 addAutoDiscoveredResources() 的插入顺序 CA/src/core/package-manager.ts:2413。JavaScript 的 sort 是稳定的，因此排名相同者保持插入顺序。

The rank is not the whole order. reload() puts command-line paths around the ranked list, and puts them in diferent places for diferent kinds CA/src/core/resource-loader.ts:573. Extensions from -e go first. Skills, prompts and themes from packages named with -e also go first, but loose --skill, --prompt-template and --theme paths are appended last. The capture kit put a skill named dup, a template /dup and a tool dup_tool in every scope and asked the loader which won:

排名并不是全部顺序。reload() 把命令行的路径放在排名列表的周边，而且对不同类别放在不同位置 CA/src/core/resource-loader.ts:573。来自 -e 的扩展排在最前。用 -e 指定的包所带来的技能、提示词和主题也排在最前，但零散的 --skill、--prompt-template 和 --theme 路径追加在最后。实测工具把一个名为 dup 的技能、一个 /dup 模板和一个 dup_tool 工具放进每个作用域，然后问加载器哪个胜出：

```javascript one name in every scope research/capture/resources-precedence.mjs JS
const loader = new DefaultResourceLoader({
    cwd, agent Dir, settings Manager,
    additionalSkillPaths: [path.join(root, "cli-skill")],
    additionalPromptTemplatePaths: [path.join(root, "cli-prompt")],
    additionalExtensionPaths: [path.join(root, "cli-ext.js")],
});
await loader.reload();
```

Cut to the call; the script first writes seven dup skills, three /dup templates and three extensions that each register dup_tool, under a temporary HOME. Run against the pinned dist/ build, ofline.

只截到调用处；脚本先在一个临时 HOME 下写入七份 dup 技能、三个 /dup 模板和三个各自注册 dup_tool 的扩展。对锁定的 dist/ 构建离线运行。

```shell
### §skills (name "dup" in seven places; first in load order wins)
winner: project settings.skills loser: project .pi/skills (auto)
loser: project .agents/skills (auto)
loser: user settings.skills loser: user ~/.pi/agent/skills (auto)
loser: user ~/.agents/skills (auto)
loser: CLI --skill

### $prompts (/dup in three places)
winner: project .pi/prompts (auto)
loser: user ~/.pi/agent/prompts (auto)
loser: CLI --prompt-template

### $extensions (load order; each registers tool "dup_tool")
loaded: CLI -eloaded: project .pi/extensions (auto)
loaded: user ~/.pi/agent/extensions (auto)
error: project .pi/extensions (auto): Tool "dup_tool" conflicts with CLI -eerror: user ~/.pi/agent/extensions (auto): Tool "dup_tool" conflicts with CLI -e
```

## F O O T G U N
## 警 告
--skill and --prompt-template cannot override anything. They are appended after every discovered and configured path CA/src/core/resource-loader.ts:597, so a skill passed on the command line loses to any same-named skill on disk, with only a collision diagnostic. -e is the opposite: what it names loads first, including the skills and templates of a package. To test a replacement skill, rename it, or pass a directory with a skills/ folder to -e as a local package. The duplicate tool in the last block is a diferent matter: in the CLI it stops startup (extensions, loading and the API (p. 113)).

--skill 和 --prompt-template 无法覆盖任何东西。它们被追加在所有发现到的和配置的路径之后 CA/src/core/resource-loader.ts:597，所以命令行传入的技能会输给磁盘上任何同名的技能，只留下一条冲突诊断。-e 正相反：它指名的内容最先加载，包括某个包的技能和模板。要测试一个替代用的技能，给它改名，或者把一个含skills/ 文件夹的目录作为本地包传给 -e。最后一段里的重复工具是另一回事：在 CLI 中它会中止启动（扩展、加载与 API (p. 113)）。

## Skills

## 技能

A skill is a directory holding SKILL.md in the Agent Skills format, or a loose Markdown file with frontmatter (system prompt construction (p. 75) shows where skills land in the prompt). The loader reads three frontmatter fields CA/src/core/skills.ts:67:

技能是一个按 Agent Skills 格式放着 SKILL.md 的目录，或者一个带 frontmatter 的散装 Markdown 文件（系统提示词的构造 (p. 75) 展示了技能落在提示词的哪个位置）。加载器读取三个 frontmatter 字段 CA/src/core/skills.ts:67：

name: optional; defaults to the name of the parent directory. Checked against the spec: at most 64 characters, ^[a-z0-9-]+\$, no leading, trailing or doubled hyphen CA/src/core/skills.ts:92. Violations are warnings; the skill still loads.

name：可选；默认取父目录的名字。会按规范校验：最多 64 个字符，^[a-z0-9-]+\$，不能有开头、结尾或重复的连字符 CA/src/core/skills.ts:92。违反只算警告；技能照样加载。

description: required. A SKILL.md without one is reported and skipped; a loose .md without one is skipped silently CA/src/core/skills.ts:304. Over 1,024 characters is a warning.

description：必填。没有它的 SKILL.md 会被报告并跳过；散装的 .md 没有它则被静默跳过 CA/src/core/skills.ts:304。超过 1024 个字符算警告。

disable-model-invocation: true hides the skill from the system prompt; only /skill:name reaches it.

disable-model-invocation: true 会把该技能从系统提示词里隐藏，只有 /skill:name 能触达它。

The spec’s other fields, such as license, compatibility and allowed-tools, are parsed and ignored. Discovery treats a directory that contains SKILL.md as a skill root and does not descend further. Elsewhere it recurses, skipping dot-entries and node_modules and honouring .gitignore, .ignore and .fdignore CA/src/core/package-manager.ts:371. Loose .md files count only at the top of \~/.pi/agent/skills and .pi/skills, and only below the top of an .agents/skills directory CA/src/core/package-manager.ts:428.

规范里的其他字段，比如 license、compatibility 和 allowed-tools，只解析不使用。发现过程把含 SKILL.md 的目录当作技能根，不再往下钻。别处则递归，跳过以点开头的条目和 node_modules，并遵守 .gitignore、.ignore 和 .fdignore CA/src/core/package-manager.ts:371。散装 .md 文件只在 \~/.pi/agent/skills 和 .pi/skills 的顶层算数，也只在 .agents/skills 目录的顶层之下算数 CA/src/core/package-manager.ts:428。

The system prompt lists each skill’s name, description and absolute path, never its body. The model reads the file when a task matches, so adding a skill changes the prompt by one entry, not by its instructions:

系统提示词只列出每个技能的名字、描述和绝对路径，绝不列正文。模型在任务匹配时才去读文件，所以添加一个技能对提示词的改变只是一个条目，而不是它的指令：

```txt the skills block of the system prompt CA/src/core/skills.ts TS
const lines = [
    "\n\nThe following skills provide specialized instructions for specific tasks.",
    fileReadTool === "read"
    ? "Use the read tool to load a skill's file when the task matches its description."
    : fileReadTool === "bash"
    ? "Use bash to load a skill's file when the task matches its description."
    : "Load a skill's file when the task matches its description.",
    "When a skill file references a relative path, resolve it against the skill directory (parent of SKILL.md / dirname of the path) and use that absolute path in tool commands.",
    "",
    "<available_skills>",
];
```

Lines 365–375 of formatSkillsForPrompt(). Each visible skill then adds <skill> with <name>, <description> and <location>, XML-escaped. The section builder wraps the result in <skills> CA/src/core/system-prompt.ts:179. With neither read nor bash among the selected tools, the block is left out.

取自 formatSkillsForPrompt() 的第 365–375 行。随后每个可见技能都追加一段 <skill>，含 <name>、<description> 和 <location>，并做 XML 转义。章节构造器把结果包进 <skills> CA/src/core/system-prompt.ts:179。若所选工具里既无 read 也无 bash，这块内容会被略去。

Typing /skill:name args replaces the input with <skill name="N" location="P">, a line References are relative to DIR., the body without frontmatter, and </skill>, followed by a blank line and the arguments CA/src/core/agentsession.ts:2146. An unknown name passes through unchanged.

输入 /skill:name args 会把输入替换为 <skill name="N" location="P">、一行 References are relative to DIR.、去掉 frontmatter 的正文以及 </skill>，之后是一个空行和参数 CA/src/core/agentsession.ts:2146。未知的名字原样透传。

## Prompt templates

## 提示词模板

A prompt template is a Markdown file that /name args expands into the prompt. The name is the file name without .md. The description is the frontmatter description, or else the first non-empty line, cut to 60 characters with ... appended when longer; argument-hint is optional CA/src/core/prompt-templates.ts:129.

提示词模板是一个 Markdown 文件，`/name args` 把它展开成提示词。名字是去掉 .md 的文件名。描述取frontmatter 的 description，否则取第一个非空行，截到 60 个字符，更长则追加 ...；argument-hint 是可选的 CA/src/core/prompt-templates.ts:129。

The conventional directories \~/.pi/agent/prompts/ and .pi/prompts/ (trusted) are scanned without recursion, as is a directory passed to --prompt-template CA/src/core/prompt-templates.ts:159. A directory named in the prompts setting or in a package is collected recursively, like any other resource directory CA/src/core/package-manager.ts:651.

约定目录 \~/.pi/agent/prompts/ 和 .pi/prompts/（需受信任）以非递归方式扫描，传给 --prompt-template 的目录也是 CA/src/core/prompt-templates.ts:159。在 prompts 设置里或某个包中点名的目录则像其他资源目录一样递归收集 CA/src/core/package-manager.ts:651。

Arguments are split on whitespace, with ' and " grouping and no escape characters CA/src/core/prompt-templates.ts:25. Substitution runs once over the template; values that themselves contain \$1 are not expanded again CA/src/core/prompttemplates.ts:71.

参数按空白切分，用 ' 和 " 分组，没有转义字符 CA/src/core/prompt-templates.ts:25。替换在模板上只跑一遍；值本身含有的 \$1 不会被再次展开 CA/src/core/prompttemplates.ts:71。

<table><tr><td>语法</td><td>值</td></tr><tr><td>$1, $2, ...</td><td>位置参数；缺失 → &quot;&quot;</td></tr><tr><td>$@, $ARGUMENTS</td><td>所有参数用空格连接</td></tr><tr><td>${N: -default}</td><td>第 N 个参数，缺失或为空时用默认值</td></tr><tr><td>${@: -default}, ${ARGUMENTS: -default}</td><td>所有参数；一个都没有时用默认值</td></tr><tr><td>${@: N}</td><td>从第 N 个开始的所有参数</td></tr><tr><td>${@: N: L}</td><td>从第 N 个开始的 L 个参数</td></tr></table>

Bash-style, one pass. From substitute Args().

Bash 风格，只跑一遍。取自 substitute Args()。

AgentSession.prompt() applies four stages to text that starts with /: a registered extension command runs and consumes it; otherwise input handlers see the raw text; then /skill: expansion; then template expansion CA/src/core/agentsession.ts:1963. from prompt() to agent_settled (p. 67) follows the text from there.

AgentSession.prompt() 对以 / 开头的文本施加四个阶段：先看有没有已注册的扩展命令，有就执行并消费掉；否则 input 处理器看到原始文本；然后是 /skill: 展开；再是模板展开 CA/src/core/agentsession.ts:1963。从 prompt() 到 agent_settled (p. 67) 那一节接着讲这条文本之后的流程。

## Themes

## 主题

Three themes are built in: system, the default, generated from the terminal’s palette CA/src/modes/interactive/theme/themecontroller.ts:175, plus dark and light. Custom themes are JSON files from \~/.pi/agent/themes/, .pi/themes/ (trusted), the themes setting, packages or --theme. Only the active custom theme in \~/.pi/agent/themes/ is watched and hotreloaded CA/src/modes/interactive/theme/theme.ts:808.

内置三个主题：system（默认，由终端调色板生成）CA/src/modes/interactive/theme/themecontroller.ts:175，以及 dark 和 light。自定义主题是来自 \~/.pi/agent/themes/、.pi/themes/（需受信任）、themes 设置、包或 --theme 的 JSON 文件。只有 \~/.pi/agent/themes/ 里那个正在使用的自定义主题会被监视并热重载 CA/src/modes/interactive/theme/theme.ts:808。

A theme file has name, optional appearance ("dark" or "light", detected from the colours when omitted), optional vars, colors and an optional export block with pageBg, cardBg and infoBg for HTML export. colors has 51 required keys and 5 optional ones. A colour value is a hex string, oklch(), okhsl(), the name of a vars entry, "" for the terminal default, or an integer 0–255 for a palette index CA/src/modes/interactive/theme/theme-json.ts:13. The setting theme: "light-name/darkname" follows the terminal’s appearance, light theme first CA/src/modes/interactive/theme/theme.ts:652; a theme name with / in it is rejected CA/src/modes/interactive/theme/theme.ts:528.

主题文件包含 name、可选的 appearance（"dark" 或 "light"，省略时从颜色推断）、可选的 vars、colors，以及一个可选的导出块，含用于 HTML 导出的 pageBg、cardBg 和 infoBg。colors 有 51 个必填键和 5 个可选键。颜色值可以是十六进制字符串、oklch()、okhsl()、某个 vars 条目的名字、"" 表示终端默认，或 0–255 的整数表示调色板索引 CA/src/modes/interactive/theme/theme-json.ts:13。设置 theme: "light-name/darkname" 会跟随终端的外观，先用浅色主题 CA/src/modes/interactive/theme/theme.ts:652；名字里含 / 的主题会被拒绝 CA/src/modes/interactive/theme/theme.ts:528。

## Pi packages

## Pi 包

A package bundles extensions, skills, prompts and themes for installation from npm, git or a local path. Its manifest is the pi key in package.json, four optional string arrays whose entries can be globs CA/src/core/pi-manifest.ts:4:

一个包把扩展、技能、提示词和主题打包在一起，可从 npm、git 或本地路径安装。它的清单是 package.json 里的 pi 键，包含四个可选的字符串数组，数组元素可以是 glob CA/src/core/pi-manifest.ts:4：

```json
a package manifest package.json
{
    "name": "@me/pi-tools",
    "keywords": ["pi-package"],
    "pi": {
    "extensions": ["/ext/*.ts"],
    "skills": ["/skills"],
    "prompts": ["/prompts"],
    "themes": ["/themes/*.json"]
    },
    "peer Dependencies": { "@earendil-works/pi-coding-agent": "*", "typebox": "*"
}
```

Illustrative. Only the pi key is read by the loader. Without it, Pi falls back to the conventional extensions/, skills/, prompts/ and themes/ directories of the package root CA/src/core/package-manager.ts:2250.

这是示意性的。加载器只读取 pi 键。没有它时，Pi 退回使用包根目录下约定俗成的 extensions/、skills/、prompts/ 和 themes/ 目录 CA/src/core/package-manager.ts:2250。

<table><tr><td>来源形式</td><td>种类</td><td>安装到</td></tr><tr><td>npm:@scope/name[@version]</td><td>npm；指定版本则锁定该版本</td><td>~/.pi/agent/npm/node_modules/，加 -l 则为 .pi/npm/...</td></tr><tr><td>git:github.com/user/repo[@ref], https://...,ssh://...</td><td>git</td><td>~/.pi/agent/git/：$\text{<path>:git clone,git checkout}$，若存在 package.json 再 npm install</td></tr><tr><td>./path,/abs,~/...</td><td>本地</td><td>就地使用</td></tr></table>

Project packages install under .pi/ and only for a trusted project. From parse Source(), getManagedNpmInstallPath(), getGitInstallRoot() and install Git() CA/src/core/package-manager.ts:2126.

项目包安装在 .pi/ 之下，且只对受信任的项目生效。取自 parse Source()、getManagedNpmInstallPath()、getGitInstallRoot() 和 install Git() CA/src/core/package-manager.ts:2126。

The commands are pi install <source> [-l], pi remove <source> [-l] (alias uninstall), pi update [--self|-- extensions|--models|--all] and pi list CA/src/package-manager-cli.ts:265. pi update with no target updates Pi itself.

命令有 pi install <source> [-l]、pi remove <source> [-l]（别名 uninstall）、pi update [--self|--extensions|--models|--all] 和 pi list CA/src/package-manager-cli.ts:265。不带目标的 pi update 会更新 Pi 自身。

CA/src/core/package-manager.ts:1721. When the same identity is configured in both scopes, the project entry wins. Configured packages that are missing are installed during reload() unless PI_OFFLINE is 1, true or yes CA/src/core/package-

CA/src/core/package-manager.ts:1721。当同一个标识在两个作用域都配置了时，项目条目胜出。已配置但缺失的包会在 reload() 期间安装，除非 PI_OFFLINE 为 1、true 或 yes CA/src/core/package-

manager.ts:54.

manager.ts:54.

The host provides pi-ai, pi-agent-core, pi-coding-agent, pi-tui and typebox to every extension. A package that lists one of them under dependencies gets a warning: “Host-provided extension packages must be declared in peer Dependencies with a “*“ range, not dependencies” CA/src/core/resource-loader.ts:93. extensions, loading and the API (p. 113) shows how the loader maps these imports.

宿主为每个扩展提供 pi-ai、pi-agent-core、pi-coding-agent、pi-tui 和 typebox。把其中任何一个列在 dependencies 下的包会得到一条警告：「Host-provided extension packages must be declared in peer Dependencies with a “*“ range, not dependencies」CA/src/core/resource-loader.ts:93。扩展、加载与 API (p. 113) 展示了加载器如何映射这些 import。

A settings entry can be an object instead of a string: { source, autoload?, extensions?, skills?, prompts?, themes? }. Each array filters what the package contributes. Plain entries and globs include, !glob excludes, +path forceincludes an exact path and -path force-excludes one, applied in that order CA/src/core/package-manager.ts:745.

设置条目可以是对象而非字符串：{ source, autoload?, extensions?, skills?, prompts?, themes? }。每个数组都过滤这个包贡献的内容。普通条目和 glob 表示包含，!glob 表示排除，+path 强制包含一个确切路径，-path 强制排除一个，按这个顺序生效 CA/src/core/package-manager.ts:745。

W H A T T H I S M E A N S F O R Y O U

这 对 你 意 味 着 什 么

Name skills and templates uniquely across scopes; a collision drops one copy with only a diagnostic.

给技能和模板起跨作用域唯一的名字；冲突只会留下一条诊断，然后丢掉一份拷贝。

To override a resource for one run, load it through -e, not --skill.

要为一个运行覆盖某项资源，用 -e 加载它，而不是 --skill。

Run untrusted checkouts with -nc if their AGENTS.md should not reach the model.

如果某个未受信任的 checkout 的 AGENTS.md 不该到达模型，就用 -nc 跑它。

Declare host packages as "*" peer dependencies in any package you publish.

在发布的任何包里，都把宿主包声明为 "*" 的 peer dependencies。

Sources: CA/src/core/resource-loader.ts (loadContextFileFromDir, findShadowedContextFile, loadProjectContextFiles, reload, loadFinalExtensionSet, dedupe Prompts, collectExtensionPackageWarnings); CA/src/core/project-trust.ts (resolveProjectTrusted); CA/src/core/trust-manager.ts; CA/src/core/extensions/runner.ts (emitProjectTrustEvent); CA/src/core/package-manager.ts (resourcePrecedenceRank, collectSkillEntries, collectAncestorAgentsSkillDirs, apply Patterns, resolve, addAutoDiscoveredResources, collectPackageResources, parse Source, getPackageIdentity); CA/src/core/skills.ts; CA/src/core/system-prompt.ts; CA/src/core/agent-session.ts (prompt, _expandSkillCommand); CA/src/core/prompt-templates.ts; CA/src/modes/interactive/theme/{theme.ts, theme-json.ts, theme-controller.ts}; CA/src/core/pi-manifest.ts; CA/src/package-manager-cli.ts; CA/docs/skills.md; research/capture/resources-precedence.mjs; research/out/resources-precedence.txt

来源：CA/src/core/resource-loader.ts（loadContextFileFromDir、findShadowedContextFile、loadProjectContextFiles、reload、loadFinalExtensionSet、dedupe Prompts、collectExtensionPackageWarnings）；CA/src/core/project-trust.ts（resolveProjectTrusted）；CA/src/core/trust-manager.ts；CA/src/core/extensions/runner.ts（emitProjectTrustEvent）；CA/src/core/package-manager.ts（resourcePrecedenceRank、collectSkillEntries、collectAncestorAgentsSkillDirs、apply Patterns、resolve、addAutoDiscoveredResources、collectPackageResources、parse Source、getPackageIdentity）；CA/src/core/skills.ts；CA/src/core/system-prompt.ts；CA/src/core/agent-session.ts（prompt、_expandSkillCommand）；CA/src/core/prompt-templates.ts；CA/src/modes/interactive/theme/{theme.ts, theme-json.ts, theme-controller.ts}；CA/src/core/pi-manifest.ts；CA/src/package-manager-cli.ts；CA/docs/skills.md；research/capture/resources-precedence.mjs；research/out/resources-precedence.txt

```typescript
a complete extension CA/docs/extensions.md TS

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
    pi.register Command("hello", {
    description: "Show a greeting",
    handler: async (name, ctx) => {
    ctx.ui.notify(`Hello, ${name || "world"}!`, "info");
    },
    });
}
```

#### Extensions: loading and the API

#### 扩展：加载与 API

An extension is onefunction that receives an \`ExtensionAPI\` with 32 methods and an event bus. What it registers during that call is held back until the call returns, so a factory that throws leaves nothing behind.

扩展是一个函数，它接收一个带 32 个方法和事件总线的 \`ExtensionAPI\`。它在那次调用中注册的内容会被暂扣到调用返回之后，所以一个抛异常的工厂不会留下任何东西。

Extensions are Pi’s main way to add features. The built-in MCP client, codemode and tool search are extensions themselves. This section shows how Pi finds and imports extension files, in what order, what happens when two extensions claim the same name, and how /reload replaces them. It then lists every ExtensionAPI method and the ToolDefinition an extension passes to register Tool(). The events an extension subscribes to are in extension events and contexts (p. 120).

扩展是 Pi 添加功能的主要途径。内置的 MCP 客户端、codemode 和工具搜索本身就是扩展。本节展示 Pi 如何查找并导入扩展文件、以什么顺序导入、两个扩展抢同一个名字时会发生什么，以及 /reload 如何替换它们。随后列出每个 ExtensionAPI 方法，以及扩展传给 register Tool() 的 ToolDefinition。扩展订阅的事件见扩展事件与上下文 (p. 120)。

## A factory and nothing else

## 只有工厂

An extension is a TypeScript or JavaScript module whose default export has this type CA/src/core/extensions/types.ts:2006:

扩展是一个 TypeScript 或 JavaScript 模块，其默认导出具有以下类型 CA/src/core/extensions/types.ts:2006：

```txt the extension contract CA/src/core/extensions/types.ts
```

```typescript export type ExtensionFactory = (pi: ExtensionAPI) => void | Promise<void>;
```

```txt
Line 2006, uncut. Pi awaits an asynchronous factory before startup continues.
```

第 2006 行，未删节。启动继续之前，Pi 会 await 一个异步工厂。

Copied from the quick start in CA/docs/extensions.md. Save it as \~/.pi/agent/extensions/hello.ts, or load it for one run with pi -e ./hello.ts; then type /hello.

摘自 CA/docs/extensions.md 的快速开始。把它保存为 \~/.pi/agent/extensions/hello.ts，或者用 pi -e ./hello.ts 为一次运行加载它；然后输入 /hello。

The shipped docs state the lifecycle rule: “Do not start processes, sockets, watchers, or timers in the factory because some invocations load extensions without starting a session.” CA/docs/extensions.md. Start long-lived resources in a session_start handler and close them in an idempotent session_shutdown handler.

随包文档给出了生命周期规则：「Do not start processes, sockets, watchers, or timers in the factory because some invocations load extensions without starting a session.」CA/docs/extensions.md。在 session_start 处理器里启动长驻资源，在一个幂等的 session_shutdown 处理器里关闭它们。

## Finding and importing

## 查找与导入

Extension paths come out of the resource pipeline in context files, skills, templates, themes and packages (p. 106). Within it, extensions have their own order: command-line -e paths first, then the ranked list, then inline factories CA/src/core/resourceloader.ts:573.

扩展路径来自上下文文件、技能、模板、主题与包 (p. 106) 里的资源流水线。在这条流水线内部，扩展有自己的顺序：先是命令行的 -e 路径，然后是排名列表，最后是内联工厂 CA/src/core/resourceloader.ts:573。

F I G . 5 . 7 E X T E N S I O N L O A D O R D E R

F I G . 5 . 7 扩 展 加 载 顺 序

F L O W

流 程

1

1

-e source>

-e 来源>

CLI · temporary scope · also builtin: →

CLI · 临时作用域 · 也包括 builtin: →

2

2

project settings extensions entries in .pi/settings.json rank 0

.pi/settings.json 中的项目设置 extensions 条目，排名 0

3

3

.pi/extensions/ trusted projects only

.pi/extensions/，仅限受信任的项目

4

4

user settings extensions entries in \~/.pi/agent/settings.json rank 2

\~/.pi/agent/settings.json 中的用户设置 extensions 条目，排名 2

5

5

\~/.pi/agent/extensions/ always rank 3

\~/.pi/agent/extensions/，始终为排名 3

6

6

packages project packages, then user packages rank 4

包：先项目包，后用户包，排名 4

7

7

built-ins builtin:lama.cpp · codemode · tool-search · mcp rank 5

内置：builtin:lama.cpp · codemode · tool-search · mcp，排名 5

8

8

inline factories SDK extension Factories · last

内联工厂：SDK 的 extension Factories · 最后

The command line loads first. Event handlers, tool renderers and first-registration lookups all follow this order. Verified by research/out/resourcesprecedence.txt (§extensions), where a -e extension loads ahead of two auto-discovered ones.

命令行最先加载。事件处理器、工具渲染器和「首次注册优先」的查找都遵循这个顺序。由 research/out/resourcesprecedence.txt（§extensions）验证，其中一个 -e 扩展比两个自动发现的扩展先加载。

<table><tr><td>方面</td><td>行为</td><td>来源</td></tr><tr><td>目录扫描</td><td>在extensions/ 目录里：直接的 *.ts 和 *.js 文件，以及每个子目录的 package.json pi.extensions 条目，否则是它的 index.ts，再否则是它的 index.js。只下潜一层。目录自己带清单或 index 时只加载那个。</td><td>package-manager.ts:563</td></tr><tr><td>导入</td><td>用 jiti 并设module Cache: false，因此每次加载都会重新求值该模块。被导入的工厂按工作目录和缓存代数缓存；/reload 会递增该代数。</td><td>loader.ts:576, loader.ts:138</td></tr><tr><td>宿主 import</td><td>编译后的二进制、打包好的 Node 构建和 TypeScript 源码得到虚拟模块；未打包的 Node 构建得到路径别名。两者映射同样的 20 个说明符。</td><td>loader.ts:571, virtual-modules.ts:14</td></tr><tr><td>内置</td><td>builtin:lama.cpp，以及可替换的 builtin:codemode、builtin:tool-search 和 builtin:mcp。用 extensions 设置里的 &quot;-builtin:&quot; 禁用某一个；--no-extensions 全部丢弃，--no-mcp 只丢 MCP。</td><td>CA/src/extensions/index.ts:7</td></tr><tr><td>SDK</td><td>只有 CLI 会添加内置扩展。用 createAgentSession() 建的会话一个都不加载，除非调用方自己传入。</td><td>CA/src/main.ts:575</td></tr><tr><td>错误</td><td>导入和工厂错误以 Failed to load extension: ... 收集起来，不会中止其余部分的加载。在 CLI 里，任何这类错误都会让启动以退出码 1 结束。</td><td>loader.ts:655, main.ts:919</td></tr></table>

Twenty import specifiers resolve to the host’s own copies. Six are TypeBox: typebox, typebox/compile, typebox/value and the same three under @sinclair/typebox. Seven are Pi packages: pi-agent-core, pi-tui, pi-ai, pi-ai/compat, pi-ai/oauth, pi-ai/providers/all and pi-coding-agent under @earendil-works/. The other seven are the same Pi packages under the legacy @mariozechner/ scope. The bare pi-ai specifier maps to the compat entry point.

二十个 import 说明符解析到宿主自己的副本。六个是 TypeBox：typebox、typebox/compile、typebox/value 以及 @sinclair/typebox 下的同样三个。七个是 Pi 包：@earendil-works/ 下的 pi-agent-core、pi-tui、pi-ai、pi-ai/compat、pi-ai/oauth、pi-ai/providers/all 和 pi-coding-agent。另外七个是同样这些 Pi 包在旧版 @mariozechner/ 作用域下的版本。裸pi-ai 说明符映射到 compat 入口点。

## Transactional registration

## 事务式注册

The API object an extension receives has three states: loading, active and failed CA/src/core/extensions/loader.ts:253. Registrations that change shared runtime state — register Provider, unregister Provider, registerMcpServer, unregisterMcpServer, registerVirtualModel, unregisterVirtualModel and flag defaults — are queued while the factory runs. commit() applies them only after the factory returns. If it throws, discard() drops the queue, unsubscribes event-bus listeners added during loading, and marks the API failed, so later calls throw Extension "<path>" failed to load and its API is no longer active. CA/src/core/extensions/loader.ts:532. After loading, the same calls take efect at once, so a command handler can register a provider without /reload.

扩展拿到的 API 对象有三种状态：loading、active 和 failed CA/src/core/extensions/loader.ts:253。会改动共享运行时状态的注册——register Provider、unregister Provider、registerMcpServer、unregisterMcpServer、registerVirtualModel、unregisterVirtualModel 以及 flag 默认值——在工厂运行期间排队。commit() 只在工厂返回后才施加它们。如果工厂抛异常，discard() 会丢掉队列、取消加载期间添加的事件总线监听，并把该 API 标记为 failed，于是后续调用会抛 Extension "<path>" failed to load，而它的 API 不再处于 active CA/src/core/extensions/loader.ts:532。加载完成之后，同样的调用会立即生效，所以命令处理器可以注册一个供应商而无需 /reload。

Tools, commands, shortcuts, flags, renderers and handlers are written onto the extension object directly. They become visible only if the extension makes it into the loaded list, which a throwing factory does not.

工具、命令、快捷键、flag、渲染器和处理器都是直接写在扩展对象上的。只有当扩展进入已加载列表时它们才可见，而抛异常的工厂进不去。

## Two extensions, one name

## 两个扩展，一个名字

The resource loader does not refuse a duplicate. When two extensions register the same tool or flag, both stay loaded and the loader adds Tool "x" conflicts with <path> to its list of extension errors CA/src/core/resource-loader.ts:1246; tool lookups take the first registration in load order CA/src/core/extensions/runner.ts:631. The CLI turns every entry of that list into an error diagnostic CA/src/main.ts:800, and an error diagnostic ends startup:

资源加载器不会拒绝重复项。当两个扩展注册同一个工具或 flag 时，两者都会保持加载，加载器把 Tool "x" conflicts with <path> 加进自己的扩展错误列表 CA/src/core/resource-loader.ts:1246；工具查找取加载顺序里的第一次注册 CA/src/core/extensions/runner.ts:631。CLI 把该列表里的每一项都变成一条错误诊断 CA/src/main.ts:800，而错误诊断会终止启动：

```shell
$ pi -ne -e <tmp>/a.js -e <tmp>/b.js -p hi
Error: Failed to load extension "<tmp>/b.js": Tool "dup_tool" conflicts with <tmp>/a.js
Hint: Start without extensions using "pi -ne".
exit code: 1
```

That is research/out/extensions-conflict.txt, from two one-line extensions that each register dup_tool, run ofline against the pinned build. An SDK caller that builds its own DefaultResourceLoader gets the same entry in get Extensions().errors

那来自 research/out/extensions-conflict.txt，用的是两个各注册 dup_tool 的单行扩展，对锁定的构建离线运行。自建 DefaultResourceLoader 的 SDK 调用方会在 get Extensions().errors 里拿到同一条目，

and decides for itself.

并自行决定。

Built-ins are the exception. A replaceable built-in that shares a tool, command or flag name with any other extension is removed before the conflict check CA/src/core/resource-loader.ts:120. A third-party extension that registers /mcp therefore replaces the built-in MCP client, with a warning that names both.

内置扩展是例外。一个可替换的内置扩展若与任何其他扩展共用工具、命令或 flag 名字，会在冲突检查之前被移除 CA/src/core/resource-loader.ts:120。因此一个注册了 /mcp 的第三方扩展会替换掉内置 MCP 客户端，并附上一条点名双方的警告。

F O O T G U N

警 告

Two installed extensions that register the same tool name stop the pi command from starting, and nothing in CA/docs/extensions.md mentions it. The suggested pi -ne does not help when either extension comes from -e, because -e paths load even with --no-extensions. Remove or disable one of the two; check the name with pi.getAllTools() before registering a generic one.

两个已安装的扩展注册同一个工具名，会让 pi 命令起不来，而 CA/docs/extensions.md 里对此只字未提。当两个扩展中有一个来自 -e 时，建议的 pi -ne 也不管用，因为 -e 路径即使加了 --no-extensions 也会加载。删掉或禁用其中一个；注册一个通用名字之前先用 pi.getAllTools() 查一下。

## Hot reload

## 热重载

/reload calls AgentSession.reload(), which replaces the whole extension runtime CA/src/core/agent-session.ts:3646:

/reload 调用 AgentSession.reload()，它会替换整个扩展运行时 CA/src/core/agent-session.ts:3646：

![](images/282fa9fe2519ba4985daf6c22a02fa3eb4f29ca59244ace70c475013d1a70f8f.jpg)

Nothing survives a reload except what the session carries over. Active tool names and flag values pass to the new runtime; everything held in an extension’s closures is gone. From agent-session.ts:3646–3684. The two final events fire only when a UI or command context is bound.

除了会话带过去的东西，没有任何东西能在重载后存活。启用的工具名和 flag 值会传给新的运行时；扩展闭包里持有的一切都没了。取自 agent-session.ts:3646–3684。最后两个事件只在绑定了 UI 或命令上下文时才触发。

After a reload or a session replacement, a captured pi or ctx from the old runtime throws: “This extension ctx is stale after session replacement or reload. Do not use a captured pi or command ctx after ctx.new Session(), ctx.fork(), ctx.switch Session(), or ctx.reload(). …” CA/src/core/extensions/runner.ts:723. Work that must run in the new session goes in the with Session callback of new Session(), fork() or switch Session(), which receives a fresh context (extension events and contexts (p. 120)).

重载或替换会话之后，从旧运行时捕获的 pi 或 ctx 会抛异常：「This extension ctx is stale after session replacement or reload. Do not use a captured pi or command ctx after ctx.new Session(), ctx.fork(), ctx.switch Session(), or ctx.reload(). …」CA/src/core/extensions/runner.ts:723。必须在新会话里运行的工作要放进 new Session()、fork() 或 switch Session() 的 with Session 回调里，它会收到一个全新的上下文（扩展事件与上下文 (p. 120)）。

## Extension API

## 扩展 API

ExtensionAPI is declared at types.ts:1553–1879. It has one on() method with 41 typed overloads, 31 other methods, and the events bus.

ExtensionAPI 声明在 types.ts:1553–1879。它有一个带 41 个类型化重载的 on() 方法、另外 31 个方法，以及 events 总线。

<table><tr><td>分组</td><td>方法</td></tr><tr><td>事件</td><td>on(event, handler) → 返回取消订阅的函数。41 个事件名；见扩展事件与上下文 (p. 120)。</td></tr><tr><td>工具</td><td>register Tool(def) · getActiveTools() · getAllTools() · setActiveTools(names)</td></tr><tr><td>命令与输入</td><td>register Command(name, { description?, getArgumentCompletions?, handler(args, ctx) })·register Shortcut(key, { description?, handler(ctx) })·register Flag(name, { description?, type: &quot;boolean&quot; | &quot;string&quot;, default? })·get Flag(name) · get Commands()</td></tr><tr><td>渲染</td><td>registerMessageRenderer(custom Type, r) · registerEntryRenderer(custom Type, r) · registerToolRenderer(resolver) · registerMarkdownTransformer(t)</td></tr><tr><td>会话</td><td>send Message({ custom Type, content, display, details }, { trigger Turn?, deliverAs?: &quot;steer&quot; | &quot;followUp&quot; | &quot;next Turn&quot; })·sendUserMessage(content, { deliverAs?, expandPromptTemplates? })</td></tr><tr><td>会话数据</td><td>append Entry(custom Type, data?) · setSessionName(name) · getSessionName() · set Label(entryId, label)</td></tr><tr><td>模型</td><td>set Model(model) → Promise··getThinkingLevel() · setThinkingLevel(level)</td></tr><tr><td>供应商</td><td>register Provider(provider) 或 register Provider(name, config) · unregister Provider(name) · registerVirtualModel(m) · unregisterVirtualModel(provider, id)</td></tr><tr><td>MCP</td><td>registerMcpServer(name, config) · unregisterMcpServer(name) · getMcpServers()</td></tr><tr><td>其他</td><td>exec(command, args, options?) · get Settings() · events（共享的 EventBus）</td></tr></table>

Registration methods write to the extension; action methods go to the shared runtime. From the ExtensionAPI interface and createExtensionAPI() CA/src/core/extensions/loader.ts:244.

注册类方法写入扩展；动作类方法作用于共享运行时。取自 ExtensionAPI 接口和 createExtensionAPI() CA/src/core/extensions/loader.ts:244。

A few behaviours are not visible in the signatures:

有几个行为在签名里看不出来：

sendUserMessage: always triggers a turn. Prompt templates and skill commands are expanded only with expandPromptTemplates: true; the default is false CA/src/core/agent-session.ts:2376.

sendUserMessage：总是触发一个轮次。只有加上 expandPromptTemplates: true 才会展开提示词模板和技能命令；默认是 false CA/src/core/agent-session.ts:2376。

append Entry: writes a custom entry to the session file. It is never sent to the model; sessions, the JSONL tree (p. 86) shows its shape.

append Entry：把一条自定义条目写进会话文件。它绝不发给模型；会话与JSONL 树 (p. 86) 展示了它的形状。

set Model: changes the session’s model without changing the saved default, and returns false when the provider has no configured auth.

set Model：改变会话的模型而不改动已保存的默认值；当该供应商没有配置 auth 时返回 false。

register Provider(name, config): with models, replaces every model of that provider; with only base Url, re-points existing models. unregister Provider restores built-in models it overrode. The config.api Key outranks models.json (configuration, models and auth (p. 99)).

register Provider(name, config)：带 models 时，替换该供应商的每一个模型；只带 base Url 时，把已有模型重新指向新端点。unregister Provider 会恢复它覆盖掉的内置模型。config 里的 api Key 优先于 models.json（配置、模型与鉴权 (p. 99)）。

registerMcpServer: not persisted; register again on every load. A server of the same name in mcp.json takes precedence; aname another extension registered throws (MCP (p. 144)).

registerMcpServer：不会持久化；每次加载都要重新注册。mcp.json 里同名的服务器优先；与另一个扩展注册的同名服务器会抛异常（MCP (p. 144)）。

get Flag: returns undefined for a flag the calling extension did not register itself.

get Flag：对调用方扩展自己没注册过的 flag 返回 undefined。

## Tool Definition

## 工具定义

register Tool() takes a ToolDefinition CA/src/core/extensions/types.ts:567. register Tool() rejects a definition whose parameters is not an object schema CA/src/core/extensions/loader.ts:291. built-in tools (p. 81) shows the built-in tools built from the same type.

register Tool() 接受一个 ToolDefinition CA/src/core/extensions/types.ts:567。register Tool() 会拒绝 parameters 不是对象 schema 的定义 CA/src/core/extensions/loader.ts:291。内置工具 (p. 81) 展示了由同一类型构建的内置工具。

```typescript
ToolDefinition, abridged CA/src/core/extensions/types.ts TS export interface ToolDefinition<TParams extends TSchema = TSchema, TDetails = unknown, TState = any> {
    name: string;
    label: string;
    description: string;
    prompt Snippet?: string;
    prompt Guidelines?: string[];
    parameters: TParams;
    constrained Sampling?: false | ConstrainedSamplingConfig;
    render Shell?: "default" | "self";
    prepare Arguments?: (args: unknown) => Static<TParams>;
    output Schema?: TSchema;
    exposure?: ToolExposure;
    namespace?: ToolNamespace;
    annotations?: ToolAnnotations;
    default Active?: boolean;
    prepare Loadout?: (loadout: ToolLoadout) => ToolLoadoutChanges | undefined;
    execution Mode?: ToolExecutionMode;
    execute(
    toolCallId: string,
    params: Static<TParams>,
    signal: AbortSignal | undefined,
    onUpdate: AgentToolUpdateCallback<TDetails> | undefined,
    ctx: ExtensionToolContext,
    ): Promise<AgentToolResult<TDetails>>;
    render Call?: (args: Static<TParams>, theme: Theme, context: ToolRenderContext<TState, Static<TParams>>) => Component;
    render Result?: (...) => Component;
}
```

Lines 567–647 with every doc comment removed and the render Result parameters cut to …; they are result, options, theme and context.

取第 567–647 行，删掉所有文档注释，并把 render Result 的参数截到 …；它们是 result、options、theme 和 context。

prompt Snippet: a one-line entry in the <tools> section of the default system prompt. A custom tool without one is left out of that section.

prompt Snippet：默认系统提示词中 <tools> 章节里的一行条目。没有它的自定义工具会被排除在该章节之外。

prompt Guidelines: bullets added to the <rules> section while the tool is active.

prompt Guidelines：工具启用期间追加到 <rules> 章节的项目符号列表。

prepare Arguments: rewrites raw arguments before schema validation, for compatibility with older argument shapes.

prepare Arguments：在 schema 校验之前重写原始参数，以兼容旧的参数形状。

output Schema: schema of structured Content in results. Codemode scripts receive the structured value instead of the text.

output Schema：结果中结构化 content 的 schema。Codemode 脚本收到的是结构化的值，而不是文本。

annotations: readOnlyHint, destructive Hint, idempotent Hint, openWorldHint, with MCP’s meanings. They come from the tool’s author and nothing verifies them.

annotations：readOnlyHint、destructiveHint、idempotentHint、openWorldHint，含义与 MCP 相同。它们来自工具作者，没有任何东西去校验。

default Active: true by default for direct and model-only tools; other exposures are never activated on registration.

default Active：对 direct 和 model-only 工具默认为 true；其他 exposure 在注册时不会被激活。

execution Mode: "sequential" or "parallel"; overrides the default for this tool (the agent loop (p. 49)).

executionMode："sequential" 或 "parallel"；覆盖该工具的默认值（智能体循环 (p. 49)）。

exposure decides how the model reaches the tool. “Callable” means callable from another tool through ctx.execute Tool(), as the codemode tool does CA/src/core/extensions/types.ts:494:

exposure 决定模型如何触达工具。「Callable」意味着可以从另一个工具通过 ctx.execute Tool() 调用，就像 codemode 工具那样 CA/src/core/extensions/types.ts:494：

<table><tr><td>EXPOSURE</td><td>向模型声明</td><td>可被工具调用</td><td>备注</td></tr><tr><td>direct（默认）</td><td>启用期间</td><td>启用期间</td><td>注册时即激活</td></tr><tr><td>model-only</td><td>启用期间</td><td>从不</td><td>用于编排类或交互类工具；注册时即激活</td></tr><tr><td>codemode</td><td>仅在显式激活后</td><td>只要已注册</td><td>列在 codemode 的工具描述里</td></tr><tr><td>deferred</td><td>仅在显式激活后</td><td>只要已注册</td><td>codemode 不列出；工具搜索可以找到它</td></tr><tr><td>hidden</td><td>从不</td><td>从不</td><td>已注册但无法触达；激活它没有效果</td></tr></table>

The active set is exactly the set declared to the model. setActiveTools() ignores unknown and hidden names

CA/src/core/extensions/types.ts:1736. There is no unregister Tool(). codemode (p. 151) covers the codemode and deferred exposures in use.

启用集合恰好就是向模型声明的那个集合。setActiveTools() 会忽略未知和 hidden 的名字 CA/src/core/extensions/types.ts:1736。没有 unregister Tool()。codemode (p. 151) 介绍了 codemode 和 deferred 这两种 exposure 的实际用法。

W H A T T H I S M E A N S F O R Y O U

这 对 你 意 味 着 什 么

Register in the factory; start processes and timers in session_start.

在工厂里注册；进程和定时器放在 session_start 里启动。

Give tools and flags distinctive names; a duplicate across two extensions stops CLI startup.

给工具和 flag 取有辨识度的名字；跨两个扩展的重名会让 CLI 启动中止。

Never keep a pi or ctx across /reload, new Session(), fork() or switch Session().

绝不要跨 /reload、new Session()、fork() 或 switch Session() 保留 pi 或 ctx。

Use -e ./ext.ts to test an extension; it loads before everything installed.

用 -e ./ext.ts 测试扩展；它会比所有已安装的东西都先加载。

Sources: CA/src/core/extensions/types.ts (ExtensionFactory, ExtensionAPI, ToolDefinition, ToolExposure, ToolAnnotations); CA/src/core/extensions/loader.ts (get Aliases, createExtensionAPI, loadExtensionModule, initialize Extension, clearExtensionCache); CA/src/core/extensions/virtual-modules.ts; CA/src/core/extensions/runner.ts (stale message, getAllRegisteredTools); CA/src/core/resource-loader.ts (reload, omitReplacedExtensions, detectExtensionConflicts); CA/src/core/package-manager.ts (resolveExtensionEntries, collectAutoExtensionEntries); CA/src/extensions/index.ts; CA/src/main.ts; CA/src/core/agent-session.ts (reload, sendUserMessage); CA/docs/extensions.md; research/capture/extensions-conflict.mjs; research/out/extensions-conflict.txt; research/out/resources-precedence.txt

来源：CA/src/core/extensions/types.ts（ExtensionFactory、ExtensionAPI、ToolDefinition、ToolExposure、ToolAnnotations）；CA/src/core/extensions/loader.ts（getAliases、createExtensionAPI、loadExtensionModule、initializeExtension、clearExtensionCache）；CA/src/core/extensions/virtual-modules.ts；CA/src/core/extensions/runner.ts（过期提示、getAllRegisteredTools）；CA/src/core/resource-loader.ts（reload、omitReplacedExtensions、detectExtensionConflicts）；CA/src/core/package-manager.ts（resolveExtensionEntries、collectAutoExtensionEntries）；CA/src/extensions/index.ts；CA/src/main.ts；CA/src/core/agent-session.ts（reload、sendUserMessage）；CA/docs/extensions.md；research/capture/extensions-conflict.mjs；research/out/extensions-conflict.txt；research/out/resources-precedence.txt

# 5.4 Extension events and contexts

# 5.4 扩展事件与上下文

An extension sees Pi through 41 events, and about half of them let it change what happens next. A handler that throws is reported and skipped, except in \`tool_call\` and \`user_bash\`, where a throw stops the action.

扩展通过 41 个事件观察 Pi，其中约一半让它能改变接下来发生什么。抛异常的处理器会被报告并跳过，\`tool_call\` 和 \`user_bash\` 除外——在这两个事件里抛异常会中止该动作。

Pi does not ofer one interception point. It ofers a typed event for each step of a run: startup, session changes, input, the system prompt, the message list, the provider request, every message and tool call, and the boundaries between turns. This section gives the dispatch rules shared by all of them and the full event table with what each handler may return. It draws one blocking call end to end, lists the context objects handlers receive, and maps the 80 entries in CA/examples/extensions/.

Pi 不提供单一的拦截点。它为一次运行的每一步都提供带类型的事件：启动、会话变更、输入、系统提示词、消息列表、供应商请求、每一条消息和每次工具调用，以及轮次之间的边界。本节给出所有事件共用的分发规则和完整事件表，以及每个处理器可以返回什么；它完整画出一通被拦截的调用，列出处理器收到的上下文对象，并梳理 CA/examples/extensions/ 里的 80 个条目。

## Dispatch rules

## 分发规则

All dispatch goes through ExtensionRunner CA/src/core/extensions/runner.ts. Four rules hold for every event:

所有分发都走 ExtensionRunner CA/src/core/extensions/runner.ts。有四条规则适用于每一个事件：

Order: handlers run in extension load order, then in registration order within one extension (extensions, loading and the API (p. 113) gives the load order). pi.on() returns a function that removes that one registration; a dispatch already in progress keeps its snapshot.

顺序：处理器按扩展加载顺序运行，同一个扩展内部再按注册顺序运行（扩展、加载与 API (p. 113) 给出了加载顺序）。pi.on() 返回一个函数，移除那一条注册；已经在进行中的分发保留自己的快照。

Awaiting: each handler is awaited before the next one runs. A slow provider_stream_event handler delays stream consumption.

等待：每个处理器都在下一个开始运行之前被 await。一个缓慢的 provider_stream_event 处理器会拖慢流的消费。

Errors: a throw is reported through the error listener as { extension Path, event, error, stack }, and dispatch continues with the next handler CA/src/core/extensions/runner.ts:1104.

错误：抛出的异常通过错误监听器以 { extensionPath, event, error, stack } 报告，分发继续下一个处理器 CA/src/core/extensions/runner.ts:1104。

Exceptions to the error rule: in tool_call the runner has no try, so a throw leaves the runner and blocks the call CA/src/core/extensions/runner.ts:1242. In user_bash the throw is reported and then rethrown CA/src/core/extensions/runner.ts:1285. Both fail closed.

错误规则的例外：在 tool_call 里 runner 没有 try，所以抛出的异常会离开 runner 并拦截这次调用 CA/src/core/extensions/runner.ts:1242。在 user_bash 里抛出的异常会先被报告，然后重新抛出 CA/src/core/extensions/runner.ts:1285。两者都是失败即关闭。

How several handlers’ results combine depends on the event. input chains transforms and stops at the first handled CA/src/core/extensions/runner.ts:1519. tool_call stops at the first block: true. The session_before_* events stop at the first cancel: true; otherwise the last non-empty result wins CA/src/core/extensions/runner.ts:1098. message_end chains replacements and rejects one that changes the role with message_end handlers must return a message with the same role. cache_warming_decision takes the last action returned. project_trust takes the first yes or no.

多个处理器的结果如何合并取决于事件。input 把各次变换串联起来，并在第一个 handled 处停下 CA/src/core/extensions/runner.ts:1519。tool_call 在第一个 block: true 处停下。session_before_* 系列事件在第一个 cancel: true 处停下；否则最后一个非空结果胜出 CA/src/core/extensions/runner.ts:1098。message_end 把替换串联起来，并拒绝任何改变角色的返回值，报 message_end handlers must return a message with the same role。cache_warming_decision 取最后返回的 action。project_trust 取第一个 yes 或 no。

## The events

## 事件一览

Legend: N notify-only, M can modify, B can block or cancel. The table follows the order of a session.

图例：N 仅通知，M 可修改，B 可拦截或取消。表格按一次会话的顺序排列。

<table><tr><td>阶段</td><td>事件与载荷</td><td>处理器返回</td><td>种类</td></tr><tr><td>启动</td><td>project_trust { cwd }，仅信任前扩展</td><td>{ trusted: "yes" | "no" | "undecided", remember? }</td><td>B</td></tr><tr><td></td><td>resources_discover { cwd, reason: startup | reload }；mcp_servers_change { servers }</td><td>{ skillPaths?, promptPaths?, themePaths? }；-</td><td>MN</td></tr><tr><td>会话</td><td>session_start { reason: startup | reload | new | resume | fork, previousSessionFile? }</td><td>-</td><td>N</td></tr><tr><td></td><td>session_before_switch { reason: new | resume, targetSessionFile? }</td><td>{ cancel? }</td><td>B</td></tr><tr><td></td><td>session_before_fork { entryId, position: before | at }</td><td>{ cancel?, skipConversationRestore? }</td><td>B</td></tr><tr><td></td><td>session_before_compact { preparation, branchEntries, customInstructions?, reason, willRetry, signal }</td><td>{ cancel?, compaction? }</td><td>B/M</td></tr><tr><td></td><td>session_compact、session_compact_failed</td><td>-</td><td>N</td></tr><tr><td></td><td>session_before_tree { preparation, signal }</td><td>{ cancel?, summary?, customInstructions?, replaceInstructions?, label? }</td><td>B/M</td></tr><tr><td></td><td>session_tree、session_info_changed { name }</td><td>-</td><td>N</td></tr><tr><td></td><td>session_shutdown { reason: quit | reload | new | resume | fork, targetSessionFile? }</td><td>-</td><td>N</td></tr><tr><td>输入</td><td>input { text, images?, source, streamingBehavior? }</td><td>continue|transform { text, images? }|handled</td><td>M/B</td></tr><tr><td></td><td>before_agent_start { prompt, images?, systemPrompt, systemPromptOptions }</td><td>{ message?, systemPrompt? }，或就地修改 systemPromptOptions</td><td>M</td></tr><tr><td>循环</td><td>agent_start、turn_start { turnIndex, timestamp }</td><td>-</td><td>N</td></tr><tr><td></td><td>context { messages }，隐藏系统消息</td><td>{ messages? }，或就地编辑</td><td>M</td></tr><tr><td></td><td>context_with_system { messages }，完整记录</td><td>{ messages? }</td><td>M</td></tr><tr><td>供应商</td><td>before_provider_request { payload }</td><td>一个替换用的 payload</td><td>M</td></tr><tr><td></td><td>before_provider_headers { headers }</td><td>就地修改；null 删除该header</td><td>M</td></tr><tr><td></td><td>after_provider_response { status, headers }、provider_stream_event { provider, api, model, data }</td><td>-</td><td>N</td></tr><tr><td></td><td>cache_warming_decision { warmCost, missCost, continuationProbability, action }</td><td>{ action?: "warm" | "stop" }</td><td>M</td></tr><tr><td>消息</td><td>message_start、message_update { message, assistantMessageEvent }</td><td>-</td><td>N</td></tr><tr><td></td><td>message_end { message }</td><td>{ message? }，角色相同</td><td>M</td></tr><tr><td>工具</td><td>tool_call { toolCallId, toolName, input, parentToolCallId? }</td><td>{ block?, reason?, terminate? }；就地修改 input</td><td>B/M</td></tr><tr><td></td><td>tool_execution_start、tool_execution_update、tool_execution_end</td><td>-</td><td>N</td></tr><tr><td></td><td>tool_result { ..., input, content, details, structuredContent?, isError, usage? }</td><td>{ content?, details?, structuredContent?, isError?, usage? }</td><td>M</td></tr><tr><td>边界</td><td>turn_end,agent_before_settle:{ entries, continue, context, outcome }</td><td>{ entries?, continue? }</td><td>M</td></tr><tr><td>UI</td><td>agent_end { messages },agent_settledui_prompt_start, ui_prompt_end { kind, title? }</td><td>-—</td><td>NN</td></tr><tr><td>模型</td><td>model_select { model, previousModel, source: set | cycle | restore }、thinking_level_select { level, previousLevel }</td><td>—</td><td>N</td></tr><tr><td>Bash</td><td>user_bash { command, excludeFromContext, cwd }</td><td>{ operations } | { result }</td><td>M/B</td></tr></table>

Nineteen of the 41 events can change what happens; the other 22 only observe. Payloads and results from types.ts:679–1490 and cache-warmer.ts:112; turn_end also carries turn Index, message, tool Results and their entry ids. agent events and the Agent class (p. 57) gives the order in which the loop emits its share of them; the capture in the life of one prompt (p. 15) shows a real stream.

41 个事件中有 19 个能改变事情走向；另外 22 个只做观察。载荷与返回值取自 types.ts:679–1490 和 cache-warmer.ts:112；turn_end 还携带 turnIndex、message、toolResults 及其条目 id。智能体事件与 Agent 类 (p. 57) 给出循环发出其中那部分事件的顺序；一条提示词的一生 (p. 15) 里的实测展示了一段真实的流。

A few rows need more than a cell:

有几行需要更多解释：

context vs context_with_system: context handlers see the conversation without system messages, and Pi puts the prompt and tool state back after each one. context_with_system handlers then see the full transcript, and their output is sent as returned. Dropping the leading system message is reported (“Handler removed the leading system message; the request has no prompt or initial tool declarations.”) but honoured CA/src/core/extensions/runner.ts:1342.

context 与 context_with_system 的区别：context 处理器看到的是不含系统消息的会话，Pi 会在每个处理器之后把提示词和工具状态放回去。context_with_system 处理器看到的是完整记录，其输出按原样发送。丢掉开头那条系统消息会被报告（「Handler removed the leading system message; the request has no prompt or initial tool declarations.」），但仍然生效 CA/src/core/extensions/runner.ts:1342。

before_agent_start: later handlers see earlier handlers’ changes to systemPromptOptions. Returning system Prompt sets forceSystemPrompt and replaces the whole prompt for the run CA/src/core/extensions/runner.ts:1454. Every returned message is collected.

before_agent_start：靠后的处理器能看到靠前处理器对 systemPromptOptions 的改动。返回 systemPrompt 会设置 forceSystemPrompt，并在本次运行中替换整条提示词 CA/src/core/extensions/runner.ts:1454。每一条被返回的 message 都会被收集。

tool_call: runs after schema validation, and input is not validated again after a handler mutates it CA/src/core/extensions/types.ts:1211. terminate: true ends the run after the current batch only when every finalized result in the batch sets it.

tool_call：在 schema 校验之后运行，处理器改动 input 之后不会再校验一次 CA/src/core/extensions/types.ts:1211。terminate: true 只有当当前批次里每一个已敲定的结果都设置了它时，才会在该批次之后结束这次运行。

tool_result: replacing content without returning structured Content drops the structured content, because it may no longer match CA/src/core/extensions/runner.ts:1194.

tool_result：只替换 content 而不返回 structuredContent，会丢掉结构化内容，因为它可能已经不再匹配 CA/src/core/extensions/runner.ts:1194。

turn_end, agent_before_settle: the two actionable boundaries. Handlers chain proposed entries — drafts of type custom, custom_message, context_edit or compaction CA/src/core/extensions/types.ts:966 — and may set continue: true for one more model request. If the final drafts fail validation, all of them are dropped and continue becomes false CA/src/core/extensions/runner.ts:1075.

turn_end、agent_before_settle：两个可操作的边界。处理器把提议的条目串联起来——类型为 custom、custom_message、context_edit 或 compaction 的草稿 CA/src/core/extensions/types.ts:966——并可以设置 continue: true 以再发一次模型请求。如果最终草稿未通过校验，它们会全部被丢弃，continue 变成 false CA/src/core/extensions/runner.ts:1075。

user_bash: fires for ! and !! commands typed by the user. The first handler that returns a result decides: { operations } swaps the execution backend, { result } replaces execution entirely. A handler that throws does not fall back to local execution: the TUI reports the error and runs nothing CA/src/modes/interactive/interactive-mode.ts:6962.

user_bash：为用户输入的 ! 和 !! 命令触发。第一个返回结果的处理器说了算：{ operations } 替换执行后端，{ result } 彻底替换执行。抛异常的处理器不会退回本地执行：TUI 报告该错误，什么都不跑 CA/src/modes/interactive/interactive-mode.ts:6962。

## One call, two handlers

## 一次调用，两个处理器

The original manual’s sequence figure holds at the pinned commit. AgentSession installs beforeToolCall on the agent and forwards it to emitToolCall() CA/src/core/agent-session.ts:646. The agent loop turns the outcome into an error tool result agent/agent-loop.ts:744.

原手册的时序图在锁定提交上仍然成立。AgentSession 在 agent 上装好 beforeToolCall，并把它转发给 emitToolCall() CA/src/core/agent-session.ts:646。智能体循环把结果变成一条错误的工具结果 agent/agent-loop.ts:744。

![](images/444bfbb245dda45f9cfdc94866edaf57240048b1958202dccfce958e95c03cd8.jpg)

A block becomes an ordinary failed tool result; the model reads the reason. Without a reason the text is Tool execution was blocked. If B had thrown instead, the error would leave the runner unreported, _beforeToolCall would rethrow it, and the loop’s catch would produce an error result carrying the exception’s message agent/agent-loop.ts:769. Schematic; from runner.ts:1242, agent-session.ts:646–669 and agent-loop.ts:724–775.

一次拦截会变成一条普通的失败工具结果；模型读它的 reason。没有 reason 时文本是 Tool execution was blocked。如果换成 B 抛出异常，错误会在未被报告的情况下离开 runner，_beforeToolCall 会重新抛出它，而循环的 catch 会产生一条携带该异常消息的错误结果 agent/agent-loop.ts:769。示意图；取自 runner.ts:1242、agent-session.ts:646–669 和 agent-loop.ts:724–775。

The shipped docs give a permission gate built on tool annotations:

随包文档给出了一个基于工具注解构建的权限闸门：

```javascript ask before any tool that is not read-only CA/docs/extensions.md pi.on("tool_call", async (event, ctx) => {
    const hints = pi.getAllTools().find((tool) => tool.name === event.tool Name)?.annotations;
    const needs Approval =
    hints?.destructive Hint === true ||
    (!hints?.readOnlyHint && ((hints?.destructive Hint ?? true) || (hints?.openWorldHint ?? true)));
    if (needs Approval && !(await ctx.ui.confirm("Allow tool call?", event.tool Name))) {
    return { block: true, reason: `${event.tool Name} was not approved` };
    }
});
Copied from CA/docs/extensions.md, lines 169–177. In print and JSON mode ctx.ui.confirm() resolves to false at once, so this gate blocks every unannotated tool there; examples/extensions/permission-gate.ts checks ctx.hasUI first.
```

摘自 CA/docs/extensions.md 第 169–177 行。在 print 和 JSON 模式下，ctx.ui.confirm() 会立刻 resolve 成 false，所以这个闸门在那里会拦下每一个没有注解的工具；examples/extensions/permission-gate.ts 先检查 ctx.hasUI。

## Contexts

## 上下文

Every handler receives an ExtensionContext as its second argument CA/src/core/extensions/types.ts:325. Tools and commands get extended versions.

每个处理器都把一个 ExtensionContext 作为第二个参数 CA/src/core/extensions/types.ts:325。工具和命令拿到的是它的扩展版本。

```typescript the three context types, members only CA/src/core/extensions/types.ts

interface ExtensionContext {
    ui: ExtensionUIContext; mode: "tui" | "rpc" | "json" | "print"; hasUI: boolean;
    cwd; session Manager: ReadOnlySessionManager; model Registry; model; scoped Models; thinking Level?;
    isIdle(); isProjectTrusted(); signal; abort(); hasPendingMessages(); shutdown();
    colonial Usage(); compact(options?); getSystemPrompt();
}

interface ExtensionToolContext extends ExtensionContext {
    readonly tools: readonly AgentTool[];
    execute Tool(name, args, options?): Promise<AgentToolCallOutcome>;
}

interface ExtensionCommandContext extends ExtensionContext {
    getSystemServiceOptions(); waitForIdle(); new Session(options?”); fork(entryId, options?”);
    navigate Tree(targetId, options?”); switch Session(session Path, options?”); reload();
}
```

Condensed from lines 325–435: types and doc comments removed, members joined onto shared lines. The member names and their order are unchanged.

压缩自第 325–435 行：去掉类型和文档注释，成员被并到共享行上。成员名称及其顺序未变。

ExtensionToolContext.execute Tool(): runs another tool through the same preparation, validation, tool_call and tool_result hooks as a model-issued call. The nested call gets the id <calling id>/<n> and never appears in the transcript. It does not reject on tool failure; failures come back with isError: true CA/src/core/extensions/types.ts:383.

ExtensionToolContext.executeTool()：让另一个工具走与模型发起的调用相同的准备、校验、tool_call 和 tool_result钩子。这次嵌套调用拿到的 id 是 <calling id>/<n>，并且绝不进入记录。它不会因工具失败而 reject；失败以 isError: true 返回 CA/src/core/extensions/types.ts:383。

ExtensionCommandContext: session control is ofered to command handlers only; the interface comment calls these “session control methods only safe in user-initiated commands” CA/src/core/extensions/types.ts:399. new Session(), fork() and switch Session() accept a with Session(ctx) callback that receives a fresh ReplacedSessionContext bound to the new session. Use it for anything after the switch; the old ctx is stale (extensions, loading and the API (p. 113)).

ExtensionCommandContext：会话控制只提供给命令处理器；接口注释称这些是「session control methods only safe in user-initiated commands」CA/src/core/extensions/types.ts:399。new Session()、fork() 和 switch Session() 接受一个 with Session(ctx) 回调，它收到一个绑定到新会话的全新 ReplacedSessionContext。切换之后的任何工作都用它；旧的 ctx 已过期（扩展、加载与 API (p. 113)）。

compact(): starts compaction and returns without waiting; pass onComplete and onError to observe it (compaction and branch summaries (p. 92)).

compact()：启动压缩后不等它结束就返回；传入 onComplete 和 onError 来观察结果（压缩与分支摘要 (p. 92)）。

ctx.ui is the ExtensionUIContext CA/src/core/extensions/types.ts:149:

ctx.ui 是 ExtensionUIContext CA/src/core/extensions/types.ts:149：

<table><tr><td>分组</td><td>成员</td></tr><tr><td>对话框</td><td>select、confirm、input（各自带 { signal?, timeout? }）；editor(title, prefill?)，不接受选项</td></tr><tr><td>状态</td><td>notify、Kingston、setWorkingMessage、setWorkingVisible、setWorkingIndicator、setHiddenThinkingLabel、setTitle</td></tr><tr><td>布局</td><td>setWidget(key, lines | factory, { placement: &quot;aboveEditor&quot; | &quot;belowEditor&quot; })、setHeader、setFooter</td></tr><tr><td>组件</td><td>custom(factory, { overlay?, overlayOptions?, onHandle? })</td></tr><tr><td>编辑器</td><td>setEditorText、getEditorText、pasteToEditor、setEditorComponent、getEditorComponent、addAutocompleteProvider、onTerminalInput</td></tr><tr><td>外观</td><td>theme、getAllThemes、getTheme、setTheme、getToolsExpanded、setToolsExpanded</td></tr></table>

editor() is the one dialog that cannot time out. Its signature takes only a title and a prefill.

editor() 是唯一不能超时的对话框。它的签名只接受一个标题和一个预填内容。

What those calls do depends on the run mode (run modes (p. 127)). hasUI is true when a real UI context is bound, which happens in the TUI and in RPC mode CA/src/core/extensions/runner.ts:621:

这些调用具体做什么取决于运行模式（运行模式 (p. 127)）。绑定了真实 UI 上下文时 hasUI 为 true，这发生在 TUI 和 RPC 模式下 CA/src/core/extensions/runner.ts:621：

<table><tr><td>模式</td><td>ctx.mode</td><td>hasUI</td><td>对话框</td><td>组件与布局</td></tr><tr><td>interactive</td><td>tui</td><td>true</td><td>完整</td><td>完整</td></tr><tr><td>RPC</td><td>rpc</td><td>true</td><td>以 extension_ui_request 发给客户端并等待回应</td><td>custom() → undefined；header、footer、编辑器组件、工作指示器都是空操作；setWidget 只接受字符串形式的 lines；getEditorText() → &quot;&quot;</td></tr><tr><td>print、JSON</td><td>print、json</td><td>false</td><td>立刻 resolve：undefined，confirm 则是 false</td><td>空操作</td></tr></table>

An extension that needs an answer must check hasUI or expect the default. From rpc-mode.ts (createExtensionUIContext) and noOpUIContext in runner.ts. RPC mode and the SDK (p. 133) specifies the RPC UI sub-protocol.

需要得到答案的扩展必须先检查 hasUI，或者接受默认值。取自 rpc-mode.ts（createExtensionUIContext）和 runner.ts 里的 noOpUIContext。RPC 模式与 SDK (p. 133) 规定了 RPC UI 子协议。

## Example extensions

##扩展示例

CA/examples/extensions/ holds 80 entries at the pinned commit: 70 single-file .ts extensions, 9 directories and a README.md research/out/stats.txt §example-extensions. The ones below each show one technique; all the names were checked against the directory listing.

CA/examples/extensions/ 在锁定提交上有 80 个条目：70 个单文件 .ts 扩展、9 个目录和一份 README.md research/out/stats.txt §example-extensions。下面每个例子展示一种技术；所有名字都对着目录列表核对过。

<table><tr><td>类别</td><td>例子</td><td>展示什么</td></tr><tr><td>安全</td><td>permission-gate.ts、protected-paths.ts、confirm-destructive.ts、dirty-repo-guard.ts、project-trust.ts、sandbox/、gondolin/</td><td>tool_call 拦截、session_before_* 取消、project_trust；sandbox/ 用@anthropic-ai/sandbox-runtime 版本替换 bash；gondolin/ 在 QEMU micro-VM 里运行内置工具</td></tr><tr><td>工作流</td><td>subagent/、plan-mode/、todo.ts、handoff.ts、preset.ts、tools.ts、git-checkpoint.ts、auto-commit-on-exit.ts</td><td>子 pi 进程、按模式区分的工具集、自定义条目里的状态</td></tr><tr><td>工具</td><td>hello.ts、dynamic-tools.ts、tool-override.ts、structured-output.ts、ssh.ts、truncated-tool.ts、question.ts</td><td>register Tool、替换内置工具、terminate: true、远程执行</td></tr><tr><td>提示词与上下文</td><td>custom-compaction.ts、trigger-compact.ts、claude-rules.ts、prompt-customizer.ts、pirate.ts、dynamic-resources/</td><td>session_before_compact、before_agent_start、resources_discover</td></tr><tr><td>UI</td><td>custom-footer.ts、custom-header.ts、modal-editor.ts、overlay-test.ts、doom-overlay/、snake.ts、status-line.ts、notify.ts</td><td>ctx.ui 布局、覆盖层、自定义编辑器</td></tr><tr><td>供应商</td><td>custom-provider-anthropic/、custom-provider-gitlab-duo/、jev-router.ts</td><td>register Provider；jev-router.ts 注册一个虚拟模型</td></tr><tr><td>管道</td><td>event-bus.ts、rpc-demo.ts、reload-runtime.ts、interactive-shell.ts、inline-bash.ts、with-deps/</td><td>pi.events、RPC UI、/reload、user_bash、带自己 node_modules 的扩展</td></tr></table>

Forty-five of the 79 examples, sorted by what they teach. Descriptions from each file’s header comment.

79 个例子中的 45 个，按它们所教的东西排序。描述取自各文件的文件头注释。

W H A T T H I S M E A N S F O R Y O U

这 对 你 意 味 着 什 么

Throw in a tool_call handler only when you mean to block; in every other event a throw is logged and ignored.

只有在真打算拦截时才在 tool_call 处理器里抛异常；在其他任何事件里，抛出的异常都只会被记日志并忽略。

Return a reason with every block; it is the only thing the model learns.

每次拦截都要返回一个 reason；那是模型唯一能学到的东西。

Check ctx.hasUI before a dialog, or choose the safe default for print and JSON runs.

弹对话框前先检查 ctx.hasUI，或者为 print 和 JSON 运行挑选安全的默认值。

Put work that follows new Session(), fork() or switch Session() inside with Session.

把跟在 new Session()、fork() 或 switch Session() 之后的工作放进 with Session。

Sources: CA/src/core/extensions/types.ts (ExtensionUIContext, ExtensionContext, ExtensionToolContext, ExtensionCommandContext, event and result interfaces, SessionBoundaryDraft); CA/src/core/extensions/runner.ts (emit, emitCacheWarmingDecision, emitMessageEnd, emitToolResult, emitToolCall, emitUserBash, emit Context, emitBeforeProviderHeaders, emitBeforeAgentStart, emitResourcesDiscover, emit Input, emit Boundary, emitProjectTrustEvent, noOpUIContext, hasUI); CA/src/core/cache-warmer.ts; CA/src/core/agent-session.ts (_beforeToolCall, _afterToolCall); agent/agent-loop.ts (prepareToolCall); CA/src/modes/rpc/rpc-mode.ts (createExtensionUIContext); CA/src/modes/printmode.ts; CA/docs/extensions.md; CA/examples/extensions *; research/out/stats.txt (§example-extensions)

来源：CA/src/core/extensions/types.ts（ExtensionUIContext、ExtensionContext、ExtensionToolContext、ExtensionCommandContext、各事件与结果接口、SessionBoundaryDraft）；CA/src/core/extensions/runner.ts（emit、emitCacheWarmingDecision、emitMessageEnd、emitToolResult、emitToolCall、emitUserBash、emitContext、emitBeforeProviderHeaders、emitBeforeAgentStart、emitResourcesDiscover、emitInput、emitBoundary、emitProjectTrustEvent、noOpUIContext、hasUI）；CA/src/core/cache-warmer.ts；CA/src/core/agent-session.ts（_beforeToolCall、_afterToolCall）；agent/agent-loop.ts（prepareToolCall）；CA/src/modes/rpc/rpc-mode.ts（createExtensionUIContext）；CA/src/modes/printmode.ts；CA/docs/extensions.md；CA/examples/extensions *；research/out/stats.txt（§example-extensions）

### 5.5 Run modes: interactive, print and JSON

### 5.5 运行模式：interactive、print 与 JSON

Every way of starting Pi runs the same \`main()\` and builds the same

启动 Pi 的每种方式都运行同一个 \`main()\`，构建同一个

\`AgentSessionRuntime\`; the mode is chosen late,from twoflags and two TTY checks, and only decides who reads the events.

\`AgentSessionRuntime\`；模式选得很晚，由两个 flag 和两次 TTY 检查决定，而且只决定谁来读这些事件。

pi in a terminal opens a full-screen editor. pi -p "…" prints one answer and exits. pi --mode json streams every event as a JSON line, and pi --mode rpc keeps a JSONL conversation open on stdin and stdout. This section follows main() from argv to the point where it hands the runtime to a mode, then covers the three modes a person or a shell script drives directly: interactive, print and JSON. RPC and the in-process SDK are in RPC mode and the SDK (p. 133). Every flag mentioned here is listed in CLI reference (p. 191).

在终端里运行 pi 会打开一个全屏编辑器。pi -p "…" 打印一个答案然后退出。pi --mode json 把每个事件作为一行 JSON 流式输出，pi --mode rpc 则在 stdin 和 stdout 上维持一段JSONL 会话。本节沿着 main() 从 argv 跟到它把运行时交给某个模式的那一刻，然后覆盖人或 shell 脚本直接驱动的三种模式：interactive、print 和 JSON。RPC 和进程内 SDK 见 RPC 模式与 SDK (p. 133)。这里提到的每个 flag 都在 CLI 参考 (p. 191) 中列出。

## One entry point

## 单一入口

The pi binary is dist/bundle/cli.js CA/package.json:10, built from a six-line src/cli.ts. It calls setup Cli(), which sets process.title, exports PI_CODING_AGENT=true and AI_AGENT=pi, silences process.emit Warning and configures the HTTP dispatcher CA/src/cli/setup.ts:4. Then it calls main(process.argv.slice(2)) CA/src/cli.ts:6. The package also exports ./rpc-entry CA/package.json:19, which does the same setup with process.title set to pi-rpc and calls main(["- -mode", "rpc", ...argv]) CA/src/rpc-entry.ts:13. It is a module entry point, not a second bin.

pi 可执行文件是 dist/bundle/cli.js CA/package.json:10，由六行的 src/cli.ts 构建。它调用 setupCli()，后者设置 process.title、导出 PI_CODING_AGENT=true 和 AI_AGENT=pi、把 process.emit Warning 静音，并配置 HTTP dispatcher CA/src/cli/setup.ts:4。然后它调用 main(process.argv.slice(2)) CA/src/cli.ts:6。这个包还导出 ./rpc-entry CA/package.json:19，它做同样的 setup，只是把 process.title 设为 pi-rpc，并调用 main(["- -mode", "rpc", ...argv]) CA/src/rpc-entry.ts:13。它是一个模块入口点，不是第二个 bin。

main() CA/src/main.ts:573 then works through a fixed order. Subcommands are dispatched before any flag parsing, so pi auth, pi install or pi mcp never build a session.

随后 main() CA/src/main.ts:573 按一个固定顺序推进。子命令在任何 flag 解析之前就被分发，因此 pi auth、pi install 或 pi mcp 都不会构建会话。

F I G . 5 . 1 0 F R O M A R G V T O A M O D E

F I G . 5 . 1 0 从 A R G V 到 一 个 模 式

![](images/3522dbfb28a758095f32d4689f99506aa610ad6c81f1069a09ea6c66f6e2ab86.jpg)

The mode is decided at step 3 but used only at step 8. Everything between — migrations, session selection, project trust, extension loading, model resolution — is identical for all four modes. Line numbers are in CA/src/main.ts. Schematic.

模式在第 3 步决定，但直到第 8 步才被使用。中间的一切——迁移、会话选择、项目信任、扩展加载、模型解析——对四种模式都完全相同。行号均在 CA/src/main.ts 中。示意图。

Steps 1–8 in Fig. 5.10 (p. 127) map onto the source as follows:

图 5.10 (p. 127) 中的步骤 1–8 在源码里对应如下：

1 · Subcommands: runAuthCommand runs first, before cleanup or settings CA/src/main.ts:582. Then handlePackageCommand (install, remove, uninstall, update, list), which always ends with process.exit CA/src/main.ts:597; then handleConfigCommand CA/src/main.ts:610; then mcp CA/src/main.ts:614.

1 · 子命令：runAuthCommand最先运行，在 cleanup 或 settings 之前 CA/src/main.ts:582。然后是 handlePackageCommand（install、remove、uninstall、update、list），它总是以 process.exit 结束 CA/src/main.ts:597；然后是 handleConfigCommand CA/src/main.ts:610；再是 mcp CA/src/main.ts:614。

2 · Flags: parse Args collects errors as diagnostics; any error prints and exits 1 CA/src/main.ts:626. --version prints and exits; --export writes HTML and exits without building a runtime CA/src/main.ts:637.

2 · flag：parseArgs 把错误收集为诊断；任何错误都会打印并以 1 退出 CA/src/main.ts:626。--version 打印后退出；--export 写出 HTML 后退出，不构建运行时 CA/src/main.ts:637。

3 · Mode: see the decision ladder below. Every mode except interactive calls takeOverStdout() here, which reroutes stray process.stdout.write calls to stderr CA/src/core/output-guard.ts:45. RPC mode rejects @file arguments at this point CA/src/main.ts:657.

3 · 模式：见下面的判定阶梯。除 interactive 外的每种模式都在这里调用 takeOverStdout()，它把游离的 process.stdout.write 调用改道到 stderr CA/src/core/output-guard.ts:45。RPC 模式在这个点上拒绝 @file 参数 CA/src/main.ts:657。

4 · Session: createSessionManager picks one branch, first match wins: --no-session (or --help, --list-models) → in memory; --fork; --session; --resume; --continue; --session-id; otherwise a new file CA/src/main.ts:358. sessions, the JSONL tree (p. 86) describes the files.

4 · 会话：createSessionManager 选定一个分支，最先匹配者胜出：--no-session（或 --help、--list-models）→ 内存；--fork；--session；--resume；--continue；--session-id；否则新建文件 CA/src/main.ts:358。会话与 JSONL 树 (p. 86) 描述了这些文件。

5 · Runtime: createAgentSessionRuntime(create Runtime, …) runs the factory at CA/src/main.ts:730: createAgentSessionServices → DefaultResourceLoader.reload() (with the project-trust prompt between pre-trust and full extension loading) → createAgentSessionFromServices. The factory is kept, so /new, /resume and /fork rebuild through it.

5 · 运行时：createAgentSessionRuntime(createRuntime, …) 在 CA/src/main.ts:730 运行工厂：createAgentSessionServices → DefaultResourceLoader.reload()（项目信任提示夹在信任前与完整扩展加载之间）→ createAgentSessionFromServices。工厂被保留下来，因此 /new、/resume 和 /fork 都通过它重建。

6 · Metadata: --help is answered only after the runtime exists, because the help text lists flags registered by loaded extensions CA/src/main.ts:877.

6 · 元数据：--help 只在运行时存在之后才作答，因为帮助文本要列出已加载扩展注册的 flag CA/src/main.ts:877。

7 · Input: piped stdin is read for every mode except RPC, and its presence downgrades interactive to print CA/src/main.ts:895. Runtime diagnostics print; any error exits 1 CA/src/main.ts:919. A non-interactive mode with no model exits 1 CA/src/main.ts:927.

7 · 输入：除 RPC 外，每种模式都会读取管道进来的 stdin，而它的存在会把 interactive 降级为 print CA/src/main.ts:895。运行时诊断会打印；任何错误都以 1 退出 CA/src/main.ts:919。非交互模式在没有模型时以 1 退出 CA/src/main.ts:927。

8 · Hand-of: runRpcMode(runtime) CA/src/main.ts:950, new InteractiveMode(runtime, …).run() CA/src/main.ts:952, or runPrintMode(runtime, { mode }) CA/src/main.ts:986. Each mode then calls session.bind Extensions(…), which emits session_start and resources_discover extension events and contexts (p. 120).

8 · 移交：runRpcMode(runtime) CA/src/main.ts:950、new InteractiveMode(runtime, …).run() CA/src/main.ts:952，或 runPrintMode(runtime, { mode }) CA/src/main.ts:986。随后每种模式都调用 session.bindExtensions(…)，它会发出 session_start 和 resources_discover 扩展事件与上下文 (p. 120)。

## The decision ladder

## 判定阶梯

```txt the whole mode decision CA/src/main.ts:112

function resolveAppMode(parsed: Args, stdinIsTTY: boolean, stdoutIsTTY: boolean): AppMode {
    if (parsed.mode === "rpc") {
    return "rpc";
    }
    if (parsed.mode === "json") {
    return "json";
    }
    if (parsed.print || !stdinIsTTY || !stdoutIsTTY) {
    return "print";
    }
    return "interactive";
}
```

Complete function, copied from the pinned checkout.

完整函数，抄自锁定的 checkout。

The ladder has one consequence that surprises people: --mode text selects nothing. It is accepted by parse Args CA/src/cli/args.ts:103, but resolveAppMode never tests for it, so pi --mode text in a terminal still opens the TUI. Use -p for one-shot text. Redirecting either stdout or stdin is enough for print mode, and piped stdin later forces print even when both checks passed CA/src/main.ts:895.

这条阶梯有一个出人意料的后果：--mode text 什么也没选。parseArgs 会接受它 CA/src/cli/args.ts:103，但 resolveAppMode 从不检查它，所以在终端里 pi --mode text 仍然会打开 TUI。要一次性文本请用 -p。把 stdout 或 stdin 中任意一个重定向就足以进入 print 模式，而管道进来的 stdin 之后会强制 print，即便两次检查都通过了 CA/src/main.ts:895。

<table><tr><td>调用方式</td><td>模式</td><td>原因</td></tr><tr><td>pi</td><td>interactive</td><td>两个流都是 TTY</td></tr><tr><td>pi --mode text</td><td>interactive</td><td>text 不被检查</td></tr><tr><td>pi -p &quot;...&quot;</td><td>print</td><td>--print</td></tr><tr><td>pi &quot;...&quot; &gt; out.txt</td><td>print</td><td>stdout 不是 TTY</td></tr><tr><td>echo &quot;...&quot; | pi</td><td>print</td><td>stdin 不是 TTY</td></tr><tr><td>pi --mode json &quot;...&quot;</td><td>json</td><td>在 --print 之前检查</td></tr><tr><td>pi --mode rpc</td><td>rpc</td><td>最先检查</td></tr></table>

--mode beats --print, and a redirect beats nothing. From resolveAppMode CA/src/main.ts:112 and the stdin downgrade at CA/src/main.ts:895.

--mode 压过 --print，而重定向压过一切都不设。取自 resolveAppMode CA/src/main.ts:112 和 CA/src/main.ts:895 处的 stdin 降级。

The four modes difer only in what they do with the three standard streams and with extension dialogs:

![](images/9f47fb281d6ecad0b08f5a2575022fe6bfb46919a866915ea165e96256e21330.jpg)

Only interactive and RPC modes can ask a question. Print and JSON modes bind no UI context, so every extension dialog resolves to its default. The three non interactive modes reroute stray process.stdout.write calls to stderr so that stdout carries only their own output. Schematic, from CA/src/main.ts:651–655, CA/src/core/output-guard.ts, CA/src/modes/print-mode.ts and CA/src/modes/rpc/rpc-mode.ts.

四种模式的差别只在于它们对三个标准流和扩展对话框的处理：

只有 interactive 和 RPC 模式能提问。Print 和 JSON 模式不绑定任何 UI 上下文，所以每个扩展对话框都会 resolve 成默认值。三种非交互模式把游离的 process.stdout.write 调用改道到 stderr，好让 stdout 只承载它们自己的输出。示意图，取自 CA/src/main.ts:651–655、CA/src/core/output-guard.ts、CA/src/modes/print-mode.ts 和 CA/src/modes/rpc/rpc-mode.ts。

## Interactive mode

## Interactive 模式

InteractiveMode is 7,072 lines CA/src/modes/interactive/interactive-mode.ts and draws everything through pi-tui pi-tui (p. 158). It has two layouts, chosen by the tui Mode setting or --tui-mode: fullscreen, the default CA/src/core/settingsmanager.ts:1349, keeps the editor and status area fixed while the transcript scrolls inside the window; regular writes into the terminal’s own scrollback CA/docs/usage.md.

InteractiveMode 有 7072 行 CA/src/modes/interactive/interactive-mode.ts，全部通过 pi-tui 绘制 pi-tui (p. 158)。它有两种布局，由 tuiMode 设置或 --tui-mode 选择：fullscreen（默认）CA/src/core/settingsmanager.ts:1349 把编辑器和状态区固定住，让记录在窗口内滚动；regular 则直接写进终端自己的回滚缓冲 CA/docs/usage.md。

The editor’s submit handler decides what a line means, in this order CA/src/modes/interactive/interactive-mode.ts:3179:

编辑器的提交处理器按下面的顺序决定一行输入的含义 CA/src/modes/interactive/interactive-mode.ts:3179：

<table><tr><td>输入</td><td>效果</td></tr><tr><td>内置的 /command</td><td>由该模式自己处理；这 24 个命令见斜杠命令与键位绑定 (p. 197)</td></tr><tr><td>! cmd</td><td>用 bash 运行 cmd，并把输出加入上下文</td></tr><tr><td>!! cmd</td><td>运行 cmd 但不把它加入上下文</td></tr><tr><td>压缩期间的任意文本</td><td>排队直到压缩结束；扩展命令仍会立即执行</td></tr><tr><td>流式期间的任意文本</td><td>session.prompt(text, { streamingBehavior: &quot;steer&quot; })</td></tr><tr><td>空闲时的任意文本</td><td>一条新的提示词</td></tr></table>

Enter steers a running agent; it does not wait. Alt+Enter queues a follow-up instead, and Alt+Up pulls queued text back into the editor. Submit handler at CA/src/modes/interactive/interactive-mode.ts:3179; keys from CA/src/core/keybindings.ts:135.

Enter 会转向一个正在运行的智能体，不会等待。Alt+Enter 则改为把一条后续消息排队，Alt+Up 把排队的文本拉回编辑器。提交处理器在 CA/src/modes/interactive/interactive-mode.ts:3179；按键来自 CA/src/core/keybindings.ts:135。

Escape is overloaded, and the first matching state wins CA/src/modes/interactive/interactive-mode.ts:3050. While the agent streams, Escape aborts and moves every queued steering and follow-up message back into the editor, joined by blank lines CA/src/modes/interactive/interactive-mode.ts:4702. While a ! command runs, it aborts the command. In bash mode it clears the line. With an empty editor, two presses within 500 ms open /tree, /fork or nothing, depending on doubleEscapeAction CA/src/modes/interactive/interactive-mode.ts:3064. Ctrl+C clears the editor, and a second press within 500 ms exits CA/src/modes/interactive/interactive-mode.ts:4231.

Escape 的语义被重载了，最先匹配的状态胜出 CA/src/modes/interactive/interactive-mode.ts:3050。智能体在流式输出时，Escape 中止运行，并把每一条排队的转向和后续消息用空行连接后移回编辑器 CA/src/modes/interactive/interactive-mode.ts:4702。! 命令正在运行时，它中止该命令。在 bash 模式下它清空当前行。编辑器为空时，500 ms 内的两次按下会打开 /tree、/fork 或什么都不做，取决于 doubleEscapeAction CA/src/modes/interactive/interactive-mode.ts:3064。Ctrl+C 清空编辑器，500 ms 内的第二次按下则退出 CA/src/modes/interactive/interactive-mode.ts:4231。

## Print mode

## Print 模式

Print mode sends its prompts in order and exits. The first prompt is assembled from three parts — piped stdin, @file text, and the first positional message — and the remaining messages follow as separate prompts CA/src/cli/initial-message.ts:20 CA/src/modes/print-mode.ts:131.

Print 模式依次发出它的提示词然后退出。第一条提示词由三部分拼成——管道进来的 stdin、@file 文本和第一条位置消息——其余消息则作为单独的提示词跟进 CA/src/cli/initial-message.ts:20 CA/src/modes/print-mode.ts:131。

```javascript what text print mode writes CA/src/modes/print-mode.ts:139 TS if (mode === "text") {
    const state = session.state;
    const last Message = state.messages[state.messages.length - 1];

    if (last Message?.role === "assistant") {
    const assistant Msg = last Message as AssistantMessage;
    if (assistant Msg.stop Reason === "error" || assistant Msg.stop Reason === "aborted") {
    console.error(assistant Msg.error Message || `Request ${assistant Msg.stop Reason}`);
    exit Code = 1;
    } else {
    for (const content of assistant Msg.content) {
    if (content.type === "text") {
    writeRawStdout(`${content.text}\n');
    }
    }
    }
}
```

Complete block. Thinking and tool-call blocks of the last message are not printed; nothing from earlier messages is printed.

完整代码块。最后一条消息里的思考块和工具调用块不会被打印；更早消息里的任何内容也不会。

Only the last assistant message reaches stdout. If the run ended in error or aborted, the error goes to stderr and the exit code is 1. A thrown error also exits 1 CA/src/modes/print-mode.ts:159.

只有最后一条 assistant 消息会到达 stdout。如果这次运行以 error 或 aborted 结束，错误会写进 stderr，退出码为 1。抛出的异常同样以 1 退出 CA/src/modes/print-mode.ts:159。

Piped stdin and the prompt are joined with no separator. readPipedStdin trims the input CA/src/main.ts:93, and buildInitialMessage joins stdin, file text and the first message with "" CA/src/cli/initial-message.ts:40. So cat notes.txt | pi -p "Summarise this" sends the file’s last line glued to “Summarise this”. The unit test passes stdin with a trailing newline, which the CLI never delivers CA/test/initial-message.test.ts. Start the prompt with a newline or a space, or put the instruction inside the piped text.

管道进来的 stdin 与提示词之间没有任何分隔符。readPipedStdin 会对输入做 trim CA/src/main.ts:93，而 buildInitialMessage 用 "" 把 stdin、文件文本和第一条消息连起来 CA/src/cli/initial-message.ts:40。所以 cat notes.txt | pi -p "Summarise this" 会把文件的最后一行粘在「Summarise this」前面送出去。单元测试传入的 stdin 末尾带换行，而 CLI 永远不会那样送 CA/test/initial-message.test.ts。让提示词以换行或空格开头，或者把指令放进管道文本里。

## JSON mode

## JSON 模式

JSON mode is print mode with a diferent subscriber. Line 1 is the session header, written before extensions are bound CA/src/modes/print-mode.ts:122. Every AgentSessionEvent follows, one JSON line each, through toJsonEvent CA/src/modes/print-mode.ts:110. Nothing else is written to stdout, and the exit code follows the same rules as text mode.

JSON 模式就是换了一个订阅者的 print 模式。第 1 行是会话头，在扩展绑定之前写出 CA/src/modes/print-mode.ts:122。随后是每一个 AgentSessionEvent，每个占一行 JSON，经过 toJsonEvent CA/src/modes/print-mode.ts:110。stdout 上不写任何别的东西，退出码遵循与 text 模式相同的规则。

toJsonEvent changes one event type. A message_update loses the cumulative message and the partial snapshot inside its assistantMessageEvent, and gains a top-level usage CA/src/modes/json-event.ts:48. A toolcall_start keeps the tool call’s id and tool Name, which would otherwise be lost with the partial CA/src/modes/json-event.ts:23. Every other event passes through unchanged. RPC mode uses the same function, so the shapes below are also the RPC event shapes.

toJsonEvent 改动了一种事件类型。message_update 失去了累积的 message 以及其 assistantMessageEvent 里的部分快照，转而多出一个顶层的 usage CA/src/modes/json-event.ts:48。toolcall_start 保留了工具调用的 id 和 toolName，否则它们会随部分快照一起丢失 CA/src/modes/json-event.ts:23。其他所有事件都原样透传。RPC 模式用的是同一个函数，所以下面的这些形状也就是 RPC 事件的形状。

The capture kit ran one prompt through a real runtime in JSON mode, with the faux provider and one inline extension that calls ctx.ui.confirm() before each tool call research/capture/rpc-and-sdk-child.mjs:

实测工具用 JSON 模式把一条提示词跑过真实运行时，使用 faux 供应商和一个在每次工具调用前调用 ctx.ui.confirm() 的内联扩展 research/capture/rpc-and-sdk-child.mjs：

```jsonl
{"type":"session","version":3,"id":"<uuid>", "timestamp":"2026-10-05T23:26:18.959Z","cwd":"<tmp>/project"}
{"type":"agent_start"}
{"type":"turn_start"}
{"type":"message_start","message":{"role":"system","content":"","sections":...}}}
{"type":"message_end","message":{"role":"system", ...}}
{"type":"message_start","message":{"role":"user","content":[{"type":"text","text":"What does hello.txt say?"}],"timestamp:<ts>}}
{"type":"message_end", ...}
{"type":"message_start","message":{"role":"assistant","content":[], ...}}
{"type":"message_update","usage":{"input":1468,"output":10, ...},"assistantMessageEvent":
{"type":"toolcall_start","content Index":1,"id":"call_1","tool Name":"read"}}

{"type":"tool_execution_start","toolCallId":"call_1","tool Name":"read","args":{"path":"hello.txt"}}"
{"type":"tool_execution_end","toolCallId":"call_1","tool Name":"read","result":{"content":[{"type":"text","text":"not confirmed"}],"details":{}],"isError":true}}

{"type":"agent_end","messages":[...],"will Retry":false}
{"type":"agent_settled"}
```

The capture holds 31 lines: the header, 1 agent_start, 2 turns, 5 message pairs, 11 message_update lines, one tool execution, agent_end and agent_settled research/out/rpc-exchange.txt §json-mode. The number of text_delta updates changes from run to run; the order does not. Long values are cut with … here.

这份实测共 31 行：会话头、1 个 agent_start、2 个轮次、5 对 message、11 行 message_update、一次工具执行、agent_end 和 agent_settled research/out/rpc-exchange.txt §json-mode。text_delta 更新的条数每次运行都会变；顺序不会。这里长值都用 … 截断。

The tool_execution_end line shows the cost of having no UI. Print and JSON modes bind extensions without a uiContext CA/src/modes/print-mode.ts:76, so the runner keeps its no-op context and ctx.hasUI is false

CA/src/core/extensions/runner.ts:621. In that context select and input resolve to undefined and confirm resolves to falseCA/src/core/extensions/runner.ts:324. The extension’s own guard blocked the tool. The same extension in RPC mode asks the client instead (Fig. 5.12 (p. 134)).

tool_execution_end 那一行展示了没有 UI 的代价。Print 和 JSON 模式绑定扩展时不带 uiContext CA/src/modes/print-mode.ts:76，所以 runner 保留自己的空操作上下文，ctx.hasUI 为 false CA/src/core/extensions/runner.ts:621。在那个上下文里 select 和 input resolve 成 undefined，confirm resolve 成 false CA/src/core/extensions/runner.ts:324。是扩展自己的守卫拦下了这个工具。同一个扩展在 RPC 模式下则会改为询问客户端（图 5.12 (p. 134)）。

D O C ≠ C O D E

文 档 ≠ 代 码

The basic run in CA/docs/json.md (§Event sequence) starts with the user message and shows its content as a string. The real stream emits a message_start/message_end pair with role: "system" before the user message, and the user message’s content is an array of content blocks research/out/rpc-exchange.txt §json-mode. A strict parser written from the documented sample fails on line 4.

CA/docs/json.md（§Event sequence）里的基本运行从用户消息开始，并把它的 content 显示为字符串。真实的流会在用户消息之前先发出一对 role: "system" 的 message_start/message_end，而且用户消息的 content 是一个内容块数组 research/out/rpc-exchange.txt §json-mode。按文档示例写的严格解析器会在第 4 行失败。

## Signals

## 信号

<table><tr><td>信号</td><td>PRINT / JSON</td><td>RPC</td></tr><tr><td>SIGTERM</td><td>dispose 运行时，退出码 143</td><td>dispose 运行时，退出码 143，stdout 未刷新</td></tr><tr><td>SIGHUP（非 Windows）</td><td>dispose 运行时，退出码 129</td><td>dispose 运行时，退出码 129</td></tr><tr><td>stdin EOF</td><td>—</td><td>dispose 运行时，退出码 0</td></tr></table>

Every orderly exit fires session_shutdown with reason: "quit". AgentSessionRuntime.dispose() emits it before disposing the session CA/src/core/agent-session-runtime.ts:404. Handlers at CA/src/modes/print-mode.ts:50 and CA/src/modes/rpc/rpc-mode.ts:366; tracked detached children are killed first in both.

每一次有序退出都会触发带 reason: "quit" 的 session_shutdown。AgentSessionRuntime.dispose() 在 dispose 会话之前发出它 CA/src/core/agent-session-runtime.ts:404。处理器在 CA/src/modes/print-mode.ts:50 和 CA/src/modes/rpc/rpc-mode.ts:366；两者都先杀掉被跟踪的 detached 子进程。

W H A T T H I S M E A N S F O R Y O U

这 对 你 意 味 着 什 么

Use -p for one-shot text; --mode text alone still opens the TUI in a terminal.

一次性文本用 -p；只写 --mode text 在终端里仍会打开 TUI。

Parse JSON mode from message_start, the deltas and message_end; there is no cumulative snapshot in message_update.

解析 JSON 模式要靠 message_start、各个 delta 和 message_end；message_update 里没有累积快照。

Give every extension dialog a safe default: in print and JSON modes confirm always answers false.

给每个扩展对话框一个安全的默认值：在 print 和 JSON 模式下 confirm 总是回答 false。

Check the exit code: 1 means the last assistant message ended in error or aborted.

检查退出码：1 意味着最后一条 assistant 消息以 error 或 aborted 结束。

Sources: CA/package.json (bin, exports); CA/src/cli.ts; CA/src/cli/setup.ts (setup Cli); CA/src/rpc-entry.ts; CA/src/main.ts (main, resolveAppMode, createSessionManager, readPipedStdin, create Runtime). CA/src/cli/args.ts (parse Args); CA/src/cli/initial-message.ts (buildInitialMessage); CA/src/core/output-guard.ts (takeOverStdout). CA/src/modes/print-mode.ts (runPrintMode); CA/src/modes/json-event.ts (toJsonEvent); CA/src/core/extensions/runner.ts (noOpUIContext, hasUI); CA/src/core/agent-session-runtime.ts (dispose). CA/src/modes/interactive/interactive-mode.ts (setupEditorSubmitHandler, setupKeyHandlers, restoreQueuedMessagesToEditor, handleCtrlC); CA/src/core/keybindings.ts; CA/src/core/settings-manager.ts (getTuiMode, getDoubleEscapeAction). CA/test/initial-message.test.ts; CA/docs/json.md, usage.md; research/capture/rpc-and-sdk-child.mjs; research/out/rpc-exchange.txt (§json-mode)

来源：CA/package.json（bin、exports）；CA/src/cli.ts；CA/src/cli/setup.ts（setupCli）；CA/src/rpc-entry.ts；CA/src/main.ts（main、resolveAppMode、createSessionManager、readPipedStdin、createRuntime）。CA/src/cli/args.ts（parseArgs）；CA/src/cli/initial-message.ts（buildInitialMessage）；CA/src/core/output-guard.ts（takeOverStdout）。CA/src/modes/print-mode.ts（runPrintMode）；CA/src/modes/json-event.ts（toJsonEvent）；CA/src/core/extensions/runner.ts（noOpUIContext、hasUI）；CA/src/core/agent-session-runtime.ts（dispose）。CA/src/modes/interactive/interactive-mode.ts（setupEditorSubmitHandler、setupKeyHandlers、restoreQueuedMessagesToEditor、handleCtrlC）；CA/src/core/keybindings.ts；CA/src/core/settings-manager.ts（getTuiMode、getDoubleEscapeAction）。CA/test/initial-message.test.ts；CA/docs/json.md、usage.md；research/capture/rpc-and-sdk-child.mjs；research/out/rpc-exchange.txt（§json-mode）

## 5.6 RPC mode and the SDK

## 5.6 RPC 模式与 SDK

RPC mode is the SDK's \`AgentSession\` withJSONL on both ends — 33 commands in, events and responses out — and its one real addition is a small protocol that lets an extension ask the client a question.

RPC 模式就是 SDK 的 \`AgentSession\`，两端都用 JSONL——进去 33 个命令，出来事件和响应——它唯一真正的 additions是一个小协议，让扩展能向客户端提问。

An IDE, a Python service or a web backend that wants Pi has two doors. It can spawn pi --mode rpc and talk JSONL over pipes, or it can import @earendil-works/pi-coding-agent and hold an AgentSession in its own process. This section records one real RPC conversation, lists every command and its response data, describes the extension UI sub-protocol and the TypeScript RpcClient, and then shows the SDK calls the CLI itself is built from. How the CLI reaches runRpcMode is in run modes (p. 127); the events themselves are in agent events and the Agent class (p. 57).

想要 Pi 的 IDE、Python 服务或 web 后端有两扇门。它可以 spawn pi --mode rpc 并通过管道说 JSONL，也可以 import @earendil-works/pi-coding-agent 并在自己进程里持有一个 AgentSession。本节记录一段真实的 RPC 会话，列出每个命令及其响应数据，描述扩展 UI 子协议和 TypeScript 的 RpcClient，然后展示 CLI 自身是由哪些 SDK 调用搭起来的。CLI 如何走到 runRpcMode 见运行模式 (p. 127)；事件本身见智能体事件与 Agent 类 (p. 57)。

#### Framing: strict JSONL

#### 分帧：严格 JSONL

Each record is one JSON object followed by LF. serializeJsonLine is JSON.stringify(value) + "\n" CA/src/modes/rpc/jsonl.ts:10. The reader splits on \n only and strips one trailing \r, so CRLF input works CA/src/modes/rpc/jsonl.ts:26.

每条记录是一个 JSON 对象后跟LF。serializeJsonLine 就是 JSON.stringify(value) + "\n" CA/src/modes/rpc/jsonl.ts:10。读取器只按 \n 切分，并剥掉一个结尾的 \r，所以 CRLF 输入也能工作 CA/src/modes/rpc/jsonl.ts:26。

```typescript why Pi does not use readline CA/src/modes/rpc/jsonL.ts:14 TS

/**
 * Attach an LF-only JSONL reader to a stream.
 *
 * This intentionally does not use Node readline. Readline splits on additional
 * Unicode separators that are valid inside JSON strings and therefore does not
 * implement strict JSONL framing.
 */
export function attachJsonLLineReader(stream: Readable,上线: (line: string) => void): () => void {
    const decoder = new StringDecoder("utf8");
    let buffer = "";
    ...
}
```

Cut after the first two statements; the rest bufers chunks and emits each LF-terminated line.

截到前两条语句为止；其余部分负责缓冲数据块，并把每个以 LF 结尾的行发出来。

The separators in question are U+2028 and U+2029. Both are legal inside a JSON string, and a model can produce either one. A client that reads with Node readline splits such a record in two and fails to parse both halves CA/docs/rpc.md §Framing. runRpcMode calls takeOverStdout() before anything else CA/src/modes/rpc/rpc-mode.ts:55, so an extension that calls console.log writes to stderr and cannot corrupt the stream.

说的那两个分隔符是 U+2028 和 U+2029。两者在 JSON 字符串里都合法，而模型可能产出其中任意一个。用 Node readline 读取的客户端会把这样一条记录切成两半，并且两半都解析失败 CA/docs/rpc.md §Framing。runRpcMode 在做任何其他事之前先调用 takeOverStdout() CA/src/modes/rpc/rpc-mode.ts:55，所以调用 console.log 的扩展会写到 stderr，无法污染数据流。

## One exchange, recorded

## 一段实录 exchanges

The capture kit spawns a real runRpcMode with the faux provider and one inline extension that calls ctx.ui.confirm() before every tool call, then plays the client research/capture/rpc-and-sdk-exchange.mjs. The model is scripted to call read once and then answer.

实测工具spawn 一个真实的 runRpcMode，使用 faux 供应商和一个在每次工具调用前调用 ctx.ui.confirm() 的内联扩展，然后扮演客户端 research/capture/rpc-and-sdk-exchange.mjs。模型被编排成先调用一次 read，然后回答。

F I G . 5 . 1 2 O N E R P C C O N V E R S A T I O N

F I G . 5 . 1 2 一 次 R P C 会 话

2

2

4

4

5

5

6

6

![](images/eb4c550aa4ebe0d87971d2a8b24eb592f9933906c12bae801f42992a6a7132f4.jpg)

The prompt response arrives before the run; agent_settled marks its end. 43 records: 6 from the client, 36 from Pi, plus the exit. Steps 2–3 are the extension UI sub-protocol. From research/out/rpc-exchange.txt; event counts vary with the number of streamed text deltas.

prompt 的响应在运行之前就到达；agent_settled 标记它的结束。共 43 条记录：客户端 6 条、Pi 36 条，加上退出。步骤 2–3 是扩展 UI 子协议。取自 research/out/rpc-exchange.txt；事件条数随流式 text delta 的数量变化。

The first three records, exactly as captured:

前三条记录，与实测完全一致：

```txt
> {"id":"1","type":"prompt","message":"What does hello.txt say?"}
< {"id":"1","type":"response","command":"prompt","success":true,"data":{"disposition":"started"}} < {"type":"agent_start"}
```

And the end of the conversation, after agent_settled:

以及会话的结尾，在 agent_settled 之后：

```jsonl
{"id":"2","type":"get_last_assistant_text"}
{ "id":"2","type":"response","command":"get_last_assistant_text","success":true,"data":{"text":"It says: Hello from the capture kit."}}
{ not json
{ "type":"response","command":"parse","success":false,"error":"Failed to parse command: Expected property name or '}' in JSON at position 1 (line 1 column 2)"
{ "id":"4","type":"make_coffee"}
{ "id":"4","type":"response","command":"make_coffee","success":false,"error":"Unknown command: make_coffee"}
> (stdin closed)
(exit code=0 signal=null)
```

## Responses and errors

## 响应与错误

Every command produces at most one response record. Events carry no command id, with one exception: bash_execution_update repeats the id of the bash command that started it CA/src/core/agent-session.ts:3847.

每个命令最多产生一条响应记录。事件不带命令 id，只有一个例外：bash_execution_update 会重复启动它的那条 bash 命令的 id CA/src/core/agent-session.ts:3847。

Success: { id?, type: "response", command, success: true, data? }. data is omitted when the command returns nothing CA/src/modes/rpc/rpc-mode.ts:64.

成功：{ id?, type: "response", command, success: true, data? }。命令没有返回内容时省略 data CA/src/modes/rpc/rpc-mode.ts:64。

Failure: { id?, type: "response", command, success: false, error } CA/src/modes/rpc/rpc-types.ts:245. A thrown handler error becomes a failure with the command’s own id and type CA/src/modes/rpc/rpc-mode.ts:790.

失败：{ id?, type: "response", command, success: false, error } CA/src/modes/rpc/rpc-types.ts:245。处理器抛出的异常会变成一条失败，带该命令自己的 id 和 type CA/src/modes/rpc/rpc-mode.ts:790。

Parse error: a line that is not JSON gets command: "parse" and no id CA/src/modes/rpc/rpc-mode.ts:755.

解析错误：不是 JSON 的一行会得到 command: "parse" 且没有 id CA/src/modes/rpc/rpc-mode.ts:755。

Unknown command: command is the unknown type, and error is Unknown command: <type> CA/src/modes/rpc/rpcmode.ts:715.

未知命令：command 是那个未知的 type，error 是 Unknown command: <type> CA/src/modes/rpc/rpcmode.ts:715。

prompt: answers when preflight accepts the prompt, through the preflight Result callback, not when the run ends CA/src/modes/rpc/rpc-mode.ts:403. disposition is started, queued or handled CA/src/core/agent-session.ts:301. handled means an extension consumed the input and no run starts, so no agent_settled will follow. A prompt rejected before preflight gets a failure response instead.

prompt：在 preflight 接受提示词时就作答——通过 preflight 的 Result 回调，而不是等运行结束 CA/src/modes/rpc/rpc-mode.ts:403。disposition 是 started、queued 或 handled CA/src/core/agent-session.ts:301。handled 表示某个扩展消费掉了输入，不会启动运行，因此后面不会有 agent_settled。在 preflight 之前就被拒绝的提示词会得到一条失败响应。

agent_end is not the end. Retries, overflow recovery, compaction and queued follow-ups can start another low-level run after it. Wait for agent_settled CA/docs/rpc.md §Run lifecycle.

agent_end 不是终点。重试、溢出恢复、压缩和排队的后续消息都可能在它之后启动另一次底层运行。要等 agent_settled CA/docs/rpc.md §Run lifecycle。

## The 33 commands

## 33 个命令

RpcCommand is a union of 33 shapes CA/src/modes/rpc/rpc-types.ts:20. Every one accepts an optional string id.

RpcCommand 是 33 种形状的联合 CA/src/modes/rpc/rpc-types.ts:20。每一个都接受一个可选的字符串 id。

<table><tr><td>领域</td><td>命令</td><td>参数</td><td>响应 data</td></tr><tr><td>提示</td><td>prompt</td><td>message, images?, streaming Behavior?: &quot;steer&quot; | &quot;followUp&quot;</td><td>{ disposition }</td></tr><tr><td></td><td>steer、follow_up</td><td>message, images?</td><td>{ disposition: &quot;queued&quot; | &quot;handled&quot; }</td></tr><tr><td></td><td>abort</td><td>-</td><td>-</td></tr><tr><td></td><td>clear_queue</td><td>-</td><td>{ steering: string[], followUp: string[] }</td></tr><tr><td></td><td>new_session</td><td>parent Session?</td><td>{ cancelled }</td></tr><tr><td>状态</td><td>get_state</td><td>-</td><td>RpcSessionState</td></tr><tr><td></td><td>get_messages</td><td>-</td><td>{ messages }</td></tr><tr><td>模型</td><td>set_model</td><td>provider, modelId</td><td>该 Model</td></tr><tr><td></td><td>cycle_model</td><td>-</td><td>{ model, thinkingLevel, isScoped} 或 null</td></tr><tr><td></td><td>get_available_models</td><td>-</td><td>{ models }</td></tr><tr><td>思考</td><td>set_thinking_level</td><td>level</td><td>-</td></tr><tr><td></td><td>cycle_thinking_level</td><td>-</td><td>{ level } 或 null</td></tr><tr><td></td><td>get_available_thinking_levels</td><td>-</td><td>{ levels }</td></tr><tr><td>队列</td><td>set_steering_mode、set_follow_up_mode</td><td>mode: &quot;all&quot; | &quot;one-at-a-time&quot;</td><td>-</td></tr><tr><td>压缩</td><td>compact</td><td>custom Instructions?</td><td>CompactionResult</td></tr><tr><td></td><td>set_auto_compaction</td><td>enabled</td><td>-</td></tr><tr><td>重试</td><td>set_auto_retry</td><td>enabled</td><td>-</td></tr><tr><td></td><td>abort_retry</td><td>-</td><td>-</td></tr><tr><td>Bash</td><td>bash</td><td>command, excludeFromContext?</td><td>BashResult；流式发出 bash_execution_update</td></tr><tr><td></td><td>abort_bash</td><td>-</td><td>-</td></tr><tr><td>会话</td><td>get_session_stats</td><td>-</td><td>SessionStats（计数、token、成本）</td></tr><tr><td></td><td>export_html</td><td>output Path?</td><td>{ path }</td></tr><tr><td></td><td>switch_session</td><td>session Path</td><td>{ cancelled }</td></tr><tr><td></td><td>fork</td><td>entryId</td><td>{ text, cancelled }</td></tr><tr><td></td><td>cloneget_entries</td><td>-since? (entry id)</td><td>{ cancelled }{ entries, leafId }</td></tr><tr><td></td><td>get_tree</td><td>—</td><td>{ tree, leafId }</td></tr><tr><td></td><td>get_last_assistant_text</td><td>—</td><td>{ text }（或 null）</td></tr><tr><td></td><td>set_session_name</td><td>name</td><td>—</td></tr><tr><td>发现</td><td>get_commands</td><td>—</td><td>{ commands }：扩展命令、提示词模板、skill:</td></tr></table>

Every command maps to one AgentSession or AgentSessionRuntime call. From the RpcCommand and RpcResponse unions CA/src/modes/rpc/rpctypes.ts:20 CA/src/modes/rpc/rpc-types.ts:116 and handle Command CA/src/modes/rpc/rpc-mode.ts:386. A dash means the success response has no data.

每个命令都对应一次 AgentSession 或 AgentSessionRuntime 调用。取自 RpcCommand 和 RpcResponse 联合类型 CA/src/modes/rpc/rpctypes.ts:20 CA/src/modes/rpc/rpc-types.ts:116 以及 handleCommand CA/src/modes/rpc/rpc-mode.ts:386。短横线表示成功响应没有 data。

Three commands fail with their own messages: set_model with Model not found: <provider>/<id> CA/src/modes/rpc/rpc-mode.ts:474, get_entries with Entry not found: <since> CA/src/modes/rpc/rpc-mode.ts:642, and set_session_name with Session name cannot be empty CA/src/modes/rpc/rpc-mode.ts:662. clone is fork at the current leaf with position: "at" CA/src/modes/rpc/rpc-mode.ts:624. new_session, switch_session, fork and clone replace the active session and rebind extensions and the event subscription to the new one CA/src/modes/rpc/rpc-mode.ts:438. Slash commands are not RPC commands: send /name as the message of a prompt, and get_commands lists what is available. The 24 built-in interactive commands in slash commands and keybindings (p. 197) are not among them.

三个命令会失败并给出各自的专属消息：set_model 报 Model not found: <provider>/<id> CA/src/modes/rpc/rpc-mode.ts:474，get_entries 报 Entry not found: <since> CA/src/modes/rpc/rpc-mode.ts:642，set_session_name 报 Session name cannot be empty CA/src/modes/rpc/rpc-mode.ts:662。clone 就是在当前叶子处、带position: "at" 的 fork CA/src/modes/rpc/rpc-mode.ts:624。new_session、switch_session、fork 和 clone 会替换当前会话，并把扩展和事件订阅重新绑定到新会话 CA/src/modes/rpc/rpc-mode.ts:438。斜杠命令不是 RPC 命令：把 /name 作为 prompt 的 message 发出去，而 get_commands 会列出可用的东西。斜杠命令与键位绑定 (p. 197) 里的 24 个内置交互命令不在其中。

get_state returns RpcSessionState CA/src/modes/rpc/rpc-types.ts:96. It has no session header; RPC mode never writes one, unlike JSON mode.

get_state 返回 RpcSessionState CA/src/modes/rpc/rpc-types.ts:96。它没有会话头；与 JSON 模式不同，RPC 模式从不写会话头。

<table><tr><td>字段</td><td>类型</td><td>字段</td><td>类型</td></tr><tr><td>model?</td><td>Model</td><td>session File?</td><td>string</td></tr><tr><td>thinkingLevel</td><td>ThinkingLevel</td><td>sessionId</td><td>string</td></tr><tr><td>isStreaming</td><td>boolean</td><td>session Name?</td><td>string</td></tr><tr><td>isCompacting</td><td>boolean</td><td>autoCompactionEnabled</td><td>boolean</td></tr><tr><td>steeringMode</td><td>&quot;all&quot; | &quot;one-at-a-time&quot;</td><td>message Count</td><td>number</td></tr><tr><td>followUpMode</td><td>&quot;all&quot; | &quot;one-at-a-time&quot;</td><td>pendingMessageCount</td><td>number</td></tr></table>

Twelve fields, read live from the session on every call. CA/src/modes/rpc/rpc-mode.ts:448.

十二个字段，每次调用都从会话实时读取。CA/src/modes/rpc/rpc-mode.ts:448。

Besides every AgentSessionEvent in JSON-mode form (run modes (p. 127)), stdout carries extension_error records, { type, extension Path, event, error }, when an extension handler throws CA/src/modes/rpc/rpc-mode.ts:349.

除了 JSON 形式的每个 AgentSessionEvent（运行模式 (p. 127)）之外，扩展处理器抛异常时，stdout 还会带上 extension_error 记录 { type, extensionPath, event, error } CA/src/modes/rpc/rpc-mode.ts:349。

## The extension UI sub-protocol

## 扩展 UI 子协议

RPC mode binds extensions with a real uiContext CA/src/modes/rpc/rpc-mode.ts:320, so ctx.hasUI is true and ctx.mode is "rpc". Each supported call becomes an extension_ui_request with a fresh crypto.randomUUID() id CA/src/modes/rpc/rpc-mode.ts:99. Dialogs wait for an extension_ui_response with that id; the other methods expect no reply.

RPC 模式用真实的 uiContext 绑定扩展 CA/src/modes/rpc/rpc-mode.ts:320，因此 ctx.hasUI 为 true，ctx.mode 为 "rpc"。每个受支持的调用都会变成一条带全新 crypto.randomUUID() id 的 extension_ui_request CA/src/modes/rpc/rpc-mode.ts:99。对话框会等待带该 id 的 extension_ui_response；其他方法则不期待回复。

<table><tr><td>方法</td><td>请求字段</td><td>客户端回复</td><td>超时或中止时的默认值</td></tr><tr><td>select</td><td>title、options[]、timeout?</td><td>{ value } 或 { cancelled: true }</td><td>undefined</td></tr><tr><td>confirm</td><td>title、message、timeout?</td><td>{ confirmed } 或 { cancelled: true }</td><td>false</td></tr></table>

RPC mode and the SDK

R P C 模 式 与 S D K

<table><tr><td>input</td><td>title, placeholder?, timeout?</td><td>{ value } 或 { cancelled: true }</td><td>undefined</td></tr><tr><td>editor</td><td>title,prefill?</td><td>{ value } 或 { cancelled: true }</td><td>无：一直等客户端</td></tr><tr><td>notify</td><td>message, notify Type?</td><td>不回复</td><td>—</td></tr><tr><td>set State</td><td>status Key, status Text</td><td>不回复</td><td>—</td></tr><tr><td>set Widget</td><td>widget Key, widget Lines, widget Placement?</td><td>不回复</td><td>—</td></tr><tr><td>set Title</td><td>title</td><td>不回复</td><td>—</td></tr><tr><td>set_editor_text</td><td>text</td><td>不回复</td><td>—</td></tr></table>

Pi, not the client, enforces dialog timeouts. createDialogPromise resolves to the default when the timeout fires or the extension’s signal aborts CA/src/modes/rpc/rpc-mode.ts:91. set Widget is sent only for string arrays; component factories are dropped CA/src/modes/rpc/rpc-mode.ts:197. pasteToEditor becomes set_editor_text.

对话框超时由 Pi 而非客户端强制执行。超时触发或扩展的 signal 中止时，createDialogPromise resolve 成默认值 CA/src/modes/rpc/rpc-mode.ts:91。setWidget 只对字符串数组发送；组件工厂被丢弃 CA/src/modes/rpc/rpc-mode.ts:197。pasteToEditor 变成 set_editor_text。

The rest of ExtensionUIContext degrades without a message. custom() returns undefined, getEditorText() returns "", set Theme() returns { success: false, … }, and the footer, header, working-indicator and editor-component setters do nothing CA/src/modes/rpc/rpc-mode.ts:179. A response whose id matches no pending request is dropped silently CA/src/modes/rpc/rpc-mode.ts:774.

ExtensionUIContext 的其余部分会无提示地降级。custom() 返回 undefined，getEditorText() 返回 ""，setTheme() 返回 { success: false, … }，而 footer、header、工作指示器和编辑器组件的 setter什么都不做 CA/src/modes/rpc/rpc-mode.ts:179。id 匹配不上任何待处理请求的响应会被静默丢弃 CA/src/modes/rpc/rpc-mode.ts:774。

## F O O T G U N
## 警 告
editor is the one dialog that does not go through createDialogPromise. It takes no timeout and ignores the abort signal CA/src/modes/rpc/rpc-mode.ts:254. A client that never answers an editor request leaves the extension waiting for the rest of the process. CA/docs/rpc-extension-ui.md says the agent side auto-resolves dialogs on timeout, which holds for the other three only. Always answer editor, if only with { cancelled: true }.

editor 是唯一不走 createDialogPromise 的对话框。它不接受 timeout，也忽略 abort signal CA/src/modes/rpc/rpc-mode.ts:254。一个从不回应 editor 请求的客户端，会让扩展一直等待到进程结束。CA/docs/rpc-extension-ui.md 说 agent 一侧会在超时时自动 resolve 对话框，这只对另外三个成立。editor 一定要回复，哪怕只回 { cancelled: true }。

## Shutdown and Rpc Client

## 关闭与 RpcClient

Closing stdin is the orderly shutdown: Pi disposes the runtime, which emits session_shutdown, and exits 0 CA/src/modes/rpc/rpc-mode.ts:802. An extension that calls ctx.shutdown() sets a flag; Pi exits after the current command or after the next agent_settled CA/src/modes/rpc/rpc-mode.ts:745. Signals are covered in run modes (p. 127).

关闭 stdin 就是有序关闭：Pi dispose 运行时，这会发出 session_shutdown，然后以 0 退出 CA/src/modes/rpc/rpc-mode.ts:802。调用 ctx.shutdown() 的扩展会设置一个标志；Pi 在当前命令之后或下一次 agent_settled 之后退出 CA/src/modes/rpc/rpc-mode.ts:745。信号见运行模式 (p. 127)。

For TypeScript callers that still want a subprocess, the package exports RpcClient CA/src/modes/rpc/rpc-client.ts. It has one typed method per command (prompt, get State, fork, get Commands and so on) and three helpers built on agent_settled:

对于仍想要子进程的 TypeScript 调用方，这个包导出了 RpcClient CA/src/modes/rpc/rpc-client.ts。它为每个命令提供一个带类型的方法（prompt、getState、fork、getCommands 等等），以及三个建立在 agent_settled 之上的辅助方法：

<table><tr><td>成员</td><td>作用</td></tr><tr><td>new RpcClient({ cliPath?, cwd?, env?, provider?, model?, args? })</td><td>只收选项；什么都不运行</td></tr><tr><td>start()</td><td>spawn node--mode rpc ...，cliPath 默认 dist/cli.js；等待 100 ms，若子进程已经退出则抛异常</td></tr><tr><td>stop()</td><td>先 SIGTERM，1000 ms 后 SIGKILL</td></tr><tr><td>onEvent(listener)</td><td>每一条不是对待处理请求响应的记录</td></tr><tr><td>waitForIdle(timeout = 60000)</td><td>在下一次 agent_settled 时 resolve</td></tr><tr><td>collectEvents(timeout = 60000)</td><td>到下一次 agent_settled 为止的所有事件</td></tr><tr><td>promptAndWait(message, images?, timeout = 60000)</td><td>先订阅，再 prompt，再收集</td></tr></table>

Every helper times out after 60 seconds by default. A long run needs an explicit timeout. From CA/src/modes/rpc/rpc-client.ts (RpcClientOptions, start, stop, onEvent, waitForIdle, collect Events, promptAndWait).

每个辅助方法默认在 60 秒后超时。长时间运行需要显式指定 timeout。取自 CA/src/modes/rpc/rpc-client.ts（RpcClientOptions、start、stop、onEvent、waitForIdle、collectEvents、promptAndWait）。

R P C C L I E N T C A N N O T A N S W E R A D I A L O G

R P C C L I E N T 无 法 回 应 对 话 框

RpcClient delivers extension_ui_request records to onEvent listeners as if they were events CA/src/modes/rpc/rpcclient.ts:523. It has no public method that writes an extension_ui_response; send is private CA/src/modes/rpc/rpcclient.ts:556. An extension that calls ctx.ui.editor(), or a confirm with no timeout, blocks the run until the client is stopped. With RpcClient, load only extensions whose dialogs set a timeout, or use the SDK. Also, cli Path is resolved against the child’s cwd and spawned with node, so the default works only inside a built checkout of the package.

RpcClient 会把 extension_ui_request 记录当作事件一样投递给 onEvent 监听器 CA/src/modes/rpc/rpcclient.ts:523。它没有任何能写出 extension_ui_response 的公共方法；send 是私有的 CA/src/modes/rpc/rpcclient.ts:556。一个调用 ctx.ui.editor()、或者调用没有 timeout 的 confirm 的扩展，会把这次运行阻塞到客户端被停止为止。用 RpcClient 时，只加载那些对话框设了 timeout 的扩展，或者改用 SDK。另外，cliPath 是相对子进程的 cwd 解析并用 node spawn 的，所以默认值只在这个包的一个已构建的 checkout 里才有效。

## The SDK

## SDK

The SDK is what the CLI runs on. createAgentSession() with no arguments discovers resources from the working directory and \~/.pi/agent, picks the settings default model or the first available one, and stores the session in a JSONL file CA/src/core/sdk.ts:181.

SDK 就是 CLI 所依赖的底层。不带参数调用 createAgentSession() 会从工作目录和 \~/.pi/agent 发现资源，选取设置里的默认模型或第一个可用模型，并把会话存进一个 JSONL 文件 CA/src/core/sdk.ts:181。

```typescript the minimal SDK program CA/examples/sdk/01-minimal.ts TS

import { createAgentSession } from "@earendil-works/pi-coding-agent";

const { session } = await createAgentSession();

try {
    session.subscribe((event) => {
    if (event.type === "message_update" && event.assistantMessageEvent.type === "text_delta") {
    process.stdout.write(event.assistantMessageEvent.delta);
    }
    });

    await session.prompt("What files are in the current directory?");
    session.state.messages.for Each((msg) => {
    console.log(msg);
    });
    console.log();
} finally {
    session.dispose();
}
```

Complete file minus its header comment. In-process events are full AgentSessionEvents: message_update still carries the cumulative message, which JSON and RPC modes strip.

完整文件，只少了文件头注释。进程内事件是完整的 AgentSessionEvents：message_update 仍然携带累积的 message，而 JSON 和 RPC 模式会把它剥掉。

session.prompt() resolves after the accepted run finishes, retries included CA/docs/sdk.md §Prompting. CreateAgentSessionOptions has 14 fields, all optional CA/src/core/sdk.ts:42:

session.prompt() 在被接受的那次运行结束后 resolve，重试也算在内 CA/docs/sdk.md §Prompting。CreateAgentSessionOptions 有 14 个字段，全部可选 CA/src/core/sdk.ts:42：

```txt
OPTION DEFAULT WHEN OMITTED
cwd the session manager's cwd, else process (.cwd)

agent Dir getAgentDir(): ~/.pi/agent or PI_CODING_AGENT_DIR

model Runtime ModelRuntime.create() over auth.json and models.json

model restored from the session, else the settings default, else the first available model

thinking Level restored from the session, else per-model setting, else settings default, else "medium"

scoped Models none; the list Ctrl+P cycles through

noTools unset; "all" or "builtin"

tools the default Tools setting, else read, bash, edit, write

exclude Tools none; applied after tools, MCP tools included

custom Tools none

resource Loader a new DefaultResourceLoader, reloaded

session Manager SessionManager.create (.cwd, ...): a persistent file

settings Manager SettingsManager.create (.cwd, agent Dir)

sessionStartEvent the startup session_start payload
```

D O C ≠ C O D E

文 档 ≠ 代 码

Without a session Manager the SDK writes a session file; pass SessionManager.inMemory() to avoid it. The result is { session, extensions Result, modelFallbackMessage? } CA/src/core/sdk.ts:99. Defaults from CA/src/core/sdk.ts:181 and CA/src/core/defaults.ts.

不带 sessionManager 时，SDK 会写一个会话文件；传入 SessionManager.inMemory() 可以避免这一点。返回值是 { session, extensionsResult, modelFallbackMessage? } CA/src/core/sdk.ts:99。默认值取自 CA/src/core/sdk.ts:181 和 CA/src/core/defaults.ts。

The CLI does not call createAgentSession directly. It uses three lower-level calls, all exported:

CLI 并不直接调用 createAgentSession。它用的是三个更底层的调用，都已导出：

createAgentSessionServices(opts): builds the cwd-bound services { cwd, agent Dir, model Runtime, settings Manager, resource Loader, diagnostics }, reloads the resource loader and registers providers that extensions queued CA/src/core/agent-session-services.ts:135.

createAgentSessionServices(opts)：构建绑定到 cwd 的服务 { cwd, agentDir, modelRuntime, settingsManager, resourceLoader, diagnostics }，重载资源加载器，并注册扩展排队提交的供应商 CA/src/core/agent-session-services.ts:135。

createAgentSessionFromServices({ services, session Manager, … }): calls createAgentSession with those services CA/src/core/agent-session-services.ts:214.

createAgentSessionFromServices({ services, sessionManager, … })：用那些服务调用 createAgentSession CA/src/core/agent-session-services.ts:214。

createAgentSessionRuntime(factory, { cwd, agent Dir, session Manager }): runs the factory once and keeps it. The returned AgentSessionRuntime has new Session, switch Session, fork, importFromJsonl, setRebindSession and dispose; each replacement tears the old session down with session_shutdown and builds a new one through the same factory CA/src/core/agent-session-runtime.ts:420.

createAgentSessionRuntime(factory, { cwd, agentDir, sessionManager })：运行工厂一次并保留它。返回的 AgentSessionRuntime 上有 newSession、switchSession、fork、importFromJsonl、setRebindSession 和 dispose；每次替换都会用 session_shutdown 拆掉旧会话，并通过同一个工厂构建新的 CA/src/core/agent-session-runtime.ts:420。

Two steps are easy to miss. First, createAgentSession never emits session_start; the host must call session.bind Extensions({ … }), as every mode does CA/src/core/agent-session.ts:3244. The MCP extension connects its servers in that handler MCP (p. 144). Second, the built-in codemode, tool-search, mcp and lama.cpp extensions come from the CLI’s main() CA/src/main.ts:575, not from the SDK. An SDK host adds them with createCodemodeExtension(), createToolSearchExtension() and createMcpExtension() in DefaultResourceLoader’s extension Factories CA/examples/sdk/14-codemode-mcp.ts. Fourteen examples in CA/examples/sdk/, from 01-minimal.ts to 14-codemodemcp.ts, cover one feature each.

有两步很容易被忽略。第一，createAgentSession 从不发出 session_start；宿主必须调用 session.bindExtensions({ … })，每种模式都是这么做的 CA/src/core/agent-session.ts:3244。MCP 扩展正是在那个处理器里连接它的服务器 MCP (p. 144)。第二，内置的 codemode、tool-search、mcp 和 llama.cpp 扩展来自 CLI 的 main() CA/src/main.ts:575，而不是来自 SDK。SDK 宿主要用 DefaultResourceLoader 的 extensionFactories 里的 createCodemodeExtension()、createToolSearchExtension() 和 createMcpExtension() 加上它们 CA/examples/sdk/14-codemode-mcp.ts。CA/examples/sdk/ 里的十四个例子，从 01-minimal.ts 到 14-codemodemcp.ts，每个覆盖一个特性。

The JSDoc on createAgentSession shows createAgentSession({ continue Session: true }) CA/src/core/sdk.ts:163. CreateAgentSessionOptions has no continue Session field, and TypeScript rejects it. To continue the latest session, pass session Manager: SessionManager.continue Recent(cwd), which is what pi -c does CA/src/main.ts:433.

createAgentSession 上的 JSDoc 写着 createAgentSession({ continueSession: true }) CA/src/core/sdk.ts:163。CreateAgentSessionOptions 并没有 continueSession 字段，TypeScript 会拒绝它。要继续最近的会话，传入 sessionManager: SessionManager.continueRecent(cwd)，这正是 pi -c 做的事 CA/src/main.ts:433。

## Choosing an integration

## 选择集成方式

<table><tr><td>选择</td><td>何时</td><td>你放弃的东西</td></tr><tr><td>SDK</td><td>同一进程内的 Node 或 Bun TypeScript</td><td>进程隔离</td></tr><tr><td>RPC</td><td>别的语言、IDE、沙箱化的子进程</td><td>直接访问对象；那 24 个内置命令</td></tr><tr><td>RpcClient</td><td>想把 Pi 当子进程跑的 TypeScript</td><td>回应扩展对话框</td></tr><tr><td>JSON 模式</td><td>一次脚本化运行，带完整事件日志</td><td>启动之后的任何输入</td></tr><tr><td>print 模式</td><td>一次脚本化运行，只要最终文本</td><td>事件、工具输出</td></tr></table>

Every row runs the same AgentSession. Only the transport and the UI context difer. From CA/docs/rpc.md (interface table) and the sections above.

每一行跑的都是同一个 AgentSession。差别只在传输方式和 UI 上下文。取自 CA/docs/rpc.md（接口表）和上面各节。

W H A T T H I S M E A N S F O R Y O U

这 对 你 意 味 着 什 么

Read RPC stdout as bytes and split on LF only; never use readline.

把 RPC 的 stdout 当字节读，只按 LF 切分；绝不要用 readline。

Treat the prompt response as “accepted” and wait for agent_settled, unless disposition is handled.

把 prompt 响应视为「已接受」，然后等 agent_settled，除非 disposition 是 handled。

Correlate responses by id; command handling is asynchronous.

用 id 关联响应；命令处理是异步的。

Answer every editor request, and avoid RpcClient when extensions open dialogs.

每一个 editor 请求都要回应；扩展会弹对话框时避开 RpcClient。

In the SDK, pass SessionManager.inMemory() for throwaway sessions and call bind Extensions before the first prompt.

在 SDK 里，用完即弃的会话传 SessionManager.inMemory()，并在第一次 prompt 之前调用 bindExtensions。

Sources: CA/src/modes/rpc/jsonl.ts (serializeJsonLine, attachJsonlLineReader). CA/src/modes/rpc/rpc-mode.ts (runRpcMode, createDialogPromise, createExtensionUIContext, handle Command, handleInputLine, shutdown). CA/src/modes/rpc/rpc-types.ts (RpcCommand, RpcResponse, RpcSessionState, RpcExtensionUIRequest, RpcExtensionUIResponse). CA/src/modes/rpc/rpc-client.ts (RpcClient). CA/src/core/agent-session.ts (PromptDisposition, bind Extensions, bash_execution_update). CA/src/core/sdk.ts (CreateAgentSessionOptions, createAgentSession); CA/src/core/agent-session-services.ts; CA/src/core/agent-sessionruntime.ts; CA/src/core/defaults.ts; CA/src/extensions/index.ts. CA/examples/sdk/01-minimal.ts, 14-codemode-mcp.ts. CA/docs/rpc.md, rpc-commands.md, rpc-extension-ui.md, sdk.md. research/capture/rpc-and-sdk-exchange.mjs, rpc-and-sdkchild.mjs; research/out/rpc-exchange.txt

来源：CA/src/modes/rpc/jsonl.ts（serializeJsonLine、attachJsonlLineReader）。CA/src/modes/rpc/rpc-mode.ts（runRpcMode、createDialogPromise、createExtensionUIContext、handleCommand、handleInputLine、shutdown）。CA/src/modes/rpc/rpc-types.ts（RpcCommand、RpcResponse、RpcSessionState、RpcExtensionUIRequest、RpcExtensionUIResponse）。CA/src/modes/rpc/rpc-client.ts（RpcClient）。CA/src/core/agent-session.ts（PromptDisposition、bindExtensions、bash_execution_update）。CA/src/core/sdk.ts（CreateAgentSessionOptions、createAgentSession）；CA/src/core/agent-session-services.ts；CA/src/core/agent-sessionruntime.ts；CA/src/core/defaults.ts；CA/src/extensions/index.ts。CA/examples/sdk/01-minimal.ts、14-codemode-mcp.ts。CA/docs/rpc.md、rpc-commands.md、rpc-extension-ui.md、sdk.md。research/capture/rpc-and-sdk-exchange.mjs、rpc-and-sdkchild.mjs；research/out/rpc-exchange.txt

![](images/9aca82bb7907f3ebe246df5a4be1c36ff03d8b6065ae9130972a3e22e4bb7a5f.jpg)
