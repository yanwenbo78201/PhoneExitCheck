# PhoneExitCheck

一个用于检查 Apple 设备型号退出信息的 **macOS** 应用程序。设备列表数据参考 [The Apple Wiki · Models](https://theapplewiki.com/wiki/Models)。

## 功能特性

- **设备型号展示**：左侧表格展示 Identifier、Generation、**Connectivity**、**Storage**（后两列见下文数据准备与 Bundle 合并说明）
- **代码生成**：右侧自动生成 Objective-C 与 Swift 形式的设备型号映射代码
- **设备检查**：选择工程目录后「对比」，在 `.h` / `.m` / `.swift` 中检索是否已包含各 Identifier 与 Generation
- **iOS 15 兼容性提示**：对不支持 iOS 15+ 的机型在结果中标注 ⚠️

---

## 应用使用方式（Xcode）

1. **打开工程**：双击或用 Xcode 打开 `PhoneExitCheck.xcodeproj`。
2. **运行**：选择目标为 **My Mac**，点击 **Run (⌘R)** 启动应用。
3. **筛选设备**：顶部分段控件选择 **All / iPhone / iPad / Apple TV / iPod**（不含 Apple Watch、Apple TV 配件类）。
4. **查看与复制代码**：左侧点选行可结合右侧查看；使用 **「复制 OC 代码」** / **「复制 Swift 代码」** 将映射表复制到剪贴板。
5. **对比工程**：
   - 点击 **「选择文件夹」**，选中要检查的 Xcode 工程或其它源码根目录；
   - 点击 **「对比」**；
   - 应用会调用 `scripts/check_device_info_browser.py`：先用浏览器拉取在线 **Models** 页做校验，再结合本地 `theapplewiki_pages`（若有）补充信息，并在工程内搜索字符串；
   - 弹窗与下方文本区会列出 **未在工程中找到** 的 Identifier / Generation；若在线 Models 拉取失败，仍会使用应用内已加载的列表做扫描，并在文案中提示。

**Connectivity / Storage 列**：**Connectivity** 在走 Python 临时 JSON 时，会用 Bundle 内 `apple_device_models.json` 补全（与维基 **Identifiers** 表一致，需先 enrich）。**Storage** 仅展示 **维基词条页 Identifiers 表** enrich 写入 Bundle 的值；无该表/该列时 JSON 中不含 `Storage`，应用左侧为空，不会回退到 Models 总表容量。

---

## 项目结构（节选）

```
PhoneExitCheck/
├── PhoneExitCheck/
│   ├── scripts/
│   │   ├── parse_apple_models.py           # 从本地 Models HTML 解析并生成 JSON
│   │   ├── fetch_theapplewiki_browser.py # 浏览器抓取维基词条页到 theapplewiki_pages/
│   │   ├── enrich_connectivity_from_wiki_pages.py  # 将 Connectivity 写入 apple_device_models.json
│   │   ├── check_device_info_browser.py   # 供 App「对比」调用（在线 Models + 工程扫描）
│   │   ├── Models - The Apple Wiki.html   # 可选：浏览器另存的 Models 整页（供 parse 使用）
│   │   ├── theapplewiki_pages/            # 可选：抓取得到的 *.html 词条页
│   │   └── readme.md                      # 抓取脚本等更细的说明
│   ├── apple_device_models.json           # 应用主数据源（Identifier → 各字段）
│   ├── DeviceModel.swift
│   ├── ViewController.swift
│   └── …
└── PhoneExitCheck.xcodeproj/
```

---

## Python 环境准备

在终端中（建议与本仓库所用 `python3` 一致）：

```bash
pip3 install beautifulsoup4
# 仅在使用「对比」或 fetch 脚本时需要：
pip3 install playwright
python3 -m playwright install chromium
```

国内若 PyPI 较慢，可自行换镜像，例如：

```bash
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple beautifulsoup4 playwright
```

---

## Python 脚本使用说明

以下命令默认在 **`PhoneExitCheck/PhoneExitCheck/scripts`** 目录下执行（请按本机路径 `cd`）。

### 1. `parse_apple_models.py` — 从本地 HTML 更新 `apple_device_models.json`

在浏览器中打开 [Models](https://theapplewiki.com/wiki/Models)，通过验证后 **另存为** 完整网页，放入 `scripts/`（可与仓库中 `Models - The Apple Wiki.html` 同名替换）。

```bash
python3 parse_apple_models.py \
  --html "Models - The Apple Wiki.html" \
  --output "../apple_device_models.json"
```

更新 JSON 后，在 Xcode 中 **重新 Run** 以便应用重新从 Bundle 加载数据。

### 2. `fetch_theapplewiki_browser.py` — 抓取各机型维基页到本地

用于离线查阅或后续 **Connectivity** 合并。需 **有界面 Chromium**，遇 Cloudflare 时在窗口内完成验证。

```bash
python3 fetch_theapplewiki_browser.py --help

python3 fetch_theapplewiki_browser.py \
  --start-url "https://theapplewiki.com/wiki/Models" \
  --seed-html "Models - The Apple Wiki.html" \
  --user-data-dir "$HOME/.cache/phoneexitcheck-chromium-wiki" \
  --out-dir "./theapplewiki_pages" \
  --max-pages 80 \
  --delay 2.5
```

更多参数、缓存跳过规则、产品线过滤等见 **`scripts/readme.md`**。

### 3. `enrich_connectivity_from_wiki_pages.py` — 把 **Connectivity / Storage** 写入主 JSON

在已存在 **`theapplewiki_pages/*.html`** 的前提下，从各词条页 **Identifiers** 下的 wikitable（**ProductType、Connectivity、Storage** 列，与维基布局一致）解析与 Identifier 同行的值，写入 **`apple_device_models.json`**，供应用左侧列展示。仅当词条页 **Identifiers** 小节 wikitable 中解析到 **Storage** 列时才写入 JSON；否则移除该条的
`Storage` 键（不再保留 Models 总表中的容量文案）。**Connectivity** 仍按维基表解析；无表则移除。

```bash
python3 enrich_connectivity_from_wiki_pages.py
```

可选参数：

```bash
python3 enrich_connectivity_from_wiki_pages.py \
  --json ../apple_device_models.json \
  --pages ./theapplewiki_pages
```

合并后请在 Xcode **重新编译运行**。

### 4. `check_device_info_browser.py` — 命令行调试（与 App 行为一致）

应用内「对比」会调用此脚本；也可在终端手动验证：

```bash
python3 check_device_info_browser.py \
  "/路径/到/工程根目录" \
  '["iPhone15,2"]' \
  '["iPhone 14 Pro"]'
```

stdout 为 **JSON**（含工程扫描结果、`models_fetch_ok`、`device_models`、`connectivity_by_identifier` 等），日志在 stderr。

**环境变量（可选）**

| 变量 | 含义 |
|------|------|
| `PHONEEXITCHECK_PLAYWRIGHT_USER_DATA` | Chromium 用户数据目录，复用 Cookie |
| `PHONEEXITCHECK_HEADLESS=1` | 尝试无头拉取（多数情况无法通过 Cloudflare） |
| `PHONEEXITCHECK_WIKI_PAGES_DIR` | 指定本地维基 HTML 目录（默认 `scripts/theapplewiki_pages`） |

---

## 数据来源与推荐工作流

1. **基础表数据**：The Apple Wiki **Models** 页 → 本地 HTML → `parse_apple_models.py` → **`apple_device_models.json`**。  
2. **Connectivity / Storage（Identifiers 表）**：用 **`fetch_theapplewiki_browser.py`** 抓取词条页到 **`theapplewiki_pages/`**，再运行 **`enrich_connectivity_from_wiki_pages.py`**：从 **Identifiers** 小节 wikitable 写入 **Connectivity**；**Storage** 仅在有维基列时写入，否则从 JSON 中移除（不再使用 Models 总表容量）。  
3. **应用内对比**：依赖 **`check_device_info_browser.py`** 在线拉取 Models（需 Playwright）；本地 `theapplewiki_pages` 可增强 JSON 中的连通性等信息。

请合理控制抓取频率与范围，遵守 The Apple Wiki 的使用条款与内容许可。

---

## 设备兼容性检查

应用会自动识别不支持 iOS 15 及以上版本的设备，并在检查结果中标记 **⚠️**。这些设备可能不需要再向业务工程中添加映射。

---

## 注意事项

- **对比**功能会启动浏览器访问维基；首次使用请完成人机验证，必要时固定 `PHONEEXITCHECK_PLAYWRIGHT_USER_DATA` 以减少重复验证。  
- 大型工程「对比」可能耗时较长，请耐心等待。  
- 若 Python 或 Playwright 未正确安装，对比或抓取会失败；请根据终端 / stderr 提示安装依赖。
