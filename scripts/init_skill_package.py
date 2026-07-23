#!/usr/bin/env python3
"""建一个「可上传目标 skill」的最小工作目录: <pkg>/target/ + 一份合法 manifest 骨架。

只做这一件事 —— 不再生成 proposal/examples/previews/working 等设计记录(那些永不进最终 zip)。
LLM 拿到骨架后只需: 写 target/SKILL.md → (按需改 target/manifest.json / 加 target/scripts/) → pack。
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

DEFAULT_ROOT = Path("/uploads/skill-design")


def sayu_slug(value: str) -> str:
    """sayu 合法 skill slug: ^[a-z][a-z0-9_-]{1,62}$ (小写字母开头)。"""
    s = re.sub(r"[^a-z0-9_-]+", "-", value.strip().lower())
    s = re.sub(r"-{2,}", "-", s).strip("-_")
    if not s:
        s = "skill"
    if not ("a" <= s[0] <= "z"):
        s = "s-" + s
    return s[:63]


def build_manifest(slug: str, name: str, description: str) -> dict:
    """合法 sayu skill manifest 骨架(对齐 pack_skill_package.py 的必填校验)。

    提示词 skill 保持 runtime_type=python + entry_main=SKILL.md; 绝不要写 prompt/md 等非法值。
    需要联网/pip 装包时改 network_policy=open 并加 target/requirements.txt。
    子工具在 dependencies 里以 platform_tools_* slug 声明; 密钥在 secrets[] 里声明。
    """
    return {
        "slug": slug,
        "kind": "skill",
        "name": name,
        "description": description,
        "version": "v1",
        "runtime_type": "python",
        "entry_main": "SKILL.md",
        "input_schema": {"type": "object", "properties": {}},
        "dependencies": [],
        "network_policy": "none",
        "timeout_sec": 120,
        "memory_mb": 1024,
        "cpu_quota": 1.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Init an uploadable target-skill package dir.")
    parser.add_argument("slug", help="目标 skill slug(会被规整成 ^[a-z][a-z0-9_-]{1,62}$)")
    parser.add_argument("name", help="目标 skill 展示名")
    parser.add_argument("description", help="目标 skill 一句话描述(注入运行时/市场展示)")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help=f"输出根。默认 {DEFAULT_ROOT}")
    args = parser.parse_args()

    slug = sayu_slug(args.slug)
    date = datetime.now().strftime("%Y-%m-%d")
    pkg_dir = Path(args.root).expanduser() / f"{slug}-{date}"
    target = pkg_dir / "target"
    # 已存在则加 -02/-03 避让, 不覆盖既有产物。
    i = 2
    while pkg_dir.exists():
        pkg_dir = Path(args.root).expanduser() / f"{slug}-{date}-{i:02d}"
        target = pkg_dir / "target"
        i += 1
    target.mkdir(parents=True, exist_ok=True)

    (target / "manifest.json").write_text(
        json.dumps(build_manifest(slug, args.name, args.description), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # 只打印目录路径(isfile=False, 不会被产物回流当文件卡) + 下一步指引。
    print("\n".join([
        f"已创建目标 skill 工作目录(合法 manifest 骨架已就位): {pkg_dir}",
        f"target_slug: {slug}",
        "",
        "下一步(每步一次 run_script):",
        "  1) 写 target/SKILL.md —— 目标 skill 的真实工作流入口(注入其运行时 system prompt)。",
        "     用 heredoc 避免引号转义炸: python - <<'PY' 里 open('target/SKILL.md','w').write('''...''')",
        "  2) 按需改 target/manifest.json(dependencies 填 platform_tools_* / network_policy / secrets),",
        "     只有确需可执行逻辑时才加 target/scripts/ 或 target/requirements.txt(默认纯 SKILL.md)。",
        f'  3) 打包(内含合法性硬校验): python scripts/pack_skill_package.py "{pkg_dir}"',
        "     # 只打 target/ 成根级可上传 zip, 打印其 /uploads/*.zip 路径回流 —— 这就是可用 skill 包。",
        "  4) 简短呈现: 这个 skill 做什么 + 在 sayu 端点「挂载」即导入为你的私有 skill。不编造交付示例文件。",
    ]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
