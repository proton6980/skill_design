#!/usr/bin/env python3
"""Create a skill-design example package without creating a target skill."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


DEFAULT_ROOT = Path("/uploads/skill-design/示例")
MANIFEST_VERSION = "1.0"
SUBDIRS = ("proposal", "examples", "previews", "working")


def normalize_slug(value: str) -> str:
    cleaned = value.strip()
    cleaned = cleaned.replace("/", "-").replace("\\", "-").replace(":", "-")
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    cleaned = cleaned.strip("-. ")
    return cleaned or "case"


def parse_deliverables(raw: str) -> list[str]:
    if not raw.strip():
        return []
    items: list[str] = []
    for item in raw.split(","):
        normalized = item.strip().lower().lstrip(".")
        if normalized and normalized not in items:
            items.append(normalized)
    return items


def unique_package_path(base: Path, reuse: bool) -> Path:
    if reuse or not base.exists():
        return base
    index = 2
    while True:
        candidate = base.with_name(f"{base.name}-{index:02d}")
        if not candidate.exists():
            return candidate
        index += 1


def build_manifest(
    package_dir: Path,
    target_family: str,
    target_skill_name: str,
    case_name: str,
    case_slug: str,
    deliverables: list[str],
) -> dict:
    expected_examples = [f"<role>.{ext}" for ext in deliverables]
    return {
        "manifest_version": MANIFEST_VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "target_skill_family": target_family,
        "target_skill_name": target_skill_name,
        "case_name": case_name,
        "case_slug": case_slug,
        "package_path": str(package_dir),
        "directories": {
            "proposal": "proposal/",
            "examples": "examples/",
            "previews": "previews/",
            "working": "working/",
        },
        "deliverable_types": deliverables,
        "expected_files": {
            "proposal": [
                "proposal/skill-overview.md",
                "proposal/workflow-tool-map.md",
                "proposal/deliverable-preview-index.md",
                "proposal/confirmation-questions.md",
            ],
            "examples": expected_examples,
            "previews": [],
            "working": [
                "working/sample-case.json",
                "working/generation-notes.md",
            ],
        },
        "validation_notes": [
            "This package scaffolds design examples only.",
            "Complete the research gate before filling a full package.",
            "Do not create or edit the target skill from this script.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a standardized example package for skill-design proposals."
    )
    parser.add_argument("target_skill_family", help="Target base skill family, e.g. ppt-brief")
    parser.add_argument("target_skill_name", help="Target version folder name, e.g. ppt-brief-v1-8")
    parser.add_argument("case_name", help="Human-readable simulated case name")
    parser.add_argument(
        "--root",
        default=str(DEFAULT_ROOT),
        help=f"Example archive root. Default: {DEFAULT_ROOT}",
    )
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Package date prefix in YYYY-MM-DD format. Default: today",
    )
    parser.add_argument(
        "--deliverables",
        default="",
        help="Comma-separated deliverable extensions, e.g. docx,xlsx,html",
    )
    parser.add_argument(
        "--reuse",
        action="store_true",
        help="Reuse the exact package path if it already exists instead of creating -02.",
    )
    args = parser.parse_args()

    target_family = normalize_slug(args.target_skill_family)
    target_skill_name = normalize_slug(args.target_skill_name)
    case_slug = normalize_slug(args.case_name)
    deliverables = parse_deliverables(args.deliverables)

    root = Path(args.root).expanduser()
    base_package_dir = root / target_family / target_skill_name / f"{args.date}-{case_slug}"
    package_dir = unique_package_path(base_package_dir, args.reuse)

    for subdir in SUBDIRS:
        (package_dir / subdir).mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(
        package_dir=package_dir,
        target_family=target_family,
        target_skill_name=target_skill_name,
        case_name=args.case_name,
        case_slug=case_slug,
        deliverables=deliverables,
    )
    manifest_path = package_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {"package_path": str(package_dir), "manifest_path": str(manifest_path)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
