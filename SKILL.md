---
name: skill-design
description: Use when you need to design and package a new sayu 沙箱 skill (or redesign an existing one). Author a minimal, real, uploadable target skill (manifest.json + SKILL.md [+ scripts/]) and pack it into an uploadable zip — no design-record ceremony, no fabricated deliverables.
---

> **Sandbox 环境说明 (sayu)**：本 skill 跑在离线 Python 3.11 沙箱，通过「运行脚本」(`platform_tools_run_script`) 执行——传 `skill` 名 + `command`，工作目录已在本 skill 根 `/workspace/skill_design/`，脚本一律相对路径调用（`python scripts/x.py`），**不要**绝对路径。
>
> **只走本 skill 自带的两个脚本**：`init_skill_package.py`（建目标 skill 工作目录 + 合法 manifest 骨架）、`pack_skill_package.py`（把 `target/` 打成可上传 zip，内含合法性硬校验）。**不要** `ls`/`find` 探路（目录固定），**不要** `read_document` 读自带文件，**不要** `platform_tools_duckduckgo`/`browser_read` 搜索（内部设计任务，除非用户显式点名对标）。每多一轮都白吃预算。
>
> **产物回流（关键）**：平台只回流 stdout 里**最后一个真实存在的单文件**（`isfile` 为真）的 `/uploads/...` 路径成文件卡——目录不产卡。最终交付就是 `pack_skill_package.py` 打出的**可上传 skill zip**，它把 zip 的 `/uploads/*.zip` 绝对路径打成最后一行。沙箱**无 `zip` CLI**，只能用该脚本（stdlib zipfile）。

# Skill Design

把用户的需求变成一个**最小、真实、可直接上传的目标 sayu skill**，并打包。产物只有一件事：一个根级布局的 skill zip（`manifest.json` + `SKILL.md` [+ 按需 `scripts/`]）。

本 skill **只设计并打包**目标 skill，**不**安装/发布/上传/注册它——那是带外步骤：用户在 sayu 端点「挂载」时，平台把这个 zip 导入为其**私有 skill**。

## 工作流（默认 3-4 轮，直路径，无确认门）

1. **理解需求**（判断，无工具）：确定目标 skill 的**用途、触发场景、输入、输出格式**。redesign 时先看清当前 skill 再定下一版。想清楚它是**纯提示词 skill**（默认，只有 `SKILL.md`）还是**确需可执行脚本**（有明确的数据处理/产物构建逻辑才加 `scripts/`）。
2. **建工作目录**：`python scripts/init_skill_package.py <slug> "<展示名>" "<一句话描述>"` —— 建 `<pkg>/target/` 并种一份合法 manifest 骨架，打印 `<pkg>` 路径与下一步。
3. **写 `target/SKILL.md`**：目标 skill 的真实工作流入口（注入其运行时 system prompt），实质内容、无占位符。用 heredoc 避免引号转义：
   ```
   python - <<'PY'
   open('<pkg>/target/SKILL.md','w',encoding='utf-8').write('''
   ...目标 skill 的真实 SKILL.md 正文...
   ''')
   PY
   ```
   按需改 `target/manifest.json`（`dependencies` 填 `platform_tools_*` slug、`network_policy`、`secrets[]`），仅确需时加 `target/scripts/…` 或 `target/requirements.txt`。
4. **打包**：`python scripts/pack_skill_package.py <pkg>` —— 只打 `target/` 成根级、固定时间戳的可上传 zip，硬校验（合法 manifest / `entry_main` 在包内 / 无占位符），打印其 `/uploads/*.zip` 路径回流。
5. **简短呈现**：说清这个 skill **做什么**、**在什么场景触发**，末尾说明用户在 sayu 端点「挂载」即导入为私有 skill。**不编造交付示例文件**——提示词类 skill 没有「交付物文件」，别硬造。

## 目标 skill 的沙箱约束（写 `target/manifest.json` / `SKILL.md` 时遵守）

目标 skill 同样跑在离线 Docker 沙箱 `/workspace/<slug>/`，由 `platform_tools_run_script` 驱动。硬约束：

- **合法 manifest 必填**：`slug`(`^[a-z][a-z0-9_-]{1,62}$`) / `kind=skill` / `name` / `version` / `runtime_type` / `entry_main=SKILL.md`。**`runtime_type` 只能是 `python`/`node`/`shell`/`custom`**（沙箱运行时，不是 skill 的性质）——提示词 skill 保持 `python`+`entry_main=SKILL.md`，**绝不要**写 `prompt`/`md` 等非法值（sayu 上传校验会拒；即便误写，后端导入也会归一，但别依赖）。
- **最小化**：默认目标 skill **只有 `SKILL.md` + `manifest.json`**。只有当某段逻辑确需可执行代码（数据处理、产物构建、格式转换）时才加 `target/scripts/`；纯「整理/总结/改写/套模板输出文本」的能力**不需要任何脚本**，写在 `SKILL.md` 里即可。
- **离线默认**：`network_policy` 默认 `none`（无外网）。仅当目标 skill 必须联网或需 pip 装包时才用 `open`，并同时给 `target/requirements.txt`。
- **预装库免声明**：Python 3.11 + `python-docx`/`openpyxl`/`python-pptx`/`pypdf`/`pymupdf`/`Pillow`/`pandas`/`requests`/`lxml`/`beautifulsoup4`/`markdown`/`pdfplumber`/`reportlab`/`pdf2image`/`defusedxml`/`pypdfium2`，系统 `poppler-utils`/`qpdf`/`curl`。只有超出此清单才需 `requirements.txt`+`network_policy=open`。
- **子工具声明**：目标 skill 要调用的 sayu 内建工具在 `manifest.dependencies` 里以 `platform_tools_*` slug 声明（`run_script`/`generate_media`/`duckduckgo`/`browser_read`/`browser_use`/`ocr_pdf`/`read_document`/`transcribe_audio`/`scheduled_task`…），并在 `SKILL.md` 的工作流里写明何时调、用什么 `mode`。联网型工具需目标 skill `network_policy=open`。
- **密钥**：目标 skill 需要的密钥在 `manifest.secrets[]` 声明（`{key,label,required,doc}`，`key` 匹配 `^[A-Z_][A-Z0-9_]*$`），值由平台注入为容器 env，**不写进包**。
- **单文件回流**：目标 skill 若产出多文件，其收尾脚本须先 zip 成单文件再打印 `/uploads/...` 路径（沙箱只回流单文件）。中间产物用 `/tmp/`。

## 写好 `target/SKILL.md` 的要点

- 开头一句 sandbox 说明（若目标 skill 有脚本：说明用 `run_script` 相对路径调用）。
- 用途 + 触发/不触发边界，让运行时能自我约束。
- 有序工作流：每步给输入、动作、（若调工具）工具与 `mode=`、产物、失败处理。纯判断步骤写「无工具」。
- 实质内容、贴合用户请求的真实专业领域，无 `<占位符>`/`TODO`/`TBD`（打包会校验并拒绝残留占位符）。
