# 五号机器人 XApp SDK

公开、可独立构建的完整开发包：**SDK 2026.10.20.1 · API 2.15 · 包格式 1**。设备 ESP32-C3，240×240。公共 API/ABI 与包格式保持不变。

[GitHub](https://github.com/Yoriuml/five-robot-app-docs) · [Gitee](https://gitee.com/yorium/five-robot-app-docs) · [官方版本索引和 SDK 下载](https://site.flashbot5.com/developer/v1/index.json) · [安装工作台](https://site.flashbot5.com/install)

固定同一标签 `sdk-2026.10.20.1`，避免跨发行版拼接头文件、工具和示例。仓库镜像网络不通时，下载官方完整 SDK ZIP 并验哈希。

## 开始

Python 3.10+；五套默认模板使用已校验的原生资产缓存，只需要 Python 标准库，不必先装字体/图标处理库。

```sh
python tools/doctor.py
python tools/create_app.py --template native-ui --id my-app --name "My App" --output dist/my-app
python tools/build.py --app dist/my-app -o dist/my-app.xapp
python tools/validate.py dist/my-app.xapp
```

doctor 报告缺少工具时才运行 `python tools/bootstrap.py`，然后复查。已有 Zig 0.15.2 / WABT 1.0.41 时跳过下载，工具支持 PATH、环境变量或 `--zig` / `--wabt`。下载与环境问题见[失败诊断](docs/troubleshooting.md)。

## 给 AI

详细规则已集中在 SDK 的[唯一 AI 执行入口](docs/ai-workflow.md)，用户只需提供下面这一句。AI 按所用能力读取真实声明，遵守首屏、按键、图标/中文、动效、内存、音频/网络及验收规则。

```text
按 https://site.flashbot5.com/developer/v1/index.json 对应 SDK 的 docs/ai-workflow.md 开发 XApp：【需求】。
```

规则对应的检查、证据层级与服务器分工见[实施状态](docs/ai-rules-rollout.md)；缓存与离线准备见[环境缓存](docs/environment-cache.md)。产品检查不等于设备运行通过。

## 开发包内容

| 内容 | 用途 |
| --- | --- |
| [14 份头文件](sdk/xapp/x622_xapp.h) | 完整公开 API 2.15 声明和结构，保持真实 ABI |
| [基础交互](examples/hello/README.md) | 启动键松手、菜单、明确退出、绘制失败处理 |
| [原生动画 UI](examples/native-ui/README.md) | 稳定节点、缓存预算、原生插值、退出释放 |
| [原生音画 UI](examples/native-ui-audio/README.md) | 可见首屏、中键动作、双轨 PCM 与退出清理 |
| [中文资源](examples/resources-zh/README.md) | 原创中文笔画底图、包内资源、条带读取 |
| [异步联网](examples/http/README.md) | Wi-Fi/HTTP 状态、错误、超时、可退出 |
| [API 索引](api.json) | 实际导入名/签名/权限/最低 API、生命周期和限制 |
| [工具锁文件](toolchain.lock.json) | 官方归档、固定版本、SHA256、支持平台 |
| `tools/doctor.py` / `bootstrap.py` | 环境诊断与可校验的工具准备 |
| `tools/create_app.py` / `build.py` / `validate.py` | 创建完整产品、编译、打包、独立语义/ABI 验收 |
| `tools/check_product.py` | 从最终包复验图标、双语标题、字形及生命周期要求；validate --product 复用 |
| `tools/test_sdk.py` / `tests/` | 所有模板实编译与主机状态/失败路径测试 |
| [发行规范](docs/releases.md) / `tools/release.py` | 冻结文件白名单、可重复 ZIP、校验清单 |
| [SDK-SNAPSHOT.json](SDK-SNAPSHOT.json) | 头文件来源与公开工具文件指纹 |

还有 [API 手册](docs/api-reference.md)、[扩展导航](docs/api-extensions.md)、[内存约束](docs/memory-profile.md)、[清单格式](docs/manifest.md)、[验收要求](docs/testing.md)。

运行 `python tools/test_sdk.py` 完整检查。构建报告包含最终 WASM 的 imports/exports；清单可要求必须保留的回调和 API，避免事件被链接删除。无需导入没有使用的 random。

本 SDK 包含全部公开声明、构建和静态验收工具；编译器按锁文件单独下载，不把数百 MB 的工具二进制塞入 Git。中文启动器/字体转换才需要可选 Pillow/fontTools 和已获授权字体。

XApp 是 freestanding C/C++ → wasm32，安装包为 `.xapp`；不运行 ESP-IDF、Python、JS，也不能把 `.bin` 改名当应用。
静态与主机桩测试不执行真实设备服务，报告的 runtime_tested/hardware_tested 保持 false，真机验收须单独记录。
不含私有固件、驱动/宿主模拟器、网站后端、部署配置、账号数据或 OTA 密钥。
