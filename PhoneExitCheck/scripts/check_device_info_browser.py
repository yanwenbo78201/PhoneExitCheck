#!/usr/bin/env python3
"""
对比工程目录中的 .h / .m / .swift 是否包含给定设备 Identifier 与 Generation 字符串。

与旧版 check_device_info.py 的 CLI 与 JSON 输出格式兼容。默认会用 Playwright 打开
https://theapplewiki.com/wiki/Models 拉取在线页面并解析表格用于校验与统计。
传入 **`--no-models-fetch`** 时**不**拉取在线 Models，仅做工程目录字符串扫描，并仍可读
`scripts/theapplewiki_pages`（或环境变量 PHONEEXITCHECK_WIKI_PAGES_DIR）下的词条 HTML，
从 **Identifiers** 段 wikitable 解析 **Connectivity / Storage** 写入输出的 device_models。

依赖：pip install playwright beautifulsoup4 && playwright install chromium

若遇 Cloudflare：需使用有界面浏览器完成验证；首次建议单独运行一次以便持久化目录写入 Cookie。
诊断信息一律输出到 stderr，stdout 仅打印 JSON（供 macOS 宿主 App 解析）。
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import sys
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError as _e:
    raise SystemExit("请先安装: pip install beautifulsoup4") from _e

MODELS_URL = "https://theapplewiki.com/wiki/Models"

# 与 fetch_theapplewiki_browser 类似的持久化目录，便于复用 Cookie
_DEFAULT_PLAYWRIGHT_USER_DATA = (
    Path.home() / "Library/Application Support/PhoneExitCheck/playwright-theapplewiki"
)


def _script_dir() -> Path:
    return Path(__file__).resolve().parent


def _import_parse_html_content():
    sys.path.insert(0, str(_script_dir()))
    from parse_apple_models import parse_html_content  # noqa: WPS433

    return parse_html_content


def fetch_models_html(
    *,
    user_data_dir: Path | None = None,
    headless: bool = False,
    timeout_ms: int = 120_000,
) -> tuple[str | None, str | None]:
    """
    使用 Chromium 拉取 Models 页 HTML。
    返回 (html, error_message)；成功时 error_message 为 None。
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, (
            "未安装 Playwright。请执行: pip install playwright && python3 -m playwright install chromium"
        )

    profile = user_data_dir or _DEFAULT_PLAYWRIGHT_USER_DATA
    profile.mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                str(profile),
                headless=headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.set_default_timeout(timeout_ms)
            page.goto(MODELS_URL, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                page.wait_for_selector("table", timeout=timeout_ms)
            except Exception as ex:
                print(f"[check_device_info_browser] 等待表格: {ex}", file=sys.stderr)
            html = page.content()
            ctx.close()

        if not html or len(html) < 5000:
            return None, "页面过短，可能被拦截或未加载完成。"

        if "Identifier" not in html:
            return (
                None,
                "页面中未找到 Identifier 列，可能仍为人机验证页；"
                "请在可见浏览器窗口完成验证后重试。",
            )
        return html, None
    except Exception as ex:
        return None, f"Playwright 拉取失败: {ex}"


def parse_models_device_map(html: str) -> dict[str, dict]:
    parse_html_content = _import_parse_html_content()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return parse_html_content(html)


def _wiki_pages_dir() -> Path:
    env = os.environ.get("PHONEEXITCHECK_WIKI_PAGES_DIR", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return _script_dir() / "theapplewiki_pages"


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _wikitables_in_identifiers_section(soup: BeautifulSoup) -> list:
    """
    仅选取 h2#Identifiers 之后紧邻的 section 内的 wikitable，
    避免整页其它表格（导航、对比表等）误匹配。
    """
    h2 = soup.select_one("h2#Identifiers")
    if h2 is None:
        return []
    sec = h2.find_next("section")
    if sec is None:
        return []
    return sec.find_all(
        "table", class_=lambda c: c and "wikitable" in c.split()
    )


def _filename_generation_score(fname: str, generation: str | None) -> int:
    """词条文件名与 Models 中 Generation 文案的粗略重合度，用于多 HTML 命中时择优。"""
    if not generation:
        return 0
    stem = Path(fname).stem.replace("_", " ").lower()
    gen = generation.lower().replace(" ", "")
    score = 0
    for tok in re.findall(r"[a-z0-9]+", stem):
        if len(tok) > 2 and tok in gen:
            score += 1
    return score


def _find_identifiers_table_column_indices(
    header_texts: list[str],
) -> tuple[int | None, int | None, int | None]:
    """表头行中定位 ProductType、Connectivity、Storage 列下标（Identifiers 下 wikitable）。"""
    lower = [h.strip().lower() for h in header_texts]
    pi = ci = si = None
    for i, h in enumerate(lower):
        hs = h.replace(" ", "")
        if "producttype" in hs:
            pi = i
        if "connectivity" in hs:
            ci = i
        if h.strip().lower() == "storage":
            si = i
    return pi, ci, si


def _extract_identifiers_row_fields(
    table,
    identifier: str,
    generation: str | None,
) -> tuple[str | None, str | None, int | None]:
    """
    在单张 wikitable 中，按 ProductType 列匹配 Identifier（或 Generation 子串），
    返回 (Connectivity, Storage, 匹配等级)。等级 0=ProductType 全等，1=包含 identifier，2=含 generation。
    """
    rows = table.find_all("tr")
    if len(rows) < 2:
        return None, None, None
    headers = [
        _normalize_ws(c.get_text(" ", strip=True))
        for c in rows[0].find_all(["th", "td"])
    ]
    pi, ci, si = _find_identifiers_table_column_indices(headers)
    if pi is None or ci is None:
        return None, None, None

    id_norm = (identifier or "").strip()
    gen_norm = (generation or "").strip()

    exact: list[tuple[str, str]] = []
    sub_id: list[tuple[str, str]] = []
    sub_gen: list[tuple[str, str]] = []

    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        idx_need = max(pi, ci, si if si is not None else -1)
        if len(cells) <= idx_need:
            continue
        pt = _normalize_ws(cells[pi].get_text(" ", strip=True))
        conn = (
            _normalize_ws(cells[ci].get_text(" ", strip=True)) if ci < len(cells) else ""
        )
        stor = ""
        if si is not None and si < len(cells):
            stor = _normalize_ws(cells[si].get_text(" ", strip=True))

        if not conn and not stor:
            continue

        if id_norm and pt == id_norm:
            exact.append((conn, stor))
        elif id_norm and id_norm in pt.replace(" ", ""):
            sub_id.append((conn, stor))
        elif gen_norm and gen_norm.lower() in pt.lower():
            sub_gen.append((conn, stor))

    def _pick(bucket: list[tuple[str, str]]) -> tuple[str | None, str | None]:
        c, s = bucket[0]
        return (c if c else None, s if s else None)

    if exact:
        c, s = _pick(exact)
        return c, s, 0
    if sub_id:
        c, s = _pick(sub_id)
        return c, s, 1
    if sub_gen:
        c, s = _pick(sub_gen)
        return c, s, 2
    return None, None, None


def _extract_best_from_identifiers_section(
    html: str,
    identifier: str,
    generation: str | None,
) -> tuple[str | None, str | None, int | None]:
    """
    仅在 Identifiers 小节内查找 wikitable；多表时取匹配等级最优的一表。
    若无 h2#Identifiers，则回退为整页 wikitable（兼容旧导出 HTML）。
    """
    if "ProductType" not in html or "Connectivity" not in html:
        return None, None, None
    soup = BeautifulSoup(html, "html.parser")
    tables = _wikitables_in_identifiers_section(soup)
    if not tables and soup.select_one("h2#Identifiers") is None:
        tables = soup.find_all(
            "table", class_=lambda c: c and "wikitable" in c.split()
        )
    best_tier: int | None = None
    best_cs: tuple[str | None, str | None] = (None, None)

    for table in tables:
        conn, stor, tier = _extract_identifiers_row_fields(table, identifier, generation)
        if tier is None:
            continue
        if best_tier is None or tier < best_tier:
            best_tier = tier
            best_cs = (conn, stor)
            if tier == 0:
                break

    if best_tier is None:
        return None, None, None
    return best_cs[0], best_cs[1], best_tier


def lookup_identifiers_table_from_saved_pages(
    pages_dir: Path,
    identifier: str,
    generation: str | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    """
    在 pages_dir 下扫描 .html，仅在各页 **Identifiers** 小节解析 ProductType 同行
    Connectivity、Storage。多文件命中时：优先匹配等级，再按文件名与 Generation 重合度。
    """
    if not identifier:
        return None, None, None, "empty_identifier"
    if not pages_dir.is_dir():
        return None, None, None, "no_pages_dir"
    html_files = sorted(pages_dir.glob("*.html"))
    if not html_files:
        return None, None, None, "no_html_files"

    saw_identifier_in_file = False
    candidates: list[tuple[int, int, str | None, str | None, str]] = []

    for path in html_files:
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if identifier not in raw:
            continue
        saw_identifier_in_file = True
        conn, stor, tier = _extract_best_from_identifiers_section(
            raw, identifier, generation
        )
        if tier is None or (not conn and not stor):
            continue
        score = _filename_generation_score(path.name, generation)
        candidates.append((tier, score, conn, stor, path.name))

    if candidates:
        best = min(candidates, key=lambda x: (x[0], -x[1], -len(x[4])))
        return best[2], best[3], best[4], None

    if not saw_identifier_in_file:
        return None, None, None, "no_page_contains_identifier"
    return None, None, None, "table_parse_no_match"


def lookup_connectivity_from_saved_pages(
    pages_dir: Path,
    identifier: str,
    generation: str | None,
) -> tuple[str | None, str | None, str | None]:
    """兼容旧接口：仅返回 connectivity 与文件名、原因。"""
    conn, stor, name, reason = lookup_identifiers_table_from_saved_pages(
        pages_dir, identifier, generation
    )
    return conn, name, reason


def build_device_models_with_connectivity(
    identifiers: list[str],
    generations: list[str],
    device_map: dict[str, dict],
    pages_dir: Path,
) -> tuple[list[dict], dict[str, str | None], dict[str, str | None], list[dict]]:
    """
    合并 Models 在线解析行与本地维基词条页 Identifiers 表中的 Connectivity、Storage。
    返回 (device_models, connectivity_by_identifier, storage_by_identifier, notes)
    """
    connectivity_by_identifier: dict[str, str | None] = {}
    storage_by_identifier: dict[str, str | None] = {}
    notes: list[dict] = []
    device_models: list[dict] = []

    for i, gid in enumerate(identifiers):
        gen = generations[i] if i < len(generations) else None
        base = dict(device_map.get(gid, {})) if device_map else {}
        conn, stor, src, reason = lookup_identifiers_table_from_saved_pages(
            pages_dir, gid, gen
        )
        connectivity_by_identifier[gid] = conn
        storage_by_identifier[gid] = stor
        if (
            not conn
            and not stor
            and reason
            and reason not in ("no_pages_dir", "no_html_files")
        ):
            notes.append({"identifier": gid, "reason": reason})

        entry: dict = {**base, "identifier": gid, "app_generation": gen, "connectivity": conn}
        if stor:
            entry["Storage"] = stor
        if src:
            entry["identifiers_table_wiki_page"] = src
        device_models.append(entry)

    return device_models, connectivity_by_identifier, storage_by_identifier, notes


def find_files_with_device_info(folder_path, identifiers, generations):
    """与 check_device_info.py 相同逻辑。"""
    extensions = (".h", ".m", ".swift")

    found_files = []
    found_identifiers = set()
    found_generations = set()

    for root, _dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(extensions):
                file_path = os.path.join(root, file)

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                        for identifier in identifiers:
                            if identifier in content:
                                found_files.append(file_path)
                                found_identifiers.add(identifier)

                        for generation in generations:
                            if generation and generation in content:
                                found_files.append(file_path)
                                found_generations.add(generation)

                except OSError as e:
                    print(f"Error reading file {file_path}: {e}", file=sys.stderr)

    found_files = list(set(found_files))

    return {
        "folder_path": folder_path,
        "total_identifiers": len(identifiers),
        "total_generations": len([g for g in generations if g]),
        "found_identifiers": list(found_identifiers),
        "found_generations": list(found_generations),
        "found_files": found_files,
        "not_found_identifiers": [i for i in identifiers if i not in found_identifiers],
        "not_found_generations": [g for g in generations if g and g not in found_generations],
    }


def main() -> None:
    raw_args = sys.argv[1:]
    no_models_fetch = "--no-models-fetch" in raw_args
    pos_args = [a for a in raw_args if a != "--no-models-fetch"]

    if len(pos_args) < 3:
        print(
            "Usage: python3 check_device_info_browser.py "
            "<folder_path> <identifiers_json> <generations_json> [--no-models-fetch]",
            file=sys.stderr,
        )
        sys.exit(1)

    folder_path = pos_args[0]
    identifiers = json.loads(pos_args[1])
    generations = json.loads(pos_args[2])

    headless = os.environ.get("PHONEEXITCHECK_HEADLESS", "").strip() in ("1", "true", "yes")
    custom_profile = os.environ.get("PHONEEXITCHECK_PLAYWRIGHT_USER_DATA")
    user_data_dir = Path(custom_profile).expanduser() if custom_profile else None

    fetch_err: str | None = None
    device_map: dict[str, dict] = {}

    if no_models_fetch:
        print(
            "[check_device_info_browser] 已跳过在线 Models 拉取（--no-models-fetch）。",
            file=sys.stderr,
        )
    else:
        print("[check_device_info_browser] 正在拉取 Models 页面…", file=sys.stderr)
        html, fetch_err = fetch_models_html(
            user_data_dir=user_data_dir, headless=headless
        )

        if html:
            print("[check_device_info_browser] 正在解析维基表格…", file=sys.stderr)
            try:
                device_map = parse_models_device_map(html)
            except Exception as ex:
                fetch_err = f"解析 Models 表格失败: {ex}"
                device_map = {}

        if html and not device_map and fetch_err is None:
            fetch_err = "未能从 Models 页解析到任何设备行（表格结构可能已变更）。"

    result = find_files_with_device_info(folder_path, identifiers, generations)

    result["models_fetch_skipped"] = no_models_fetch
    if no_models_fetch:
        result["models_fetch_ok"] = True
        result["models_fetch_error"] = ""
        result["models_page_device_count"] = 0
        result["identifiers_not_on_models_page"] = []
        result["generation_mismatches_vs_wiki"] = []
    else:
        result["models_fetch_ok"] = fetch_err is None and bool(device_map)
        result["models_fetch_error"] = fetch_err or ""
        result["models_page_device_count"] = len(device_map)
        result["identifiers_not_on_models_page"] = [
            i for i in identifiers if i and i not in device_map
        ]

        # 可选：若维基行存在 Generation，标出 App 传入的 Generation 与维基不一致（仅诊断）
        generation_mismatches = []
        for i, gid in enumerate(identifiers):
            if i >= len(generations):
                break
            g = generations[i]
            row = device_map.get(gid) if device_map else None
            if not row or not g:
                continue
            wiki_g = row.get("Generation")
            if wiki_g and wiki_g != g:
                generation_mismatches.append(
                    {"identifier": gid, "app_generation": g, "wiki_generation": wiki_g}
                )
        result["generation_mismatches_vs_wiki"] = generation_mismatches

    pages_dir = _wiki_pages_dir()
    device_models, conn_by_id, stor_by_id, id_notes = build_device_models_with_connectivity(
        identifiers, generations, device_map, pages_dir
    )
    result["device_models"] = device_models
    result["connectivity_by_identifier"] = conn_by_id
    result["storage_by_identifier"] = stor_by_id
    result["identifiers_table_lookup_notes"] = id_notes
    result["connectivity_pages_dir"] = str(pages_dir)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
