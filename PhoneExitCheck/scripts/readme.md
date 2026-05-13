# fetch_theapplewiki_browser.py

在**真实 Chromium 窗口**中打开 [The Apple Wiki](https://theapplewiki.com/wiki/Models)，由你完成 Cloudflare 等验证后，按维基**内链广度优先**抓取页面并保存为本地 HTML。适用于机型对照、离线查阅或与项目内 `parse_apple_models.py` 等流程配合。

## 设计原则

- **不绕过站点防护**：依赖可见浏览器与人工验证，不使用伪造指纹或对抗 CDN 的手段。
- **默认只保留四类产品线词条**：`IPhone…`、`IPad…`、`IPod…`、`Apple_TV…` / `AppleTV…`（与维基常见标题一致）；`Special:`、`Talk:`、`Category:` 等命名空间会被排除。
- **断点续抓**：若 `--out-dir` 中已存在与 URL 对应的主文件名 `{词条 slug}.html`，则**跳过该页下载**，从本地文件解析链接并继续队列；`--max-pages` 只统计**本运行新保存**的篇数。
- **礼貌抓取**：通过 `--delay` 控制两次导航之间的间隔。

## 环境要求

- Python 3.9+（与当前项目一致即可）
- 依赖：

```bash
pip install playwright beautifulsoup4
python3 -m playwright install chromium
```

若从 PyPI 安装较慢，可自行换镜像，例如：

```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple playwright beautifulsoup4
```

## 基本用法

在 `PhoneExitCheck/scripts` 目录下执行：

```bash
python3 fetch_theapplewiki_browser.py --help
```

典型命令（持久化浏览器配置、合并本地 Models 页里的设备链接、输出到子目录）：

```bash
python3 fetch_theapplewiki_browser.py \
  --start-url "https://theapplewiki.com/wiki/Models" \
  --seed-html "Models - The Apple Wiki.html" \
  --user-data-dir "$HOME/.cache/phoneexitcheck-chromium-wiki" \
  --out-dir "./theapplewiki_pages" \
  --max-pages 80 \
  --delay 2.5
```

流程简述：

1. 启动 Chromium 并打开 `--start-url`（默认 Models）。
2. 在浏览器中**完成人机验证**（若出现）。
3. 回到终端**按回车**，脚本从当前页与种子 HTML 收集链接并入队，再依次访问并保存（或跳过已有文件）。

## 命令行参数

| 参数 | 说明 |
|------|------|
| `--start-url` | 首先打开的页面，默认 `https://theapplewiki.com/wiki/Models`。 |
| `--seed-html` | 可多次指定；从本地已保存的完整维基 HTML 中解析内链加入队列（常与浏览器另存的 `Models - The Apple Wiki.html` 配合）。 |
| `--out-dir` | 保存 HTML 的目录，默认 `./theapplewiki_pages`。 |
| `--max-pages` | 本运行**最多新下载并保存**的词条数；目录中已存在的主文件不计入。 |
| `--delay` | 每次在线 `goto` 后的等待秒数，默认 `2.0`（仅影响实际发起导航的间隔）。 |
| `--user-data-dir` | Chromium 用户数据目录，用于持久化 Cookie，减少重复验证。 |
| `--no-follow` | 只处理初始队列（起始页种子 + `--seed-html`），不从已抓页面继续发现新链接。 |
| `--headless` | 无头模式；多数情况下**无法通过 Cloudflare**，默认不建议开启。 |
| `--all-wiki-pages` | 关闭产品线过滤，行为接近早期「抓取非跳过命名空间下大量内链」的版本。 |
| `--force-redownload` | 忽略本地已有 `{slug}.html`，对每个 URL 重新在线下载并保存。 |

## 本地缓存规则

- 命中条件：`{out_dir}/{与 save_page 一致的主 slug}.html` 存在且非空。
- 若历史上因文件名冲突保存为 `slug_1.html` 等，**不会**视为该 URL 的缓存（避免误判）；该 URL 会再次在线拉取并尽量写回主文件名逻辑。
- 默认的 Models 起始页通常**不会**被保存（标题不属于四类产品线），但仍用于在浏览器中过验证并抽取设备词条链接。

## 与仓库其他脚本的关系

- **`parse_apple_models.py`**：从本地 HTML（例如另存的 Models 整页）解析表格并生成 `apple_device_models.json`；与本脚本职责分离，本脚本不负责改 JSON。
- 可将本脚本输出目录中的 HTML 留作离线参考，或按需再写小工具解析。

## 合规与使用建议

- 遵守 [The Apple Wiki](https://theapplewiki.com/) 的使用条款与内容许可（如 CC 等），合理控制 `--max-pages` 与 `--delay`，避免对服务器造成过大压力。
- 抓取结果仅供个人或团队开发、对照研究等合法用途。

---

## check_device_info_browser.py

由 **PhoneExitCheck** 在点击「对比」时调用：先用 Playwright 打开在线 [Models](https://theapplewiki.com/wiki/Models)（**不读取**仓库内本地 Models HTML），解析维基表格后，再对所选工程目录中的 `.h` / `.m` / `.swift` 做与旧版 `check_device_info.py` 相同的字符串扫描。

- **持久化目录**：默认 `~/Library/Application Support/PhoneExitCheck/playwright-theapplewiki`（可与浏览器抓取流程共用 Cookie）。
- **环境变量**：`PHONEEXITCHECK_HEADLESS=1` 尝试无头拉取（多数情况无法通过 Cloudflare）；`PHONEEXITCHECK_PLAYWRIGHT_USER_DATA` 可指向自定义 Chromium 用户数据目录。
- **stdout**：仅输出 JSON；诊断信息在 stderr。

### Connectivity（本地词条页）

若 `scripts/theapplewiki_pages/` 下有用 `fetch_theapplewiki_browser.py` 抓取的 HTML，对比结果中会多出：

- `device_models`：每条为 Models 在线表字段 + `identifier`、`app_generation`、`connectivity`、`connectivity_wiki_page`（若有）。
- `connectivity_by_identifier` / `storage_by_identifier`：来自本地维基 HTML 的 Identifiers 表。
- `identifiers_table_lookup_notes`：未解析到时的原因（如无页面、有页面但表不匹配）。
- 目录可通过环境变量 **`PHONEEXITCHECK_WIKI_PAGES_DIR`** 覆盖。

维基 **ProductType** 列为硬件代号（如 `iPad11,6`），脚本**优先用 Identifier 与 ProductType 单元格匹配**；若未命中且传入了 **Generation**，再尝试 **ProductType 文本包含 Generation 子串**（少数页面可用）。

## 常见问题

**终端提示找不到 `playwright`？**  
使用 `python3 -m playwright install chromium`，并用同一解释器运行脚本：`python3 fetch_theapplewiki_browser.py …`。

**一直 403 或无法加载？**  
在**有界面**模式下完成验证；必要时固定 `--user-data-dir` 后多试一次。

**想全站多类型词条而不仅是 iPhone/iPad/iPod/Apple TV？**  
加 `--all-wiki-pages`，并自行评估抓取范围与合规性。
