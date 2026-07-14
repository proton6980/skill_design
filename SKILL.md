---
name: skill-design
description: Use when you need to design a new sayu 沙箱 skill or redesign an existing one before creation, especially when the workflow, tool contracts, resource minimality, realistic deliverables, version plan, or confirmation boundary must be resolved first.
---

> **Sandbox 环境说明 (sayu)**：本 skill 跑在离线 Python 3.11 沙箱，通过「运行脚本」(`platform_tools_run_script`) 工具执行——你传 `skill` 名 + `command`，工作目录已切到本 skill 根 `/workspace/skill_design/`，所有脚本用相对路径调用，**不要**用绝对路径。**可用**：纯标准库脚本，离线可跑，无需装包。**始终走本 skill 自带脚本**（`scaffold_example_package.py` / `validate_design_package.py` / `pack_package.py`）生成、校验、打包，**不要**手拼 shell 逐个写文件（易在引号转义上炸）。中间产物可用 `/tmp/`。
>
> **读自带 references 用 `cat`，不要用 `read_document`**：本 skill 自带的契约/参考在 `/workspace/skill_design/references/`，用 `run_script` 的 `cat references/skill-design-proposal-contract.md` 读。`read_document` 只认用户上传目录，读自带文件**必被拒**（白烧一轮）。
>
> **禁止外部搜索（除非用户显式点名对标）**：这是内部设计任务。**禁止**调用 `platform_tools_duckduckgo` / `platform_tools_browser_read`——仅当用户消息里**显式**出现「对标 / 竞品调研 / 查一下市面上」等字样才检索；「做一个 X skill」这类需求默认**一律不检索**，对标状态填 `exempt_with_reason`（完全内部）。每次多余检索都白吃一轮 LLM 预算。
>
> **禁止枚举文件系统 / 反复探路**：本 skill 目录结构固定且已知——契约在 `references/skill-design-proposal-contract.md`，脚手架 / 校验 / 打包三件套在 `scripts/`（`scaffold_example_package.py` / `validate_design_package.py` / `pack_package.py`）。**禁止**用 `ls` / `find` 反复确认环境（每次都白吃一轮预算）。默认直路径不含任何探查：`cat references/skill-design-proposal-contract.md`（一次）→ `scaffold` → 写各文件内容 → `validate` → `pack` 打 zip。
>
> **产物回流（关键，做错用户一个文件都收不到）**：平台只回流 stdout 里的**单个真实文件**（`isfile` 为真）——**打印目录不产卡**，`package_path` 目录路径没用。设计方案包是多文件目录，收尾**必须**用 `python scripts/pack_package.py <包目录>` 打成一个 zip，并让 stdout 的最后一行是那个 **zip 的 `/uploads/...` 绝对路径**（脚本已只打印它）。沙箱**无 `zip` CLI**，只能用该脚本（stdlib zipfile）。一个 zip = 一张文件卡，用户下载解压即整包。

# Skill Design

Design a decision-complete skill proposal and realistic delivery preview before creation. Research the real work first, keep the proposed target skill minimal, and make every tool call auditable.

This skill stops at design. It never creates, updates, installs, publishes, or uploads the target skill.

## Required Boundaries

- Read `references/skill-design-proposal-contract.md` before writing a package — via `run_script` 的 `cat references/skill-design-proposal-contract.md`（**不要** `read_document`）。
- Save design packages only under `/uploads/skill-design/<target-skill-family>/<target-skill-name>/<YYYY-MM-DD>-<case-slug>/`.
- Use the same fixed package for `全新 skill` and `重新设计已有 skill`; a redesign is not a change log.
- Do not scaffold a full package until the use case, professional context, audience, deliverables, location, version, and preservation policy are clear.
- If research status is `blocked`, stop before scaffolding a full package and report the blocker.

## Ordered Workflow

1. **Ground and frame.** Confirm goal, trigger boundaries, inputs, final users, formats, location, version, and preservation from the user message, supplied materials, and active invocation state. **无需 `ls` / `find` 枚举文件系统**——目录结构已知。
2. **Research before designing.** Examine user/local materials, the bundled contract, and existing sayu skills first. External web research (`platform_tools_duckduckgo`) is **default-skipped** for these internal tasks — use `对标状态：exempt_with_reason`（完全内部）unless the user explicitly asks for benchmarking or the target domain genuinely needs public workflow evidence, then use `completed`. Convert observations into transferable mechanisms with applicability conditions.
3. **Choose mode and version.** For a redesign, inspect the complete current skill, preserve it, and propose the next two-part version. Put current state and `保留 / 调整 / 删除` decisions in the full proposal.
4. **Minimize the target.** Start from one substantive `SKILL.md` plus the sayu-required `manifest.json`. Add a target `scripts/`, `references/`, `assets/`, `requirements.txt`, field group, or output format only when the minimality audit identifies its unique consumer and why it cannot be inlined or merged.
5. **Decide the example strategy.** Choose `none`, `inline`, or `separate_resource`. Package files under `examples/` do not imply a target-skill example resource.
6. **Specify the workflow and tools.** Give every step inputs, action, stage output, validation, and failure handling. Use `无` for judgment-only steps. External tools the target skill uses are declared as `platform_tools_*` slugs in `manifest.dependencies`; each workflow row names the callable with an explicit `mode=` and satisfies the sandbox-script/artifact, web/browser, and media contracts in the reference.
7. **Scaffold and write.** After research passes, run `python scripts/scaffold_example_package.py` with target extensions. Fill the complete package and realistic 1:1 examples from a domain-relevant case.
8. **Validate.** Inspect rendered or reopened artifacts, replace manifest placeholders, and run `python scripts/validate_design_package.py <package>`. For a response draft, also pass `--final-response <path>`.
9. **Package for delivery.** Run `python scripts/pack_package.py <package>` to zip the whole design package into one file, and print the single `/uploads/...zip` path it emits — this is what the platform reflows into a downloadable file card. Do **not** print the package directory path; a directory does not reflow.
10. **Present the confirmation gate.** Show `Skill 概述`, `工作流步骤与工具`, `最终交付示例文件`, and `确认门` in that order. Offer only `修改`, `停止`, or `打包为可上传的 skill 包`, then stop.

## Contract Gate

The reference is the single source of truth for exact Markdown table schemas, research statuses, redesign fields, package contents, manifest and sample-case fields, tool contracts, validation rules, and final-response structure. Do not recreate those field inventories here.
