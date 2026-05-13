#!/usr/bin/env python3
"""
从 scripts/theapplewiki_pages 各词条页 **Identifiers** 段下的 wikitable（ProductType /
Connectivity / Storage 列）读取与硬件代号同行的 **Connectivity** 与 **Storage**，
合并进 PhoneExitCheck/apple_device_models.json。

依赖：beautifulsoup4（逻辑在 check_device_info_browser.py）

用法:
  python3 enrich_connectivity_from_wiki_pages.py
  python3 enrich_connectivity_from_wiki_pages.py --json ../apple_device_models.json --pages ./theapplewiki_pages
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _script_dir() -> Path:
    return Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json",
        type=Path,
        default=_script_dir().parent / "apple_device_models.json",
        help="apple_device_models.json 路径",
    )
    parser.add_argument(
        "--pages",
        type=Path,
        default=_script_dir() / "theapplewiki_pages",
        help="维基 HTML 目录",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(_script_dir()))
    from check_device_info_browser import lookup_identifiers_table_from_saved_pages

    data = json.loads(args.json.read_text(encoding="utf-8"))
    n_conn = n_stor = 0
    for ident, info in data.items():
        if not isinstance(info, dict):
            continue
        gen = info.get("Generation")
        conn, stor, _src, _reason = lookup_identifiers_table_from_saved_pages(
            args.pages, ident, gen
        )
        if conn:
            info["Connectivity"] = conn
            n_conn += 1
        else:
            info.pop("Connectivity", None)
        if stor:
            info["Storage"] = stor
            n_stor += 1
        else:
            # 无 Identifiers 表 Storage（如 IPhone_3G 页无该小节）则移除，避免沿用 Models 总表容量
            info.pop("Storage", None)

    args.json.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"已写入 {args.json}：共 {len(data)} 条；Identifiers 表补充 Connectivity {n_conn} 条、Storage {n_stor} 条。",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
