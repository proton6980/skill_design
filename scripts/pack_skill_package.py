#!/usr/bin/env python3
"""把设计包里的 target/ 打成「可直接上传的 sayu skill zip」，打印该 zip 的 /uploads 绝对路径。

与 pack_package.py 的区别(关键):
- pack_package.py 打**整个设计方案包**(proposal/examples/…), 给人下载审阅, 布局带包裹目录, **不可上传**。
- 本脚本只打 **target/** 内容, 且**放在 zip 根**(`manifest.json`/`SKILL.md`/`scripts/…` 在压缩包根) ——
  sayu 上传解析 (`ManifestParser`) 只认根目录的 `manifest.json`, `CapabilityZipExtractor` 保留完整条目路径不剥包裹目录,
  所以目标 skill 文件必须在 zip 根。这就是「打包为可上传的 skill 包」真正要交付的东西。

为什么固定时间戳: 同内容两次打包字节须一致 → sha 稳定, 否则后端内容寻址 / update-from-github no-op 失效
(对齐 GitHubSkillImporter.buildImportZip)。沙箱无 `zip` CLI, 用 stdlib zipfile, 离线可跑。

产物回流: 平台只回流 stdout 里**单个真实文件**(`isfile`), 故只打印这一个 zip 的 /uploads 路径。
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]{1,62}$")
PLACEHOLDER_RE = re.compile(r"<[^>\n]{1,40}>|TODO|TBD|FIXME|占位")
FIXED_DATE_TIME = (2020, 1, 1, 0, 0, 0)  # 固定时间戳 → 同内容 → 同 sha


def _fail(msg: str) -> "SystemExit":
    return SystemExit(f"[pack_skill_package] 失败: {msg}")


def _validate_target(target_dir: Path) -> tuple[str, list[Path]]:
    """轻校验 target/ 是一个合法可上传 skill; 返回 (slug, 待打包文件列表)。"""
    if not target_dir.is_dir():
        raise _fail(f"缺少 target/ 目录: {target_dir}")

    manifest_path = target_dir / "manifest.json"
    if not manifest_path.is_file():
        raise _fail("target/manifest.json 不存在(先写目标 skill 的 manifest)")
    try:
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        raise _fail(f"target/manifest.json 非法 JSON: {e}")

    for key in ("slug", "kind", "name", "version", "runtime_type", "entry_main"):
        if not str(m.get(key, "")).strip():
            raise _fail(f"target/manifest.json 缺必填字段: {key}")
    if m.get("kind") != "skill":
        raise _fail(f"target/manifest.json kind 必须是 'skill'(当前 {m.get('kind')!r})")

    slug = str(m["slug"]).strip()
    if not SLUG_RE.match(slug):
        raise _fail(f"target/manifest.json slug 非法(须 ^[a-z][a-z0-9_-]{{1,62}}$): {slug!r}")

    entry = str(m["entry_main"]).strip()
    if not entry.lower().endswith(".md"):
        raise _fail(f"skill 的 entry_main 须是 .md 文件: {entry!r}")
    if not (target_dir / entry).is_file():
        raise _fail(f"entry_main 声明的文件不在 target/ 内: {entry}")

    files = [p for p in sorted(target_dir.rglob("*")) if p.is_file()]
    if not files:
        raise _fail("target/ 内没有文件")

    # 占位符闸: SKILL.md / manifest.json 不得残留 <占位>/TODO/TBD(会当真被上传)。
    for rel in (entry, "manifest.json"):
        text = (target_dir / rel).read_text(encoding="utf-8", errors="replace")
        hit = PLACEHOLDER_RE.search(text)
        if hit:
            raise _fail(f"target/{rel} 残留占位符/待办: {hit.group(0)!r} —— 先填实再打包")

    return slug, files


def pack(package_dir: Path) -> Path:
    package_dir = package_dir.resolve()
    # 允许直接传 target/ 或传设计包根(自动进 target/)。
    target_dir = package_dir if package_dir.name == "target" else package_dir / "target"
    slug, files = _validate_target(target_dir)

    # zip 落在设计包目录旁(同在 /uploads 下), 文件名 = 目标 slug + .zip。
    out_root = target_dir.parent
    zip_path = out_root / f"{slug}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            arcname = str(path.relative_to(target_dir))  # 根级布局: manifest.json / SKILL.md / scripts/…
            info = zipfile.ZipInfo(arcname, date_time=FIXED_DATE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pack the design package's target/ into one uploadable sayu skill zip."
    )
    parser.add_argument("package_path", help="设计方案包目录(/uploads/skill-design/... 下)或其 target/ 目录")
    args = parser.parse_args()
    zip_path = pack(Path(args.package_path))
    # 只打印这一个 zip 的绝对路径 → 平台回流成单张文件卡 → 即可上传的 skill 包
    print(str(zip_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
