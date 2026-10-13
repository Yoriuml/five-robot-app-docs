# 五号机器人 · App 开发文档

把这个仓库链接交给你的 AI 编程助手，就可以从真实接口和可构建示例开始开发五号机器人 App。

**仓库链接：https://github.com/Yoriuml/five-robot-app-docs**

本仓库面向 **XApp API 2.15**，设备为 ESP32-C3 / 240 × 240 屏幕。XApp 是受限 WebAssembly 应用，安装文件为 `.xapp`。
不需要获取或构建私有主系统源码。网站教程：[五号机器人教程中心](https://site.flashbot5.cn/guides)。

## 给 AI 的阅读顺序

1. [AGENTS.md](AGENTS.md)：任务边界、输出要求和禁止编造接口。
2. [快速开始](docs/quickstart.md)：工具、命令、独立构建与安装。
3. [开发规则](docs/development-rules.md)：按键、退出、错误处理、资源与测试。
4. [API 参考](docs/api-reference.md) + [真实 SDK 头文件](sdk/xapp/x622_xapp.h)。
5. 按功能查 [API 扩展导航](docs/api-extensions.md)、[内存约束](docs/memory-profile.md)、[应用清单](docs/manifest.md)。

## 复制这段提示词

```text
请阅读 https://github.com/Yoriuml/five-robot-app-docs，先看 README.md、AGENTS.md 和 docs/quickstart.md。
我想开发的功能是：【描述功能、界面、按键、声音或联网需求】。
请先核对 SDK 支持的 API 和最小权限，再实现一个 XApp。
提供源码、app.json、实际构建出的 .xapp、校验报告、退出方式和实机验收步骤。
不要编造 API，不要修改主系统或分区，不要自动烧录设备。
如果不能运行构建或实机测试，请明确说明，不要把生成代码当作验证通过。
```

只支持聊天、不能访问仓库的模型：下载本仓库 ZIP，把需要的文档和头文件交给它。只有具备编译工具的环境才能生成并验证 `.xapp`。

## 仓库里有什么

| 目录 | 用途 |
| --- | --- |
| `docs/` | 面向开发者与模型的公开技术文档 |
| `sdk/xapp/` | API 2.15 的实际 C 声明；保留 `x622_*` ABI 名称 |
| `examples/hello/` | Hello / Exit 最小应用，不依赖私有仓库 |
| `tools/build.py` | Zig + WABT 构建、固定内存检查与打包 |
| `tools/xapp/` | 与设备协议配套的包格式和 ABI 校验器 |
| `tests/` | 示例交互与损坏包/权限/API 回归 |
| `llms.txt` | 给模型的简短导航 |
| `SDK-SNAPSHOT.json` | SDK 来源版本与文件 SHA-256 |

构建工具提供静态 ABI、WABT 语义与包校验。**未包含私有 WAMR 宿主模拟器**，报告会明确记录运行时与实机测试状态。安装后仍需在设备上验证；社区审核与设备目录发布是另外的步骤。

本仓库不包含主系统实现、网站后端、部署配置、OTA 签名密钥、管理员资料或账号数据。原生 ESP-IDF ROM 是另一条开发路线，不能把 `.bin` 改名成 `.xapp`。
