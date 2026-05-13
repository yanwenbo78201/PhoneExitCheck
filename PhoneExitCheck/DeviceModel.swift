import Foundation

struct DeviceInfo: Codable {
    let Generation: String?
    let A_Number: String?
    let Bootrom: String?
    let FCC_ID: String?
    let Internal_Name: String?
    let Identifier: String?
    let Color: String?
    let Finish: String?
    let Storage: String?
    let Model: String?
    let First_iPad_Compatibility: String?
    /// 网络类型等（如 Wi-Fi / Cellular）；来自 `apple_device_models.json` 时可选
    let Connectivity: String?

    enum CodingKeys: String, CodingKey {
        case Generation
        case A_Number = "\"A\" Number"
        case Bootrom
        case FCC_ID
        case Internal_Name = "Internal Name"
        case Identifier
        case Color
        case Finish
        case Storage
        case Model
        case First_iPad_Compatibility = "First iPad Compatibility"
        case Connectivity
    }
}

extension DeviceInfo {
    /// 若本条目某字段为空，则用 Bundle 快照中对应字段补全（Python 临时 JSON 可能缺 Connectivity 等）
    private static func preferNonEmpty(_ primary: String?, _ fallback: String?) -> String? {
        let p = (primary ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        if !p.isEmpty { return p }
        let f = (fallback ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        return f.isEmpty ? nil : f
    }

    func mergingBundledSupplementals(from bundled: DeviceInfo?) -> DeviceInfo {
        guard let b = bundled else { return self }
        let conn = Self.preferNonEmpty(Connectivity, b.Connectivity)
        // Storage：仅采用 Bundle 内由维基词条页 Identifiers 表 enrich 写入的值，绝不回退到 Python/Models 临时数据
        let stor = Self.preferNonEmpty(b.Storage, nil)
        return DeviceInfo(
            Generation: Generation,
            A_Number: A_Number,
            Bootrom: Bootrom,
            FCC_ID: FCC_ID,
            Internal_Name: Internal_Name,
            Identifier: Identifier,
            Color: Color,
            Finish: Finish,
            Storage: stor,
            Model: Model,
            First_iPad_Compatibility: First_iPad_Compatibility,
            Connectivity: conn
        )
    }
}

class DeviceDataManager {
    static let shared = DeviceDataManager()

    private(set) var devices: [String: DeviceInfo] = [:]
    private(set) var sortedIdentifiers: [String] = []

    private init() {}

    /// 从 App Bundle 内的 `apple_device_models.json` 合并字段：Connectivity 可补全 Python 临时 JSON；
    /// Storage 仅使用 Bundle 中维基 enrich 结果（无则清空，不回退 Models 表）。
    private func mergeBundledSupplementalFieldsFromSnapshot() {
        guard let url = Bundle.main.url(forResource: "apple_device_models", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let bundled = try? JSONDecoder().decode([String: DeviceInfo].self, from: data)
        else {
            print("[DeviceDataManager] mergeBundledSupplementals: 无法读取 Bundle 内 apple_device_models.json，跳过合并")
            return
        }
        var next = devices
        for (id, info) in devices {
            if let b = bundled[id] {
                next[id] = info.mergingBundledSupplementals(from: b)
            }
        }
        devices = next
        let nConn = next.values.filter { ($0.Connectivity ?? "").isEmpty == false }.count
        let nStor = next.values.filter { ($0.Storage ?? "").isEmpty == false }.count
        print("[DeviceDataManager] mergeBundledSupplementals: Connectivity 非空 \(nConn) 条，Storage 非空 \(nStor) 条")
    }
    
    // 自然排序比较函数
    private func naturalCompare(_ a: String, _ b: String) -> ComparisonResult {
        let pattern = "([A-Za-z]+)(\\d+)(?:[,\\.](\\d+))?"
        
        func extractComponents(from str: String) -> (String, Int, Int) {
            if let regex = try? NSRegularExpression(pattern: pattern, options: []),
               let match = regex.firstMatch(in: str, range: NSRange(str.startIndex..., in: str)) {
                let type = String(str[Range(match.range(at: 1), in: str)!])
                let major = match.range(at: 2).location != NSNotFound 
                    ? Int(str[Range(match.range(at: 2), in: str)!]) ?? 0
                    : 0
                let minor = match.range(at: 3).location != NSNotFound 
                    ? Int(str[Range(match.range(at: 3), in: str)!]) ?? 0
                    : 0
                return (type, major, minor)
            }
            return (str, 0, 0)
        }
        
        let (typeA, majorA, minorA) = extractComponents(from: a)
        let (typeB, majorB, minorB) = extractComponents(from: b)
        
        // 先按类型排序
        if typeA != typeB {
            return typeA.compare(typeB)
        }
        
        // 再按主版本号排序
        if majorA != majorB {
            return majorA < majorB ? .orderedAscending : .orderedDescending
        }
        
        // 最后按次版本号排序
        if minorA != minorB {
            return minorA < minorB ? .orderedAscending : .orderedDescending
        }
        
        return .orderedSame
    }

    func loadFromJSON() {
        print("[DeviceDataManager] Starting to load JSON...")
        
        // 首先尝试通过Python脚本生成JSON
        let resourcePath = Bundle.main.resourcePath ?? ""
        let pythonScriptPath = "\(resourcePath)/parse_apple_models.py"
        let htmlFilePath = "\(resourcePath)/Models - The Apple Wiki.html"
        let tempOutputPath = "/tmp/apple_devices_temp.json"
        
        print("[DeviceDataManager] Python script: \(pythonScriptPath)")
        print("[DeviceDataManager] HTML file: \(htmlFilePath)")
        
        let scriptExists = FileManager.default.fileExists(atPath: pythonScriptPath)
        let htmlExists = FileManager.default.fileExists(atPath: htmlFilePath)
        
        print("[DeviceDataManager] Script exists: \(scriptExists), HTML exists: \(htmlExists)")
        
        if scriptExists && htmlExists {
            print("[DeviceDataManager] Running Python script...")
            let process = Process()
            process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
            process.arguments = [pythonScriptPath, "--html", htmlFilePath, "--output", tempOutputPath]
            
            let outputPipe = Pipe()
            let errorPipe = Pipe()
            process.standardOutput = outputPipe
            process.standardError = errorPipe
            
            do {
                try process.run()
                process.waitUntilExit()
                
                if process.terminationStatus == 0 {
                    let outputData = outputPipe.fileHandleForReading.readDataToEndOfFile()
                    let output = String(data: outputData, encoding: .utf8) ?? ""
                    print("[DeviceDataManager] Python script output: \(output)")
                    print("[DeviceDataManager] ✅ Python script executed successfully")
                    
                    // 从临时文件加载数据
                    if FileManager.default.fileExists(atPath: tempOutputPath) {
                        let data = try Data(contentsOf: URL(fileURLWithPath: tempOutputPath))
                        devices = try JSONDecoder().decode([String: DeviceInfo].self, from: data)
                        mergeBundledSupplementalFieldsFromSnapshot()
                        sortedIdentifiers = devices.keys.sorted { naturalCompare($0, $1) == .orderedAscending }
                        print("[DeviceDataManager] ✅ Successfully loaded \(devices.count) devices from Python script")
                        print("[DeviceDataManager] First 3 identifiers: \(sortedIdentifiers.prefix(3))")
                        NotificationCenter.default.post(name: NSNotification.Name("DeviceDataLoaded"), object: nil)
                        return
                    }
                } else {
                    let errorData = errorPipe.fileHandleForReading.readDataToEndOfFile()
                    let errorOutput = String(data: errorData, encoding: .utf8) ?? ""
                    print("[DeviceDataManager] ❌ Python script failed: \(errorOutput)")
                }
            } catch {
                print("[DeviceDataManager] ❌ Error running Python script: \(error)")
            }
        } else {
            print("[DeviceDataManager] Python script or HTML file not found, falling back to local JSON")
        }
        
        // 备用：尝试从多个位置加载JSON文件
        let possiblePaths = [
            Bundle.main.url(forResource: "apple_device_models", withExtension: "json"),
            Bundle.main.bundleURL.appendingPathComponent("apple_device_models.json"),
            URL(fileURLWithPath: FileManager.default.currentDirectoryPath).appendingPathComponent("apple_device_models.json")
        ]

        for (index, url) in possiblePaths.enumerated() {
            if let url = url {
                let path = url.path
                let exists = FileManager.default.fileExists(atPath: path)
                print("[DeviceDataManager] Path \(index): \(path) - exists: \(exists)")
                
                if exists {
                    do {
                        let data = try Data(contentsOf: url)
                        print("[DeviceDataManager] Successfully read data, size: \(data.count) bytes")
                        
                        devices = try JSONDecoder().decode([String: DeviceInfo].self, from: data)
                        sortedIdentifiers = devices.keys.sorted { naturalCompare($0, $1) == .orderedAscending }
                        
                        print("[DeviceDataManager] ✅ Successfully loaded \(devices.count) devices from: \(path)")
                        print("[DeviceDataManager] First 3 identifiers: \(sortedIdentifiers.prefix(3))")
                        
                        return
                    } catch {
                        print("[DeviceDataManager] ❌ Error loading from \(path): \(error)")
                    }
                }
            }
        }

        print("[DeviceDataManager] ❌ Failed to load JSON from all locations")
    }

    func getDevice(identifier: String) -> DeviceInfo? {
        return devices[identifier]
    }

    func getAllIdentifiers() -> [String] {
        return sortedIdentifiers
    }

    func getDeviceType(identifier: String) -> String {
        if identifier.hasPrefix("iPhone") {
            return "iPhone"
        } else if identifier.hasPrefix("iPad") {
            return "iPad"
        } else if identifier.hasPrefix("iPod") {
            return "iPod"
        } else if identifier.hasPrefix("AppleTV") {
            return "Apple TV"
        } else if identifier.hasPrefix("Watch") {
            return "Apple Watch"
        } else if identifier.hasPrefix("AudioAccessory") {
            return "Apple TV Accessories"
        }
        return "Unknown"
    }

    func getDevicesByType(_ type: String) -> [(String, DeviceInfo)] {
        return sortedIdentifiers
            .filter { getDeviceType(identifier: $0) == type }
            .map { ($0, devices[$0]!) }
    }
}