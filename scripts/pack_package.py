#!/usr/bin/env python3
"""把一个设计方案包目录打成单个 zip，打印该 zip 的 /uploads 绝对路径。

为什么必须这么收尾（否则用户一个文件都收不到）：
- 平台 run_script 的产物回流 (`skill_sandbox/tool.py::_detect_output_file`) 只认 stdout 里
  **单个真实文件**（`os.path.isfile` 为真）——**目录不算**。打印 package_path 目录 → isfile=False → 不产卡。
- 沙箱基础镜像**没有 `zip` CLI**（只有 poppler/qpdf/curl），故用 stdlib `zipfile`，离线可跑。
一个 zip = 一个真实文件 = 一张文件卡，用户下载解压即整包。
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


def pack(package_dir: Path) -> Path:
    package_dir = package_dir.resolve()
    if not package_dir.is_dir():
        raise SystemExit(f"不是目录: {package_dir}")
    # zip 落在包目录旁边（同在 /uploads/... 下），文件名 = 包目录名 + .zip
    zip_path = package_dir.parent / f"{package_dir.name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(package_dir.rglob("*")):
            if path.is_file():
                # arcname 带上包目录名，解压即得一个命名文件夹
                arcname = Path(package_dir.name) / path.relative_to(package_dir)
                zf.write(path, arcname)
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Zip a design package directory into one reflowable file."
    )
    parser.add_argument("package_path", help="设计方案包目录（/uploads/skill-design/... 下）")
    args = parser.parse_args()
    zip_path = pack(Path(args.package_path))
    # 只打印这一个 zip 的绝对路径 → 平台回流成单张文件卡
    print(str(zip_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
