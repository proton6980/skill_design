# Skill Design Proposal Contract

Use this contract whenever `skill-design` prepares a creation-before-confirmation package. It is the single detailed contract for proposal schemas, research evidence, target-skill minimality, example strategy, tool calls, realistic preview artifacts, validation, and the final confirmation response.

The workflow designs a target **sayu 沙箱 skill**; it does not create, update, install, publish, or upload that target skill.

## sayu 沙箱目标约束

Every target skill designed here is a sayu 沙箱 skill — a zip package (`manifest.json` + `SKILL.md` + `scripts/` [+ `references/`/`assets/`/`requirements.txt`]) uploaded to sayu, materialized into an offline Docker sandbox at `/workspace/<slug>/`, and driven by the global `platform_tools_run_script` tool. Design against these hard constraints:

- **离线默认**：`manifest.network_policy` 默认 `none`（容器无外网）。仅当目标 skill 必须联网或需 pip 装包时才用 `open`，并同时提供 `requirements.txt`；`bridge_only` 与 `none` 对沙箱等价（都断外网）。
- **只读根 + 三个可写目录**：容器根文件系统只读，只有 `/workspace/<slug>/`（skill 自身）、`/uploads/`（产物回流）、`/tmp/`（临时）可写。
- **产物回流约定（单文件）**：`platform_tools_run_script` 只从 stdout 抓**最后一个真实存在的单个文件**（`isfile` 为真）的 `/uploads/...` 路径生成文件卡——**目录不产卡**。因此多文件产物（如本 skill 的设计方案包）**必须先打成一个 zip**（用 `scripts/pack_package.py`，沙箱无 `zip` CLI，脚本走 stdlib zipfile），再打印该 zip 的 `/uploads/...` 绝对路径。设计目标 skill 时同理：若目标 skill 交付多文件，其收尾脚本也应 zip 成单文件回流。中间文件用 `/tmp/`。
- **相对脚本调用**：`run_script` 的工作目录已在 `/workspace/<slug>/`，脚本一律相对路径调用（`python scripts/x.py`）。
- **基础镜像预装库**（免在 `dependencies`/`requirements.txt` 里声明）：Python 3.11 + `python-docx`/`openpyxl`/`python-pptx`/`pypdf`/`pymupdf`/`Pillow`/`pandas`/`requests`/`lxml`/`beautifulsoup4`/`markdown`/`pdfplumber`/`reportlab`/`pdf2image`/`defusedxml`/`pypdfium2`，系统 `poppler-utils`(`pdftoppm`)/`qpdf`/`curl`。只有超出此清单的库才需 `requirements.txt` + `network_policy=open`。
- **secret 声明**：目标 skill 需要的密钥在 `manifest.secrets[]` 里声明（`{key,label,required,doc}`，`key` 匹配 `^[A-Z_][A-Z0-9_]*$`）；值由平台密钥池或按挂载配置注入为容器 env，不写进包。
- **子工具声明**：目标 skill 调用的 sayu 内建工具在 `manifest.dependencies` 里以 `platform_tools_*` slug 声明，运行时渲染成该 skill 的「可用工具」。

## Research Before Workflow Design

Research in this order:

1. User-provided and local materials, including real successful outputs, failed outputs, current skill files, project rules, fixtures, and validation evidence.
2. Public industry standards and real professional workflows.
3. Existing Agent, Skill, and tool implementations.
4. Transfer observations into mechanisms, always stating the conditions under which each mechanism applies and the concrete effect on the target skill.

Default to `exempt_with_reason`（理由：sayu 沙箱 skill 设计是完全内部的任务，本地契约与既有 skill 已是充分证据）。只有当用户明确要求对标，或目标 skill 的专业领域确实需要公开工作流证据时，才升级为 `completed` 做外部检索——不要为一个内部设计任务默认烧一轮 `platform_tools_duckduckgo`。Record exactly one status under `## 行业与实现对标`:

- `对标状态：completed`: requires the exact benchmark table below, including at least one `行业工作流` row and one `Agent/Skill 实现` row. Both required rows must cite an `http://` or `https://` source.
- `对标状态：exempt_with_reason`: allowed only when the user forbids web access, the work is fully internal, or local evidence is already sufficient. It requires substantive `豁免理由：` and `本地证据：` entries.
- `对标状态：blocked`: use when required evidence cannot be obtained. Stop and report the blocker before scaffolding or presenting a full package. A full validator run rejects this status.

The completed benchmark table has exactly these columns:

| 层次 | 来源 | 观察事实 | 可迁移机制（含适用前提） | 对目标 skill 的具体影响 |
|---|---|---|---|---|
| 行业工作流 | https://example.com/industry-source | 可核查的流程事实 | 可迁移机制及其适用前提 | 对步骤、输入、输出或验证的明确改变 |
| Agent/Skill 实现 | https://example.com/implementation-source | 可核查的实现事实 | 可迁移机制及其适用前提 | 对资源、工具契约或失败处理的明确改变 |

Do not turn benchmark observations into imitation instructions. The proposal must identify a mechanism and its applicability condition.

## Fixed Design Package

Use the same package for `全新 skill` and `重新设计已有 skill`:

`/uploads/skill-design/示例/<target-skill-family>/<target-skill-name>/<YYYY-MM-DD>-<case-slug>/`

Required contents:

**设计记录（不进可上传 zip）**
- `proposal/skill-overview.md`
- `proposal/workflow-tool-map.md`
- `proposal/deliverable-preview-index.md`
- `proposal/confirmation-questions.md`
- `examples/` containing realistic files in every target deliverable format
- `previews/` containing rendered previews, screenshots, exported review files, or inspection notes
- `working/sample-case.json`
- `working/generation-notes.md`
- `manifest.json`（设计包自身元数据：`target_skill_family`/`expected_files`/`deliverable_types` 等，**不是**目标 skill 的 manifest）

**★可上传的目标 skill（`target/` —— `pack_skill_package.py` 只打这一层）**
- `target/manifest.json`：目标 skill 的**合法 sayu skill manifest**（scaffold 已种合法骨架）。必填 `slug`(`^[a-z][a-z0-9_-]{1,62}$`)/`kind=skill`/`name`/`version`/`runtime_type`/`entry_main=SKILL.md`；按设计细化 `description`/`dependencies`(`platform_tools_*` slug)/`network_policy`/`secrets[]`/资源配额。**`runtime_type` 只能是 `python`/`node`/`shell`/`custom`（沙箱运行时，不是 skill 的性质）——提示词 skill（纯 `SKILL.md`）保持 `python`+`entry_main=SKILL.md`，绝不要写 `prompt`/`md` 等非法值（sayu 上传校验会拒）。** 见 `## 设计包 manifest.json` 下方对目标 manifest 的字段约束。
- `target/SKILL.md`：目标 skill 的真实工作流入口（注入运行时 system prompt），实质内容、无占位符。
- `target/scripts/…`、`target/references/…`、`target/assets/…`、`target/requirements.txt`：**仅当**最小化审计判定目标 skill 确需时才加（默认只有 `SKILL.md` + `manifest.json`）。

The design-record folders are not target-skill resources. In particular, files under the package's `examples/` never imply that the target skill should bundle example files. Only `target/` contents are packed into the uploadable skill zip (root-level layout, fixed timestamp).

After the research gate passes, scaffold with:

```bash
python scripts/scaffold_example_package.py <target-skill-family> <target-skill-name> "<case-name>" --deliverables docx,xlsx,html [--target-slug <slug>] [--target-name "<name>"]
```

Adjust `--deliverables` to the proposed target outputs. Replace every manifest `<role>.<ext>` placeholder before full validation. Fill `target/SKILL.md` and finalize `target/manifest.json` before packing.

## `proposal/skill-overview.md`

Use this heading order:

1. `# <target skill name> 创建前设计`
2. `## Skill 概述`
3. `## 行业与实现对标`
4. `## 用户与触发边界`
5. `## 输入维度`
6. `## 输出维度`
7. `## 保存位置与版本策略`
8. `## 依赖工具与资源`
9. `## 目标 Skill 最小化审计`
10. `## 示例策略`
11. `## 风险与待确认`

### Skill overview fields

Include:

- `Design type`: `全新 skill` or `重新设计已有 skill`
- `Skill goal`
- `需求理解摘要`
- `专业领域`
- `目标使用场景`
- `交付物使用者`
- `示例案例选择理由`
- Primary users
- Trigger requests
- Non-trigger requests
- Required inputs
- Optional inputs
- Final deliverables
- Proposed category folder
- Proposed family folder
- Proposed version folder
- Semantic version
- Preservation policy
- Required tools or skills
- Required scripts, references, and assets for the future target skill
- Risks
- Confirmation questions

The demand-understanding entries must be specific enough to prove that the simulated case, professional terminology, output density, and decisions match the user's requested domain. Do not substitute a generic marketing, review, or operations case for another professional domain.

### Redesign fields

For `重新设计已有 skill`, also include under `## Skill 概述`:

- `当前 skill 路径`
- `当前 skill 名称`
- `当前 active invocation 路径`
- `当前状态摘要`
- `主要缺口或失败模式`

Include under `## 保存位置与版本策略`:

- `当前版本`: current `manifest.version` and case folder name
- `建议新版本`: proposed `manifest.version` and case folder name
- `版本迭代理由`
- `旧版本保留路径`: design-package/preview 归档路径 under `/uploads/skill-design/...`
- `新版本保存路径`: 新版本 design-package 保存路径 under `/uploads/skill-design/...`
- `当前上线版本`: sayu 当前发布指向的版本（`current_version_id` 对应的 `manifest.version`），如有
- `建议上线版本`: 后续创建流程发布后应指向的版本

Default to the next version slot unless the user explicitly chooses another valid version. Preserve the old version (sayu 版本不可变，旧版本自动留存). Put `保留 / 调整 / 删除` decisions inside the user boundary, input, output, dependency/resource, and relevant workflow content; do not replace the proposal with a diff.

## Target Skill Minimality

The default callable target consists of one substantive `SKILL.md` plus the sayu-required `manifest.json`. Do not default to target `references/`, `scripts/`, `assets/`, `requirements.txt`, example files, or empty directories.

Use exactly this table under `## 目标 Skill 最小化审计`:

| 候选项 | 类型（文件/字段组/格式） | 唯一消费者或用途 | 不可内联或合并原因 | 决策（保留/合并/删除） |
|---|---|---|---|---|
| SKILL.md | 文件 | sayu 运行时注入系统提示词的唯一工作流入口 | 必须作为发现与执行入口，不能并入元数据 | 保留 |
| manifest.json | 文件 | sayu 上传校验与运行时元数据（slug/kind/entry_main/runtime_type/network_policy/dependencies/secrets） | 机器读取位置固定，不能并入 SKILL.md | 保留 |

Audit rules:

- Add one row for every planned target `scripts/...`, `references/...`, `assets/...`, or `requirements.txt` path named in the overview. `scripts/` is a first-class sandbox resource (the executable logic run via `platform_tools_run_script`); `requirements.txt` is only justified when a needed library is outside the base image and `network_policy=open`.
- Add one row for every planned `字段组：...` declaration.
- Add one `.<ext>` format row for every target deliverable type declared in `manifest.json`, including secondary formats.
- A retained row needs a substantive unique consumer or use and a substantive reason it cannot be inlined or merged.
- `决策` is exactly `保留`, `合并`, or `删除`. A merged or deleted candidate must not remain declared as a planned target resource.
- Do not count this design package's `proposal/`, `examples/`, `previews/`, `working/`, or `manifest.json` support paths as future target resources.

## Example Strategy

An example decision is mandatory; a target example file is not. Use exactly one row under `## 示例策略` with exactly these columns:

| 决策 | 需要解决的具体歧义 | 示例形式与位置 | 使用或加载条件 | 独立文件必要性 |
|---|---|---|---|---|
| none | 无 | 无 | 不适用 | 不适用 |

Allowed decisions:

- `none`: use when the target workflow has no material ambiguity that an example would resolve.
- `inline`: put the example in the target `SKILL.md`. Name the ambiguity and the inline location; do not declare a separate resource.
- `separate_resource`: name the ambiguity, a real target resource path, the observable condition that loads it, and a substantive reason it cannot be inline. The resource also needs a retained minimality row.

The design package may still contain realistic deliverables under `examples/` for user review when the target strategy is `none` or `inline`.

## `proposal/workflow-tool-map.md`

Use exactly this table:

| 步骤 | 输入/前置条件 | 动作 | 工具与调用模式 | 阶段产物 | 验证 | 缺失/失败处理 |
|---|---|---|---|---|---|---|

Rules for every row:

- Include the initial need and professional-context analysis before workflow or example selection.
- Name every step before, during, and after execution.
- Inputs, action, stage output, validation, and failure handling must be substantive.
- A judgment-only row uses `无` in `工具与调用模式`.
- Every external-tool row names the callable and includes `mode=<value>`. Do not hide tools in prose.
- For redesigns, the table is the complete redesigned workflow and uses `保留 / 调整 / 删除` where current behavior changes.

### sayu 工具面

The target skill's own logic runs as sandbox scripts invoked through `platform_tools_run_script`. Any *other* sayu builtin tool the target skill leans on must be declared in `manifest.dependencies` (as a `platform_tools_*` slug) and referenced in the workflow row's `工具与调用模式` cell with an explicit `mode=`. Available builtin tools:

- `platform_tools_run_script` — 在沙箱里跑本 skill 的脚本（`skill` + `command`）。目标 skill 的主要执行手段。
- `platform_tools_generate_media` — 由提示词生成图片/视频。
- `platform_tools_duckduckgo` — 联网搜索并抓取结果正文。
- `platform_tools_browser_read` — 读取给定 URL 的正文。
- `platform_tools_browser_use` — 操作真实浏览器（导航/点击/输入/截图）。
- `platform_tools_ocr_rapidocr_onnxruntime` / `platform_tools_ocr_pdf` — 图片 / 扫描版 PDF 文字识别。
- `platform_tools_read_document` — 抽取 .docx/.pdf/.xlsx/.pptx/纯文本正文（也用于产物回读校验）。
- `platform_tools_transcribe_audio` — 语音转文字。
- `platform_tools_scheduled_task` — 会话级定时任务。

`platform_tools_duckduckgo`/`platform_tools_browser_*` 及联网型 `platform_tools_generate_media` 需要目标 skill 的 `network_policy=open`；离线 skill 只用本地脚本与随包资源。

### Media-generation rows

sayu 的图片/视频生成用 `platform_tools_generate_media`（需 `network_policy=open`）。它不区分 `text_to_image`/`reference_guided_generation`/`image_edit` 等模式——那是别的平台的契约，不要照搬。

- `工具与调用模式`: `platform_tools_generate_media mode=<image|video>`（`mode` 标明产物类型）。
- `动作`: 说明提示词来源与关键约束；若以参考图为输入，在 `输入/前置条件` 声明 `role=... source=... required=yes|no`。
- `验证`: 必须含目视检查（`view_image` 或明确的视觉核验），生成结果不能只凭文字断言。
- `缺失/失败处理`: 缺输入时 `ask` 或 `stop`；当输入承载产品、人物、角色、品牌、标识等身份关键内容时，不得静默降级，必须索要或停止。

### Web and browser rows

联网检索/浏览用 `platform_tools_duckduckgo`、`platform_tools_browser_read`、`platform_tools_browser_use`（均需 `network_policy=open`）。Name the access mode and make the research boundary auditable:

- `工具与调用模式`: callable plus `mode=...`
- inputs or action: `query_scope=...` or `page_scope=...`
- stage output or validation: `evidence=...`
- failure handling: `fallback=...`

Use primary sources for technical claims and record the exact page or evidence needed. A fallback may narrow scope, switch to local evidence, ask the user, or stop; it must not fabricate a result.

### Document, spreadsheet, presentation, and PDF rows

沙箱 skill 的文档/表格/演示/PDF 产物由脚本经 `platform_tools_run_script` 生成，写到 `/uploads/` 并打印路径回流。For artifact builders, name:

- `source_of_truth=...` in inputs or action
- `builder=...` in the tool or action — 具体的沙箱脚本（如 `builder=scripts/build_report.py`）
- `final_artifact=/uploads/...` in the stage output — 落在 `/uploads/` 下的绝对路径
- a render or reopen check in validation — 用 `platform_tools_read_document` 回读，或脚本内重新解析（`render`/`reopen`/`回读`）
- `return_to=step-<n>` in failure handling

The return step must lead back to the content or build stage that can correct the observed defect.

## `proposal/deliverable-preview-index.md`

Use this order:

1. `# 交付结果预览`
2. A paragraph naming the simulated case and why it matches the request
3. This exact table:

| 交付物 | 真实示例文件 | 预览/检查文件 | 格式说明 | 模拟内容摘要 |
|---|---|---|---|---|

Rules:

- Every target deliverable type has a real same-extension file in `examples/`.
- Every row explains the target use case, professional decision, or execution action served by the example.
- Hard-to-inspect files have a rendered preview, screenshot, export, or inspection note in `previews/`.
- Examples are filled with realistic case data, terminology, structure, and content density.
- A redesign previews the redesigned final deliverables, including a fresh example of any preserved format.
- Never list proposal files, `manifest.json`, or `working/` files as target deliverables.

## `proposal/confirmation-questions.md`

Use this order:

1. `# 创建前确认`
2. `## 已确认`
3. `## 仍需用户决定`
4. `## 下一步选项`

> **说明**：本文件是**设计记录归档**（记录已确认 / 待决 / 历史选项），**不再是聊天流程的停止点**——`validate` 通过后**直接打包**。下方 `下一步选项` 三项为固定归档字段（校验器要求原样保留），运行时**不据此停下等确认**。

The next-step options are exactly:

- `修改`
- `停止`
- `打包为可上传的 skill 包`

`validate` 通过后**直接** run `python scripts/pack_skill_package.py <package>`（无需用户在此确认）—— 它只打 `target/`（目标 skill 真实文件）成**根级布局、固定时间戳**的 zip，打印其 `/uploads/...zip` 路径回流。**这个 zip 即可直接被 sayu 上传/导入成 skill**（根级 `manifest.json` + `SKILL.md`，对齐 `ManifestParser` / `CapabilityZipExtractor` 的期望）。

本 skill 到「产出可上传 zip」为止，**不自行注册/上传/发布**目标 skill —— 那是带外步骤：平台在开发者「挂载」时把该 zip 导入为**用户私有 skill**（owner-scoped，`test-run` 通过后 `private_ready`），或经 `POST /admin/skills/upload` / 开发者门户 / GitHub 导入。`secrets[]` 由平台密钥池或按挂载配置注入，不写进包。

## 设计包 `manifest.json`

这是**设计方案包自身**的描述文件（由 `scaffold_example_package.py` 生成），与目标 sayu skill 的 `manifest.json` 不是一回事，不要混淆。Required keys:

- `manifest_version`
- `created_at`
- `target_skill_family`
- `target_skill_name`
- `case_name`
- `case_slug`
- `package_path`
- `directories`
- `deliverable_types`
- `expected_files`
- `validation_notes`

Use relative paths inside `directories` and `expected_files` when possible. Keep `package_path` absolute. `expected_files.examples` must point to real files before full validation.

## `working/sample-case.json`

Required non-empty keys:

- `user_need`
- `domain`
- `professional_context`
- `deliverable_use_case`
- `example_relevance_rationale`

Values must explain why the case was chosen and how it represents the requested skill. Use concrete strings or structured objects, not placeholders.

## `working/generation-notes.md`

Record source materials, research access, builders, render/reopen checks, validator commands, limitations, and any approved research exemption. Do not use these notes as a substitute for required proposal fields.

## Validation

For a fresh scaffold only:

```bash
python scripts/validate_design_package.py <package-path> --scaffold-only
```

For a complete package:

```bash
python scripts/validate_design_package.py <package-path>
```

For a complete package plus a drafted response:

```bash
python scripts/validate_design_package.py <package-path> --final-response <response.md>
```

Before presentation, also inspect every real artifact in its appropriate rendered or reopened form. A validator does not replace visual or content review.

## Final Chat Response Contract

The final user-facing response uses these headings in order:

1. `Skill 概述`
2. `工作流步骤与工具`
3. `最终交付示例文件`
4. `产物与下一步`

Rules:

- Summarize the target design, not the design work log.
- Show the complete proposed execution flow and concrete tool modes, including initial need analysis.
- Under `最终交付示例文件`, link only real target deliverables under `examples/`, state their formats, and explain their relevance. Label proposal links separately as design-package references.
- Under `产物与下一步`, 说明可上传 skill zip **已打包**（末行是它的 `/uploads/...zip` 路径），并说明用户在 sayu 端点「挂载」时会把它导入为用户私有 skill。
- **不设确认门、不停下等确认**——`validate` 通过即打包，本轮直接给出结果与 zip 路径。

## Self-Check

- No target skill was created, uploaded, or published.
- No examples were saved inside a callable skill package.
- Research follows the required order and has a valid non-blocked status for a full package.
- A completed benchmark contains both required sourced layers; an exemption contains both reason and local evidence.
- The fixed proposal, example, preview, working, and manifest package is complete.
- The overview contains demand context, target boundaries, save/version decisions, minimality audit, and example strategy.
- Every planned target resource, field group, and deliverable format has a minimality row.
- Every external tool row has its mode and tool-specific contract.
- Every declared deliverable has a realistic same-extension example and review evidence.
- Redesigns contain current state, version and 上线版本 fields, preservation, and `保留 / 调整 / 删除` decisions.
- No unfinished markers, placeholders, stale skill names, or generic unrelated cases remain.
- The final response follows the four-heading order (末节 `产物与下一步`) and includes the produced uploadable zip path; it does not present a chat gate.
