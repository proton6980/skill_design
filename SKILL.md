---
name: skill-design
description: Use when you need to design a new sayu 沙箱 skill or redesign an existing one, resolving workflow, tool contracts, resource minimality, realistic deliverables, version plan, and confirmation boundary — then emit the real uploadable target skill package (manifest.json + SKILL.md [+ scripts/]).
---

> **Sandbox 环境说明 (sayu)**：本 skill 跑在离线 Python 3.11 沙箱，通过「运行脚本」(`platform_tools_run_script`) 工具执行——你传 `skill` 名 + `command`，工作目录已切到本 skill 根 `/workspace/skill_design/`，所有脚本用相对路径调用，**不要**用绝对路径。**可用**：纯标准库脚本，离线可跑，无需装包。**始终走本 skill 自带脚本**（`scaffold_example_package.py` 建包 / `validate_design_package.py` 校验设计记录 / `pack_skill_package.py` 打可上传 skill 包；`pack_package.py` 仅在需要给人下载整份设计记录时可选用），**不要**手拼 shell 逐个写文件（易在引号转义上炸）。中间产物可用 `/tmp/`。
>
> **读自带 references 用 `cat`，不要用 `read_document`**：本 skill 自带的契约/参考在 `/workspace/skill_design/references/`，用 `run_script` 的 `cat references/skill-design-proposal-contract.md` 读。`read_document` 只认用户上传目录，读自带文件**必被拒**（白烧一轮）。
>
> **禁止外部搜索（除非用户显式点名对标）**：这是内部设计任务。**禁止**调用 `platform_tools_duckduckgo` / `platform_tools_browser_read`——仅当用户消息里**显式**出现「对标 / 竞品调研 / 查一下市面上」等字样才检索；「做一个 X skill」这类需求默认**一律不检索**，对标状态填 `exempt_with_reason`（完全内部）。每次多余检索都白吃一轮 LLM 预算。
>
> **禁止枚举文件系统 / 反复探路**：本 skill 目录结构固定且已知——契约在 `references/skill-design-proposal-contract.md`，脚手架/校验/打包在 `scripts/`（`scaffold_example_package.py` / `validate_design_package.py` / `pack_skill_package.py` / `pack_package.py`）。**禁止**用 `ls` / `find` 反复确认环境（每次都白吃一轮预算）。默认直路径不含任何探查：`cat references/skill-design-proposal-contract.md`（一次）→ `scaffold` → 写各文件（含 `target/` 目标 skill）→ `validate` → 呈现确认门 → 用户确认后 `pack_skill_package.py` 打可上传 zip。
>
> **产物回流（关键，做错用户拿不到可用 skill）**：平台只回流 stdout 里的**单个真实文件**（`isfile` 为真）——打印目录不产卡。最终交付是**可上传的目标 skill zip**：用户在确认门选「打包为可上传的 skill 包」后，跑 `python scripts/pack_skill_package.py <包目录>`，它只打 `target/` 成**根级布局**（`manifest.json`/`SKILL.md`/`scripts/…` 在压缩包根）、固定时间戳的 zip，并把该 zip 的 `/uploads/...` 绝对路径打成 stdout 最后一行。这个 zip 即可直接被 sayu 上传/导入成 skill。沙箱**无 `zip` CLI**，只能用该脚本（stdlib zipfile）。

# Skill Design

Design a decision-complete skill and its realistic delivery preview, then emit the real uploadable target skill package. Research the real work first, keep the target skill minimal, and make every tool call auditable.

This skill **designs and packages** the target skill (its real `manifest.json` + `SKILL.md` [+ `scripts/`] under `target/`, zipped by `pack_skill_package.py` into an uploadable package). It **does not itself install, publish, register, or upload** that skill into sayu — 上传/建库/发布是带外步骤（平台在「挂载」时把这个 zip 导入为用户私有 skill）。

## Required Boundaries

- Read `references/skill-design-proposal-contract.md` before writing a package — via `run_script` 的 `cat references/skill-design-proposal-contract.md`（**不要** `read_document`）。
- Save packages only under `/uploads/skill-design/<target-skill-family>/<target-skill-name>/<YYYY-MM-DD>-<case-slug>/`.
- `target/` 存**可上传的目标 skill 真实文件**（scaffold 已种合法 `target/manifest.json` 骨架）；`proposal/`、`examples/`、`previews/`、`working/` 是设计记录，**不进**可上传 zip。
- Use the same fixed package for `全新 skill` and `重新设计已有 skill`; a redesign is not a change log.
- Do not scaffold a full package until the use case, professional context, audience, deliverables, location, version, and preservation policy are clear.
- If research status is `blocked`, stop before scaffolding a full package and report the blocker.

## Ordered Workflow

1. **Ground and frame.** Confirm goal, trigger boundaries, inputs, final users, formats, location, version, and preservation from the user message, supplied materials, and active invocation state. **无需 `ls` / `find` 枚举文件系统**——目录结构已知。
2. **Research before designing.** Examine user/local materials, the bundled contract, and existing sayu skills first. External web research (`platform_tools_duckduckgo`) is **default-skipped** for these internal tasks — use `对标状态：exempt_with_reason`（完全内部）unless the user explicitly asks for benchmarking or the target domain genuinely needs public workflow evidence, then use `completed`. Convert observations into transferable mechanisms with applicability conditions.
3. **Choose mode and version.** For a redesign, inspect the complete current skill, preserve it, and propose the next two-part version. Put current state and `保留 / 调整 / 删除` decisions in the full proposal.
4. **Minimize the target and author it.** The uploadable target consists of one substantive `target/SKILL.md` plus the sayu-required `target/manifest.json`（已种合法骨架，按设计细化 name/description/dependencies/network_policy/secrets/deliverable，别动 kind/entry_main）。Add `target/scripts/`, `target/references/`, `target/assets/`, or `target/requirements.txt` only when the minimality audit identifies its unique consumer and why it cannot be inlined or merged.
5. **Decide the example strategy.** Choose `none`, `inline`, or `separate_resource`. Design-record files under `examples/` do not imply a target-skill example resource.
6. **Specify the workflow and tools.** Give every step inputs, action, stage output, validation, and failure handling in `target/SKILL.md`. Use `无` for judgment-only steps. External tools the target skill uses are declared as `platform_tools_*` slugs in `target/manifest.json` `dependencies`; each workflow row names the callable with an explicit `mode=` and satisfies the sandbox-script/artifact, web/browser, and media contracts in the reference.
7. **Scaffold and write.** After research passes, run `python scripts/scaffold_example_package.py` with target extensions（可带 `--target-slug` / `--target-name`）。Fill the design record (`proposal/`, realistic `examples/`) **and** the real `target/` skill files from a domain-relevant case.
8. **Validate.** Inspect rendered or reopened artifacts, replace manifest placeholders, and run `python scripts/validate_design_package.py <package>`（校验设计记录）。目标 skill 由第 10 步 `pack_skill_package.py` 硬校验（合法 manifest / entry_main 在包内 / SKILL.md 非空 / 无占位符）。
9. **Present the confirmation gate.** Show `Skill 概述`, `工作流步骤与工具`, `最终交付示例文件`, and `确认门` in that order. Offer only `修改`, `停止`, or `打包为可上传的 skill 包`, then stop.
10. **Package on confirmation.** 用户选「打包为可上传的 skill 包」后，run `python scripts/pack_skill_package.py <package>` —— 它只打 `target/` 成根级、固定时间戳的**可上传 skill zip**，打印它这**一个** `/uploads/...zip` 路径（这就是可直接使用的 skill 包）。若还需给人一份设计记录下载，可**先**跑 `pack_package.py`、**再**跑 `pack_skill_package.py`（保证 skill zip 路径是最后一行、被回流）。

## Contract Gate

The reference is the single source of truth for exact Markdown table schemas, research statuses, redesign fields, package contents, target manifest and sample-case fields, tool contracts, validation rules, and final-response structure. Do not recreate those field inventories here.
