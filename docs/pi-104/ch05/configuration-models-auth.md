---
title: 配置、模型与身份验证
---

<div class="section-kicker">5.1 / CONFIGURATION & EXTENSIONS</div>

# 配置、模型与身份验证

---

Pi 从两个目录读取配置，一个属于用户，一个属于项目。项目目录只有在该文件夹受信任后才会生效，而且有四项设置绝不会从项目目录读取。



在发送第一个请求之前，Pi 必须确定四件事：文件放在哪里、哪些设置生效、调用哪个模型，以及发送哪个凭据。每个问题的答案都按固定顺序来自磁盘上的文件。本节说明智能体目录的布局，展示用户设置与项目设置如何合并，逐字段解读 `models.json` 模式，并给出 API 密钥与初始模型的解析顺序。

## 两个目录



智能体目录是 Pi 为每位用户存储所有内容的根目录。如果设置了 `$PI_CODING_AGENT_DIR`，`getAgentDir()` 就返回它，否则返回 `~/.pi/agent`，见 `CA/src/config.ts:605`。这两个名称都不是硬编码的。`CONFIG_DIR_NAME` 来自 `package.json` 中的 `piConfig.configDir`，默认值为 `.pi`；`APP_NAME` 来自 `piConfig.name`，默认值为 `pi`，见 `CA/src/config.ts:579`。环境变量名称由应用名称构造，因此名为 `tau` 的改名分支读取的是 `TAU_CODING_AGENT_DIR`，见 `CA/src/config.ts:585`。



<BookFigure id="5.1" />

```bash
~/.pi/agent/ 用户作用域 · 始终加载
    | settings.json 严格 JSON，使用文件锁
    | keybindings.json
    | models.json 自定义提供商与模型 · 允许注释
    | models-store.json 动态目录缓存
    | auth.json 凭据 · 创建时权限为 0600，目录权限为 0700
    | mcp.json · mcp-auth.json · mcp.log 日志超过 5 MB 时轮转为 mcp.log.1
    | trust.json 项目信任决定
    | AGENTS.md | CLAUDE.md 全局上下文文件
    | SYSTEM.md · APPEND_SYSTEM.md 替换或追加系统提示词
    | extensions/skills/prompts/themes/ 自动发现
    | sessions/--<cwd>--/*.json 每个工作目录各有一个目录
    | npm/node_modules/ · git/<host>/<path> 用户作用域包
    | tmp/extensions/ 一次性 -e 安装 · 0700
    | bin/ 托管的 fd 和 rg
    | crashes.json · pi-debug.log

~/.agents/skills/ Agent Skills 标准 · 用户作用域

<project>/.pi/ 仅在项目受信任时加载
    | settings.json · mcp.json · SYSTEM.md · APPEND_SYSTEM.md
    | extensions/skills/prompts/themes/
    | npm/ · git/ 项目作用域包

<project>/.agents/skills/ 从 cwd 向上直到 git 根目录 · 仅限受信任项目

<every ancestor>/AGENTS.md | CLAUDE.md 无须信任
```

> 一个目录始终加载，另一个等待信任。路径对应于固定提交。会话目录名称由工作目录转换而来：删除开头的斜杠，将每个 `/`、`\` 和 `:` 替换为 `-`，再在两端加上 `--`，见 `CA/src/core/session-manager.ts:592`。来源：`config.ts`、`auth-storage.ts:25`、`extensions/mcp/log.ts:10`、`package-manager.ts:232` 和 `trust-manager.ts:30`。
> 
> 



<strong>玫红色条目是 `hasTrustRequiringProjectResources()` 检查的对象</strong>：`<cwd>/.pi` 下的 `settings.json`、`mcp.json`、`extensions`、`skills`、`prompts`、`themes`、`SYSTEM.md` 或 `APPEND_SYSTEM.md` 中的任意一项，或者工作目录及其任意祖先目录中的 `.agents/skills` 目录，见 `CA/src/core/trust-manager.ts:186`。如果这些资源都不存在，项目就直接视为受信任，不会弹出提示。如果存在这些资源，具体如何决定是否信任，见“上下文文件、技能、模板、主题与包”（原书第106页）。



`auth.json` 创建时的权限为 `0600`，其所在目录创建时的权限为 `0700`。这些权限只在创建时设置，因此管理员之后设置的权限不会被更改，见 `CA/src/core/auth-storage.ts:24`。每次读写 `auth.json`、`settings.json` 和 `trust.json` 都会获取 `proper-lockfile` 锁，最多重试 10 次，间隔 20 ms，见 `CA/src/core/auth-storage.ts:69`。

## 设置：两个文件，一次合并



`SettingsManager` 读取 `~/.pi/agent/settings.json` 和 `<cwd>/.pi/settings.json`，然后用 `deepMergeSettings(global, project)` 合并，见 `CA/src/core/settings-manager.ts:250`。不受信任的项目提供的是 `{}`，见 `CA/src/core/settings-manager.ts:474`。两个文件都必须是严格 JSON：去掉 BOM 后直接执行 `JSON.parse`，不会移除注释，见 `CA/src/core/settings-manager.ts:487`。



<BookFigure id="5.2" />

> 除四项设置外，所有冲突都由项目设置胜出。此图为示意图。合并规则来自 `deepMergeObjects` 和 `mergeDefaultTools`，见 `CA/src/core/settings-manager.ts:195`；只读取全局值的位置见 `settings-manager.ts:1023`、`:1100`、`:1176` 和 `main.ts:594`。
> 
> 



合并只会递归处理普通对象。项目中的数组和标量会直接替换全局值。唯一的例外是 `defaultTools`：如果项目列表完全由 `+name` 和 `-name` 条目组成，就会追加到全局列表，因此它修改的是继承的选择，而不是将其替换，见 `CA/src/core/settings-manager.ts:225`。基础选择为 `read`、`bash`、`edit`、`write`，见 `CA/src/core/settings-manager.ts:215`。



有四个键只从全局文件读取：

|<strong>键</strong>|<strong>默认值</strong>|<strong>仅限全局的原因</strong>|<strong>参见</strong>|
|---|---|---|---|
|`defaultProjectTrust`|`"ask"`|项目不得决定自己的信任状态|`settings-manager.ts:1100`|
|`cacheWarming`|`"streaming"`|“每次刷新都会花钱”|`settings-manager.ts:1023`|
|`httpProxy`|未设置|应用为 `HTTP_PROXY` 和 `HTTPS_PROXY`|`main.ts:594`|
|`deviceId`|首次使用时创建（登录对话框）|此次安装的固定 UUID|`settings-manager.ts:1176`|



项目文件可以设置这些键，但 Pi 会忽略它们。关于 `cacheWarming` 的注释引自 `settings-manager.ts:182`。



资源数组 `packages`、`extensions`、`skills`、`prompts` 和 `themes` 确实会参与合并，但没有任何代码读取合并后的值。包管理器分别读取全局文件和项目文件，并加载两者，见 `CA/src/core/package-manager.ts:920`；“上下文文件、技能、模板、主题与包”（原书第106页）给出了顺序。加载时，旧键会在内存中迁移：`queueMode` 变为 `steeringMode`，布尔值 `websockets` 变为 `transport: "websocket"` 或 `"sse"`，对象形式的 `skills` 变为数组，`retry.maxDelayMs` 变为 `retry.provider.maxRetryDelayMs`，见 `CA/src/core/settings-manager.ts:504`。“设置参考”（原书第202页）列出了所有键。

## models\.json



`~/.pi/agent/models.json` 用于添加提供商和模型，或者修补内置提供商和模型。与 `settings.json` 不同，它可以包含注释：`ModelConfig.load()` 在 `JSON.parse` 之前运行 `stripJsonComments`，然后根据 TypeBox 模式验证结果，见 `CA/src/core/model-config.ts:310`。解析错误或模式错误不会让 Pi 停止运行。配置会以空内容加载，同时显示错误，例如在 TUI 中显示 `models.json error: …`。每次刷新目录都会重新读取该文件，见 `CA/src/core/model-runtime.ts:840`；打开 `/model` 选择器时也会在后台启动一次刷新。



```ts
const ProviderConfigSchema = Type.Object({
    name: Type.Optional(Type.String({ minLength: 1 })),
    baseUrl: Type.Optional(Type.String({ minLength: 1 })),
    apiKey: Type.Optional(Type.String({ minLength: 1 })),
    api: Type.Optional(Type.String({ minLength: 1 })),
    oauth: Type.Optional(Type.Literal("radius")),
    headers: Type.Optional(Type.Record(Type.String(), Type.String())),
    compat: Type.Optional(ProviderCompatSchema),
    authHeader: Type.Optional(Type.Boolean()),
    models: Type.Optional(Type.Array(ModelDefinitionSchema)),
    modelOverrides: Type.Optional(Type.Record(Type.String(), ModelOverrideSchema)),
});

const ModelsConfigSchema = Type.Object({
    providers: Type.Record(Type.String(), ProviderConfigSchema),
});
```

> 第 242–257 行，未删节。`ProviderCompatSchema` 是 OpenAI Completions、OpenAI Responses 和 Anthropic Messages 兼容性对象的联合类型。
> 
> 



- `baseUrl`、`api`：端点与传输 API。自定义模型必须同时具备这两项，可在模型层或提供商层指定，也可从同一提供商的内置模型继承。否则加载会失败，并报出 `no "api" specified` 或 `"baseUrl" is required when defining custom models`，见 `CA/src/core/provider-composer.ts:216`。

- `apiKey`、`headers`：使用下文介绍的值语法。

- `authHeader`：为 `true` 时，使用解析出的密钥添加 `Authorization: Bearer <key>`。如果没有密钥，会报错 `authHeader requires a resolved API key`，见 `CA/src/core/provider-composer.ts:382`。

- `oauth: "radius"`：模式接受的唯一 OAuth 值。它要求设置 `baseUrl`，见 `CA/src/core/provider-composer.ts:306`。

- `models`：完整定义。如果某个定义的 `id` 与该提供商的内置聊天模型相同，就在原位置替换它；否则追加到列表中，见 `CA/src/core/provider-composer.ts:331`。

- `modelOverrides`：以模型 `id` 为键的局部补丁。除 `id`、`api` 和 `baseUrl` 外，它们接受定义中的所有字段。



如果某个提供商条目没有设置 `baseUrl`、`headers`、`compat`、`modelOverrides`、`models`、`apiKey`、`oauth` 和 `authHeader` 中的任何一项，就会被拒绝，见 `CA/src/core/provider-composer.ts:310`。新模型省略字段时采用以下默认值，见 `CA/src/core/provider-composer.ts:236`：



|<strong>字段</strong>|<strong>默认值</strong>|
|---|---|
|`name`|`id` 的值|
|`reasoning`|`false`|
|`input`|`["text"]`|
|`cost`|`{ input: 0, output: 0, cacheRead: 0, cacheWrite: 0 }`|
|`contextWindow`|`128000`|
|`maxTokens`|`16384`|



在 Pi 的记账中，没有标价的本地模型不产生费用。来源：`modelFromJson()`。如果设置了 `contextWindow` 和 `maxTokens`，它们必须为正数。



使用 OpenAI Chat Completions API 的本地 `lama.cpp` 或 vLLM 服务器需要一个提供商条目。下面示例的每个字段都在固定提交的模式中，包括 `qwen-chat-template` 思考格式，见 `CA/src/core/model-config.ts:105`：



本地 OpenAI 兼容端点，`~/.pi/agent/models.json`（JSON）



```json
{
    "providers": {
    "local": {
    "baseUrl": "http://127.0.0.1:8080/v1",
    "api": "openai-completions",
    "apiKey": "none",
    "compat": { "supportsDeveloperRole": false, "thinkingFormat": "qwen-chat-template" },
    "models": [{ "id": "qwen3-coder", "reasoning": true, "contextWindow": 262144 }]
    }
    }
}
```



此示例配置已对照 `ModelsConfigSchema` 检查。占位用的 `apiKey` 使模型可用；“身份验证、费用、重试与目录”（原书第41页）解释了为什么凭据无法解析的模型不会出现在 `/model` 中。

### 值语法



`apiKey` 和每个请求头的值都经过同一个解析器，见 `CA/src/core/resolve-config-value.ts:145`。以 `!` 开头的值是 shell 命令；去除首尾空白后的标准输出就是最终值，该命令有 10 秒超时限制，见 `CA/src/core/resolve-config-value.ts:189`。其他值都是模板：`$NAME` 和 `${NAME}` 插入环境变量，`$$` 表示字面量 `$`，`$!` 表示字面量 `!`。只要引用的任意变量未设置，整个值就无法解析；解析密钥时会报错 `Failed to resolve API key for provider "<id>" from environment variable: NAME`，见 `CA/src/core/resolve-config-value.ts:243`。



`resolveConfigValue()` 的注释说，命令输出会在进程的整个生命周期内缓存。但密钥和请求头的处理路径并不使用它：`composeApiKeyAuth()` 调用 `resolveConfigValueOrThrow()`，后者运行的是不带缓存的变体，见 `CA/src/core/provider-composer.ts:467`。`models.json` 中的 `!` 命令会在每次解析凭据时运行，因此要让它尽快完成。`CA/docs/models.md` 对这种不缓存的行为描述正确。

## API 密钥解析



如果同一提供商有多个凭据来源，组合后的 `ApiKeyAuth.resolve()` 会选择第一个适用的来源，见 `CA/src/core/provider-composer.ts:457`：



<BookFigure id="5.3" />

> 存储的登录凭据优先于配置的密钥。第一个匹配项胜出。步骤 1 是 `RuntimeCredentials.read()` 在存储内容之前返回的凭据，见 `CA/src/core/runtime-credentials.ts:24`，因此它进入的分支与步骤 2 相同。步骤 2–4 是 `resolve()` 的三个分支。`CA/docs/models.md` 也给出了相同的顺序。
> 
> 



只有确定模型之后才会设置 `--api-key`。如果没有指定模型，启动时会报出 `--api-key requires a model to be specified via --model, --provider/--model, or --models`，见 `CA/src/main.ts:832`。在步骤 3 中，扩展的 `apiKey` 优先于 `models.json` 中同一提供商的值，见 `CA/src/core/provider-composer.ts:392`；`authHeader` 以及名称相同的请求头也遵循这一规则。



步骤 2 的优先级高于步骤 3。`/login` 为某个提供商存储密钥后，修改 `models.json` 中的 `apiKey` 不会产生任何变化，直到 `/logout` 删除存储的凭据。`/logout` 只处理 `/login` 保存的内容，不会改变环境变量和 `models.json`。

## 选择模型



模型引用的格式为 `provider/id` 或单独的 `id`，可以带可选的 `:level` 思考级别后缀。`parseModelPattern()` 首先尝试将整个字符串作为模型解析。只有失败后，它才会在最后一个 `:` 处分割，并在后缀对应某个思考级别时将其视为思考级别，见 `CA/src/core/model-resolver.ts:204`。因此，诸如 `…:exacto` 的 OpenRouter ID 会按 ID 解析。精确匹配不区分大小写。部分匹配优先选择别名，即没有 `-YYYYMMDD` 后缀或以 `-latest` 结尾的 ID，而不是带日期的 ID，见 `CA/src/core/model-resolver.ts:74`。`--models` 和 `enabledModels` 中的 glob 模式匹配也不区分大小写，见 `CA/src/core/model-resolver.ts:318`。



会话启动时使用的模型，由分布在三个函数中的优先级链决定：

<BookFigure id="5.4" />

> 恢复的会话会保留原来的模型，除非命令行将其覆盖。第一个匹配项胜出。步骤 1–2 在 `buildSessionOptions()` 中执行，步骤 3 在 `createAgentSession()` 中执行，步骤 4–5 在 `findInitialModel()` 中执行。
> 
> 



> <strong>文档 ≠ 代码</strong>
> 
> `findInitialModel()` 上方的注释列出了五个步骤，第三步是“从会话恢复（如果继续或恢复会话）”，见 `CA/src/core/model-resolver.ts:618`。但该函数没有会话恢复这一步。会话恢复发生在调用它之前，位于 `createAgentSession()` 中，见 `CA/src/core/sdk.ts:213`；而函数自身的行内注释将“设置中的默认值”编号为步骤 3。
> 
> 

### 虚拟模型



虚拟模型是一个目录条目，它会为每个请求选择一个实际模型。扩展通过 `pi.registerVirtualModel({ provider, id, name, route })` 注册虚拟模型，见 `CA/src/core/extensions/types.ts:1872`。每次请求之前，Pi 都会调用 `route(request, ctx)`，将 `request.reason` 设置为 `user`、`continuation`、`retry` 或 `direct`；路由器返回实际模型、思考级别以及可选状态，见 `CA/src/core/virtual-models.ts:50`。模型选择、`ctx.model` 和 `model_change` 条目使用虚拟模型的名称；助手消息记录的是实际模型。路由器状态以自定义条目的形式保存在会话分支上，其 `customType: "pi.virtual-model-state"`，见 `CA/src/core/virtual-models.ts:8`。`CA/docs/virtual-models.md` 记录了完整约定。



> <strong>这对你意味着什么：</strong>
> 
> - 使用 `/login` 将凭据放入 `auth.json`，或者在 `models.json` 中使用 `$VAR` 引用；绝不要把明文密钥提交到项目中。
> 
> - 不要在 `settings.json` 中写注释。只有 `models.json` 会移除注释。
> 
> - 在全局文件中设置 `defaultProjectTrust`、`cacheWarming` 和 `httpProxy`；项目文件无法更改它们。
> 
> - 为脚本使用 `--model provider/id:level` 固定模型；否则，恢复的会话会保留上次使用的模型。
> 
> 



> 来源：`CA/src/config.ts`（`getAgentDir`、`CONFIG_DIR_NAME`、`ENV_AGENT_DIR`）；`CA/src/core/trust-manager.ts`（`TRUST_REQUIRING_PROJECT_CONFIG_RESOURCES`、`hasTrustRequiringProjectResources`）；`CA/src/core/auth-storage.ts`（`FileAuthStorageBackend`）；`CA/src/core/session-manager.ts:592`；`CA/src/core/settings-manager.ts`（`deepMergeObjects`、`mergeDefaultTools`、`deepMergeSettings`、`migrateSettings`、仅限全局的 getter）；`CA/src/main.ts`（`buildSessionOptions`、`--api-key` 检查、`applyHttpProxySettings`）；`CA/src/core/model-config.ts`（`ModelConfig.load`、模式）；`CA/src/core/provider-composer.ts`（`modelFromJson`、`applyModelsJson`、`composeApiKeyAuth`、`withConfiguredAuth`）；`CA/src/core/resolve-config-value.ts`；`CA/src/core/runtime-credentials.ts`；`CA/src/core/model-resolver.ts`（`isAlias`、`parseModelPattern`、`resolveModelScopeFromModels`、`findInitialModel`）；`CA/src/core/sdk.ts`（`createAgentSession`）；`CA/src/core/virtual-models.ts`；`CA/docs/models.md`；`CA/docs/virtual-models.md`。
> 
>
