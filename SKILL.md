---
name: skill-design
description: Use when you need to design a new sayu 沙箱 skill or redesign an existing one before creation, especially when the workflow, tool contracts, resource minimality, realistic deliverables, version plan, or confirmation boundary must be resolved first.
---

> **Sandbox 环境说明 (sayu)**：本 skill 跑在离线 Python 3.11 沙箱，通过「运行脚本」(`platform_tools_run_script`) 工具执行——你传 `skill` 名 + `command`，工作目录已切到本 skill 根 `/workspace/skill_design/`，所有脚本用相对路径调用（`python scripts/scaffold_example_package.py …`、`python scripts/validate_design_package.py …`），**不要**用绝对路径。**可用**：纯标准库脚本，离线可跑，无需装包。**产物回流**：设计方案包写到 `/uploads/skill-design/…` 下，并在 stdout 打印其路径（脚本已打印 `package_path`），否则用户拿不到文件。中间产物可用 `/tmp/`。

# Skill Design

Design a decision-complete skill proposal and realistic delivery preview before creation. Research the real work first, keep the proposed target skill minimal, and make every tool call auditable.

This skill stops at design. It never creates, updates, installs, publishes, or uploads the target skill.

## Required Boundaries

- Read `references/skill-design-proposal-contract.md` before writing a package.
- Save design packages only under `/uploads/skill-design/<target-skill-family>/<target-skill-name>/<YYYY-MM-DD>-<case-slug>/`.
- Use the same fixed package for `全新 skill` and `重新设计已有 skill`; a redesign is not a change log.
- Do not scaffold a full package until the use case, professional context, audience, deliverables, location, version, and preservation policy are clear.
- If research status is `blocked`, stop before scaffolding a full package and report the blocker.

## Ordered Workflow

1. **Ground and frame.** Inspect project rules, supplied materials, existing versions and outputs, and active invocation state. Confirm goal, trigger boundaries, inputs, final users, formats, location, version, and preservation.
2. **Research before designing.** Examine, in order: user/local materials and real successes or failures; public industry standards and workflows; existing Agent, Skill, and tool implementations. Convert observations into transferable mechanisms with applicability conditions. Public research is required by default; use only the contract-defined `completed`, `exempt_with_reason`, or `blocked` status.
3. **Choose mode and version.** For a redesign, inspect the complete current skill, preserve it, and propose the next two-part version. Put current state and `保留 / 调整 / 删除` decisions in the full proposal.
4. **Minimize the target.** Start from one substantive `SKILL.md` plus the sayu-required `manifest.json`. Add a target `scripts/`, `references/`, `assets/`, `requirements.txt`, field group, or output format only when the minimality audit identifies its unique consumer and why it cannot be inlined or merged.
5. **Decide the example strategy.** Choose `none`, `inline`, or `separate_resource`. Package files under `examples/` do not imply a target-skill example resource.
6. **Specify the workflow and tools.** Give every step inputs, action, stage output, validation, and failure handling. Use `无` for judgment-only steps. External tools the target skill uses are declared as `platform_tools_*` slugs in `manifest.dependencies`; each workflow row names the callable with an explicit `mode=` and satisfies the sandbox-script/artifact, web/browser, and media contracts in the reference.
7. **Scaffold and write.** After research passes, run `python scripts/scaffold_example_package.py` with target extensions. Fill the complete package and realistic 1:1 examples from a domain-relevant case.
8. **Validate.** Inspect rendered or reopened artifacts, replace manifest placeholders, and run `python scripts/validate_design_package.py <package>`. For a response draft, also pass `--final-response <path>`.
9. **Present the confirmation gate.** Show `Skill 概述`, `工作流步骤与工具`, `最终交付示例文件`, and `确认门` in that order. Offer only `修改`, `停止`, or `打包为可上传的 skill 包`, then stop.

## Contract Gate

The reference is the single source of truth for exact Markdown table schemas, research statuses, redesign fields, package contents, manifest and sample-case fields, tool contracts, validation rules, and final-response structure. Do not recreate those field inventories here.
