Files on disk decide the model, the context and the tools; extensions can intercept nearly everything else.

![](images/8e4327e610837fdee54058a79abb5dad9c7ae9a7d806e261fda13349a4284251.jpg)

## 5.1 Configuration, models and auth

Pi reads its configuration from two directories, one per user and one per project. The project directory counts only after the folder is trusted, and four settings never come from it at all.

Before Pi sends a single request it has to settle four questions: where its files live, which settings apply, which model to call, and which credential to send. Each answer comes from files on disk, in a fixed order. This section maps the agent directory, shows how user and project settings merge, reads the models.json schema field by field, and gives the resolution order for API keys and for the initial model.

## Two directories

The agent directory is the root of everything Pi stores per user. getAgentDir() returns \$PI_CODING_AGENT_DIR when it is set and \~/.pi/agent otherwise CA/src/config.ts:605. Neither name is hard-coded. CONFIG_DIR_NAME comes from piConfig.config Dir in package.json and defaults to .pi; APP_NAME comes from piConfig.name and defaults to pi CA/src/config.ts:579. The environment variable is built from the app name, so a rebranded fork named tau reads TAU_CODING_AGENT_DIR CA/src/config.ts:585.

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

The rose entries are the ones hasTrustRequiringProjectResources() checks: any of settings.json, mcp.json, extensions, skills, prompts, themes, SYSTEM.md or APPEND_SYSTEM.md under <cwd>/.pi, or an .agents/skills directory in the working directory or any ancestor CA/src/core/trust-manager.ts:186. When none exists, the project counts as trusted without a prompt. How the decision is made when one does exist is in context files, skills, templates, themes and packages (p. 106).

auth.json is created with mode 0600 inside a directory created with 0700. The mode applies only on creation, so permissions an administrator set later are left alone CA/src/core/auth-storage.ts:24. Every read and write of auth.json, settings.json and trust.json takes a proper-lockfile lock, retried up to 10 times at 20 ms intervals CA/src/core/auth-storage.ts:69.

#### Settings: two files, one merge

SettingsManager reads \~/.pi/agent/settings.json and <cwd>/.pi/settings.json and merges them with deepMergeSettings(global, project) CA/src/core/settings-manager.ts:250. An untrusted project contributes {} CA/src/core/settings-manager.ts:474. Both files are strict JSON: JSON.parse after a BOM strip, with no comment stripping CA/src/core/settings-manager.ts:487.

![](images/f8685fd91162dafd9c34c78554898f055bd412ced2ec20be6500b6f072c960a8.jpg)
The project wins every collision except four. Schematic. Merge rules from deepMergeObjects and mergeDefaultTools CA/src/core/settingsmanager.ts:195; global-only reads at settings-manager.ts:1023, :1100, :1176 and main.ts:594.

The merge recurses only into plain objects. Arrays and scalars from the project replace the global value outright. default Tools is the one exception: a project list made only of +name and -name entries is appended to the global list, so it edits the inherited selection instead of replacing it CA/src/core/settings-manager.ts:225. The base selection is read, bash, edit, write CA/src/core/settings-manager.ts:215.

Four keys are read from the global file only:

<table><tr><td>KEY</td><td>DEFAULT</td><td>WHY GLOBAL</td><td>SEE</td></tr><tr><td>defaultProjectTrust</td><td>&quot;ask&quot;</td><td>a project must not decide its own trust</td><td>settings-manager.ts:1100</td></tr><tr><td>cache Warming</td><td>&quot;streaming&quot;</td><td>&quot;each refresh costs money&quot;</td><td>settings-manager.ts:1023</td></tr><tr><td>http Proxy</td><td>unset</td><td>applied as HTTP_PROXY and HTTPS_PROXY</td><td>main.ts:594</td></tr><tr><td>deviceId</td><td>created on first use (the login dialog)</td><td>stable UUID of the installation</td><td>settings-manager.ts:1176</td></tr></table>

A project file can set these keys; Pi ignores them. The comment on cache Warming is quoted from settings-manager.ts:182.

The resource arrays packages, extensions, skills, prompts and themes do pass through the merge, but nothing reads the merged value. The package manager reads the global and project files separately and loads both CA/src/core/packagemanager.ts:920; context files, skills, templates, themes and packages (p. 106) gives the order. On load, old keys are migrated in memory: queue Mode becomes steering Mode, the boolean websockets becomes transport: "websocket" or "sse", an object-form skills becomes an array, and retry.maxDelayMs becomes retry.provider.maxRetryDelayMs CA/src/core/settings-manager.ts:504. settings reference (p. 202) lists every key.

## models.json

\~/.pi/agent/models.json adds providers and models or patches built-in ones. Unlike settings.json it may contain comments: ModelConfig.load() runs stripJsonComments before JSON.parse, then validates the result against a TypeBox schema CA/src/core/model-config.ts:310. A parse or schema error does not stop Pi. The config loads empty and the error is shown, for example as models.json error: … in the TUI. The file is read again on every catalogue refresh CA/src/core/modelruntime.ts:840, and opening the /model selector starts one in the background.

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

base Url, api: the endpoint and wire API. A custom model needs both, at model or provider level, or inherited from a built-in model of the same provider. Otherwise loading fails with no "api" specified or "base Url" is required when defining custom models CA/src/core/provider-composer.ts:216.

api Key, headers: values in the syntax described below.

auth Header: when true, adds Authorization: Bearer <key> with the resolved key. With no key it fails with auth Header requires a resolved API key CA/src/core/provider-composer.ts:382.

oauth: "radius": the only OAuth value the schema accepts. It requires base Url CA/src/core/provider-composer.ts:306.

models: full definitions. A definition whose id matches a built-in chat model of that provider replaces it in place; otherwise it is appended CA/src/core/provider-composer.ts:331.

model Overrides: partial patches keyed by model id. They accept every definition field except id, api and base Url.

A provider entry that sets none of base Url, headers, compat, model Overrides, models, api Key, oauth or auth Header is rejected CA/src/core/provider-composer.ts:310. A new model takes these defaults when fields are omitted CA/src/core/provider-composer.ts:236:

<table><tr><td>FIELD</td><td>DEFAULT</td></tr><tr><td>name</td><td>the id</td></tr><tr><td>reasoning</td><td>false</td></tr><tr><td>input</td><td>[&quot;text&quot;]</td></tr><tr><td>cost</td><td>{ input: 0, output: 0, cache Read: 0, cache Write: 0 }</td></tr><tr><td>context Window</td><td>128000</td></tr><tr><td>max Tokens</td><td>16384</td></tr></table>

An unpriced local model costs nothing in Pi’s accounting. From modelFromJson(). context Window and max Tokens must be positive when set.

A local lama.cpp or vLLM server that speaks the OpenAI Chat Completions API needs one provider entry. Every field in this example is in the schema at the pinned commit, including the qwen-chat-template thinking format CA/src/core/modelconfig.ts:105:

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

## Value syntax

api Key and every header value go through the same resolver CA/src/core/resolve-config-value.ts:145. A value that starts with ! is a shell command; its trimmed stdout is the value, and the command has a 10-second timeout CA/src/core/resolve-configvalue.ts:189. Any other value is a template: \$NAME and \${NAME} interpolate environment variables, \$\$ is a literal \$ and \$! a literal !. If any referenced variable is unset, the whole value is unresolved, and resolving a key then fails with Failed to resolve API key for provider "<id>" from environment variable: NAME CA/src/core/resolve-configvalue.ts:243.

The comment on resolveConfigValue() says command output is cached for the life of the process. The key and header path does not use it: composeApiKeyAuth() calls resolveConfigValueOrThrow(), which runs the uncached variant CA/src/core/providercomposer.ts:467. A ! command in models.json runs at every credential resolution, so keep it fast. CA/docs/models.md states the uncached behaviour correctly.

## API key resolution

When several credential sources exist for one provider, the composed ApiKeyAuth.resolve() picks the first that applies CA/src/core/provider-composer.ts:457:

![](images/26c84150e6e56521d972a6914caea90ae97ccf7e7ab82104675704b325afc190.jpg)
A stored login beats a configured key. First match wins. Step 1 is a credential that RuntimeCredentials.read() returns ahead of the store CA/src/core/runtime-credentials.ts:24, so it lands in the same branch as step 2. Steps 2–4 are the three branches of resolve(). The same order is stated in CA/docs/models.md.

--api-key is set only after the model is known. Without one, startup reports --api-key requires a model to be specified via --model, --provider/--model, or --models CA/src/main.ts:832. In step 3 an extension’s api Key takes precedence over the models.json value for the same provider CA/src/core/provider-composer.ts:392; the same holds for auth Header and for headers with the same name.

Step 2 outranks step 3. After /login stores a key for a provider, editing api Key in models.json changes nothing until /logout removes the stored credential. /logout touches only what /login saved; environment variables and models.json are left as they are.

## Choosing the model

A model reference is provider/id or a bare id, with an optional :level thinking sufix. parseModelPattern() first tries the whole string as a model. Only when that fails does it split on the last : and treat the sufix as a thinking level, if it names one CA/src/core/model-resolver.ts:204. OpenRouter ids such as …:exacto therefore resolve as ids. An exact match is caseinsensitive. A partial match prefers aliases, ids without a -YYYYMMDD sufix or ending in -latest, over dated ids CA/src/core/model-resolver.ts:74. Glob patterns in --models and enabled Models match case-insensitively CA/src/core/model-resolver.ts:318.

The model a session starts with comes from a ladder spread over three functions:

![](images/668ee44e1063cab203f823853ed06d1f53de54319a2f829e05a84aa9a14a4ace.jpg)

A resumed session keeps its model unless the command line overrides it. First match wins. Steps 1–2 run in buildSessionOptions(), step 3 in createAgentSession(), steps 4–5 in findInitialModel().

## D O C ≠ C O D E

The comment above findInitialModel() lists five steps, the third being “Restored from session (if continuing/resuming)” CA/src/core/model-resolver.ts:618. The function has no session step. Session restore happens before it is called, in createAgentSession() CA/src/core/sdk.ts:213, and the function’s own inline comments number the settings default as step 3.

## Virtual models

A virtual model is a catalogue entry that picks a physical model per request. An extension registers one with pi.registerVirtualModel({ provider, id, name, route }) CA/src/core/extensions/types.ts:1872. Pi calls route(request, ctx) before each request with request.reason set to user, continuation, retry or direct; the router returns a physical model, a thinking level and optional state CA/src/core/virtual-models.ts:50. The selection, ctx.model and model_change entries name the virtual model; assistant messages record the physical one. Router state is stored on the session branch as a custom entry with custom Type: "pi.virtual-model-state" CA/src/core/virtual-models.ts:8. CA/docs/virtual-models.md documents the full contract.

## W H A T T H I S M E A N S F O R Y O U
Put credentials in auth.json with /login, or in models.json as \$VAR references; never commit literal keys to a project.

Keep settings.json free of comments. Only models.json strips them.

Set defaultProjectTrust, cache Warming and http Proxy in the global file; a project file cannot change them.

Pin a model for scripts with --model provider/id:level; a resumed session otherwise keeps its last model.

Sources: CA/src/config.ts (getAgentDir, CONFIG_DIR_NAME, ENV_AGENT_DIR); CA/src/core/trust-manager.ts (TRUST_REQUIRING_PROJECT_CONFIG_RESOURCES, hasTrustRequiringProjectResources); CA/src/core/auth-storage.ts (FileAuthStorageBackend); CA/src/core/session-manager.ts:592; CA/src/core/settings-manager.ts (deepMergeObjects, mergeDefaultTools, deepMergeSettings, migrate Settings, global-only getters) CA/src/main.ts (buildSessionOptions, -apikey check, applyHttpProxySettings); CA/src/core/model-config.ts (ModelConfig.load, schemas); CA/src/core/providercomposer.ts (modelFromJson, applyModelsJson, composeApiKeyAuth, withConfiguredAuth); CA/src/core/resolve-config-value.ts; CA/src/core/runtime-credentials.ts; CA/src/core/model-resolver.ts (isAlias, parseModelPattern, resolveModelScopeFromModels, findInitialModel); CA/src/core/sdk.ts (createAgentSession); CA/src/core/virtual-models.ts; CA/docs/models.md; CA/docs/virtual-models.md

# 5.2 Context files, skills, templates, themes, packages

Every resource Pi loads goes through one function,

\`DefaultResourceLoader.reload()\`. It settles trust, collects paths from five

kinds ofsource, and lets thefirst copy ofa name win, so the order it collects in decides everything.

A project can ship its own skills, prompt templates, themes and extensions, and so can the user, a package or the command line. When two of them use the same name, one is silently dropped. This section follows reload() from the trust decision to the last theme. It gives the precedence rank that settles collisions, with a capture that puts one skill name in seven places. It then covers each resource kind and the package manager that ships them.

## Context files

Context files are the AGENTS.md and CLAUDE.md files whose text enters the system prompt as project context (system prompt construction (p. 75)). In each directory Pi takes the first file that exists among AGENTS.override.md, AGENTS.md, AGENTS.MD, CLAUDE.md and CLAUDE.MD CA/src/core/resource-loader.ts:185. Only one file per directory is read.

loadProjectContextFiles() reads the agent directory first, then walks from the working directory up to the filesystem root and emits the ancestors root-first, skipping any path already seen CA/src/core/resource-loader.ts:232. In a git linked worktree nested inside its main repository, the main repository’s copy of the same file is skipped, because both cover the same logical repository CA/src/core/resource-loader.ts:214. --no-context-files (-nc) turns loading of.

F O O T G U N

Context files need no trust. The walk in loadProjectContextFiles() has no trust check, so the AGENTS.md of a freshly cloned, untrusted repository and of every directory above it reaches the model. Trust gates .pi/ and .agents/skills, not context files. Use - nc when the text of a checkout should not reach the model.

## The loading pipeline

reload() runs at startup and on /reload CA/src/core/resource-loader.ts:509. Trust is settled first, because it decides whether the project half of the configuration exists at all.

A handler that returns “undecided” passes the question down the ladder. First match wins. Handler order is extension load order CA/src/core/extensions/runner.ts:295. Step 4 uses findNearestTrustEntry(), so trusting a parent folder covers every folder below it CA/src/core/trust-manager.ts:45.
![](images/028092b3a1a35ea25864656441d62b5f74c88ae9bc6ca06c507166f2b4c2d271.jpg)
Trust is decided before anything project-local is read. Steps in source order, resource-loader.ts:509–674. Extensions loaded in the pre-trust pass are reused in step 5, not imported twice CA/src/core/resource-loader.ts:747.

## The trust decision

The pre-trust pass forces the project to untrusted and loads only user-scope and command-line extensions; built-in extensions wait for the final pass because a loaded extension cannot be unloaded CA/src/core/resource-loader.ts:501. Those extensions can answer the project_trust event. resolveProjectTrusted() then walks a first-match ladder CA/src/core/projecttrust.ts:46:

![](images/4f9332bfe8d9119fe66ceca89518229afc7289d37ca294c95963e0c16bc31caa.jpg)

The prompt reads “Trust project folder? … This allows pi to load .pi settings and resources, install missing project packages, and execute project extensions.” CA/src/core/project-trust.ts:24. Choosing a “this session only” option writes nothing to trust.json.

## F O O T G U N
The two halves of .agents/skills handling disagree about how far up to look. hasTrustRequiringProjectResources() checks every ancestor up to the filesystem root CA/src/core/trust-manager.ts:196. Skill discovery stops at the git root CA/src/core/package-manager.ts:468. An .agents/skills directory above the repository root makes Pi ask for trust, and after you grant it, none of its skills load.

#### Collisions: the precedence rank

package Manager.resolve() collects resources into one map per kind, then sorts them by resourcePrecedenceRank() CA/src/core/package-manager.ts:192. Lower ranks sort first, and the first copy of a name wins.

<table><tr><td>RANK</td><td>SOURCE</td><td>EXAMPLE</td></tr><tr><td>0</td><td>project settings entry</td><td>skills: [&quot;/tools/skills&quot;] in .pi/settings.json</td></tr><tr><td>1</td><td>project, auto-discovered</td><td>.pi/skills/, then .agents/skills/ from cwd up to the git root</td></tr><tr><td>2</td><td>user settings entry</td><td>skills in ~/.pi/agent/settings.json</td></tr><tr><td>3</td><td>user, auto-discovered</td><td>~/.pi/agent/skills/, then ~/.agents/skills/</td></tr><tr><td>4</td><td>package resource</td><td>anything a package contributes, project packages before user packages</td></tr><tr><td>5</td><td>built-in</td><td>builtin:mcp, builtin:codemode, ... (extensions only)</td></tr></table>

A settings entry outranks the conventional directory of the same scope. From resourcePrecedenceRank() and the insertion order of addAutoDiscoveredResources() CA/src/core/package-manager.ts:2413. JavaScript’s sort is stable, so equal ranks keep insertion order.

The rank is not the whole order. reload() puts command-line paths around the ranked list, and puts them in diferent places for diferent kinds CA/src/core/resource-loader.ts:573. Extensions from -e go first. Skills, prompts and themes from packages named with -e also go first, but loose --skill, --prompt-template and --theme paths are appended last. The capture kit put a skill named dup, a template /dup and a tool dup_tool in every scope and asked the loader which won:

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
--skill and --prompt-template cannot override anything. They are appended after every discovered and configured path CA/src/core/resource-loader.ts:597, so a skill passed on the command line loses to any same-named skill on disk, with only a collision diagnostic. -e is the opposite: what it names loads first, including the skills and templates of a package. To test a replacement skill, rename it, or pass a directory with a skills/ folder to -e as a local package. The duplicate tool in the last block is a diferent matter: in the CLI it stops startup (extensions, loading and the API (p. 113)).

## Skills

A skill is a directory holding SKILL.md in the Agent Skills format, or a loose Markdown file with frontmatter (system prompt construction (p. 75) shows where skills land in the prompt). The loader reads three frontmatter fields CA/src/core/skills.ts:67:

name: optional; defaults to the name of the parent directory. Checked against the spec: at most 64 characters, ^[a-z0-9-]+\$, no leading, trailing or doubled hyphen CA/src/core/skills.ts:92. Violations are warnings; the skill still loads.

description: required. A SKILL.md without one is reported and skipped; a loose .md without one is skipped silently CA/src/core/skills.ts:304. Over 1,024 characters is a warning.

disable-model-invocation: true hides the skill from the system prompt; only /skill:name reaches it.

The spec’s other fields, such as license, compatibility and allowed-tools, are parsed and ignored. Discovery treats a directory that contains SKILL.md as a skill root and does not descend further. Elsewhere it recurses, skipping dot-entries and node_modules and honouring .gitignore, .ignore and .fdignore CA/src/core/package-manager.ts:371. Loose .md files count only at the top of \~/.pi/agent/skills and .pi/skills, and only below the top of an .agents/skills directory CA/src/core/package-manager.ts:428.

The system prompt lists each skill’s name, description and absolute path, never its body. The model reads the file when a task matches, so adding a skill changes the prompt by one entry, not by its instructions:

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

Typing /skill:name args replaces the input with <skill name="N" location="P">, a line References are relative to DIR., the body without frontmatter, and </skill>, followed by a blank line and the arguments CA/src/core/agentsession.ts:2146. An unknown name passes through unchanged.

## Prompt templates

A prompt template is a Markdown file that /name args expands into the prompt. The name is the file name without .md. The description is the frontmatter description, or else the first non-empty line, cut to 60 characters with ... appended when longer; argument-hint is optional CA/src/core/prompt-templates.ts:129.

The conventional directories \~/.pi/agent/prompts/ and .pi/prompts/ (trusted) are scanned without recursion, as is a directory passed to --prompt-template CA/src/core/prompt-templates.ts:159. A directory named in the prompts setting or in a package is collected recursively, like any other resource directory CA/src/core/package-manager.ts:651.

Arguments are split on whitespace, with ' and " grouping and no escape characters CA/src/core/prompt-templates.ts:25. Substitution runs once over the template; values that themselves contain \$1 are not expanded again CA/src/core/prompttemplates.ts:71.

<table><tr><td>SYNTAX</td><td>VALUE</td></tr><tr><td>$1, $2, ...</td><td>positional argument; missing → &quot;&quot;</td></tr><tr><td>$@, $ARGUMENTS</td><td>all arguments joined by spaces</td></tr><tr><td>${N: -default}</td><td>argument N, or the default if missing or empty</td></tr><tr><td>${@: -default}, ${ARGUMENTS: -default}</td><td>all arguments, or the default if there are none</td></tr><tr><td>${@: N}</td><td>arguments from N on</td></tr><tr><td>${@: N: L}</td><td>L arguments starting at N</td></tr></table>

Bash-style, one pass. From substitute Args().

AgentSession.prompt() applies four stages to text that starts with /: a registered extension command runs and consumes it; otherwise input handlers see the raw text; then /skill: expansion; then template expansion CA/src/core/agentsession.ts:1963. from prompt() to agent_settled (p. 67) follows the text from there.

## Themes

Three themes are built in: system, the default, generated from the terminal’s palette CA/src/modes/interactive/theme/themecontroller.ts:175, plus dark and light. Custom themes are JSON files from \~/.pi/agent/themes/, .pi/themes/ (trusted), the themes setting, packages or --theme. Only the active custom theme in \~/.pi/agent/themes/ is watched and hotreloaded CA/src/modes/interactive/theme/theme.ts:808.

A theme file has name, optional appearance ("dark" or "light", detected from the colours when omitted), optional vars, colors and an optional export block with pageBg, cardBg and infoBg for HTML export. colors has 51 required keys and 5 optional ones. A colour value is a hex string, oklch(), okhsl(), the name of a vars entry, "" for the terminal default, or an integer 0–255 for a palette index CA/src/modes/interactive/theme/theme-json.ts:13. The setting theme: "light-name/darkname" follows the terminal’s appearance, light theme first CA/src/modes/interactive/theme/theme.ts:652; a theme name with / in it is rejected CA/src/modes/interactive/theme/theme.ts:528.

## Pi packages

A package bundles extensions, skills, prompts and themes for installation from npm, git or a local path. Its manifest is the pi key in package.json, four optional string arrays whose entries can be globs CA/src/core/pi-manifest.ts:4:

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

<table><tr><td>SOURCE FORM</td><td>KIND</td><td>INSTALLED TO</td></tr><tr><td>npm:@scope/name[@version]</td><td>npm; an exact version is pinned</td><td>~/.pi/agent/npm/node_modules/,or.pi/npm/... with -l</td></tr><tr><td>git:github.com/user/repo[@ref], https://...,ssh://...</td><td>git</td><td>~/.pi/agent/git/: $\text{<path>:git clone,git checkout}$ , then npm install if a package.json exists</td></tr><tr><td>./path,/abs,~/...</td><td>local</td><td>used in place</td></tr></table>

Project packages install under .pi/ and only for a trusted project. From parse Source(), getManagedNpmInstallPath(), getGitInstallRoot() and install Git() CA/src/core/package-manager.ts:2126.

The commands are pi install <source> [-l], pi remove <source> [-l] (alias uninstall), pi update [--self|-- extensions|--models|--all] and pi list CA/src/package-manager-cli.ts:265. pi update with no target updates Pi itself.

CA/src/core/package-manager.ts:1721. When the same identity is configured in both scopes, the project entry wins. Configured packages that are missing are installed during reload() unless PI_OFFLINE is 1, true or yes CA/src/core/package-

manager.ts:54.

The host provides pi-ai, pi-agent-core, pi-coding-agent, pi-tui and typebox to every extension. A package that lists one of them under dependencies gets a warning: “Host-provided extension packages must be declared in peer Dependencies with a “*“ range, not dependencies” CA/src/core/resource-loader.ts:93. extensions, loading and the API (p. 113) shows how the loader maps these imports.

A settings entry can be an object instead of a string: { source, autoload?, extensions?, skills?, prompts?, themes? }. Each array filters what the package contributes. Plain entries and globs include, !glob excludes, +path forceincludes an exact path and -path force-excludes one, applied in that order CA/src/core/package-manager.ts:745.

W H A T T H I S M E A N S F O R Y O U

Name skills and templates uniquely across scopes; a collision drops one copy with only a diagnostic.

To override a resource for one run, load it through -e, not --skill.

Run untrusted checkouts with -nc if their AGENTS.md should not reach the model.

Declare host packages as "*" peer dependencies in any package you publish.

Sources: CA/src/core/resource-loader.ts (loadContextFileFromDir, findShadowedContextFile, loadProjectContextFiles, reload, loadFinalExtensionSet, dedupe Prompts, collectExtensionPackageWarnings); CA/src/core/project-trust.ts (resolveProjectTrusted); CA/src/core/trust-manager.ts; CA/src/core/extensions/runner.ts (emitProjectTrustEvent); CA/src/core/package-manager.ts (resourcePrecedenceRank, collectSkillEntries, collectAncestorAgentsSkillDirs, apply Patterns, resolve, addAutoDiscoveredResources, collectPackageResources, parse Source, getPackageIdentity); CA/src/core/skills.ts; CA/src/core/system-prompt.ts; CA/src/core/agent-session.ts (prompt, _expandSkillCommand); CA/src/core/prompt-templates.ts; CA/src/modes/interactive/theme/{theme.ts, theme-json.ts, theme-controller.ts}; CA/src/core/pi-manifest.ts; CA/src/package-manager-cli.ts; CA/docs/skills.md; research/capture/resources-precedence.mjs; research/out/resources-precedence.txt

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

An extension is onefunction that receives an \`ExtensionAPI\` with 32 methods and an event bus. What it registers during that call is held back until the call returns, so a factory that throws leaves nothing behind.

Extensions are Pi’s main way to add features. The built-in MCP client, codemode and tool search are extensions themselves. This section shows how Pi finds and imports extension files, in what order, what happens when two extensions claim the same name, and how /reload replaces them. It then lists every ExtensionAPI method and the ToolDefinition an extension passes to register Tool(). The events an extension subscribes to are in extension events and contexts (p. 120).

## A factory and nothing else

An extension is a TypeScript or JavaScript module whose default export has this type CA/src/core/extensions/types.ts:2006:

```txt the extension contract CA/src/core/extensions/types.ts
```

```typescript export type ExtensionFactory = (pi: ExtensionAPI) => void | Promise<void>;
```

```txt
Line 2006, uncut. Pi awaits an asynchronous factory before startup continues.
```

Copied from the quick start in CA/docs/extensions.md. Save it as \~/.pi/agent/extensions/hello.ts, or load it for one run with pi -e ./hello.ts; then type /hello.

The shipped docs state the lifecycle rule: “Do not start processes, sockets, watchers, or timers in the factory because some invocations load extensions without starting a session.” CA/docs/extensions.md. Start long-lived resources in a session_start handler and close them in an idempotent session_shutdown handler.

## Finding and importing

Extension paths come out of the resource pipeline in context files, skills, templates, themes and packages (p. 106). Within it, extensions have their own order: command-line -e paths first, then the ranked list, then inline factories CA/src/core/resourceloader.ts:573.

F I G . 5 . 7 E X T E N S I O N L O A D O R D E R

F L O W

1

-e source>

CLI · temporary scope · also builtin: →

2

project settings extensions entries in .pi/settings.json rank 0

→

3

.pi/extensions/ trusted projects only

→

4

user settings extensions entries in \~/.pi/agent/settings.json rank 2

→

5

\~/.pi/agent/extensions/ always rank 3

→

6

packages project packages, then user packages rank 4

→

7

built-ins builtin:lama.cpp · codemode · tool-search · mcp rank 5

→

8

inline factories SDK extension Factories · last

The command line loads first. Event handlers, tool renderers and first-registration lookups all follow this order. Verified by research/out/resourcesprecedence.txt (§extensions), where a -e extension loads ahead of two auto-discovered ones.

<table><tr><td>ASPECT</td><td>BEHAVIOUR</td><td>SOURCE</td></tr><tr><td>Directory scan</td><td>In an extensions/ directory: direct *.ts and *.js files, and each subdirectory&#x27;s package.json pi.extensions entries, else its index.ts, else its index.js. One level deep. A directory that itself has a manifest or index loads only that.</td><td>package-manager.ts:563</td></tr><tr><td>Import</td><td>jiti with module Cache: false, so each load re-evaluates the module. Imported factories are cached per working directory and cache generation; /reload bumps the generation.</td><td>loader.ts:576, loader.ts:138</td></tr><tr><td>Host imports</td><td>Compiled binaries, the bundled Node build and TypeScript source get virtual modules; an unbundled Node build gets path aliases. Both map the same 20 specifiers.</td><td>loader.ts:571, virtual-modules.ts:14</td></tr><tr><td>Built-ins</td><td>builtin:lama.cpp, and the replaceable builtin:codemode, builtin:tool-search and builtin:mcp. Disable one with &quot;-builtin:&quot; in the extensions setting; --no-extensions drops all of them, --no-mcp only MCP.</td><td>CA/src/extensions/index.ts:7</td></tr><tr><td>SDK</td><td>Only the CLI adds the built-ins. A session made with createAgentSession() loads none unless the caller passes them.</td><td>CA/src/main.ts:575</td></tr><tr><td>Errors</td><td>Import and factory errors are collected as Failed to load extension: ... and do not stop loading the rest. In the CLI, any such error ends startup with exit code 1.</td><td>loader.ts:655, main.ts:919</td></tr></table>

Twenty import specifiers resolve to the host’s own copies. Six are TypeBox: typebox, typebox/compile, typebox/value and the same three under @sinclair/typebox. Seven are Pi packages: pi-agent-core, pi-tui, pi-ai, pi-ai/compat, pi-ai/oauth, pi-ai/providers/all and pi-coding-agent under @earendil-works/. The other seven are the same Pi packages under the legacy @mariozechner/ scope. The bare pi-ai specifier maps to the compat entry point.

## Transactional registration

The API object an extension receives has three states: loading, active and failed CA/src/core/extensions/loader.ts:253. Registrations that change shared runtime state — register Provider, unregister Provider, registerMcpServer, unregisterMcpServer, registerVirtualModel, unregisterVirtualModel and flag defaults — are queued while the factory runs. commit() applies them only after the factory returns. If it throws, discard() drops the queue, unsubscribes event-bus listeners added during loading, and marks the API failed, so later calls throw Extension "<path>" failed to load and its API is no longer active. CA/src/core/extensions/loader.ts:532. After loading, the same calls take efect at once, so a command handler can register a provider without /reload.

Tools, commands, shortcuts, flags, renderers and handlers are written onto the extension object directly. They become visible only if the extension makes it into the loaded list, which a throwing factory does not.

## Two extensions, one name

The resource loader does not refuse a duplicate. When two extensions register the same tool or flag, both stay loaded and the loader adds Tool "x" conflicts with <path> to its list of extension errors CA/src/core/resource-loader.ts:1246; tool lookups take the first registration in load order CA/src/core/extensions/runner.ts:631. The CLI turns every entry of that list into an error diagnostic CA/src/main.ts:800, and an error diagnostic ends startup:

```shell
$ pi -ne -e <tmp>/a.js -e <tmp>/b.js -p hi
Error: Failed to load extension "<tmp>/b.js": Tool "dup_tool" conflicts with <tmp>/a.js
Hint: Start without extensions using "pi -ne".
exit code: 1
```

That is research/out/extensions-conflict.txt, from two one-line extensions that each register dup_tool, run ofline against the pinned build. An SDK caller that builds its own DefaultResourceLoader gets the same entry in get Extensions().errors

and decides for itself.

Built-ins are the exception. A replaceable built-in that shares a tool, command or flag name with any other extension is removed before the conflict check CA/src/core/resource-loader.ts:120. A third-party extension that registers /mcp therefore replaces the built-in MCP client, with a warning that names both.

F O O T G U N

Two installed extensions that register the same tool name stop the pi command from starting, and nothing in CA/docs/extensions.md mentions it. The suggested pi -ne does not help when either extension comes from -e, because -e paths load even with --no-extensions. Remove or disable one of the two; check the name with pi.getAllTools() before registering a generic one.

## Hot reload

/reload calls AgentSession.reload(), which replaces the whole extension runtime CA/src/core/agent-session.ts:3646:

![](images/282fa9fe2519ba4985daf6c22a02fa3eb4f29ca59244ace70c475013d1a70f8f.jpg)

Nothing survives a reload except what the session carries over. Active tool names and flag values pass to the new runtime; everything held in an extension’s closures is gone. From agent-session.ts:3646–3684. The two final events fire only when a UI or command context is bound.

After a reload or a session replacement, a captured pi or ctx from the old runtime throws: “This extension ctx is stale after session replacement or reload. Do not use a captured pi or command ctx after ctx.new Session(), ctx.fork(), ctx.switch Session(), or ctx.reload(). …” CA/src/core/extensions/runner.ts:723. Work that must run in the new session goes in the with Session callback of new Session(), fork() or switch Session(), which receives a fresh context (extension events and contexts (p. 120)).

## Extension API

ExtensionAPI is declared at types.ts:1553–1879. It has one on() method with 41 typed overloads, 31 other methods, and the events bus.

<table><tr><td>GROUP</td><td>METHODS</td></tr><tr><td>Events</td><td>on(event, handler) → unsubscribe function. 41 event names; see extension events and contexts (p. 120).</td></tr><tr><td>Tools</td><td>register Tool(def) · getActiveTools() · getAllTools() · setActiveTools(names)</td></tr><tr><td>Commands and input</td><td>register Command(name, { description?, getArgumentCompletions?, handler(args, ctx) })·register Shortcut(key, { description?, handler(ctx) })·register Flag(name, { description?, type: &quot;boolean&quot; | &quot;string&quot;, default? })·get Flag(name) · get Commands()</td></tr><tr><td>Rendering</td><td>registerMessageRenderer(custom Type, r) · registerEntryRenderer(custom Type, r) · registerToolRenderer(resolver) · registerMarkdownTransformer(t)</td></tr><tr><td>Conversation</td><td>send Message({ custom Type, content, display, details }, { trigger Turn?, deliverAs?: &quot;steer&quot; | &quot;followUp&quot; | &quot;next Turn&quot; })·sendUserMessage(content, { deliverAs?, expandPromptTemplates? })</td></tr><tr><td>Session data</td><td>append Entry(custom Type, data?) · setSessionName(name) · getSessionName() · set Label(entryId, label)</td></tr><tr><td>Model</td><td>set Model(model) → Promise··getThinkingLevel() · setThinkingLevel(level)</td></tr><tr><td>Providers</td><td>register Provider(provider) or register Provider(name, config) · unregister Provider(name) · registerVirtualModel(m) · unregisterVirtualModel(provider, id)</td></tr><tr><td>MCP</td><td>registerMcpServer(name, config) · unregisterMcpServer(name) · getMcpServers()</td></tr><tr><td>Other</td><td>exec(command, args, options?) · get Settings() · events (shared EventBus)</td></tr></table>

Registration methods write to the extension; action methods go to the shared runtime. From the ExtensionAPI interface and createExtensionAPI() CA/src/core/extensions/loader.ts:244.

A few behaviours are not visible in the signatures:

sendUserMessage: always triggers a turn. Prompt templates and skill commands are expanded only with expandPromptTemplates: true; the default is false CA/src/core/agent-session.ts:2376.

append Entry: writes a custom entry to the session file. It is never sent to the model; sessions, the JSONL tree (p. 86) shows its shape.

set Model: changes the session’s model without changing the saved default, and returns false when the provider has no configured auth.

register Provider(name, config): with models, replaces every model of that provider; with only base Url, re-points existing models. unregister Provider restores built-in models it overrode. The config.api Key outranks models.json (configuration, models and auth (p. 99)).

registerMcpServer: not persisted; register again on every load. A server of the same name in mcp.json takes precedence; aname another extension registered throws (MCP (p. 144)).

get Flag: returns undefined for a flag the calling extension did not register itself.

## Tool Definition

register Tool() takes a ToolDefinition CA/src/core/extensions/types.ts:567. register Tool() rejects a definition whose parameters is not an object schema CA/src/core/extensions/loader.ts:291. built-in tools (p. 81) shows the built-in tools built from the same type.

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

prompt Snippet: a one-line entry in the <tools> section of the default system prompt. A custom tool without one is left out of that section.

prompt Guidelines: bullets added to the <rules> section while the tool is active.

prepare Arguments: rewrites raw arguments before schema validation, for compatibility with older argument shapes.

output Schema: schema of structured Content in results. Codemode scripts receive the structured value instead of the text.

annotations: readOnlyHint, destructive Hint, idempotent Hint, openWorldHint, with MCP’s meanings. They come from the tool’s author and nothing verifies them.

default Active: true by default for direct and model-only tools; other exposures are never activated on registration.

execution Mode: "sequential" or "parallel"; overrides the default for this tool (the agent loop (p. 49)).

exposure decides how the model reaches the tool. “Callable” means callable from another tool through ctx.execute Tool(), as the codemode tool does CA/src/core/extensions/types.ts:494:

<table><tr><td>EXPOSURE</td><td>DECLARED TO THE MODEL</td><td>CALLABLE FROM TOOLS</td><td>NOTES</td></tr><tr><td>direct (default)</td><td>while active</td><td>while active</td><td>activated on registration</td></tr><tr><td>model-only</td><td>while active</td><td>never</td><td>for orchestrating or interactive tools; activated on registration</td></tr><tr><td>codemode</td><td>only if explicitly activated</td><td>whenever registered</td><td>listed in codemode tools&#x27; descriptions</td></tr><tr><td>deferred</td><td>only if explicitly activated</td><td>whenever registered</td><td>not listed by codemode; tool search can find it</td></tr><tr><td>hidden</td><td>never</td><td>never</td><td>registered but unreachable; activating it has no effect</td></tr></table>

The active set is exactly the set declared to the model. setActiveTools() ignores unknown and hidden names

CA/src/core/extensions/types.ts:1736. There is no unregister Tool(). codemode (p. 151) covers the codemode and deferred exposures in use.

W H A T T H I S M E A N S F O R Y O U

Register in the factory; start processes and timers in session_start.

Give tools and flags distinctive names; a duplicate across two extensions stops CLI startup.

Never keep a pi or ctx across /reload, new Session(), fork() or switch Session().

Use -e ./ext.ts to test an extension; it loads before everything installed.

Sources: CA/src/core/extensions/types.ts (ExtensionFactory, ExtensionAPI, ToolDefinition, ToolExposure, ToolAnnotations); CA/src/core/extensions/loader.ts (get Aliases, createExtensionAPI, loadExtensionModule, initialize Extension, clearExtensionCache); CA/src/core/extensions/virtual-modules.ts; CA/src/core/extensions/runner.ts (stale message, getAllRegisteredTools); CA/src/core/resource-loader.ts (reload, omitReplacedExtensions, detectExtensionConflicts); CA/src/core/package-manager.ts (resolveExtensionEntries, collectAutoExtensionEntries); CA/src/extensions/index.ts; CA/src/main.ts; CA/src/core/agent-session.ts (reload, sendUserMessage); CA/docs/extensions.md; research/capture/extensions-conflict.mjs; research/out/extensions-conflict.txt; research/out/resources-precedence.txt

# 5.4 Extension events and contexts

An extension sees Pi through 41 events, and about half of them let it change what happens next. A handler that throws is reported and skipped, except in \`tool_call\` and \`user_bash\`, where a throw stops the action.

Pi does not ofer one interception point. It ofers a typed event for each step of a run: startup, session changes, input, the system prompt, the message list, the provider request, every message and tool call, and the boundaries between turns. This section gives the dispatch rules shared by all of them and the full event table with what each handler may return. It draws one blocking call end to end, lists the context objects handlers receive, and maps the 80 entries in CA/examples/extensions/.

## Dispatch rules

All dispatch goes through ExtensionRunner CA/src/core/extensions/runner.ts. Four rules hold for every event:

Order: handlers run in extension load order, then in registration order within one extension (extensions, loading and the API (p. 113) gives the load order). pi.on() returns a function that removes that one registration; a dispatch already in progress keeps its snapshot.

Awaiting: each handler is awaited before the next one runs. A slow provider_stream_event handler delays stream consumption.

Errors: a throw is reported through the error listener as { extension Path, event, error, stack }, and dispatch continues with the next handler CA/src/core/extensions/runner.ts:1104.

Exceptions to the error rule: in tool_call the runner has no try, so a throw leaves the runner and blocks the call CA/src/core/extensions/runner.ts:1242. In user_bash the throw is reported and then rethrown CA/src/core/extensions/runner.ts:1285. Both fail closed.

How several handlers’ results combine depends on the event. input chains transforms and stops at the first handled CA/src/core/extensions/runner.ts:1519. tool_call stops at the first block: true. The session_before_* events stop at the first cancel: true; otherwise the last non-empty result wins CA/src/core/extensions/runner.ts:1098. message_end chains replacements and rejects one that changes the role with message_end handlers must return a message with the same role. cache_warming_decision takes the last action returned. project_trust takes the first yes or no.

## The events

Legend: N notify-only, M can modify, B can block or cancel. The table follows the order of a session.

<table><tr><td>PHASE</td><td>EVENT AND PAYLOAD</td><td>HANDLER RETURNS</td><td>KIND</td></tr><tr><td>Startup</td><td>project_trust { cwd },pre-trust extensions only</td><td>{ trusted: "yes" | "no" | "undecided", remember? }</td><td>B</td></tr><tr><td></td><td>resources_discover { cwd, reason: startup | reload }mcp_servers_change { servers }</td><td>{ skill Paths?, prompt Paths?, theme Paths? }-</td><td>MN</td></tr><tr><td>Session</td><td>session_start { reason: startup | reload | new | resume | fork, previousSessionFile? }</td><td>-</td><td>N</td></tr><tr><td></td><td>session_before_switch { reason: new | resume, targetSessionFile? }</td><td>{ cancel? }</td><td>B</td></tr><tr><td></td><td>session_before_fork { entryId, position: before | at }</td><td>{ cancel?, skipConversationRestore? }</td><td>B</td></tr><tr><td></td><td>session_before_compact { preparation, branch Entries, custom Instructions?, reason, will Retry, signal }</td><td>{ cancel?, compaction? }</td><td>B/M</td></tr><tr><td></td><td>session_compact,session_compact_failed</td><td>-</td><td>N</td></tr><tr><td></td><td>session_before_tree { preparation, signal }</td><td>{ cancel?, summary?, custom Instructions?, replace Instructions?, label? }</td><td>B/M</td></tr><tr><td></td><td>session_tree,session_info_changed { name }</td><td>-</td><td>N</td></tr><tr><td></td><td>session_shutdown { reason: quit | reload | new | resume | fork, targetSessionFile? }</td><td>-</td><td>N</td></tr><tr><td>Input</td><td>input { text, images?, source, streaming Behavior? }</td><td>continue|transform { text, images? }|handled</td><td>M/B</td></tr><tr><td></td><td>before_agent_start { prompt, images?, system Prompt, systemPromptOptions }</td><td>{ message?, system Prompt? },or mutate systemPromptOptions</td><td>M</td></tr><tr><td>Loop</td><td>agent_start,turn_start { turn Index, timestamp }</td><td>-</td><td>N</td></tr><tr><td></td><td>context { messages },system messages hidden</td><td>{ messages? },or edit in place</td><td>M</td></tr><tr><td></td><td>context_with_system { messages },full transcript</td><td>{ messages? }</td><td>M</td></tr><tr><td>Provider</td><td>before_provider_request { payload }</td><td>a replacement payload</td><td>M</td></tr><tr><td></td><td>before_provider_headers { headers }</td><td>mutate in place; null deletes a header</td><td>M</td></tr><tr><td></td><td>after_provider_response { status, headers }, provider_stream_event { provider, api, model, data }</td><td>-</td><td>N</td></tr><tr><td></td><td>cache_warming_decision { warm Cost, miss Cost, continuation Probability, action }</td><td>{ action?: "warm" | "stop" }</td><td>M</td></tr><tr><td>Messages</td><td>message_start,message_update { message, assistantMessageEvent }</td><td>-</td><td>N</td></tr><tr><td></td><td>message_end { message }</td><td>{ message? },same role</td><td>M</td></tr><tr><td>Tools</td><td>tool_call { toolCallId, tool Name, input, parentToolCallId? }</td><td>{ block?, reason?, terminate? };mutate input in place</td><td>B/M</td></tr><tr><td></td><td>tool_execution_start,tool_execution_update, tool_execution_end</td><td>-</td><td>N</td></tr><tr><td></td><td>tool_result { ..., input, content, details, structured Content?, isError, usage? }</td><td>{ content?, details?, structured Content?, isError?, usage? }</td><td>M</td></tr><tr><td>Boundaries</td><td>turn_end,agent_before_settle:{ entries, continue, context, outcome }</td><td>{ entries?, continue? }</td><td>M</td></tr><tr><td>UI</td><td>agent_end { messages },agent_settledui_prompt_start, ui_prompt_end { kind, title? }</td><td>-—</td><td>NN</td></tr><tr><td>Model</td><td>model_select { model, previous Model, source: set | cycle | restore }, thinking_level_select { level, previous Level }</td><td>—</td><td>N</td></tr><tr><td>Bash</td><td>user_bash { command, excludeFromContext, cwd }</td><td>{ operations } | { result }</td><td>M/B</td></tr></table>

Nineteen of the 41 events can change what happens; the other 22 only observe. Payloads and results from types.ts:679–1490 and cache-warmer.ts:112; turn_end also carries turn Index, message, tool Results and their entry ids. agent events and the Agent class (p. 57) gives the order in which the loop emits its share of them; the capture in the life of one prompt (p. 15) shows a real stream.

A few rows need more than a cell:

context vs context_with_system: context handlers see the conversation without system messages, and Pi puts the prompt and tool state back after each one. context_with_system handlers then see the full transcript, and their output is sent as returned. Dropping the leading system message is reported (“Handler removed the leading system message; the request has no prompt or initial tool declarations.”) but honoured CA/src/core/extensions/runner.ts:1342.

before_agent_start: later handlers see earlier handlers’ changes to systemPromptOptions. Returning system Prompt sets forceSystemPrompt and replaces the whole prompt for the run CA/src/core/extensions/runner.ts:1454. Every returned message is collected.

tool_call: runs after schema validation, and input is not validated again after a handler mutates it CA/src/core/extensions/types.ts:1211. terminate: true ends the run after the current batch only when every finalized result in the batch sets it.

tool_result: replacing content without returning structured Content drops the structured content, because it may no longer match CA/src/core/extensions/runner.ts:1194.

turn_end, agent_before_settle: the two actionable boundaries. Handlers chain proposed entries — drafts of type custom, custom_message, context_edit or compaction CA/src/core/extensions/types.ts:966 — and may set continue: true for one more model request. If the final drafts fail validation, all of them are dropped and continue becomes false CA/src/core/extensions/runner.ts:1075.

user_bash: fires for ! and !! commands typed by the user. The first handler that returns a result decides: { operations } swaps the execution backend, { result } replaces execution entirely. A handler that throws does not fall back to local execution: the TUI reports the error and runs nothing CA/src/modes/interactive/interactive-mode.ts:6962.

## One call, two handlers

The original manual’s sequence figure holds at the pinned commit. AgentSession installs beforeToolCall on the agent and forwards it to emitToolCall() CA/src/core/agent-session.ts:646. The agent loop turns the outcome into an error tool result agent/agent-loop.ts:744.

![](images/444bfbb245dda45f9cfdc94866edaf57240048b1958202dccfce958e95c03cd8.jpg)

A block becomes an ordinary failed tool result; the model reads the reason. Without a reason the text is Tool execution was blocked. If B had thrown instead, the error would leave the runner unreported, _beforeToolCall would rethrow it, and the loop’s catch would produce an error result carrying the exception’s message agent/agent-loop.ts:769. Schematic; from runner.ts:1242, agent-session.ts:646–669 and agent-loop.ts:724–775.

The shipped docs give a permission gate built on tool annotations:

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

## Contexts

Every handler receives an ExtensionContext as its second argument CA/src/core/extensions/types.ts:325. Tools and commands get extended versions.

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

ExtensionToolContext.execute Tool(): runs another tool through the same preparation, validation, tool_call and tool_result hooks as a model-issued call. The nested call gets the id <calling id>/<n> and never appears in the transcript. It does not reject on tool failure; failures come back with isError: true CA/src/core/extensions/types.ts:383.

ExtensionCommandContext: session control is ofered to command handlers only; the interface comment calls these “session control methods only safe in user-initiated commands” CA/src/core/extensions/types.ts:399. new Session(), fork() and switch Session() accept a with Session(ctx) callback that receives a fresh ReplacedSessionContext bound to the new session. Use it for anything after the switch; the old ctx is stale (extensions, loading and the API (p. 113)).

compact(): starts compaction and returns without waiting; pass onComplete and onError to observe it (compaction and branch summaries (p. 92)).

ctx.ui is the ExtensionUIContext CA/src/core/extensions/types.ts:149:

<table><tr><td>GROUP</td><td>MEMBERS</td></tr><tr><td>Dialogs</td><td>select, confirm, input (each with { signal?, timeout? }); editor(title, prefill?) without options</td></tr><tr><td>Status</td><td>notify, Kingston, setWorkingMessage, setWorkingVisible, setWorkingIndicator, setHiddenThinkingLabel, set Title</td></tr><tr><td>Layout</td><td>set Widget(key, lines | factory, { placement: &quot;above Editor&quot; | &quot;below Editor&quot; }), set Header, set Footer</td></tr><tr><td>Components</td><td>custom(factory, { overlay?, overlay Options?, onHandle? })</td></tr><tr><td>Editor</td><td>setEditorText, getEditorText, pasteToEditor, setEditorComponent, getEditorComponent, addAutocompleteProvider, onTerminalInput</td></tr><tr><td>Appearance</td><td>theme, getAllThemes, get Theme, set Theme, getToolsExpanded, setToolsExpanded</td></tr></table>

editor() is the one dialog that cannot time out. Its signature takes only a title and a prefill.

What those calls do depends on the run mode (run modes (p. 127)). hasUI is true when a real UI context is bound, which happens in the TUI and in RPC mode CA/src/core/extensions/runner.ts:621:

<table><tr><td>MODE</td><td>ctx.mode</td><td>hasUI</td><td>DIALOGS</td><td>COMPONENTS AND LAYOUT</td></tr><tr><td>interactive</td><td>tui</td><td>true</td><td>full</td><td>full</td></tr><tr><td>RPC</td><td>rpc</td><td>true</td><td>sent to the client as extension_ui_request and awaited</td><td>custom() → undefined; header, footer, editor component, working indicator: no-ops; set Widget with string lines only; getEditorText() → &quot;&quot;</td></tr><tr><td>print, JSON</td><td>print, json</td><td>false</td><td>resolve at once: undefined, or false for confirm</td><td>no-ops</td></tr></table>

An extension that needs an answer must check hasUI or expect the default. From rpc-mode.ts (createExtensionUIContext) and noOpUIContext in runner.ts. RPC mode and the SDK (p. 133) specifies the RPC UI sub-protocol.

## Example extensions

CA/examples/extensions/ holds 80 entries at the pinned commit: 70 single-file .ts extensions, 9 directories and a README.md research/out/stats.txt §example-extensions. The ones below each show one technique; all the names were checked against the directory listing.

<table><tr><td>CATEGORY</td><td>EXAMPLES</td><td>WHAT THEY SHOW</td></tr><tr><td>Safety</td><td>permission-gate.ts,protected-paths.ts, confirm-destructive.ts,dirty-repo-guard.ts, project-trust.ts,sandbox/,gondolin/</td><td>tool_call blocking,session_before_*cancel,project_trust; sandbox/ replaces bash with an @anthropic-ai/sandbox-runtime version; gondolin/ runs the built-in tools in a QEMU micro-VM</td></tr><tr><td>Workflow</td><td>subagent/,plan-mode/,todo.ts,handoff.ts, preset.ts,tools.ts,git-checkpoint.ts,auto-commit-on-exit.ts</td><td>child pi processes, tool sets per mode, state in custom entries</td></tr><tr><td>Tools</td><td>hello.ts,dynamic-tools.ts,tool-override.ts, structured-output.ts,ssh.ts,truncated-tool.ts,question.ts</td><td>register Tool, replacing a built-in, terminate: true, remote execution</td></tr><tr><td>Prompt and context</td><td>custom-compaction.ts,trigger-compact.ts, claude-rules.ts,prompt-customizer.ts, pirate.ts,dynamic-resources/</td><td>session_before_compact, before_agent_start, resources_discover</td></tr><tr><td>UI</td><td>custom-footer.ts,custom-header.ts,modal-editor.ts,overlay-test.ts,doom-overlay/, snake.ts,status-line.ts,notify.ts</td><td>ctx.ui layout, overlays, custom editors</td></tr><tr><td>Providers</td><td>custom-provider-anthropic/,custom-provider-gitlab-duo/,jev-router.ts</td><td>register Provider; jev-router.ts registers a virtual model</td></tr><tr><td>Plumbing</td><td>event-bus.ts,rpc-demo.ts,reload-runtime.ts, interactive-shell.ts,inline-bash.ts,with-deps/</td><td>pi.events,RPC UI,/reload,user_bash,an extension with its own node_modules</td></tr></table>

Forty-five of the 79 examples, sorted by what they teach. Descriptions from each file’s header comment.

W H A T T H I S M E A N S F O R Y O U

Throw in a tool_call handler only when you mean to block; in every other event a throw is logged and ignored.

Return a reason with every block; it is the only thing the model learns.

Check ctx.hasUI before a dialog, or choose the safe default for print and JSON runs.

Put work that follows new Session(), fork() or switch Session() inside with Session.

Sources: CA/src/core/extensions/types.ts (ExtensionUIContext, ExtensionContext, ExtensionToolContext, ExtensionCommandContext, event and result interfaces, SessionBoundaryDraft); CA/src/core/extensions/runner.ts (emit, emitCacheWarmingDecision, emitMessageEnd, emitToolResult, emitToolCall, emitUserBash, emit Context, emitBeforeProviderHeaders, emitBeforeAgentStart, emitResourcesDiscover, emit Input, emit Boundary, emitProjectTrustEvent, noOpUIContext, hasUI); CA/src/core/cache-warmer.ts; CA/src/core/agent-session.ts (_beforeToolCall, _afterToolCall); agent/agent-loop.ts (prepareToolCall); CA/src/modes/rpc/rpc-mode.ts (createExtensionUIContext); CA/src/modes/printmode.ts; CA/docs/extensions.md; CA/examples/extensions *; research/out/stats.txt (§example-extensions)

### 5.5 Run modes: interactive, print and JSON

Every way of starting Pi runs the same \`main()\` and builds the same

\`AgentSessionRuntime\`; the mode is chosen late,from twoflags and two TTY checks, and only decides who reads the events.

pi in a terminal opens a full-screen editor. pi -p "…" prints one answer and exits. pi --mode json streams every event as a JSON line, and pi --mode rpc keeps a JSONL conversation open on stdin and stdout. This section follows main() from argv to the point where it hands the runtime to a mode, then covers the three modes a person or a shell script drives directly: interactive, print and JSON. RPC and the in-process SDK are in RPC mode and the SDK (p. 133). Every flag mentioned here is listed in CLI reference (p. 191).

## One entry point

The pi binary is dist/bundle/cli.js CA/package.json:10, built from a six-line src/cli.ts. It calls setup Cli(), which sets process.title, exports PI_CODING_AGENT=true and AI_AGENT=pi, silences process.emit Warning and configures the HTTP dispatcher CA/src/cli/setup.ts:4. Then it calls main(process.argv.slice(2)) CA/src/cli.ts:6. The package also exports ./rpc-entry CA/package.json:19, which does the same setup with process.title set to pi-rpc and calls main(["- -mode", "rpc", ...argv]) CA/src/rpc-entry.ts:13. It is a module entry point, not a second bin.

main() CA/src/main.ts:573 then works through a fixed order. Subcommands are dispatched before any flag parsing, so pi auth, pi install or pi mcp never build a session.

F I G . 5 . 1 0 F R O M A R G V T O A M O D E
![](images/3522dbfb28a758095f32d4689f99506aa610ad6c81f1069a09ea6c66f6e2ab86.jpg)

The mode is decided at step 3 but used only at step 8. Everything between — migrations, session selection, project trust, extension loading, model resolution — is identical for all four modes. Line numbers are in CA/src/main.ts. Schematic.

Steps 1–8 in Fig. 5.10 (p. 127) map onto the source as follows:

1 · Subcommands: runAuthCommand runs first, before cleanup or settings CA/src/main.ts:582. Then handlePackageCommand (install, remove, uninstall, update, list), which always ends with process.exit CA/src/main.ts:597; then handleConfigCommand CA/src/main.ts:610; then mcp CA/src/main.ts:614.

2 · Flags: parse Args collects errors as diagnostics; any error prints and exits 1 CA/src/main.ts:626. --version prints and exits; --export writes HTML and exits without building a runtime CA/src/main.ts:637.

3 · Mode: see the decision ladder below. Every mode except interactive calls takeOverStdout() here, which reroutes stray process.stdout.write calls to stderr CA/src/core/output-guard.ts:45. RPC mode rejects @file arguments at this point CA/src/main.ts:657.

4 · Session: createSessionManager picks one branch, first match wins: --no-session (or --help, --list-models) → in memory; --fork; --session; --resume; --continue; --session-id; otherwise a new file CA/src/main.ts:358. sessions, the JSONL tree (p. 86) describes the files.

5 · Runtime: createAgentSessionRuntime(create Runtime, …) runs the factory at CA/src/main.ts:730: createAgentSessionServices → DefaultResourceLoader.reload() (with the project-trust prompt between pre-trust and full extension loading) → createAgentSessionFromServices. The factory is kept, so /new, /resume and /fork rebuild through it.

6 · Metadata: --help is answered only after the runtime exists, because the help text lists flags registered by loaded extensions CA/src/main.ts:877.

7 · Input: piped stdin is read for every mode except RPC, and its presence downgrades interactive to print CA/src/main.ts:895. Runtime diagnostics print; any error exits 1 CA/src/main.ts:919. A non-interactive mode with no model exits 1 CA/src/main.ts:927.

8 · Hand-of: runRpcMode(runtime) CA/src/main.ts:950, new InteractiveMode(runtime, …).run() CA/src/main.ts:952, or runPrintMode(runtime, { mode }) CA/src/main.ts:986. Each mode then calls session.bind Extensions(…), which emits session_start and resources_discover extension events and contexts (p. 120).

## The decision ladder

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

The ladder has one consequence that surprises people: --mode text selects nothing. It is accepted by parse Args CA/src/cli/args.ts:103, but resolveAppMode never tests for it, so pi --mode text in a terminal still opens the TUI. Use -p for one-shot text. Redirecting either stdout or stdin is enough for print mode, and piped stdin later forces print even when both checks passed CA/src/main.ts:895.

<table><tr><td>INVOCATION</td><td>MODE</td><td>WHY</td></tr><tr><td>pi</td><td>interactive</td><td>both streams are TTYs</td></tr><tr><td>pi --mode text</td><td>interactive</td><td>text is not tested</td></tr><tr><td>pi -p &quot;...&quot;</td><td>print</td><td>--print</td></tr><tr><td>pi &quot;...&quot; &gt; out.txt</td><td>print</td><td>stdout is not a TTY</td></tr><tr><td>echo &quot;...&quot; | pi</td><td>print</td><td>stdin is not a TTY</td></tr><tr><td>pi --mode json &quot;...&quot;</td><td>json</td><td>tested before --print</td></tr><tr><td>pi --mode rpc</td><td>rpc</td><td>tested first</td></tr></table>

--mode beats --print, and a redirect beats nothing. From resolveAppMode CA/src/main.ts:112 and the stdin downgrade at CA/src/main.ts:895.

The four modes difer only in what they do with the three standard streams and with extension dialogs:

![](images/9f47fb281d6ecad0b08f5a2575022fe6bfb46919a866915ea165e96256e21330.jpg)

Only interactive and RPC modes can ask a question. Print and JSON modes bind no UI context, so every extension dialog resolves to its default. The three non interactive modes reroute stray process.stdout.write calls to stderr so that stdout carries only their own output. Schematic, from CA/src/main.ts:651–655, CA/src/core/output-guard.ts, CA/src/modes/print-mode.ts and CA/src/modes/rpc/rpc-mode.ts.

## Interactive mode

InteractiveMode is 7,072 lines CA/src/modes/interactive/interactive-mode.ts and draws everything through pi-tui pi-tui (p. 158). It has two layouts, chosen by the tui Mode setting or --tui-mode: fullscreen, the default CA/src/core/settingsmanager.ts:1349, keeps the editor and status area fixed while the transcript scrolls inside the window; regular writes into the terminal’s own scrollback CA/docs/usage.md.

The editor’s submit handler decides what a line means, in this order CA/src/modes/interactive/interactive-mode.ts:3179:

<table><tr><td>INPUT</td><td>EFFECT</td></tr><tr><td>a built-in /command</td><td>handled by the mode itself; the 24 commands are in slash commands and keybindings (p. 197)</td></tr><tr><td>! cmd</td><td>runs cmd with bash and adds the output to the context</td></tr><tr><td>!! cmd</td><td>runs cmd without adding it to the context</td></tr><tr><td>any text while compacting</td><td>queued until compaction ends; extension commands still run at once</td></tr><tr><td>any text while streaming</td><td>session.prompt(text, { streaming Behavior: &quot;steer&quot; })</td></tr><tr><td>any text when idle</td><td>a new prompt</td></tr></table>

Enter steers a running agent; it does not wait. Alt+Enter queues a follow-up instead, and Alt+Up pulls queued text back into the editor. Submit handler at CA/src/modes/interactive/interactive-mode.ts:3179; keys from CA/src/core/keybindings.ts:135.

Escape is overloaded, and the first matching state wins CA/src/modes/interactive/interactive-mode.ts:3050. While the agent streams, Escape aborts and moves every queued steering and follow-up message back into the editor, joined by blank lines CA/src/modes/interactive/interactive-mode.ts:4702. While a ! command runs, it aborts the command. In bash mode it clears the line. With an empty editor, two presses within 500 ms open /tree, /fork or nothing, depending on doubleEscapeAction CA/src/modes/interactive/interactive-mode.ts:3064. Ctrl+C clears the editor, and a second press within 500 ms exits CA/src/modes/interactive/interactive-mode.ts:4231.

## Print mode

Print mode sends its prompts in order and exits. The first prompt is assembled from three parts — piped stdin, @file text, and the first positional message — and the remaining messages follow as separate prompts CA/src/cli/initial-message.ts:20 CA/src/modes/print-mode.ts:131.

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

Only the last assistant message reaches stdout. If the run ended in error or aborted, the error goes to stderr and the exit code is 1. A thrown error also exits 1 CA/src/modes/print-mode.ts:159.

Piped stdin and the prompt are joined with no separator. readPipedStdin trims the input CA/src/main.ts:93, and buildInitialMessage joins stdin, file text and the first message with "" CA/src/cli/initial-message.ts:40. So cat notes.txt | pi -p "Summarise this" sends the file’s last line glued to “Summarise this”. The unit test passes stdin with a trailing newline, which the CLI never delivers CA/test/initial-message.test.ts. Start the prompt with a newline or a space, or put the instruction inside the piped text.

## JSON mode

JSON mode is print mode with a diferent subscriber. Line 1 is the session header, written before extensions are bound CA/src/modes/print-mode.ts:122. Every AgentSessionEvent follows, one JSON line each, through toJsonEvent CA/src/modes/print-mode.ts:110. Nothing else is written to stdout, and the exit code follows the same rules as text mode.

toJsonEvent changes one event type. A message_update loses the cumulative message and the partial snapshot inside its assistantMessageEvent, and gains a top-level usage CA/src/modes/json-event.ts:48. A toolcall_start keeps the tool call’s id and tool Name, which would otherwise be lost with the partial CA/src/modes/json-event.ts:23. Every other event passes through unchanged. RPC mode uses the same function, so the shapes below are also the RPC event shapes.

The capture kit ran one prompt through a real runtime in JSON mode, with the faux provider and one inline extension that calls ctx.ui.confirm() before each tool call research/capture/rpc-and-sdk-child.mjs:

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

The tool_execution_end line shows the cost of having no UI. Print and JSON modes bind extensions without a uiContext CA/src/modes/print-mode.ts:76, so the runner keeps its no-op context and ctx.hasUI is false

CA/src/core/extensions/runner.ts:621. In that context select and input resolve to undefined and confirm resolves to falseCA/src/core/extensions/runner.ts:324. The extension’s own guard blocked the tool. The same extension in RPC mode asks the client instead (Fig. 5.12 (p. 134)).

D O C ≠ C O D E

The basic run in CA/docs/json.md (§Event sequence) starts with the user message and shows its content as a string. The real stream emits a message_start/message_end pair with role: "system" before the user message, and the user message’s content is an array of content blocks research/out/rpc-exchange.txt §json-mode. A strict parser written from the documented sample fails on line 4.

## Signals

<table><tr><td>SIGNAL</td><td>PRINT / JSON</td><td>RPC</td></tr><tr><td>SIGTERM</td><td>dispose runtime, exit 143</td><td>dispose runtime, exit 143, stdout not flushed</td></tr><tr><td>SIGHUP (not Windows)</td><td>dispose runtime, exit 129</td><td>dispose runtime, exit 129</td></tr><tr><td>stdin EOF</td><td>—</td><td>dispose runtime, exit 0</td></tr></table>

Every orderly exit fires session_shutdown with reason: "quit". AgentSessionRuntime.dispose() emits it before disposing the session CA/src/core/agent-session-runtime.ts:404. Handlers at CA/src/modes/print-mode.ts:50 and CA/src/modes/rpc/rpc-mode.ts:366; tracked detached children are killed first in both.

W H A T T H I S M E A N S F O R Y O U

Use -p for one-shot text; --mode text alone still opens the TUI in a terminal.

Parse JSON mode from message_start, the deltas and message_end; there is no cumulative snapshot in message_update.

Give every extension dialog a safe default: in print and JSON modes confirm always answers false.

Check the exit code: 1 means the last assistant message ended in error or aborted.

Sources: CA/package.json (bin, exports); CA/src/cli.ts; CA/src/cli/setup.ts (setup Cli); CA/src/rpc-entry.ts; CA/src/main.ts (main, resolveAppMode, createSessionManager, readPipedStdin, create Runtime). CA/src/cli/args.ts (parse Args); CA/src/cli/initial-message.ts (buildInitialMessage); CA/src/core/output-guard.ts (takeOverStdout). CA/src/modes/print-mode.ts (runPrintMode); CA/src/modes/json-event.ts (toJsonEvent); CA/src/core/extensions/runner.ts (noOpUIContext, hasUI); CA/src/core/agent-session-runtime.ts (dispose). CA/src/modes/interactive/interactive-mode.ts (setupEditorSubmitHandler, setupKeyHandlers, restoreQueuedMessagesToEditor, handleCtrlC); CA/src/core/keybindings.ts; CA/src/core/settings-manager.ts (getTuiMode, getDoubleEscapeAction). CA/test/initial-message.test.ts; CA/docs/json.md, usage.md; research/capture/rpc-and-sdk-child.mjs; research/out/rpc-exchange.txt (§json-mode)

## 5.6 RPC mode and the SDK

RPC mode is the SDK's \`AgentSession\` withJSONL on both ends — 33 commands in, events and responses out — and its one real addition is a small protocol that lets an extension ask the client a question.

An IDE, a Python service or a web backend that wants Pi has two doors. It can spawn pi --mode rpc and talk JSONL over pipes, or it can import @earendil-works/pi-coding-agent and hold an AgentSession in its own process. This section records one real RPC conversation, lists every command and its response data, describes the extension UI sub-protocol and the TypeScript RpcClient, and then shows the SDK calls the CLI itself is built from. How the CLI reaches runRpcMode is in run modes (p. 127); the events themselves are in agent events and the Agent class (p. 57).

#### Framing: strict JSONL

Each record is one JSON object followed by LF. serializeJsonLine is JSON.stringify(value) + "\n" CA/src/modes/rpc/jsonl.ts:10. The reader splits on \n only and strips one trailing \r, so CRLF input works CA/src/modes/rpc/jsonl.ts:26.

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

The separators in question are U+2028 and U+2029. Both are legal inside a JSON string, and a model can produce either one. A client that reads with Node readline splits such a record in two and fails to parse both halves CA/docs/rpc.md §Framing. runRpcMode calls takeOverStdout() before anything else CA/src/modes/rpc/rpc-mode.ts:55, so an extension that calls console.log writes to stderr and cannot corrupt the stream.

## One exchange, recorded

The capture kit spawns a real runRpcMode with the faux provider and one inline extension that calls ctx.ui.confirm() before every tool call, then plays the client research/capture/rpc-and-sdk-exchange.mjs. The model is scripted to call read once and then answer.

F I G . 5 . 1 2 O N E R P C C O N V E R S A T I O N

2

4

5

6

![](images/eb4c550aa4ebe0d87971d2a8b24eb592f9933906c12bae801f42992a6a7132f4.jpg)

The prompt response arrives before the run; agent_settled marks its end. 43 records: 6 from the client, 36 from Pi, plus the exit. Steps 2–3 are the extension UI sub-protocol. From research/out/rpc-exchange.txt; event counts vary with the number of streamed text deltas.

The first three records, exactly as captured:

```txt
> {"id":"1","type":"prompt","message":"What does hello.txt say?"}
< {"id":"1","type":"response","command":"prompt","success":true,"data":{"disposition":"started"}} < {"type":"agent_start"}
```

And the end of the conversation, after agent_settled:

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

Every command produces at most one response record. Events carry no command id, with one exception: bash_execution_update repeats the id of the bash command that started it CA/src/core/agent-session.ts:3847.

Success: { id?, type: "response", command, success: true, data? }. data is omitted when the command returns nothing CA/src/modes/rpc/rpc-mode.ts:64.

Failure: { id?, type: "response", command, success: false, error } CA/src/modes/rpc/rpc-types.ts:245. A thrown handler error becomes a failure with the command’s own id and type CA/src/modes/rpc/rpc-mode.ts:790.

Parse error: a line that is not JSON gets command: "parse" and no id CA/src/modes/rpc/rpc-mode.ts:755.

Unknown command: command is the unknown type, and error is Unknown command: <type> CA/src/modes/rpc/rpcmode.ts:715.

prompt: answers when preflight accepts the prompt, through the preflight Result callback, not when the run ends CA/src/modes/rpc/rpc-mode.ts:403. disposition is started, queued or handled CA/src/core/agent-session.ts:301. handled means an extension consumed the input and no run starts, so no agent_settled will follow. A prompt rejected before preflight gets a failure response instead.

agent_end is not the end. Retries, overflow recovery, compaction and queued follow-ups can start another low-level run after it. Wait for agent_settled CA/docs/rpc.md §Run lifecycle.

## The 33 commands

RpcCommand is a union of 33 shapes CA/src/modes/rpc/rpc-types.ts:20. Every one accepts an optional string id.

<table><tr><td>AREA</td><td>COMMAND</td><td>PARAMETERS</td><td>RESPONSE data</td></tr><tr><td>Prompting</td><td>prompt</td><td>message, images?, streaming Behavior?: "steer" | "followUp"</td><td>{ disposition }</td></tr><tr><td></td><td>steer, follow_up</td><td>message, images?</td><td>{ disposition: "queued" | "handled" }</td></tr><tr><td></td><td>abort</td><td>-</td><td>-</td></tr><tr><td></td><td>clear_queue</td><td>-</td><td>{ steering: string[], followUp: string[] }</td></tr><tr><td></td><td>new_session</td><td>parent Session?</td><td>{ cancelled }</td></tr><tr><td>State</td><td>get_state</td><td>-</td><td>RpcSessionState</td></tr><tr><td></td><td>get_messages</td><td>-</td><td>{ messages }</td></tr><tr><td>Model</td><td>set_model</td><td>provider, modelId</td><td>the Model</td></tr><tr><td></td><td>cycle_model</td><td>-</td><td>{ model, thinking Level, isScoped} or null</td></tr><tr><td></td><td>get_available_models</td><td>-</td><td>{ models }</td></tr><tr><td>Thinking</td><td>set_thinking_level</td><td>level</td><td>-</td></tr><tr><td></td><td>cycle_thinking_level</td><td>-</td><td>{ level } or null</td></tr><tr><td></td><td>get_available_thinking_levels</td><td>-</td><td>{ levels }</td></tr><tr><td>Queues</td><td>set_steering_mode, set_follow_up_mode</td><td>mode: "all" | "one-at-a-time"</td><td>-</td></tr><tr><td>Compaction</td><td>compact</td><td>custom Instructions?</td><td>CompactionResult</td></tr><tr><td></td><td>set_auto_compaction</td><td>enabled</td><td>-</td></tr><tr><td>Retry</td><td>set_auto_retry</td><td>enabled</td><td>-</td></tr><tr><td></td><td>abort_retry</td><td>-</td><td>-</td></tr><tr><td>Bash</td><td>bash</td><td>command, excludeFromContext?</td><td>BashResult; streams bash_execution_update</td></tr><tr><td></td><td>abort_bash</td><td>-</td><td>-</td></tr><tr><td>Session</td><td>get_session_stats</td><td>-</td><td>SessionStats (counts, tokens, cost)</td></tr><tr><td></td><td>export_html</td><td>output Path?</td><td>{ path }</td></tr><tr><td></td><td>switch_session</td><td>session Path</td><td>{ cancelled }</td></tr><tr><td></td><td>fork</td><td>entryId</td><td>{ text, cancelled }</td></tr><tr><td></td><td>cloneget_entries</td><td>-since? (entry id)</td><td>{ cancelled }{ entries, leafId }</td></tr><tr><td></td><td>get_tree</td><td>—</td><td>{ tree, leafId }</td></tr><tr><td></td><td>get_last_assistant_text</td><td>—</td><td>{ text } (ornull)</td></tr><tr><td></td><td>set_session_name</td><td>name</td><td>—</td></tr><tr><td>Discovery</td><td>get_commands</td><td>—</td><td>{ commands }: extension commands, prompt templates, skill:</td></tr></table>

Every command maps to one AgentSession or AgentSessionRuntime call. From the RpcCommand and RpcResponse unions CA/src/modes/rpc/rpctypes.ts:20 CA/src/modes/rpc/rpc-types.ts:116 and handle Command CA/src/modes/rpc/rpc-mode.ts:386. A dash means the success response has no data.

Three commands fail with their own messages: set_model with Model not found: <provider>/<id> CA/src/modes/rpc/rpc-mode.ts:474, get_entries with Entry not found: <since> CA/src/modes/rpc/rpc-mode.ts:642, and set_session_name with Session name cannot be empty CA/src/modes/rpc/rpc-mode.ts:662. clone is fork at the current leaf with position: "at" CA/src/modes/rpc/rpc-mode.ts:624. new_session, switch_session, fork and clone replace the active session and rebind extensions and the event subscription to the new one CA/src/modes/rpc/rpc-mode.ts:438. Slash commands are not RPC commands: send /name as the message of a prompt, and get_commands lists what is available. The 24 built-in interactive commands in slash commands and keybindings (p. 197) are not among them.

get_state returns RpcSessionState CA/src/modes/rpc/rpc-types.ts:96. It has no session header; RPC mode never writes one, unlike JSON mode.

<table><tr><td>FIELD</td><td>TYPE</td><td>FIELD</td><td>TYPE</td></tr><tr><td>model?</td><td>Model</td><td>session File?</td><td>string</td></tr><tr><td>thinking Level</td><td>ThinkingLevel</td><td>sessionId</td><td>string</td></tr><tr><td>isStreaming</td><td>boolean</td><td>session Name?</td><td>string</td></tr><tr><td>isCompacting</td><td>boolean</td><td>autoCompactionEnabled</td><td>boolean</td></tr><tr><td>steering Mode</td><td>&quot;all&quot; | &quot;one-at-a-time&quot;</td><td>message Count</td><td>number</td></tr><tr><td>followUpMode</td><td>&quot;all&quot; | &quot;one-at-a-time&quot;</td><td>pendingMessageCount</td><td>number</td></tr></table>

Twelve fields, read live from the session on every call. CA/src/modes/rpc/rpc-mode.ts:448.

Besides every AgentSessionEvent in JSON-mode form (run modes (p. 127)), stdout carries extension_error records, { type, extension Path, event, error }, when an extension handler throws CA/src/modes/rpc/rpc-mode.ts:349.

## The extension UI sub-protocol

RPC mode binds extensions with a real uiContext CA/src/modes/rpc/rpc-mode.ts:320, so ctx.hasUI is true and ctx.mode is "rpc". Each supported call becomes an extension_ui_request with a fresh crypto.randomUUID() id CA/src/modes/rpc/rpc-mode.ts:99. Dialogs wait for an extension_ui_response with that id; the other methods expect no reply.

<table><tr><td>METHOD</td><td>REQUEST FIELDS</td><td>CLIENT REPLIES</td><td>DEFAULT ON TIMEOUT OR ABORT</td></tr><tr><td>select</td><td>title,options[],timeout?</td><td>{ value }or{ cancelled: true }</td><td>undefined</td></tr><tr><td>confirm</td><td>title,message,timeout?</td><td>{ confirmed }or{ cancelled: true }</td><td>false</td></tr></table>

RPC mode and the SDK

<table><tr><td>input</td><td>title, placeholder?, timeout?</td><td>{ value } or { cancelled: true }</td><td>undefined</td></tr><tr><td>editor</td><td>title,prefill?</td><td>{ value } or { cancelled: true }</td><td>none: waits for the client</td></tr><tr><td>notify</td><td>message, notify Type?</td><td>no reply</td><td>—</td></tr><tr><td>set State</td><td>status Key, status Text</td><td>no reply</td><td>—</td></tr><tr><td>set Widget</td><td>widget Key, widget Lines, widget Placement?</td><td>no reply</td><td>—</td></tr><tr><td>set Title</td><td>title</td><td>no reply</td><td>—</td></tr><tr><td>set_editor_text</td><td>text</td><td>no reply</td><td>—</td></tr></table>

Pi, not the client, enforces dialog timeouts. createDialogPromise resolves to the default when the timeout fires or the extension’s signal aborts CA/src/modes/rpc/rpc-mode.ts:91. set Widget is sent only for string arrays; component factories are dropped CA/src/modes/rpc/rpc-mode.ts:197. pasteToEditor becomes set_editor_text.

The rest of ExtensionUIContext degrades without a message. custom() returns undefined, getEditorText() returns "", set Theme() returns { success: false, … }, and the footer, header, working-indicator and editor-component setters do nothing CA/src/modes/rpc/rpc-mode.ts:179. A response whose id matches no pending request is dropped silently CA/src/modes/rpc/rpc-mode.ts:774.

## F O O T G U N
editor is the one dialog that does not go through createDialogPromise. It takes no timeout and ignores the abort signal CA/src/modes/rpc/rpc-mode.ts:254. A client that never answers an editor request leaves the extension waiting for the rest of the process. CA/docs/rpc-extension-ui.md says the agent side auto-resolves dialogs on timeout, which holds for the other three only. Always answer editor, if only with { cancelled: true }.

## Shutdown and Rpc Client

Closing stdin is the orderly shutdown: Pi disposes the runtime, which emits session_shutdown, and exits 0 CA/src/modes/rpc/rpc-mode.ts:802. An extension that calls ctx.shutdown() sets a flag; Pi exits after the current command or after the next agent_settled CA/src/modes/rpc/rpc-mode.ts:745. Signals are covered in run modes (p. 127).

For TypeScript callers that still want a subprocess, the package exports RpcClient CA/src/modes/rpc/rpc-client.ts. It has one typed method per command (prompt, get State, fork, get Commands and so on) and three helpers built on agent_settled:

<table><tr><td>MEMBER</td><td>WHAT IT DOES</td></tr><tr><td>new RpcClient({ cli Path?, cwd?, env?, provider?, model?, args? })</td><td>options only; nothing runs</td></tr><tr><td>start()</td><td>spawns node--mode rpc ..., cli Path defaulting to dist/cli.js; waits 100 ms and throws if the child already exited</td></tr><tr><td>stop()</td><td>SIGTERM, then SIGKILL after 1,000 ms</td></tr><tr><td>onEvent(listener)</td><td>every record that is not a response to a pending request</td></tr><tr><td>waitForIdle(timeout = 60000)</td><td>resolves on the next agent_settled</td></tr><tr><td>collect Events(timeout = 60000)</td><td>every event up to the next agent_settled</td></tr><tr><td>promptAndWait(message, images?, timeout = 60000)</td><td>subscribes, then prompts, then collects</td></tr></table>

Every helper times out after 60 seconds by default. A long run needs an explicit timeout. From CA/src/modes/rpc/rpc-client.ts (RpcClientOptions, start, stop, onEvent, waitForIdle, collect Events, promptAndWait).

R P C C L I E N T C A N N O T A N S W E R A D I A L O G

RpcClient delivers extension_ui_request records to onEvent listeners as if they were events CA/src/modes/rpc/rpcclient.ts:523. It has no public method that writes an extension_ui_response; send is private CA/src/modes/rpc/rpcclient.ts:556. An extension that calls ctx.ui.editor(), or a confirm with no timeout, blocks the run until the client is stopped. With RpcClient, load only extensions whose dialogs set a timeout, or use the SDK. Also, cli Path is resolved against the child’s cwd and spawned with node, so the default works only inside a built checkout of the package.

## The SDK

The SDK is what the CLI runs on. createAgentSession() with no arguments discovers resources from the working directory and \~/.pi/agent, picks the settings default model or the first available one, and stores the session in a JSONL file CA/src/core/sdk.ts:181.

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

session.prompt() resolves after the accepted run finishes, retries included CA/docs/sdk.md §Prompting. CreateAgentSessionOptions has 14 fields, all optional CA/src/core/sdk.ts:42:

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

Without a session Manager the SDK writes a session file; pass SessionManager.inMemory() to avoid it. The result is { session, extensions Result, modelFallbackMessage? } CA/src/core/sdk.ts:99. Defaults from CA/src/core/sdk.ts:181 and CA/src/core/defaults.ts.

The CLI does not call createAgentSession directly. It uses three lower-level calls, all exported:

createAgentSessionServices(opts): builds the cwd-bound services { cwd, agent Dir, model Runtime, settings Manager, resource Loader, diagnostics }, reloads the resource loader and registers providers that extensions queued CA/src/core/agent-session-services.ts:135.

createAgentSessionFromServices({ services, session Manager, … }): calls createAgentSession with those services CA/src/core/agent-session-services.ts:214.

createAgentSessionRuntime(factory, { cwd, agent Dir, session Manager }): runs the factory once and keeps it. The returned AgentSessionRuntime has new Session, switch Session, fork, importFromJsonl, setRebindSession and dispose; each replacement tears the old session down with session_shutdown and builds a new one through the same factory CA/src/core/agent-session-runtime.ts:420.

Two steps are easy to miss. First, createAgentSession never emits session_start; the host must call session.bind Extensions({ … }), as every mode does CA/src/core/agent-session.ts:3244. The MCP extension connects its servers in that handler MCP (p. 144). Second, the built-in codemode, tool-search, mcp and lama.cpp extensions come from the CLI’s main() CA/src/main.ts:575, not from the SDK. An SDK host adds them with createCodemodeExtension(), createToolSearchExtension() and createMcpExtension() in DefaultResourceLoader’s extension Factories CA/examples/sdk/14-codemode-mcp.ts. Fourteen examples in CA/examples/sdk/, from 01-minimal.ts to 14-codemodemcp.ts, cover one feature each.

The JSDoc on createAgentSession shows createAgentSession({ continue Session: true }) CA/src/core/sdk.ts:163. CreateAgentSessionOptions has no continue Session field, and TypeScript rejects it. To continue the latest session, pass session Manager: SessionManager.continue Recent(cwd), which is what pi -c does CA/src/main.ts:433.

## Choosing an integration

<table><tr><td>CHOOSE</td><td>WHEN</td><td>YOU GIVE UP</td></tr><tr><td>SDK</td><td>Node or Bun TypeScript in the same process</td><td>process isolation</td></tr><tr><td>RPC</td><td>another language, an IDE, a sandboxed child process</td><td>direct object access; the 24 built-in commands</td></tr><tr><td>RpcClient</td><td>TypeScript that wants Pi as a subprocess</td><td>answering extension dialogs</td></tr><tr><td>JSON mode</td><td>one scripted run with a full event log</td><td>any input after start</td></tr><tr><td>print mode</td><td>one scripted run, final text only</td><td>events, tool output</td></tr></table>

Every row runs the same AgentSession. Only the transport and the UI context difer. From CA/docs/rpc.md (interface table) and the sections above.

W H A T T H I S M E A N S F O R Y O U

Read RPC stdout as bytes and split on LF only; never use readline.

Treat the prompt response as “accepted” and wait for agent_settled, unless disposition is handled.

Correlate responses by id; command handling is asynchronous.

Answer every editor request, and avoid RpcClient when extensions open dialogs.

In the SDK, pass SessionManager.inMemory() for throwaway sessions and call bind Extensions before the first prompt.

Sources: CA/src/modes/rpc/jsonl.ts (serializeJsonLine, attachJsonlLineReader). CA/src/modes/rpc/rpc-mode.ts (runRpcMode, createDialogPromise, createExtensionUIContext, handle Command, handleInputLine, shutdown). CA/src/modes/rpc/rpc-types.ts (RpcCommand, RpcResponse, RpcSessionState, RpcExtensionUIRequest, RpcExtensionUIResponse). CA/src/modes/rpc/rpc-client.ts (RpcClient). CA/src/core/agent-session.ts (PromptDisposition, bind Extensions, bash_execution_update). CA/src/core/sdk.ts (CreateAgentSessionOptions, createAgentSession); CA/src/core/agent-session-services.ts; CA/src/core/agent-sessionruntime.ts; CA/src/core/defaults.ts; CA/src/extensions/index.ts. CA/examples/sdk/01-minimal.ts, 14-codemode-mcp.ts. CA/docs/rpc.md, rpc-commands.md, rpc-extension-ui.md, sdk.md. research/capture/rpc-and-sdk-exchange.mjs, rpc-and-sdkchild.mjs; research/out/rpc-exchange.txt

![](images/9aca82bb7907f3ebe246df5a4be1c36ff03d8b6065ae9130972a3e22e4bb7a5f.jpg)
