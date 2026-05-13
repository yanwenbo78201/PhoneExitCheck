//
//  ViewController.swift
//  PhoneExitCheck
//
//  Created by Computer  on 08/05/26.
//

import Cocoa

class ViewController: NSViewController, NSTableViewDataSource, NSTableViewDelegate {

    private var tableView: NSTableView!
    private var scrollView: NSScrollView!
    private var segmentedControl: NSSegmentedControl!
    private var currentDeviceType: String = "All"
    
    // 代码展示区域
    private var ocTextView: NSTextView!
    private var swiftTextView: NSTextView!
    private var ocCopyButton: NSButton!
    private var swiftCopyButton: NSButton!
    
    // 文件夹选择
    private var selectedPathLabel: NSTextField!
    private var selectFolderButton: NSButton!
    private var compareButton: NSButton!
    
    // 对比结果展示区域
    private var resultScrollView: NSScrollView!
    private var resultTextView: NSTextView!
    
    // 容器视图
    private var leftContainer: NSView!
    private var rightContainer: NSView!

    override func viewDidLoad() {
        super.viewDidLoad()
        print("[ViewController] viewDidLoad called")
        setupUI()
        
        // 监听数据加载完成通知
        NotificationCenter.default.addObserver(self, selector: #selector(onDeviceDataLoaded), name: NSNotification.Name("DeviceDataLoaded"), object: nil)
        
        print("[ViewController] UI setup complete, waiting for data...")
    }
    
    override func viewDidAppear() {
        super.viewDidAppear()
        print("[ViewController] viewDidAppear called")
        updateCodeViews()
    }
    
    @objc private func onDeviceDataLoaded() {
        print("[ViewController] Device data loaded notification received")
        DispatchQueue.main.async {
            self.tableView.reloadData()
            self.updateCodeViews()
            print("[ViewController] Table reloaded with data")
        }
    }

    private func setupUI() {
        // 创建分段控件
        segmentedControl = NSSegmentedControl(
            labels: ["All", "iPhone", "iPad", "Apple TV", "iPod"],
            trackingMode: .selectOne,
            target: self,
            action: #selector(segmentedControlChanged(_:))
        )
        segmentedControl.translatesAutoresizingMaskIntoConstraints = false
        segmentedControl.selectedSegment = 0
        view.addSubview(segmentedControl)
        
        // 创建左侧容器
        leftContainer = NSView()
        leftContainer.translatesAutoresizingMaskIntoConstraints = false
        leftContainer.wantsLayer = true
        leftContainer.layer?.borderColor = NSColor.lightGray.cgColor
        leftContainer.layer?.borderWidth = 1
        view.addSubview(leftContainer)
        
        // 创建右侧容器
        rightContainer = NSView()
        rightContainer.translatesAutoresizingMaskIntoConstraints = false
        rightContainer.wantsLayer = true
        rightContainer.layer?.borderColor = NSColor.lightGray.cgColor
        rightContainer.layer?.borderWidth = 1
        view.addSubview(rightContainer)
        
        // 左侧表格
        scrollView = NSScrollView()
        scrollView.translatesAutoresizingMaskIntoConstraints = false
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = true
        scrollView.autohidesScrollers = true
        scrollView.borderType = .noBorder

        tableView = NSTableView()
        tableView.delegate = self
        tableView.dataSource = self
        tableView.usesAlternatingRowBackgroundColors = true
        tableView.rowHeight = 24
        tableView.gridStyleMask = [.solidHorizontalGridLineMask]

        let columns = [
            ("Identifier", 130),
            ("Generation", 200),
            ("Connectivity", 95),
            ("Storage", 110)
        ]

        for (title, width) in columns {
            let column = NSTableColumn(identifier: NSUserInterfaceItemIdentifier(title))
            column.title = title
            column.width = CGFloat(width)
            column.minWidth = 80
            column.maxWidth = 400
            tableView.addTableColumn(column)
        }

        scrollView.documentView = tableView
        leftContainer.addSubview(scrollView)
        
        // 右侧代码展示区域
        setupCodeViews()

        NSLayoutConstraint.activate([
            segmentedControl.topAnchor.constraint(equalTo: view.topAnchor, constant: 20),
            segmentedControl.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
            segmentedControl.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),
            
            leftContainer.topAnchor.constraint(equalTo: segmentedControl.bottomAnchor, constant: 16),
            leftContainer.bottomAnchor.constraint(equalTo: view.bottomAnchor, constant: -20),
            leftContainer.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
            leftContainer.widthAnchor.constraint(equalTo: view.widthAnchor, multiplier: 0.45),
            
            rightContainer.topAnchor.constraint(equalTo: segmentedControl.bottomAnchor, constant: 16),
            rightContainer.bottomAnchor.constraint(equalTo: view.bottomAnchor, constant: -20),
            rightContainer.leadingAnchor.constraint(equalTo: leftContainer.trailingAnchor, constant: 16),
            rightContainer.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),
            
            scrollView.topAnchor.constraint(equalTo: leftContainer.topAnchor, constant: 8),
            scrollView.bottomAnchor.constraint(equalTo: leftContainer.bottomAnchor, constant: -8),
            scrollView.leadingAnchor.constraint(equalTo: leftContainer.leadingAnchor, constant: 8),
            scrollView.trailingAnchor.constraint(equalTo: leftContainer.trailingAnchor, constant: -8)
        ])
        
        // 初始化代码视图
        // 设置初始测试文本
        ocTextView.string = "NSDictionary *deviceMap = @{\n    // 数据加载中...\n};"
        swiftTextView.string = "let deviceMap: [String: String] = [\n    // 数据加载中...\n]"
        updateCodeViews()
    }
    
    private func setupCodeViews() {
        // 创建OC代码区域
        let ocLabel = NSTextField(labelWithString: "Objective-C")
        ocLabel.font = NSFont.boldSystemFont(ofSize: 13)
        ocLabel.translatesAutoresizingMaskIntoConstraints = false
        rightContainer.addSubview(ocLabel)
        
        // 使用NSTextView + NSScrollView实现可滚动代码展示
        let ocScrollView = NSScrollView()
        ocScrollView.translatesAutoresizingMaskIntoConstraints = false
        ocScrollView.hasVerticalScroller = true
        ocScrollView.hasHorizontalScroller = true
        ocScrollView.autohidesScrollers = false
        ocScrollView.borderType = .bezelBorder
        
        ocTextView = NSTextView()
        ocTextView.isEditable = false
        ocTextView.isSelectable = true
        ocTextView.font = NSFont(name: "Menlo", size: 11) ?? NSFont.systemFont(ofSize: 11)
        ocTextView.backgroundColor = NSColor.white
        ocTextView.textColor = NSColor.black
        ocTextView.drawsBackground = true
        ocTextView.autoresizingMask = [.width, .height]
        
        ocScrollView.documentView = ocTextView
        rightContainer.addSubview(ocScrollView)
        
        ocCopyButton = NSButton(title: "复制 OC 代码", target: self, action: #selector(copyOCCode))
        ocCopyButton.translatesAutoresizingMaskIntoConstraints = false
        ocCopyButton.bezelStyle = .rounded
        rightContainer.addSubview(ocCopyButton)
        
        // 创建Swift代码区域
        let swiftLabel = NSTextField(labelWithString: "Swift")
        swiftLabel.font = NSFont.boldSystemFont(ofSize: 13)
        swiftLabel.translatesAutoresizingMaskIntoConstraints = false
        rightContainer.addSubview(swiftLabel)
        
        // 使用NSTextView + NSScrollView实现可滚动代码展示
        let swiftScrollView = NSScrollView()
        swiftScrollView.translatesAutoresizingMaskIntoConstraints = false
        swiftScrollView.hasVerticalScroller = true
        swiftScrollView.hasHorizontalScroller = true
        swiftScrollView.autohidesScrollers = false
        swiftScrollView.borderType = .bezelBorder
        
        swiftTextView = NSTextView()
        swiftTextView.isEditable = false
        swiftTextView.isSelectable = true
        swiftTextView.font = NSFont(name: "Menlo", size: 11) ?? NSFont.systemFont(ofSize: 11)
        swiftTextView.backgroundColor = NSColor.white
        swiftTextView.textColor = NSColor.black
        swiftTextView.drawsBackground = true
        swiftTextView.autoresizingMask = [.width, .height]
        
        swiftScrollView.documentView = swiftTextView
        rightContainer.addSubview(swiftScrollView)
        
        swiftCopyButton = NSButton(title: "复制 Swift 代码", target: self, action: #selector(copySwiftCode))
        swiftCopyButton.translatesAutoresizingMaskIntoConstraints = false
        swiftCopyButton.bezelStyle = .rounded
        rightContainer.addSubview(swiftCopyButton)
        
        // 添加文件夹选择功能
        selectedPathLabel = NSTextField()
        selectedPathLabel.translatesAutoresizingMaskIntoConstraints = false
        selectedPathLabel.isEditable = false
        selectedPathLabel.isSelectable = true
        selectedPathLabel.font = NSFont.systemFont(ofSize: 11)
        selectedPathLabel.backgroundColor = NSColor(white: 0.95, alpha: 1.0)
        selectedPathLabel.textColor = NSColor.darkGray
        selectedPathLabel.drawsBackground = true
        selectedPathLabel.isBordered = true
        selectedPathLabel.lineBreakMode = .byTruncatingMiddle
        selectedPathLabel.stringValue = "未选择文件夹"
        rightContainer.addSubview(selectedPathLabel)
        
        selectFolderButton = NSButton(title: "选择文件夹", target: self, action: #selector(selectFolder))
        selectFolderButton.translatesAutoresizingMaskIntoConstraints = false
        selectFolderButton.bezelStyle = .rounded
        rightContainer.addSubview(selectFolderButton)
        
        // 添加对比按钮
        compareButton = NSButton(title: "对比", target: self, action: #selector(compare))
        compareButton.translatesAutoresizingMaskIntoConstraints = false
        compareButton.bezelStyle = .rounded
        compareButton.isEnabled = false  // 初始不可用
        rightContainer.addSubview(compareButton)
        
        // 添加对比结果展示区域
        let resultLabel = NSTextField(labelWithString: "未包含的设备")
        resultLabel.font = NSFont.boldSystemFont(ofSize: 13)
        resultLabel.translatesAutoresizingMaskIntoConstraints = false
        rightContainer.addSubview(resultLabel)
        
        resultScrollView = NSScrollView()
        resultScrollView.translatesAutoresizingMaskIntoConstraints = false
        resultScrollView.hasVerticalScroller = true
        resultScrollView.hasHorizontalScroller = true
        resultScrollView.autohidesScrollers = false
        resultScrollView.borderType = .bezelBorder
        
        resultTextView = NSTextView()
        resultTextView.isEditable = false
        resultTextView.isSelectable = true
        resultTextView.font = NSFont(name: "Menlo", size: 11) ?? NSFont.systemFont(ofSize: 11)
        resultTextView.backgroundColor = NSColor(white: 0.98, alpha: 1.0)
        resultTextView.textColor = NSColor.red
        resultTextView.drawsBackground = true
        resultTextView.autoresizingMask = [.width, .height]
        
        resultScrollView.documentView = resultTextView
        rightContainer.addSubview(resultScrollView)
        
        NSLayoutConstraint.activate([
            ocLabel.topAnchor.constraint(equalTo: rightContainer.topAnchor, constant: 8),
            ocLabel.leadingAnchor.constraint(equalTo: rightContainer.leadingAnchor, constant: 8),
            
            ocScrollView.topAnchor.constraint(equalTo: ocLabel.bottomAnchor, constant: 4),
            ocScrollView.leadingAnchor.constraint(equalTo: rightContainer.leadingAnchor, constant: 8),
            ocScrollView.trailingAnchor.constraint(equalTo: rightContainer.trailingAnchor, constant: -8),
            ocScrollView.heightAnchor.constraint(equalToConstant: 150),
            
            ocCopyButton.topAnchor.constraint(equalTo: ocScrollView.bottomAnchor, constant: 4),
            ocCopyButton.trailingAnchor.constraint(equalTo: rightContainer.trailingAnchor, constant: -8),
            
            swiftLabel.topAnchor.constraint(equalTo: ocCopyButton.bottomAnchor, constant: 12),
            swiftLabel.leadingAnchor.constraint(equalTo: rightContainer.leadingAnchor, constant: 8),
            
            swiftScrollView.topAnchor.constraint(equalTo: swiftLabel.bottomAnchor, constant: 4),
            swiftScrollView.leadingAnchor.constraint(equalTo: rightContainer.leadingAnchor, constant: 8),
            swiftScrollView.trailingAnchor.constraint(equalTo: rightContainer.trailingAnchor, constant: -8),
            swiftScrollView.heightAnchor.constraint(equalToConstant: 150),
            
            swiftCopyButton.topAnchor.constraint(equalTo: swiftScrollView.bottomAnchor, constant: 4),
            swiftCopyButton.trailingAnchor.constraint(equalTo: rightContainer.trailingAnchor, constant: -8),
            
            selectedPathLabel.topAnchor.constraint(equalTo: swiftCopyButton.bottomAnchor, constant: 12),
            selectedPathLabel.leadingAnchor.constraint(equalTo: rightContainer.leadingAnchor, constant: 8),
            selectedPathLabel.trailingAnchor.constraint(equalTo: selectFolderButton.leadingAnchor, constant: -8),
            selectedPathLabel.heightAnchor.constraint(equalToConstant: 28),
            
            selectFolderButton.topAnchor.constraint(equalTo: swiftCopyButton.bottomAnchor, constant: 12),
            selectFolderButton.trailingAnchor.constraint(equalTo: rightContainer.trailingAnchor, constant: -8),
            selectFolderButton.widthAnchor.constraint(equalToConstant: 100),
            
            compareButton.topAnchor.constraint(equalTo: selectFolderButton.bottomAnchor, constant: 8),
            compareButton.trailingAnchor.constraint(equalTo: rightContainer.trailingAnchor, constant: -8),
            compareButton.widthAnchor.constraint(equalToConstant: 100),
            
            resultLabel.topAnchor.constraint(equalTo: compareButton.bottomAnchor, constant: 12),
            resultLabel.leadingAnchor.constraint(equalTo: rightContainer.leadingAnchor, constant: 8),
            
            resultScrollView.topAnchor.constraint(equalTo: resultLabel.bottomAnchor, constant: 4),
            resultScrollView.leadingAnchor.constraint(equalTo: rightContainer.leadingAnchor, constant: 8),
            resultScrollView.trailingAnchor.constraint(equalTo: rightContainer.trailingAnchor, constant: -8),
            resultScrollView.heightAnchor.constraint(greaterThanOrEqualToConstant: 200),
            resultScrollView.bottomAnchor.constraint(equalTo: rightContainer.bottomAnchor, constant: -8)
        ])
        
        print("[ViewController] setupCodeViews completed")
    }
    
    @objc private func segmentedControlChanged(_ sender: NSSegmentedControl) {
        let types = ["All", "iPhone", "iPad", "Apple TV", "iPod"]
        currentDeviceType = types[sender.selectedSegment]
        print("[ViewController] Selected device type: \(currentDeviceType)")
        tableView.reloadData()
        updateCodeViews()
        
        // 清空未包含设备区域
        resultTextView.string = ""
    }
    
    private func updateCodeViews() {
        let identifiers = getFilteredIdentifiers()
        print("[ViewController] updateCodeViews called, identifiers count: \(identifiers.count)")
        
        let ocCode = generateOCCode()
        let swiftCode = generateSwiftCode()
        
        print("[ViewController] Generated OC code length: \(ocCode.count)")
        print("[ViewController] Generated Swift code length: \(swiftCode.count)")
        print("[ViewController] OC code preview: \(ocCode.prefix(100))...")
        
        DispatchQueue.main.async {
            self.ocTextView.string = ocCode
            self.swiftTextView.string = swiftCode
            print("[ViewController] Code views updated, ocTextView string length: \(self.ocTextView.string.count)")
        }
    }
    
    private func generateOCCode() -> String {
        let identifiers = getFilteredIdentifiers()
        
        if identifiers.isEmpty {
            return "NSDictionary *deviceMap = @{\n    // 暂无数据，请等待数据加载或检查数据源\n};"
        }
        
        var code = "NSDictionary *deviceMap = @{\n"
        
        for identifier in identifiers {
            if let device = DeviceDataManager.shared.getDevice(identifier: identifier) {
                let generation = device.Generation ?? ""
                code += "    @\"\(identifier)\": @\"\(generation)\",\n"
            }
        }
        
        code += "};"
        return code
    }
    
    private func generateSwiftCode() -> String {
        let identifiers = getFilteredIdentifiers()
        
        if identifiers.isEmpty {
            return "let deviceMap: [String: String] = [\n    // 暂无数据，请等待数据加载或检查数据源\n]"
        }
        
        var code = "let deviceMap: [String: String] = [\n"
        
        for identifier in identifiers {
            if let device = DeviceDataManager.shared.getDevice(identifier: identifier) {
                let generation = device.Generation ?? ""
                code += "    \"\(identifier)\": \"\(generation)\",\n"
            }
        }
        
        code += "]"
        return code
    }
    
    @objc private func copyOCCode() {
        let code = ocTextView.string
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(code, forType: .string)
        showCopySuccess(message: "OC代码已复制到剪贴板")
    }
    
    @objc private func copySwiftCode() {
        let code = swiftTextView.string
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(code, forType: .string)
        showCopySuccess(message: "Swift代码已复制到剪贴板")
    }
    
    private func showCopySuccess(message: String) {
        let alert = NSAlert()
        alert.messageText = message
        alert.addButton(withTitle: "确定")
        alert.runModal()
    }
    
    @objc private func selectFolder() {
        let openPanel = NSOpenPanel()
        openPanel.title = "选择文件夹"
        openPanel.showsResizeIndicator = true
        openPanel.showsHiddenFiles = false
        openPanel.canChooseDirectories = true
        openPanel.canChooseFiles = false
        openPanel.allowsMultipleSelection = false
        
        let response = openPanel.runModal()
        
        if response == .OK, let url = openPanel.url {
            selectedPathLabel.stringValue = url.path
            compareButton.isEnabled = true  // 选择路径后启用对比按钮
            print("[ViewController] Selected folder: \(url.path)")
        }
    }
    
    @objc private func compare() {
        let path = selectedPathLabel.stringValue
        print("[ViewController] Compare button clicked, path: \(path)")
        
        // 获取当前展示的设备标识符和Generation，并过滤掉Apple TV Accessories和Apple Watch
        let identifiers = getFilteredIdentifiers().filter { identifier in
            let deviceType = DeviceDataManager.shared.getDeviceType(identifier: identifier)
            return deviceType != "Apple TV Accessories" && deviceType != "Apple Watch"
        }
        let generations = identifiers.compactMap { identifier in
            DeviceDataManager.shared.getDevice(identifier: identifier)?.Generation
        }
        
        print("[ViewController] Checking \(identifiers.count) identifiers and \(generations.count) generations")
        
        // 调用Python脚本
        checkDeviceInfoInFiles(folderPath: path, identifiers: identifiers, generations: generations)
    }
    
    private func checkDeviceInfoInFiles(folderPath: String, identifiers: [String], generations: [String]) {
        let resourcePath = Bundle.main.resourcePath ?? ""
        let pythonScriptPath = "\(resourcePath)/check_device_info_browser.py"
        
        // 检查脚本文件是否存在
        guard FileManager.default.fileExists(atPath: pythonScriptPath) else {
            showAlert(title: "错误", message: "Python脚本不存在: \(pythonScriptPath)")
            return
        }
        
        // 将列表转换为JSON字符串
        let encoder = JSONEncoder()
        encoder.outputFormatting = .withoutEscapingSlashes
        
        guard let identifiersData = try? encoder.encode(identifiers),
              let identifiersJson = String(data: identifiersData, encoding: .utf8),
              let generationsData = try? encoder.encode(generations),
              let generationsJson = String(data: generationsData, encoding: .utf8) else {
            showAlert(title: "错误", message: "无法编码数据")
            return
        }
        
        // 创建进程
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        process.arguments = [
            pythonScriptPath,
            folderPath,
            identifiersJson,
            generationsJson,
            "--no-models-fetch",
        ]
        
        // 创建管道获取输出
        let outputPipe = Pipe()
        let errorPipe = Pipe()
        process.standardOutput = outputPipe
        process.standardError = errorPipe
        
        do {
            try process.run()
            process.waitUntilExit()
            
            // 读取输出
            let outputData = outputPipe.fileHandleForReading.readDataToEndOfFile()
            let output = String(data: outputData, encoding: .utf8) ?? ""
            
            if let result = parseCheckResult(jsonString: output) {
                displayCheckResult(result)
            } else {
                let errorData = errorPipe.fileHandleForReading.readDataToEndOfFile()
                let errorOutput = String(data: errorData, encoding: .utf8) ?? ""
                showAlert(title: "错误", message: "解析结果失败:\n\(errorOutput)")
            }
            
        } catch {
            showAlert(title: "错误", message: "执行脚本失败: \(error.localizedDescription)")
        }
    }
    
    private func parseCheckResult(jsonString: String) -> [String: Any]? {
        guard let data = jsonString.data(using: .utf8) else {
            return nil
        }
        
        do {
            if let result = try JSONSerialization.jsonObject(with: data, options: []) as? [String: Any] {
                return result
            }
        } catch {
            print("[ViewController] JSON parsing error: \(error)")
        }
        
        return nil
    }
    
    private func displayCheckResult(_ result: [String: Any]) {
        let folderPath = result["folder_path"] as? String ?? ""
        let totalIdentifiers = result["total_identifiers"] as? Int ?? 0
        let totalGenerations = result["total_generations"] as? Int ?? 0
        let foundIdentifiers = result["found_identifiers"] as? [String] ?? []
        let foundGenerations = result["found_generations"] as? [String] ?? []
        let notFoundIdentifiers = result["not_found_identifiers"] as? [String] ?? []
        let notFoundGenerations = result["not_found_generations"] as? [String] ?? []
        let modelsFetchOk = result["models_fetch_ok"] as? Bool ?? true
        let modelsFetchError = result["models_fetch_error"] as? String ?? ""
        let modelsPageCount = result["models_page_device_count"] as? Int ?? 0
        let identifiersNotOnWiki = result["identifiers_not_on_models_page"] as? [String] ?? []

        let wikiStatusLine: String = {
            if result["models_fetch_skipped"] as? Bool == true {
                return "已跳过在线 Models；仅扫描所选文件夹中的源码是否包含 Identifier / Generation。\n\n"
            }
            if !modelsFetchOk {
                return "提示：在线 Models 页面未成功拉取或解析（\(modelsFetchError)）。下方对比仍使用应用内设备列表；请确认已安装 Playwright/Chromium，必要时在弹出浏览器中完成验证。\n\n"
            }
            if modelsPageCount > 0 {
                var line = "已从 The Apple Wiki Models 页解析 \(modelsPageCount) 条设备表项。\n"
                if !identifiersNotOnWiki.isEmpty {
                    line += "以下 Identifier 未出现在当前维基表格中（可能应用数据较新或维基未收录）：\n"
                    line += identifiersNotOnWiki.joined(separator: ", ") + "\n"
                }
                return line + "\n"
            }
            return ""
        }()
        
        // 获取当前设备数据用于配对展示
        let identifiers = getFilteredIdentifiers()
        
        // 构建未找到的标识符和Generation配对列表
        var notFoundPairs: [(String, String)] = []
        var unsupportedDevices: [String] = [] // 不支持iOS 15的设备
        for identifier in identifiers {
            if notFoundIdentifiers.contains(identifier) {
                if let device = DeviceDataManager.shared.getDevice(identifier: identifier),
                   let generation = device.Generation {
                    notFoundPairs.append((identifier, generation))
                    // 检查设备是否支持iOS 15及以上
                    if !isDeviceSupportiOS15(identifier: identifier) {
                        unsupportedDevices.append("\(identifier) (\(generation))")
                    }
                } else {
                    notFoundPairs.append((identifier, ""))
                    if !isDeviceSupportiOS15(identifier: identifier) {
                        unsupportedDevices.append(identifier)
                    }
                }
            }
        }
        
        // 构建结果文本并显示在结果区域
        if notFoundPairs.isEmpty {
            resultTextView.string = wikiStatusLine + "所有设备信息都已在文件中找到！"
            resultTextView.textColor = NSColor.green
        } else {
            var resultText = wikiStatusLine
            for (identifier, generation) in notFoundPairs {
                let note = !isDeviceSupportiOS15(identifier: identifier) ? " ⚠️不支持iOS 15+" : ""
                resultText += "\(identifier) : \(generation)\(note)\n"
            }
            
            // 使用NSAttributedString实现不同颜色
            let attributedString = NSMutableAttributedString(string: resultText)
            attributedString.addAttribute(.foregroundColor, value: NSColor.red, range: NSRange(location: 0, length: resultText.count))
            
            // 添加不支持iOS 15+的设备数量统计（颜色加深）
            if unsupportedDevices.count > 0 {
                let separator = "\n---\n"
                let statsText = "\(unsupportedDevices.count) 个设备不支持iOS 15+（仅供参考）"
                let statsString = NSAttributedString(string: separator + statsText, attributes: [
                    .foregroundColor: NSColor(red: 0.6, green: 0, blue: 0, alpha: 1) // 深红色
                ])
                attributedString.append(statsString)
            }
            
            resultTextView.textStorage?.setAttributedString(attributedString)
            resultTextView.textColor = NSColor.red // 设置默认颜色
        }
        
        // 检查是否所有标识符和Generation都没有找到
        let allNotFound = notFoundIdentifiers.count == totalIdentifiers && 
                          notFoundGenerations.count == totalGenerations
        
        // 构建备注信息
        var noteText = ""
        if !unsupportedDevices.isEmpty {
            noteText = "\n\n备注：以下设备不支持iOS 15.0及以上版本，可能不需要添加：\n" + unsupportedDevices.joined(separator: "\n")
        }
        
        if allNotFound {
            let wikiNote = modelsFetchOk ? "" : "\n\n\(modelsFetchError)"
            showAlert(title: "未找到匹配", message: "在文件夹 \(folderPath) 中未找到任何设备标识符或Generation信息。\(noteText)\(wikiNote)")
        } else if !notFoundPairs.isEmpty {
            let wikiNote = modelsFetchOk ? "" : "\n\n在线 Models：\(modelsFetchError)"
            showAlert(title: "检查完成", message: "部分设备信息未在文件中找到，请查看下方的详细列表。\(noteText)\(wikiNote)")
        } else {
            let wikiNote = modelsFetchOk ? "" : "\n\n在线 Models：\(modelsFetchError)"
            showAlert(title: "检查完成", message: "所有设备信息都已在文件中找到！\(wikiNote)")
        }
    }
    
    private func isDeviceSupportiOS15(identifier: String) -> Bool {
        // 根据设备标识符判断是否支持iOS 15及以上
        // iPhone: iPhone7,2及之后支持iOS 15（iPhone 6s及之后）
        // iPad: iPad6,7及之后支持iOS 15（iPad Pro 10.5及之后）
        // iPod: iPod touch 7支持iOS 15
        
        let pattern = "([A-Za-z]+)(\\d+)(?:[,\\.](\\d+))?"
        if let regex = try? NSRegularExpression(pattern: pattern, options: []),
           let match = regex.firstMatch(in: identifier, range: NSRange(identifier.startIndex..., in: identifier)) {
            
            let type = String(identifier[Range(match.range(at: 1), in: identifier)!])
            let major = match.range(at: 2).location != NSNotFound 
                ? Int(identifier[Range(match.range(at: 2), in: identifier)!]) ?? 0
                : 0
            
            switch type {
            case "iPhone":
                // iPhone 6s (iPhone8,1)及之后支持iOS 15
                // iPhone7,2 = iPhone 6s
                return major >= 7
            case "iPad":
                // iPad Pro 10.5 (iPad6,7)及之后支持iOS 15
                // iPad5,1 = iPad Air 2
                // iPad6,1 = iPad Pro 9.7
                // iPad6,7 = iPad Pro 10.5
                return major >= 6
            case "iPod":
                // iPod touch 7支持iOS 15
                return major >= 7
            case "AppleTV":
                // Apple TV 4K (AppleTV5,3)及之后支持tvOS 15
                return major >= 5
            default:
                return true
            }
        }
        
        return true
    }
    
    private func showAlert(title: String, message: String) {
        let alert = NSAlert()
        alert.messageText = title
        alert.informativeText = message
        alert.addButton(withTitle: "确定")
        alert.runModal()
    }
    
    private func getFilteredIdentifiers() -> [String] {
        if currentDeviceType == "All" {
            // 过滤掉Apple TV Accessories和Apple Watch
            return DeviceDataManager.shared.getAllIdentifiers().filter { identifier in
                let deviceType = DeviceDataManager.shared.getDeviceType(identifier: identifier)
                return deviceType != "Apple TV Accessories" && deviceType != "Apple Watch"
            }
        } else {
            return DeviceDataManager.shared.getDevicesByType(currentDeviceType)
                .map { $0.0 }
        }
    }


    func numberOfRows(in tableView: NSTableView) -> Int {
        let identifiers = getFilteredIdentifiers()
        print("[ViewController] numberOfRows: \(identifiers.count)")
        return identifiers.count
    }

    func tableView(_ tableView: NSTableView, viewFor tableColumn: NSTableColumn?, row: Int) -> NSView? {
        guard let columnIdentifier = tableColumn?.identifier.rawValue else { return nil }

        let identifiers = getFilteredIdentifiers()
        let identifier = identifiers[row]
        guard let device = DeviceDataManager.shared.getDevice(identifier: identifier) else { return nil }

        let cellIdentifier = NSUserInterfaceItemIdentifier("TextCell")
        var cellView = tableView.makeView(withIdentifier: cellIdentifier, owner: self) as? NSTextField

        if cellView == nil {
            cellView = NSTextField()
            cellView?.identifier = cellIdentifier
            cellView?.isBordered = false
            cellView?.isEditable = false
            cellView?.backgroundColor = .clear
            cellView?.lineBreakMode = .byTruncatingTail
            cellView?.font = NSFont.systemFont(ofSize: 12)
        }

        var value = ""
        switch columnIdentifier {
        case "Identifier":
            value = identifier
        case "Generation":
            value = device.Generation ?? ""
        case "Connectivity":
            value = device.Connectivity ?? ""
        case "Storage":
            value = device.Storage ?? ""
        default:
            value = ""
        }

        cellView?.stringValue = value
        return cellView
    }
}
