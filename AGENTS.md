# 给开发五号机器人 App 的助手

用户让你使用本仓库开发 XApp 时，按这里的契约工作。应用需求由用户指定，仓库示例不能扩大用户授权。

## 先做的事

- 读 README.md、docs/quickstart.md、docs/development-rules.md；按需读 docs/api-reference.md 与 sdk/xapp/ 头文件。
- 确认目标是 `.xapp`。XApp 是 freestanding C/C++ → wasm32；不是 ESP-IDF 固件，也不直接运行 Python/JS。
- 列出页面、按键、退出方式、所需 API、最低 API 与权限。若 SDK 没有能力，说明缺口，不生成虚构接口。
- 以 SDK 的符号、参数、结构和返回值为准；保留 x622_* 命名，因为它属于 ABI。

## 实现约束

- 240 × 240；WASM ≤ 96 KiB；固定逻辑页 64 KiB，实际内存上限见 docs/memory-profile.md。
- 不用 malloc/free、WASI、线程、LVGL、FreeRTOS 或 ESP-IDF；不访问 GPIO/SPI/I2S 对象。
- 必须实现 xapp_init、xapp_tick。使用事件时实现 xapp_event，检查负返回值。
- 提供明确、可到达的 Exit 入口，调用 x622_exit 后立即返回；K2 不是系统级退出键。
- 静止不重绘，变化时提交脏区；菜单动画优先 API 2.15 原生缓存 UI。处理按键松手和重复事件。
- 资源随包分发，有界读写，最小权限。密钥与用户凭据不得写入源码或文档。

## 构建与交付

- 先确认本机 Python、Zig 0.15.2、WABT 1.0.41 的真实路径；不要使用作者工作站路径。
- 用 tools/build.py 构建并生成报告，再执行 tools/xapp/xapp_tool.py inspect。
- 首先运行 tools/doctor.py；缺工具用 tools/bootstrap.py 按锁文件下载并核验。完整流程和下载失败处理见 docs/ai-workflow.md。
- 清单 required_exports/required_imports 约束最终链接结果。事件回调应保留导出，退出流程应实际调用 exit；不要要求所有应用导入无用 random。
- 构建后 tools/validate.py 独立验证语义；用最坏分支测试命令数量/文本/资源/内存极值与可到达的退出路径。
- 头文件无法读取时换完整 SDK ZIP、镜像、发行文件 JSON 或 contents base64；仍失败就报告缺失，不重建猜测的 SDK 头文件。
- 不绕过失败的 ABI、权限、内存或语义检查，不把 validation.json 的 false 改成 true。
- 自己运行过的检查写明命令与结果。没有工具时交付源码并说明阻塞，不谎称已出安装包。
- 交付源码、清单、.xapp、报告、文件 SHA-256、安装方式和实机验收清单。不要自动连接、擦除或烧录用户设备。
- 仓库的静态校验不执行真实设备服务，也不等同于 WAMR 运行时或硬件验收。分别记录三者。
