# PhoneExitCheck

一个用于检查 Apple 设备型号退出信息的 macOS 应用程序，数据来源根据https://theapplewiki.com/wiki/Models 中获取的设备型号数据。

## 功能特性

- **设备型号展示**: 展示 iPhone、iPad、Apple TV、iPod 等设备的标识符和型号信息
- **代码生成**: 自动生成 Objective-C 和 Swift 格式的设备型号映射代码
- **设备检查**: 对比项目文件，检查哪些设备型号信息尚未包含
- **iOS 15 兼容性提示**: 自动识别不支持 iOS 15+ 的设备

## 项目结构

```
PhoneExitCheck/
├── PhoneExitCheck/
│   ├── Assets.xcassets/          # 资源文件
│   ├── Base.lproj/               # 界面文件
│   ├── scripts/                  # Python 脚本
│   │   ├── check_device_info.py  # 检查设备信息脚本
│   │   ├── parse_apple_models.py # 解析设备型号脚本
│   │   └── Models - The Apple Wiki.html # 设备数据来源
│   ├── AppDelegate.swift         # 应用代理
│   ├── DeviceModel.swift         # 设备数据模型和管理器
│   ├── ViewController.swift      # 主界面控制器
│   ├── PhoneExitCheck.entitlements # 权限配置
│   └── apple_device_models.json  # 设备型号数据
└── PhoneExitCheck.xcodeproj/     # Xcode 项目文件
```

## 使用说明

1. **打开项目**: 使用 Xcode 打开 `PhoneExitCheck.xcodeproj`
2. **运行应用**: 点击 Xcode 的 Run 按钮启动应用
3. **选择设备类型**: 使用顶部分段控件选择要查看的设备类型（All、iPhone、iPad、Apple TV、iPod）
4. **生成代码**: 右侧会自动生成对应的 Objective-C 和 Swift 代码
5. **复制代码**: 点击"复制 OC 代码"或"复制 Swift 代码"按钮复制到剪贴板
6. **检查项目**: 
   - 点击"选择文件夹"按钮选择要检查的项目目录
   - 点击"对比"按钮检查设备信息是否已包含在项目文件中
   - 查看"未包含的设备"区域了解哪些设备需要添加

## 设备兼容性检查

应用会自动识别不支持 iOS 15 及以上版本的设备，并在检查结果中标记 ⚠️ 符号。这些设备可能不需要添加到项目中。

## 技术栈

- **语言**: Swift 5 / Objective-C
- **框架**: Cocoa (AppKit)
- **辅助工具**: Python 3

## 数据来源

设备型号数据来源于 Apple Wiki，通过 `scripts/parse_apple_models.py` 脚本解析 HTML 文件生成 JSON 数据。

## 注意事项

- 确保已安装 Python 3（通常 macOS 自带）
- 首次运行可能需要等待数据加载
- 建议在检查大型项目时耐心等待对比结果