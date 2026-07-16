#!/usr/bin/env python3
"""Validate skill-design proposal packages and optional final responses."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


REQUIRED_DIRS = ("proposal", "examples", "previews", "working")
REQUIRED_PROPOSAL_FILES = (
    "proposal/skill-overview.md",
    "proposal/workflow-tool-map.md",
    "proposal/deliverable-preview-index.md",
    "proposal/confirmation-questions.md",
)
REQUIRED_WORKING_FILES = (
    "working/sample-case.json",
    "working/generation-notes.md",
)
SUPPORT_FILE_PATTERNS = (
    "proposal/",
    "skill-overview.md",
    "workflow-tool-map.md",
    "deliverable-preview-index.md",
    "confirmation-questions.md",
    "manifest.json",
    "working/",
)
FINAL_DELIVERABLE_FORBIDDEN_PATTERNS = SUPPORT_FILE_PATTERNS + ("previews/",)
FINAL_HEADINGS = (
    "Skill 概述",
    "工作流步骤与工具",
    "最终交付示例文件",
    "产物与下一步",
)
REDESIGN_VERSION_FIELDS = (
    "当前版本",
    "建议新版本",
    "版本迭代理由",
    "旧版本保留路径",
    "新版本保存路径",
    "当前上线版本",
    "建议上线版本",
)
DEMAND_OVERVIEW_FIELDS = (
    "需求理解摘要",
    "专业领域",
    "目标使用场景",
    "交付物使用者",
    "示例案例选择理由",
)
SAMPLE_CASE_KEYS = (
    "user_need",
    "domain",
    "professional_context",
    "deliverable_use_case",
    "example_relevance_rationale",
)
WORKFLOW_NEED_TERMS = ("需求", "理解", "专业", "场景")
PREVIEW_RELEVANCE_TERMS = ("需求", "使用场景", "专业", "用途", "决策", "执行")

BENCHMARK_COLUMNS = (
    "层次",
    "来源",
    "观察事实",
    "可迁移机制（含适用前提）",
    "对目标 skill 的具体影响",
)
MINIMALITY_COLUMNS = (
    "候选项",
    "类型（文件/字段组/格式）",
    "唯一消费者或用途",
    "不可内联或合并原因",
    "决策（保留/合并/删除）",
)
EXAMPLE_STRATEGY_COLUMNS = (
    "决策",
    "需要解决的具体歧义",
    "示例形式与位置",
    "使用或加载条件",
    "独立文件必要性",
)
WORKFLOW_COLUMNS = (
    "步骤",
    "输入/前置条件",
    "动作",
    "工具与调用模式",
    "阶段产物",
    "验证",
    "缺失/失败处理",
)
PREVIEW_COLUMNS = (
    "交付物",
    "真实示例文件",
    "预览/检查文件",
    "格式说明",
    "模拟内容摘要",
)

ALLOWED_BENCHMARK_STATUSES = {"completed", "exempt_with_reason", "blocked"}
ALLOWED_EXAMPLE_DECISIONS = {"none", "inline", "separate_resource"}
ALLOWED_MINIMALITY_DECISIONS = {"保留", "合并", "删除"}
ALLOWED_IMAGE_MODES = {"image", "video"}
VALID_CONFIRMATION_OPTIONS = ("修改", "停止", "打包为可上传的 skill 包")
CONFIRMATION_HEADINGS = (
    ("创建前确认", 1),
    ("已确认", 2),
    ("仍需用户决定", 2),
    ("下一步选项", 2),
)
ABSENT_EXAMPLE_VALUES = {"无", "不适用", "none", "n/a", "na"}
PROHIBITED_BENCHMARK_FIELD = "不应" + "照搬"
GENERIC_CALLABLE_TOKENS = {
    "api",
    "builder",
    "callable",
    "client",
    "command",
    "connector",
    "create",
    "external",
    "mode",
    "plugin",
    "read",
    "run",
    "script",
    "service",
    "tool",
    "write",
}
ARTIFACT_BUILD_MODES = {
    "create",
    "build",
    "generate",
    "write",
    "edit",
    "update",
    "render",
    "export",
    "compose",
    "convert",
    "produce",
}
HARD_TO_INSPECT_EXTENSIONS = {
    "bmp",
    "docx",
    "gif",
    "jpeg",
    "jpg",
    "pdf",
    "png",
    "pptx",
    "tiff",
    "webp",
    "xlsx",
    "zip",
}
VAGUE_VALUES = {
    "",
    "无",
    "不适用",
    "待定",
    "待补",
    "待补充",
    "待确认",
    "待完善",
    "n/a",
    "na",
    "none",
    "null",
    "同上",
    "默认",
}


@dataclass(frozen=True)
class MarkdownTable:
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    line_number: int

    def dictionaries(self) -> list[dict[str, str]]:
        return [dict(zip(self.columns, row)) for row in self.rows]


def normalize_cell(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        value = value[1:-1].strip()
    return re.sub(r"\s+", " ", value)


def strip_html_comments(text: str) -> str:
    """Remove non-rendered Markdown HTML comments before semantic validation."""

    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def split_markdown_row(line: str) -> tuple[str, ...] | None:
    """Split a pipe-table row while respecting escaped pipes and inline code."""

    stripped = line.strip()
    if "|" not in stripped:
        return None
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith(r"\|"):
        stripped = stripped[:-1]

    cells: list[str] = []
    current: list[str] = []
    escaped = False
    in_code = False
    for char in stripped:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            current.append(char)
            continue
        if char == "`":
            in_code = not in_code
            current.append(char)
            continue
        if char == "|" and not in_code:
            cells.append(normalize_cell("".join(current)))
            current = []
            continue
        current.append(char)
    if escaped:
        current.append("\\")
    cells.append(normalize_cell("".join(current)))
    return tuple(cells)


def is_separator_row(cells: tuple[str, ...]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def parse_markdown_tables(text: str) -> list[MarkdownTable]:
    """Parse actual Markdown pipe tables into normalized headers and rows."""

    lines = [
        re.sub(r"^\s*(?:>\s*)+", "", line)
        for line in strip_html_comments(text).splitlines()
    ]
    tables: list[MarkdownTable] = []
    index = 0
    fence_marker: str | None = None
    while index + 1 < len(lines):
        fence = re.match(r"^\s*(`{3,}|~{3,})", lines[index])
        if fence:
            marker = fence.group(1)[0]
            fence_marker = None if fence_marker == marker else marker
            index += 1
            continue
        if fence_marker is not None:
            index += 1
            continue
        header = split_markdown_row(lines[index])
        separator = split_markdown_row(lines[index + 1])
        if (
            header is None
            or separator is None
            or len(header) != len(separator)
            or not is_separator_row(separator)
        ):
            index += 1
            continue

        rows: list[tuple[str, ...]] = []
        row_index = index + 2
        while row_index < len(lines):
            row = split_markdown_row(lines[row_index])
            if row is None or len(row) != len(header) or is_separator_row(row):
                break
            rows.append(row)
            row_index += 1
        tables.append(MarkdownTable(header, tuple(rows), index + 1))
        index = max(row_index, index + 2)
    return tables


def heading_match(text: str, heading: str) -> re.Match[str] | None:
    return re.search(
        rf"^(?P<marks>#{{1,6}})\s+{re.escape(heading)}\s*$",
        text,
        re.MULTILINE,
    )


def heading_position(text: str, heading: str) -> int:
    match = heading_match(text, heading)
    return match.start() if match else -1


def heading_section(text: str, heading: str) -> str:
    match = heading_match(text, heading)
    if not match:
        return ""
    level = len(match.group("marks"))
    next_heading = re.search(
        rf"^#{{1,{level}}}\s+.+$",
        text[match.end() :],
        re.MULTILINE,
    )
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.end() : end]


def heading_tail(text: str, heading: str) -> str:
    """Return everything after a heading through EOF, including later headings."""

    match = heading_match(text, heading)
    return text[match.end() :] if match else ""


def section_between(text: str, start_heading: str, end_heading: str) -> str:
    start = heading_position(text, start_heading)
    end = heading_position(text, end_heading)
    if start == -1 or end == -1 or end <= start:
        return ""
    return text[start:end]


def exact_table(
    section: str,
    columns: tuple[str, ...],
    label: str,
    errors: list[str],
) -> MarkdownTable | None:
    for table in parse_markdown_tables(section):
        if table.columns == columns:
            return table
    rendered = " | ".join(columns)
    errors.append(f"{label} must use exact Markdown table columns: {rendered}")
    return None


def is_substantive(value: str, minimum: int = 4) -> bool:
    normalized = normalize_cell(value).strip("`*_。；，:： ")
    if normalized.lower() in VAGUE_VALUES:
        return False
    if re.search(r"<[^>]+>|\b(?:todo|tbd|placeholder)\b", normalized, re.I):
        return False
    return len(normalized) >= minimum


def is_absent_example_value(value: str) -> bool:
    normalized = normalize_cell(value).strip("`*_。；，:： ").lower()
    return normalized in ABSENT_EXAMPLE_VALUES


def assignment_value(text: str, key: str) -> str | None:
    """Return one contract assignment without consuming the next assignment."""

    match = re.search(rf"\b{re.escape(key)}\s*=\s*", text, re.I)
    if not match:
        return None

    tail = text[match.end() :]
    boundaries: list[int] = []
    delimiter = re.search(r"[；;|,，\n]", tail)
    if delimiter:
        boundaries.append(delimiter.start())
    next_assignment = re.search(
        r"(?:^|\s+)(?=[A-Za-z_][A-Za-z0-9_]*\s*=)",
        tail,
    )
    if next_assignment:
        boundaries.append(next_assignment.start())
    end = min(boundaries) if boundaries else len(tail)
    return normalize_cell(tail[:end])


def is_filled_assignment(value: str | None) -> bool:
    if value is None:
        return False
    normalized = normalize_cell(value).strip("`*_。；，:： ")
    if not normalized or normalized.lower() in VAGUE_VALUES:
        return False
    if re.fullmatch(r"(?:\.{2,}|…+|⋯+)", normalized):
        return False
    placeholder_remainder = normalized.strip(
        "`*_。；，,:： .…⋯()（）[]【】{}<>《》"
    )
    if placeholder_remainder.lower() in VAGUE_VALUES:
        return False
    return not re.search(r"<[^>]+>|\b(?:todo|tbd|placeholder)\b", normalized, re.I)


def is_allowed_research_exemption(reason: str) -> bool:
    """Recognize only explicit positive forms of the three exemption categories."""

    normalized = normalize_cell(reason)
    invalid_or_negated = re.search(
        r"(?:用户|委托方).{0,20}(?:没有|并未|未曾|不曾|并非|不是|未|不).{0,8}"
        r"(?:禁止|拒绝|限制)|"
        r"(?:用户|委托方).{0,16}(?:可能|也许|或许|待确认|尚未确认).{0,8}"
        r"(?:禁止|不允许|拒绝|限制)|"
        r"(?:本地|既有).{0,12}(?:证据|材料|契约)?.{0,8}"
        r"(?:不完整|不充分|不足|不全|并不完整|尚不完整|未覆盖|不可重复|"
        r"完整性未确认|充分性未确认|待确认)|"
        r"(?:完整性|充分性).{0,6}(?:未确认|待确认|不足)|"
        r"(?:允许|同意|授权).{0,12}(?:web|网络|联网|公开|外部).{0,8}(?:检索|研究|搜索|访问)?|"
        r"公开研究.{0,8}(?:可进行|可以|能够|仍可|允许)|"
        r"(?:不是|并非|不属于|并不|非).{0,6}(?:完全内部|仅限内部|内部固定|内网)|"
        r"(?:不属于|不是|并非|不能|不应).{0,6}豁免|"
        r"user.{0,30}(?:did not|didn't|does not|doesn't|do not|don't|never|not).{0,12}"
        r"(?:forbid|disallow|prohibit).{0,12}(?:web|internet)|"
        r"(?:permit|allow|authorize).{0,20}(?:web|internet|public research)|"
        r"local evidence.{0,16}(?:incomplete|insufficient|not complete|unconfirmed)|"
        r"not fully internal",
        normalized,
        re.I,
    )
    if invalid_or_negated:
        return False

    user_forbids_web = bool(
        re.search(r"用户|委托方", normalized)
        and re.search(r"禁止|不允许|拒绝|未授权|要求不", normalized)
        and re.search(r"web|网络|联网|公开|外部", normalized, re.I)
    )
    fully_internal = bool(
        re.search(r"任务|工作|流程|目标能力", normalized)
        and re.search(r"完全内部|仅限内部|仅限内网|内部固定|仓库内既有固定契约", normalized)
        and re.search(r"不涉及|不依赖|无需|仅限", normalized)
    )
    sufficient_local_evidence = bool(
        re.search(r"本地|既有", normalized)
        and re.search(r"证据|材料|契约|fixture|验证", normalized, re.I)
        and re.search(r"充分|足够", normalized)
    )
    english_category = bool(
        re.search(
            r"user.{0,30}(?:forbids?|disallows?|prohibits?).{0,20}(?:web|internet)|"
            r"(?:fully internal|internal[- ]only).{0,30}(?:no external|without external)|"
            r"sufficient (?:and )?(?:complete )?local evidence",
            normalized,
            re.I,
        )
    )
    return user_forbids_web or fully_internal or sufficient_local_evidence or english_category


def load_manifest(package_dir: Path, errors: list[str]) -> dict | None:
    manifest_path = package_dir / "manifest.json"
    if not manifest_path.exists():
        errors.append("missing manifest.json")
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"manifest.json is not valid JSON: {exc}")
        return None
    if not isinstance(manifest, dict):
        errors.append("manifest.json root must be an object")
        return None
    return manifest


def require_paths(package_dir: Path, paths: tuple[str, ...], errors: list[str]) -> None:
    for relative_path in paths:
        if not (package_dir / relative_path).exists():
            errors.append(f"missing required file: {relative_path}")


def validate_manifest(package_dir: Path, manifest: dict, errors: list[str]) -> None:
    required_keys = (
        "manifest_version",
        "created_at",
        "target_skill_family",
        "target_skill_name",
        "case_name",
        "case_slug",
        "package_path",
        "directories",
        "deliverable_types",
        "expected_files",
        "validation_notes",
    )
    for key in required_keys:
        if key not in manifest:
            errors.append(f"manifest missing key: {key}")

    package_path = manifest.get("package_path")
    if package_path and Path(package_path).expanduser().resolve() != package_dir:
        errors.append(f"manifest package_path does not match package: {package_path}")

    directories = manifest.get("directories", {})
    if not isinstance(directories, dict):
        errors.append("manifest directories must be an object")
        directories = {}
    for dirname in REQUIRED_DIRS:
        if not (package_dir / dirname).is_dir():
            errors.append(f"missing required directory: {dirname}/")
        if dirname not in directories:
            errors.append(f"manifest directories missing: {dirname}")


def expected_examples(manifest: dict) -> list[str]:
    expected_files = manifest.get("expected_files", {})
    examples = expected_files.get("examples", []) if isinstance(expected_files, dict) else []
    return [item for item in examples if isinstance(item, str)]


def validate_expected_preview_files(
    package_dir: Path,
    manifest: dict,
    errors: list[str],
) -> None:
    expected_files = manifest.get("expected_files", {})
    if not isinstance(expected_files, dict):
        errors.append("manifest expected_files must be an object")
        return
    previews = expected_files.get("previews", [])
    if not isinstance(previews, list):
        errors.append("manifest expected_files.previews must be an array")
        return
    for item in previews:
        if not isinstance(item, str) or not item.strip():
            errors.append("manifest expected_files.previews contains an invalid path")
            continue
        if "<role>" in item:
            errors.append(f"preview placeholder was not replaced: {item}")
            continue
        relative_path = item if item.startswith("previews/") else f"previews/{item}"
        validate_package_relative_file(
            package_dir,
            relative_path,
            "manifest expected preview",
            errors,
        )


def validate_scaffold(package_dir: Path, manifest: dict, errors: list[str]) -> None:
    validate_manifest(package_dir, manifest, errors)
    deliverables = manifest.get("deliverable_types", [])
    examples = expected_examples(manifest)
    if deliverables and not examples:
        errors.append("manifest has deliverable_types but no expected example placeholders")
    for example in examples:
        if not example.startswith("<role>.") and not example.startswith("examples/"):
            errors.append(
                "scaffold expected example should be a placeholder or examples/ path: "
                f"{example}"
            )


def relative_paths_in_cell(cell: str, root: str) -> set[str]:
    pattern = re.compile(
        rf"(?<![A-Za-z0-9_./-]){re.escape(root)}/[^\s`'\"，。；、|)）\]]+"
    )
    return {normalize_candidate(match.group(0)) for match in pattern.finditer(cell)}


def validate_package_relative_file(
    package_dir: Path,
    relative_path: str,
    label: str,
    errors: list[str],
) -> None:
    candidate = Path(relative_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        errors.append(f"{label} must be a safe package-relative path: {relative_path}")
        return
    resolved = (package_dir / candidate).resolve()
    try:
        resolved.relative_to(package_dir)
    except ValueError:
        errors.append(f"{label} escapes the package: {relative_path}")
        return
    if not resolved.is_file():
        errors.append(f"{label} does not exist: {relative_path}")


def normalized_expected_example_paths(manifest: dict) -> set[str]:
    normalized: set[str] = set()
    for item in expected_examples(manifest):
        if "<role>" in item:
            continue
        normalized.add(item if item.startswith("examples/") else f"examples/{item}")
    return normalized


def validate_preview_index(
    preview_index: str,
    package_dir: Path,
    manifest: dict,
    errors: list[str],
) -> None:
    if "examples/" not in preview_index:
        errors.append("deliverable-preview-index.md does not reference examples/")
    if not any(term in preview_index for term in PREVIEW_RELEVANCE_TERMS):
        errors.append("deliverable-preview-index.md does not explain example relevance to user need")
    table = exact_table(preview_index, PREVIEW_COLUMNS, "deliverable preview index", errors)
    if table is None:
        return
    if not table.rows:
        errors.append("deliverable preview index table has no deliverable rows")
        return

    manifest_types = {
        str(item).strip().lower().lstrip(".")
        for item in manifest.get("deliverable_types", [])
        if str(item).strip()
    }
    represented_types: set[str] = set()
    represented_examples: set[str] = set()

    for index, row in enumerate(table.dictionaries(), start=1):
        deliverable_cells = f"{row['交付物']} {row['真实示例文件']}"
        for pattern in SUPPORT_FILE_PATTERNS:
            if pattern in deliverable_cells:
                errors.append(
                    f"deliverable preview row {index} lists support file as deliverable: {pattern}"
                )

        example_paths = relative_paths_in_cell(row["真实示例文件"], "examples")
        row_example_exts: set[str] = set()
        if not example_paths:
            errors.append(
                f"deliverable preview row {index} must name a real examples/ path"
            )
        for relative_path in sorted(example_paths):
            represented_examples.add(relative_path)
            validate_package_relative_file(
                package_dir,
                relative_path,
                f"deliverable preview row {index} example",
                errors,
            )
            ext = Path(relative_path).suffix.lower().lstrip(".")
            declared_ext = Path(normalize_candidate(row["交付物"])).suffix.lower().lstrip(".")
            if ext:
                represented_types.add(ext)
                row_example_exts.add(ext)
            if declared_ext and declared_ext != ext:
                errors.append(
                    f"deliverable preview row {index} deliverable extension does not match example: "
                    f".{declared_ext} != .{ext}"
                )
            if ext not in manifest_types:
                errors.append(
                    f"deliverable preview row {index} example type is not declared in manifest: .{ext}"
                )

        preview_paths = relative_paths_in_cell(row["预览/检查文件"], "previews")
        if not preview_paths:
            if row_example_exts.intersection(HARD_TO_INSPECT_EXTENSIONS):
                errors.append(
                    f"deliverable preview row {index} hard-to-inspect artifact requires a previews/ path"
                )
            elif not is_absent_example_value(row["预览/检查文件"]):
                errors.append(
                    f"deliverable preview row {index} inspection entry must be a previews/ path or 不适用"
                )
        for relative_path in sorted(preview_paths):
            validate_package_relative_file(
                package_dir,
                relative_path,
                f"deliverable preview row {index} inspection file",
                errors,
            )

    for missing_type in sorted(manifest_types - represented_types):
        errors.append(
            f"deliverable preview index missing manifest deliverable type: .{missing_type}"
        )

    expected_paths = normalized_expected_example_paths(manifest)
    for missing_path in sorted(expected_paths - represented_examples):
        errors.append(f"deliverable preview index missing manifest example: {missing_path}")
    for extra_path in sorted(represented_examples - expected_paths):
        errors.append(f"deliverable preview index has unmanifested example: {extra_path}")


def normalize_option(value: str) -> str:
    return normalize_cell(value).strip("`*_。；，. ")


def validate_exact_option_section(
    section: str,
    label: str,
    errors: list[str],
) -> None:
    nonempty_lines = [line.strip() for line in section.splitlines() if line.strip()]
    option_lines: list[str] = []
    intro_lines: list[str] = []
    unexpected_lines: list[str] = []
    options_started = False
    for line in nonempty_lines:
        match = re.fullmatch(r"[-*+]\s+(.+)", line)
        if match:
            options_started = True
            option_lines.append(normalize_option(match.group(1)))
        elif not options_started and not intro_lines:
            intro_lines.append(line)
        else:
            unexpected_lines.append(line)
    if intro_lines:
        intro = normalize_cell(intro_lines[0])
        if len(intro) > 50 or intro.startswith("#"):
            unexpected_lines.extend(intro_lines)
    if tuple(option_lines) != VALID_CONFIRMATION_OPTIONS:
        errors.append(
            f"{label} must contain exactly these options in order: "
            + " | ".join(VALID_CONFIRMATION_OPTIONS)
        )
    if unexpected_lines:
        errors.append(f"{label} must stop after the three options; unexpected content follows")


def validate_heading_contract(
    text: str,
    required: tuple[tuple[str, int], ...],
    label: str,
    errors: list[str],
) -> None:
    text = strip_html_comments(text)
    positions: list[int] = []
    complete = True
    for heading, expected_level in required:
        matches = list(
            re.finditer(
                rf"^(?P<marks>#{{1,6}})\s+{re.escape(heading)}\s*$",
                text,
                re.MULTILINE,
            )
        )
        if not matches:
            errors.append(f"{label} missing heading: {heading}")
            complete = False
            continue
        if len(matches) != 1:
            errors.append(f"{label} heading must appear exactly once: {heading}")
            complete = False
        first = matches[0]
        positions.append(first.start())
        if len(first.group("marks")) != expected_level:
            errors.append(f"{label} heading has wrong level: {heading}")
    if complete and positions != sorted(positions):
        errors.append(f"{label} headings are not in the required order")
    observed = [
        (match.group("text").strip(), len(match.group("marks")))
        for match in re.finditer(
            r"^(?P<marks>#{1,6})\s+(?P<text>.+?)\s*$",
            text,
            re.MULTILINE,
        )
    ]
    expected = [(heading, level) for heading, level in required]
    if observed != expected:
        errors.append(f"{label} must contain only the required headings in order")


def validate_confirmation_questions(text: str, errors: list[str]) -> None:
    validate_heading_contract(
        text,
        CONFIRMATION_HEADINGS,
        "proposal confirmation document",
        errors,
    )
    section = heading_tail(text, "下一步选项")
    if not section:
        errors.append("confirmation-questions.md missing section: 下一步选项")
        return
    validate_exact_option_section(section, "proposal confirmation gate", errors)


def validate_research(overview: str, errors: list[str]) -> None:
    section = heading_section(overview, "行业与实现对标")
    if not section:
        errors.append("skill-overview.md missing section: 行业与实现对标")
        return
    section = strip_html_comments(section)

    status_match = re.search(
        r"对标状态\s*[：:]\s*([A-Za-z_]+)",
        section,
    )
    if not status_match:
        errors.append("industry benchmark missing status: completed|exempt_with_reason|blocked")
        return
    status = status_match.group(1)
    if status not in ALLOWED_BENCHMARK_STATUSES:
        errors.append(f"industry benchmark has unsupported status: {status}")
        return

    if status == "blocked":
        errors.append("industry benchmark status is blocked; stop before scaffolding a full package")
        return

    if status == "exempt_with_reason":
        reason = re.search(r"豁免理由\s*[：:]\s*(.+)", section)
        evidence = re.search(r"本地证据\s*[：:]\s*(.+)", section)
        if not reason or not is_substantive(reason.group(1)):
            errors.append("exempt_with_reason requires a substantive 豁免理由：")
        elif not is_allowed_research_exemption(reason.group(1)):
            errors.append(
                "exempt_with_reason is allowed only for user-forbidden web, "
                "fully internal work, or already-sufficient local evidence"
            )
        if not evidence or not is_substantive(evidence.group(1)):
            errors.append("exempt_with_reason requires substantive 本地证据：")
        return

    if re.search(
        rf"^\s*(?:[-*+]\s*)?(?:\*\*|__|`)?"
        rf"{re.escape(PROHIBITED_BENCHMARK_FIELD)}(?:\*\*|__|`)?\s*[：:]|"
        rf"^\s*(?:[-*+]\s*)?(?:\*\*|__|`)?"
        rf"{re.escape(PROHIBITED_BENCHMARK_FIELD)}\s*[：:](?:\*\*|__|`)?|"
        rf"^\s*#{{1,6}}\s+{re.escape(PROHIBITED_BENCHMARK_FIELD)}\s*$",
        section,
        re.MULTILINE,
    ):
        errors.append("completed benchmark contains a prohibited do-not-copy field")

    tables = parse_markdown_tables(section)
    if len(tables) != 1:
        errors.append(
            "completed benchmark must contain exactly one Markdown table with the contract columns"
        )
        return
    table = tables[0]
    if table.columns != BENCHMARK_COLUMNS:
        rendered = " | ".join(BENCHMARK_COLUMNS)
        errors.append(f"industry benchmark must use exact Markdown table columns: {rendered}")
        return
    rows = table.dictionaries()
    for required_layer in ("行业工作流", "Agent/Skill 实现"):
        layer_rows = [row for row in rows if row["层次"] == required_layer]
        if not layer_rows:
            errors.append(f"completed benchmark missing required layer: {required_layer}")
            continue
        if not any(re.search(r"https?://\S+", row["来源"]) for row in layer_rows):
            errors.append(
                f"completed benchmark layer {required_layer} requires an http(s) source"
            )
        for row in layer_rows:
            for column in BENCHMARK_COLUMNS[2:]:
                if not is_substantive(row[column]):
                    errors.append(
                        f"completed benchmark layer {required_layer} has empty or vague {column}"
                    )


def normalize_candidate(value: str) -> str:
    return normalize_cell(value).strip("`*_。；，,()（） ")


def declaration_is_planned(context: str) -> bool | None:
    """Classify one resource mention as planned, historical, or ignorable."""

    negated_transition = re.search(
        r"(?:不得|不可|不能|不应|无需|禁止|避免|拒绝|不(?!再)|不再)\s*"
        r"(?:删除|移除|废弃|取消|淘汰|并入|合并|归并)|"
        r"(?:do not|must not|cannot|can't|should not|never)\s+"
        r"(?:delete|remove|retire|deprecate|merge)",
        context,
        re.I,
    )
    if negated_transition:
        return True
    transition = re.search(
        r"删除|移除|废弃|取消|淘汰|不再(?:使用|保留|加载)|"
        r"并入|合并|归并|"
        r"delete|remove|retire|deprecat|merge",
        context,
        re.I,
    )
    if transition:
        return False
    future_plan = re.search(
        r"计划|拟(?:新增|保留|使用|加载)|建议(?:新增|保留|使用|加载)|"
        r"将(?:新增|保留|使用|加载)|(?:新版本|目标版本).{0,12}(?:新增|保留|使用|加载)|"
        r"新增(?:目标)?资源|保留(?:现有|原有|旧版)|继续(?:使用|加载|保留)|"
        r"required|planned|future|retain|keep|add|create|will use",
        context,
        re.I,
    )
    if future_plan:
        return True
    historical = re.search(
        r"现有|当前|原有|旧版|旧版本|历史|遗留|曾经|"
        r"existing|current|previous|historical|legacy",
        context,
        re.I,
    )
    if historical:
        return False
    planned = re.search(
        r"目标(?:资源|脚本|引用|资产)|保留|使用|加载|需要|target",
        context,
        re.I,
    )
    if planned:
        return True
    return None


def declaration_context(text: str, start: int, end: int) -> str:
    """Return the clause governing one declaration without mixing sibling items."""

    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end == -1:
        line_end = len(text)
    line = text[line_start:line_end]
    if line.count("|") >= 2:
        return line

    relative_start = start - line_start
    relative_end = end - line_start
    delimiters = "；;。.!?！？,，"
    clause_start = max((line.rfind(char, 0, relative_start) for char in delimiters), default=-1) + 1
    following = [line.find(char, relative_end) for char in delimiters]
    following = [position for position in following if position != -1]
    clause_end = min(following) if following else len(line)
    return line[clause_start:clause_end]


def declared_target_items(overview: str) -> dict[str, bool]:
    """Collect audited items and whether each is an affirmative target plan."""

    declaration_text = strip_html_comments(overview)
    for excluded_heading in ("行业与实现对标", "目标 Skill 最小化审计"):
        match = heading_match(declaration_text, excluded_heading)
        if not match:
            continue
        level = len(match.group("marks"))
        next_heading = re.search(
            rf"^#{{1,{level}}}\s+.+$",
            declaration_text[match.end() :],
            re.MULTILINE,
        )
        end = match.end() + next_heading.start() if next_heading else len(declaration_text)
        declaration_text = declaration_text[: match.start()] + declaration_text[end:]

    items: dict[str, bool] = {}
    is_redesign = "重新设计已有 skill" in overview
    path_pattern = re.compile(
        r"(?<![A-Za-z0-9_./-])(?:references|scripts|assets)/"
        r"[^\s`'\"，。；、|)）]+"
    )
    for match in path_pattern.finditer(declaration_text):
        classification = declaration_is_planned(
            declaration_context(declaration_text, match.start(), match.end())
        )
        if classification is False and not is_redesign:
            continue
        planned = classification is not False
        candidate = normalize_candidate(match.group(0))
        items[candidate] = items.get(candidate, False) or planned
    for match in re.finditer(
        r"字段组\s*[：:]\s*([A-Za-z0-9_.\-/\u4e00-\u9fff]+)",
        declaration_text,
    ):
        classification = declaration_is_planned(
            declaration_context(declaration_text, match.start(), match.end())
        )
        if classification is False and not is_redesign:
            continue
        planned = classification is not False
        candidate = f"字段组：{normalize_candidate(match.group(1))}"
        items[candidate] = items.get(candidate, False) or planned
    return items


def validate_minimality(overview: str, manifest: dict, errors: list[str]) -> dict[str, dict[str, str]]:
    section = heading_section(overview, "目标 Skill 最小化审计")
    if not section:
        errors.append("skill-overview.md missing section: 目标 Skill 最小化审计")
        return {}
    table = exact_table(section, MINIMALITY_COLUMNS, "target skill minimality audit", errors)
    if table is None:
        return {}
    if not table.rows:
        errors.append("target skill minimality audit has no rows")
        return {}

    row_map: dict[str, dict[str, str]] = {}
    for row in table.dictionaries():
        candidate = normalize_candidate(row["候选项"])
        if not candidate:
            errors.append("minimality audit row has an empty candidate")
            continue
        if candidate in row_map:
            errors.append(f"minimality audit has duplicate candidate: {candidate}")
        row_map[candidate] = row
        decision = normalize_cell(row["决策（保留/合并/删除）"])
        if decision not in ALLOWED_MINIMALITY_DECISIONS:
            errors.append(f"minimality audit candidate {candidate} has invalid decision: {decision}")
        if decision == "保留":
            if not is_substantive(row["唯一消费者或用途"]):
                errors.append(
                    f"retained minimality candidate {candidate} requires a substantive unique consumer or use"
                )
            if not is_substantive(row["不可内联或合并原因"]):
                errors.append(
                    f"retained minimality candidate {candidate} requires a substantive non-inline/non-merge reason"
                )

    for baseline in ("SKILL.md", "manifest.json"):
        row = row_map.get(baseline)
        if row is None:
            errors.append(f"minimality audit missing default callable file: {baseline}")
        elif normalize_cell(row["决策（保留/合并/删除）"]) != "保留":
            errors.append(f"minimality audit default callable file must be retained: {baseline}")

    required_items = declared_target_items(overview)
    for raw_ext in manifest.get("deliverable_types", []):
        ext = str(raw_ext).strip().lower().lstrip(".")
        if ext:
            required_items[f".{ext}"] = True

    for item, must_retain in sorted(required_items.items()):
        row = row_map.get(item)
        if row is None and item.startswith("字段组："):
            bare_name = item.split("：", 1)[1]
            candidate_row = row_map.get(bare_name)
            if candidate_row and "字段组" in candidate_row["类型（文件/字段组/格式）"]:
                row = candidate_row
        if row is None:
            errors.append(f"minimality audit missing declared target item: {item}")
        elif must_retain and normalize_cell(row["决策（保留/合并/删除）"]) != "保留":
            errors.append(f"declared target item is not retained in minimality audit: {item}")
    return row_map


def validate_example_strategy(
    overview: str,
    minimality_rows: dict[str, dict[str, str]],
    errors: list[str],
) -> None:
    section = heading_section(overview, "示例策略")
    if not section:
        errors.append("skill-overview.md missing section: 示例策略")
        return
    table = exact_table(section, EXAMPLE_STRATEGY_COLUMNS, "example strategy", errors)
    if table is None:
        return
    if len(table.rows) != 1:
        errors.append("example strategy must contain exactly one decision row")
        return

    row = table.dictionaries()[0]
    decision = normalize_cell(row["决策"])
    if decision not in ALLOWED_EXAMPLE_DECISIONS:
        errors.append(f"example strategy has invalid decision: {decision}")
        return
    if decision == "none":
        for column in EXAMPLE_STRATEGY_COLUMNS[1:]:
            if not is_absent_example_value(row[column]):
                errors.append(
                    f"none example strategy requires {column} to be 无 or 不适用"
                )
        return

    ambiguity = row["需要解决的具体歧义"]
    location = normalize_candidate(row["示例形式与位置"])
    loading = row["使用或加载条件"]
    necessity = row["独立文件必要性"]
    if not is_substantive(ambiguity):
        errors.append(f"{decision} example strategy requires a substantive ambiguity")

    if decision == "inline":
        if "SKILL.md" not in location:
            errors.append("inline example strategy must locate the example in target SKILL.md")
        joined = " ".join(row[column] for column in EXAMPLE_STRATEGY_COLUMNS[1:])
        if re.search(r"(?:references|scripts|assets)/[^\s`'\"，。；、|)）]+", joined):
            errors.append("inline example strategy must not declare a separate target resource")
        if not is_substantive(loading):
            errors.append("inline example strategy requires a substantive use condition")
        contradictory_necessity = re.search(
            r"必须.{0,8}(?:独立|文件)|(?<!不)需要.{0,8}独立|不能内联|不可内联|"
            r"requires?.{0,8}separate|cannot.{0,8}inline",
            necessity,
            re.I,
        )
        if contradictory_necessity:
            errors.append("inline example strategy cannot require an independent file")
        return

    if not re.fullmatch(r"(?:references|scripts|assets)/[^\s]+", location):
        errors.append("separate_resource example strategy requires a real target resource path")
    if not is_substantive(loading):
        errors.append("separate_resource example strategy requires a substantive loading condition")
    if not is_substantive(necessity):
        errors.append("separate_resource example strategy requires a substantive non-inline reason")
    audited = minimality_rows.get(location)
    if audited is None:
        errors.append(f"separate_resource example path missing minimality audit row: {location}")
    elif normalize_cell(audited["决策（保留/合并/删除）"]) != "保留":
        errors.append(f"separate_resource example path is not retained: {location}")


def tool_mode(tool: str) -> str | None:
    match = re.search(r"\bmode\s*=\s*([A-Za-z0-9_-]+)", tool, re.I)
    return match.group(1).lower() if match else None


def tool_callable(tool: str) -> str | None:
    """Require exactly one concrete callable token before mode=."""

    mode_match = re.search(r"\bmode\s*=", tool, re.I)
    if not mode_match:
        return None
    prefix = tool[: mode_match.start()] if mode_match else tool
    prefix = prefix.strip("`*_ \t；;,，")
    match = re.fullmatch(
        r"(?:\$?[A-Za-z][A-Za-z0-9_.:-]*|(?:\.?\.?/)?[A-Za-z0-9_.-]+/"
        r"[A-Za-z0-9_./-]+)",
        prefix,
    )
    if not match:
        return None
    candidate = match.group(0)
    components = [
        component
        for component in re.split(r"[.$:/_-]+", candidate.lstrip("$").lower())
        if component
    ]
    if components and all(component in GENERIC_CALLABLE_TOKENS for component in components):
        return None
    return candidate


def is_web_callable(callable_name: str) -> bool:
    lowered = callable_name.lower()
    return bool(
        re.search(r"(?:^|[.:/_-])web(?:\.run)?(?:$|[.:/_-])", lowered)
        or re.search(r"(?:^|[.:/_-])(?:browser|playwright|chrome|duckduckgo)(?:$|[.:/_-])", lowered)
    )


def is_artifact_build(callable_name: str, mode: str | None) -> bool:
    mode_parts = set(re.split(r"[_-]+", mode or ""))
    if not mode_parts.intersection(ARTIFACT_BUILD_MODES):
        return False
    return bool(
        re.search(
            r"(?:^|[.:/_-])(?:documents?|spreadsheets?|presentations?|"
            r"docx|xlsx|pptx|pdf)(?:$|[.:/_-])",
            callable_name.lower(),
        )
    )


def validate_image_row(row: dict[str, str], row_label: str, errors: list[str]) -> None:
    """sayu 媒体生成 (platform_tools_generate_media) 契约: mode=image|video + 目视检查。

    不套用 Codex imagegen 的 text_to_image/output(count,ratio,...) 硬契约 —— sayu 无此模式。
    仅保留通用要求: 声明产物类型、结果须目视核验、身份关键的必需参考图不得静默降级。
    """
    mode = tool_mode(row["工具与调用模式"])
    if mode not in ALLOWED_IMAGE_MODES:
        errors.append(
            f"workflow row {row_label} media generation requires mode=image|video"
        )

    validation = row["验证"]
    if not (
        "view_image" in validation
        or re.search(r"视觉.*(?:检查|对照|核验|审阅)|目视检查|visual inspection", validation, re.I)
    ):
        errors.append(
            f"workflow row {row_label} media validation requires view_image or explicit visual inspection"
        )

    # 参考图输入 (role=/source=/required=): 承载身份关键内容的必需图不得 missing_action=downgrade。
    segments = [
        segment.strip()
        for segment in re.split(r"[；;]", row["输入/前置条件"])
        if re.search(r"\b(?:role|source|required)\s*=", segment)
    ]
    missing_action_match = re.search(
        r"\bmissing_action\s*=\s*(ask|downgrade|stop)\b",
        row["缺失/失败处理"],
    )
    if missing_action_match and missing_action_match.group(1) == "downgrade":
        identity_pattern = re.compile(
            r"identity|product|brand|logo|person|portrait|face|character|"
            r"身份|产品|品牌|标识|人物|人脸|角色",
            re.I,
        )
        for segment in segments:
            role = re.search(r"\brole\s*=\s*([^\s；;]+)", segment)
            source = re.search(r"\bsource\s*=\s*([^\s；;]+)", segment)
            required = re.search(r"\brequired\s*=\s*yes\b", segment)
            identity_text = " ".join(
                match.group(1) for match in (role, source) if match is not None
            )
            if required and identity_pattern.search(identity_text):
                errors.append(
                    f"workflow row {row_label} identity-critical required image cannot use missing_action=downgrade"
                )
                break


def validate_web_row(row: dict[str, str], row_label: str, errors: list[str]) -> None:
    scope_text = f"{row['输入/前置条件']}；{row['动作']}"
    scope_values = [
        assignment_value(scope_text, key)
        for key in ("query_scope", "page_scope", "query", "page")
    ]
    if not any(is_filled_assignment(value) for value in scope_values):
        errors.append(
            f"workflow row {row_label} web/browser call requires a non-empty query/page scope assignment"
        )
    evidence_text = f"{row['阶段产物']}；{row['验证']}"
    if not is_filled_assignment(assignment_value(evidence_text, "evidence")):
        errors.append(
            f"workflow row {row_label} web/browser call requires non-empty evidence=..."
        )
    if not is_filled_assignment(
        assignment_value(row["缺失/失败处理"], "fallback")
    ):
        errors.append(
            f"workflow row {row_label} web/browser call requires non-empty fallback=..."
        )


def validate_artifact_row(
    row: dict[str, str],
    row_label: str,
    prior_steps: set[str],
    errors: list[str],
) -> None:
    source_text = f"{row['输入/前置条件']}；{row['动作']}"
    if not is_filled_assignment(assignment_value(source_text, "source_of_truth")):
        errors.append(
            f"workflow row {row_label} artifact build requires non-empty source_of_truth=..."
        )
    builder_text = f"{row['工具与调用模式']}；{row['动作']}"
    if not is_filled_assignment(assignment_value(builder_text, "builder")):
        errors.append(f"workflow row {row_label} artifact build requires non-empty builder=...")
    if not is_filled_assignment(
        assignment_value(row["阶段产物"], "final_artifact")
    ):
        errors.append(
            f"workflow row {row_label} artifact build requires non-empty final_artifact=..."
        )
    if not re.search(r"render|reopen|渲染|重新打开|回读", row["验证"], re.I):
        errors.append(f"workflow row {row_label} artifact build missing render/reopen check")
    return_to = assignment_value(row["缺失/失败处理"], "return_to")
    if not is_filled_assignment(return_to):
        errors.append(
            f"workflow row {row_label} artifact failure handling requires non-empty return_to=..."
        )
    elif normalize_cell(return_to or "") not in prior_steps:
        errors.append(
            f"workflow row {row_label} artifact return_to must name a prior workflow step"
        )


def register_step_aliases(steps: set[str], row_label: str) -> None:
    steps.add(row_label)
    steps.add(f"step-{row_label}")
    numeric_prefix = re.match(r"\d+", row_label)
    if numeric_prefix:
        steps.add(numeric_prefix.group(0))
        steps.add(f"step-{numeric_prefix.group(0)}")


def validate_workflow(workflow: str, errors: list[str]) -> None:
    missing_terms = [term for term in WORKFLOW_NEED_TERMS if term not in workflow]
    if missing_terms:
        errors.append(
            "workflow-tool-map.md missing need-analysis/professional-context terms: "
            + ", ".join(missing_terms)
        )

    table = exact_table(workflow, WORKFLOW_COLUMNS, "workflow tool map", errors)
    if table is None:
        return
    if not table.rows:
        errors.append("workflow tool map has no workflow rows")
        return

    first_row = table.dictionaries()[0]
    first_row_text = f"{first_row['输入/前置条件']} {first_row['动作']}"
    missing_first_row_terms = [
        term for term in WORKFLOW_NEED_TERMS if term not in first_row_text
    ]
    if missing_first_row_terms:
        errors.append(
            "first workflow row must perform demand and professional-context analysis; missing: "
            + ", ".join(missing_first_row_terms)
        )

    prior_steps: set[str] = set()
    for row in table.dictionaries():
        row_label = normalize_cell(row["步骤"]) or "<unknown>"
        for column in (
            "输入/前置条件",
            "动作",
            "阶段产物",
            "验证",
            "缺失/失败处理",
        ):
            if not is_substantive(row[column]):
                errors.append(f"workflow row {row_label} has empty or vague {column}")

        tool = normalize_cell(row["工具与调用模式"])
        if tool == "无":
            register_step_aliases(prior_steps, row_label)
            continue
        mode = tool_mode(tool)
        if mode is None:
            errors.append(f"workflow row {row_label} external tool missing mode=<value>")
        callable_name = tool_callable(tool)
        if callable_name is None:
            errors.append(
                f"workflow row {row_label} external tool requires a callable before mode=<value>"
            )
            register_step_aliases(prior_steps, row_label)
            continue

        lowered_callable = callable_name.lower()
        if (
            "generate_media" in lowered_callable
            or "image_gen" in lowered_callable
            or "imagegen" in lowered_callable
        ):
            validate_image_row(row, row_label, errors)
        if is_web_callable(callable_name):
            validate_web_row(row, row_label, errors)
        if is_artifact_build(callable_name, mode):
            validate_artifact_row(row, row_label, prior_steps, errors)

        register_step_aliases(prior_steps, row_label)


def validate_overview(
    overview: str,
    manifest: dict,
    errors: list[str],
) -> None:
    for field in DEMAND_OVERVIEW_FIELDS:
        if field not in overview:
            errors.append(f"skill-overview.md missing demand-understanding field: {field}")
    if "重新设计已有 skill" in overview:
        for field in REDESIGN_VERSION_FIELDS:
            if field not in overview:
                errors.append(f"redesign overview missing version field: {field}")

    validate_research(overview, errors)
    minimality_rows = validate_minimality(overview, manifest, errors)
    validate_example_strategy(overview, minimality_rows, errors)


def validate_sample_case(sample_case_path: Path, errors: list[str]) -> None:
    try:
        sample_case = json.loads(sample_case_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"working/sample-case.json is not valid JSON: {exc}")
        return
    if not isinstance(sample_case, dict):
        errors.append("working/sample-case.json must contain a JSON object")
        return
    for key in SAMPLE_CASE_KEYS:
        value = sample_case.get(key)
        if value in (None, "", [], {}):
            errors.append(f"working/sample-case.json missing or empty key: {key}")


def validate_full_package(package_dir: Path, manifest: dict, errors: list[str]) -> None:
    validate_manifest(package_dir, manifest, errors)
    require_paths(package_dir, REQUIRED_PROPOSAL_FILES, errors)
    require_paths(package_dir, REQUIRED_WORKING_FILES, errors)
    validate_expected_preview_files(package_dir, manifest, errors)

    examples = expected_examples(manifest)
    if not examples:
        errors.append("manifest expected_files.examples is empty")
    for example in examples:
        if "<role>" in example:
            errors.append(f"example placeholder was not replaced: {example}")
            continue
        relative_path = example if example.startswith("examples/") else f"examples/{example}"
        if not (package_dir / relative_path).exists():
            errors.append(f"missing expected example file: {relative_path}")

    examples_dir = package_dir / "examples"
    example_files = [path for path in examples_dir.glob("*") if path.is_file()]
    if not example_files:
        errors.append("examples/ has no real files")

    deliverable_types = {
        str(item).lower().lstrip(".")
        for item in manifest.get("deliverable_types", [])
        if str(item).strip()
    }
    example_exts = {path.suffix.lower().lstrip(".") for path in example_files if path.suffix}
    missing_exts = sorted(deliverable_types - example_exts)
    if missing_exts:
        errors.append(f"examples/ missing declared deliverable types: {', '.join(missing_exts)}")

    preview_index_path = package_dir / "proposal/deliverable-preview-index.md"
    if preview_index_path.exists():
        validate_preview_index(
            preview_index_path.read_text(encoding="utf-8"),
            package_dir,
            manifest,
            errors,
        )

    confirmation_path = package_dir / "proposal/confirmation-questions.md"
    if confirmation_path.exists():
        validate_confirmation_questions(
            confirmation_path.read_text(encoding="utf-8"),
            errors,
        )

    workflow_path = package_dir / "proposal/workflow-tool-map.md"
    if workflow_path.exists():
        validate_workflow(workflow_path.read_text(encoding="utf-8"), errors)

    overview_path = package_dir / "proposal/skill-overview.md"
    if overview_path.exists():
        validate_overview(overview_path.read_text(encoding="utf-8"), manifest, errors)

    sample_case_path = package_dir / "working/sample-case.json"
    if sample_case_path.exists():
        validate_sample_case(sample_case_path, errors)


def validate_final_response(
    response_path: Path,
    package_dir: Path,
    errors: list[str],
) -> None:
    if not response_path.exists():
        errors.append(f"final response file not found: {response_path}")
        return

    text = response_path.read_text(encoding="utf-8")
    positions: list[int] = []
    for heading in FINAL_HEADINGS:
        matches = list(
            re.finditer(
                rf"^#{{1,6}}\s+{re.escape(heading)}\s*$",
                text,
                re.MULTILINE,
            )
        )
        position = matches[0].start() if matches else -1
        if not matches:
            errors.append(f"final response missing heading: {heading}")
        elif len(matches) != 1:
            errors.append(f"final response heading must appear exactly once: {heading}")
        positions.append(position)

    if all(position >= 0 for position in positions) and positions != sorted(positions):
        errors.append("final response headings are not in the required order")

    deliverable_section = section_between(text, "最终交付示例文件", "产物与下一步")
    if deliverable_section:
        visible_deliverable_section = strip_html_comments(deliverable_section)
        example_paths = relative_paths_in_cell(visible_deliverable_section, "examples")
        if not example_paths:
            errors.append("final deliverable section does not reference a real examples/ file")
        for relative_path in sorted(example_paths):
            validate_package_relative_file(
                package_dir,
                relative_path,
                "final response deliverable example",
                errors,
            )
        for pattern in FINAL_DELIVERABLE_FORBIDDEN_PATTERNS:
            if pattern in visible_deliverable_section:
                errors.append(f"final deliverable section lists support file: {pattern}")

    # 无确认门: 末节 产物与下一步 只需存在(上面已校验 heading), 不再校验固定选项。


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate skill-design proposal package structure and final response contracts."
    )
    parser.add_argument("package_path", help="Path to the generated skill-design example package")
    parser.add_argument(
        "--final-response",
        help="Optional Markdown file containing the final chat response to validate.",
    )
    parser.add_argument(
        "--scaffold-only",
        action="store_true",
        help="Only validate directories and manifest for a freshly scaffolded package.",
    )
    args = parser.parse_args()

    package_dir = Path(args.package_path).expanduser().resolve()
    errors: list[str] = []
    if not package_dir.exists():
        errors.append(f"package path does not exist: {package_dir}")
    elif not package_dir.is_dir():
        errors.append(f"package path is not a directory: {package_dir}")

    manifest = load_manifest(package_dir, errors) if not errors else None
    if manifest is not None:
        if args.scaffold_only:
            validate_scaffold(package_dir, manifest, errors)
        else:
            validate_full_package(package_dir, manifest, errors)

    if args.final_response:
        validate_final_response(
            Path(args.final_response).expanduser().resolve(),
            package_dir,
            errors,
        )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    mode = "scaffold" if args.scaffold_only else "full"
    print(f"OK: {mode} package contract validated: {package_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
