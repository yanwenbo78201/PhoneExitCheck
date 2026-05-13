#!/usr/bin/env python3
"""
使用真实浏览器会话批量保存 The Apple Wiki 词条页 HTML（用于离线查阅机型相关子页面）。

设计要点：
- 不尝试绕过 Cloudflare：由你在可见浏览器窗口里完成验证后再继续。
- 可选持久化用户数据目录，减少重复验证。
- 从起始页 + 可选本地 Models HTML 收集 wiki 内链，BFS 抓取，数量与间隔可控。
- 默认只抓取并保存与 iPhone / iPad / iPod / Apple TV 词条相关的页面（见 is_device_family_wiki_title）。
- 若输出目录中已有同名 HTML（与保存规则一致），则跳过该 URL 的网络下载与写盘，从本地解析链接并继续抓取其余页面。

依赖：
  pip install playwright beautifulsoup4
  playwright install chromium

用法示例：
  python3 fetch_theapplewiki_browser.py \\
    --out-dir ./theapplewiki_pages \\
    --max-pages 80 \\
    --delay 2.5

  python3 fetch_theapplewiki_browser.py \\
    --seed-html "Models - The Apple Wiki.html" \\
    --user-data-dir ~/.cache/phoneexitcheck-chromium-wiki \\
    --max-pages 120
"""

from __future__ import annotations

import argparse
import re
import time
from collections import deque
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse, parse_qs

try:
    from bs4 import BeautifulSoup
except ImportError as e:
    raise SystemExit("请先安装: pip install beautifulsoup4") from e

# 不抓取的命名空间（减少噪音与体积）
SKIP_TITLE_PREFIXES = (
    "Special:",
    "Talk:",
    "User:",
    "User_talk:",
    "File:",
    "MediaWiki:",
    "Template:",
    "Template_talk:",
    "Help:",
    "Category:",
    "The_Apple_Wiki:",
)


def _slug_from_url(url: str) -> str:
    p = urlparse(url)
    path = p.path.rstrip("/")
    if "/wiki/" in path:
        title = path.split("/wiki/", 1)[-1]
    elif path.endswith("/index.php"):
        q = parse_qs(p.query)
        titles = q.get("title", [])
        title = titles[0] if titles else "index"
    else:
        title = path.replace("/", "_") or "root"
    title = unquote(title)
    safe = re.sub(r"[^\w\-.,()]+", "_", title, flags=re.UNICODE)
    return safe[:200] or "page"


def normalize_wiki_url(url: str) -> str | None:
    """归一化为 https://theapplewiki.com/wiki/Title 形式（尽量）。"""
    url = url.split("#", 1)[0].strip()
    if not url:
        return None
    p = urlparse(url)
    host = p.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host != "theapplewiki.com":
        return None

    if p.path.startswith("/wiki/"):
        title = p.path[len("/wiki/") :]
        if not title:
            return None
        return f"https://theapplewiki.com/wiki/{title}"

    if p.path.endswith("index.php") or p.path.endswith("/index.php"):
        qs = parse_qs(p.query)
        titles = qs.get("title")
        if titles and titles[0]:
            t = titles[0]
            return f"https://theapplewiki.com/wiki/{t}"
    return None


def should_skip_title(title: str) -> bool:
    t = title.lstrip("/")
    for prefix in SKIP_TITLE_PREFIXES:
        if t.startswith(prefix):
            return True
    if "action=edit" in t or "redlink=1" in t:
        return True
    return False


def wiki_title_from_url(url: str) -> str:
    """从规范 wiki URL 取出词条标题（未解码片段）。"""
    p = urlparse(url)
    if not p.path.startswith("/wiki/"):
        return ""
    return unquote(p.path[6:])


def is_device_family_wiki_title(title: str) -> bool:
    """
    是否属于 iPhone / iPad / iPod / Apple TV 产品线词条（与 The Apple Wiki 常见命名一致）。
    """
    title = unquote(title).strip()
    if not title or should_skip_title(title):
        return False
    t = title.lower()
    if t.startswith("iphone"):
        return True
    if t.startswith("ipad"):
        return True
    if t.startswith("ipod"):
        return True
    if t.startswith("apple_tv") or t.startswith("appletv"):
        return True
    return False


def extract_wiki_links(
    html: str, page_url: str, *, device_only: bool = True
) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")
    found: set[str] = set()
    for a in soup.find_all("a", href=True):
        raw = a["href"].strip()
        joined = urljoin(page_url, raw)
        norm = normalize_wiki_url(joined)
        if not norm:
            continue
        # title 部分
        title = urlparse(norm).path
        if title.startswith("/wiki/"):
            title = title[6:]
        title = unquote(title)
        if should_skip_title(title):
            continue
        if device_only and not is_device_family_wiki_title(title):
            continue
        found.add(norm)
    return found


def find_cached_page_path(
    out_dir: Path, url: str, *, force_redownload: bool = False
) -> Path | None:
    """
    若 out_dir 中已有本脚本保存过的页面（主文件名 = _slug_from_url(url).html），返回该路径。
    带序号后缀的冲突文件名不视为缓存命中（避免误判其他 URL）。
    """
    if force_redownload or not out_dir.is_dir():
        return None
    primary = out_dir / f"{_slug_from_url(url)}.html"
    if primary.is_file() and primary.stat().st_size > 0:
        return primary
    return None


def save_page(out_dir: Path, url: str, html: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = _slug_from_url(url) + ".html"
    path = out_dir / fname
    # 避免不同 URL 映射到同一文件名时覆盖
    if path.exists():
        stem = path.stem
        for i in range(1, 1000):
            cand = out_dir / f"{stem}_{i}.html"
            if not cand.exists():
                path = cand
                break
    path.write_text(html, encoding="utf-8")
    return path


def collect_seeds_from_local_html(
    html_path: Path, *, device_only: bool = True
) -> set[str]:
    text = html_path.read_text(encoding="utf-8", errors="replace")
    base = "https://theapplewiki.com/wiki/Models"
    return extract_wiki_links(text, base, device_only=device_only)


def run() -> None:
    parser = argparse.ArgumentParser(
        description="在真实浏览器中通过验证后，批量保存 The Apple Wiki 页面 HTML。"
    )
    parser.add_argument(
        "--start-url",
        default="https://theapplewiki.com/wiki/Models",
        help="浏览器首先打开的页面（默认 Models）",
    )
    parser.add_argument(
        "--seed-html",
        action="append",
        default=[],
        metavar="PATH",
        help="可多次指定：从本地已保存的维基 HTML 中提取内链加入待抓队列",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("./theapplewiki_pages"),
        help="保存 HTML 的目录",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=60,
        help="本运行最多新下载并保存多少个词条页（已存在于 out-dir 的不计入）",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="每次导航之间的秒数，降低对站点的压力",
    )
    parser.add_argument(
        "--user-data-dir",
        type=Path,
        default=None,
        help="Chromium 用户数据目录（持久化 Cookie，建议指定）",
    )
    parser.add_argument(
        "--no-follow",
        action="store_true",
        help="只抓取队列中的 URL，不从已下载页面继续发现新链接",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="无头模式（通常无法通过 Cloudflare，默认关闭）",
    )
    parser.add_argument(
        "--all-wiki-pages",
        action="store_true",
        help="不限制产品线：抓取并保存所有非跳过命名空间的 wiki 内链（旧版行为）",
    )
    parser.add_argument(
        "--force-redownload",
        action="store_true",
        help="忽略 out-dir 中已有 HTML，一律重新下载保存",
    )
    args = parser.parse_args()
    device_only = not args.all_wiki_pages

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise SystemExit(
            "请先安装 Playwright:\n  pip install playwright\n  playwright install chromium"
        ) from e

    seeds: set[str] = set()
    for p in args.seed_html:
        hp = Path(p).expanduser().resolve()
        if not hp.is_file():
            print(f"[跳过] 找不到本地 HTML: {hp}")
            continue
        part = collect_seeds_from_local_html(hp, device_only=device_only)
        print(f"[种子] 从 {hp.name} 解析到 {len(part)} 个 wiki 内链")
        seeds |= part

    start = normalize_wiki_url(args.start_url) or args.start_url
    queue: deque[str] = deque()

    visited: set[str] = set()
    saved = 0
    skipped_cached = 0
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("\n即将启动浏览器。请在窗口内完成人机验证（如有），再回到终端按回车开始队列抓取。\n")
    if device_only:
        print("[过滤] 仅抓取 iPhone / iPad / iPod / Apple TV 相关词条页；起始页若非上述产品线则只用于发现链接、不写入磁盘。\n")

    browser = None
    with sync_playwright() as p:
        launch_kw = {
            "headless": args.headless,
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        if args.user_data_dir:
            args.user_data_dir.mkdir(parents=True, exist_ok=True)
            context = p.chromium.launch_persistent_context(
                str(args.user_data_dir),
                **launch_kw,
            )
            page = context.pages[0] if context.pages else context.new_page()
        else:
            browser = p.chromium.launch(**launch_kw)
            context = browser.new_context()
            page = context.new_page()

        page.goto(start, wait_until="domcontentloaded", timeout=120_000)
        input(">>> 验证完成后按回车开始抓取（Ctrl+C 可中止）…\n")

        start_nu = normalize_wiki_url(start)
        html_bootstrap = page.content()
        if start_nu:
            visited.add(start_nu)
            save_start = args.all_wiki_pages or is_device_family_wiki_title(
                wiki_title_from_url(start_nu)
            )
            if save_start and saved < args.max_pages:
                cached = find_cached_page_path(
                    args.out_dir, start_nu, force_redownload=args.force_redownload
                )
                if cached:
                    print(f"[起始页] 本地已有 {cached.name}，跳过保存")
                    skipped_cached += 1
                else:
                    try:
                        path = save_page(args.out_dir, start_nu, html_bootstrap)
                        print(f"[起始页] 已保存 {path.name}")
                        saved += 1
                    except Exception as ex:
                        print(f"[起始页] 保存失败: {ex}")

            if not args.no_follow:
                for link in extract_wiki_links(
                    html_bootstrap, start_nu, device_only=device_only
                ):
                    if link not in visited:
                        queue.append(link)

        for u in seeds:
            nu = normalize_wiki_url(u)
            if nu and nu not in visited:
                if device_only and not is_device_family_wiki_title(
                    wiki_title_from_url(nu)
                ):
                    continue
                queue.append(nu)

        while queue and saved < args.max_pages:
            url = queue.popleft()
            nu = normalize_wiki_url(url)
            if not nu or nu in visited:
                continue
            if device_only and not is_device_family_wiki_title(
                wiki_title_from_url(nu)
            ):
                continue
            visited.add(nu)

            cached = find_cached_page_path(
                args.out_dir, nu, force_redownload=args.force_redownload
            )
            if cached is not None:
                try:
                    html = cached.read_text(encoding="utf-8", errors="replace")
                except OSError as ex:
                    print(f"      读取本地缓存失败: {ex}，改为在线拉取")
                    cached = None

            if cached is not None:
                skipped_cached += 1
                print(f"[本地已有] 跳过下载 {cached.name}\n      {nu}")
            else:
                try:
                    print(f"[新下载 {saved + 1}/{args.max_pages}] 打开 {nu}")
                    page.goto(nu, wait_until="domcontentloaded", timeout=120_000)
                    time.sleep(max(0.0, args.delay))
                    html = page.content()
                    path = save_page(args.out_dir, nu, html)
                    print(f"      已保存 {path.name}")
                    saved += 1
                except Exception as ex:
                    print(f"      失败: {ex}")
                    continue

            if not args.no_follow:
                for link in extract_wiki_links(html, nu, device_only=device_only):
                    if link not in visited:
                        queue.append(link)

        context.close()
        if browser is not None:
            browser.close()

    print(
        f"\n完成：本运行新保存 {saved} 个页面；"
        f"跳过（本地已有）{skipped_cached} 个；目录 {args.out_dir.resolve()}"
    )


if __name__ == "__main__":
    run()
