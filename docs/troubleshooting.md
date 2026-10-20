# 失败诊断

| 现象 | 处理 |
| --- | --- |
| Git/curl 连不上 | 下载固定标签 ZIP，换 GitHub/Gitee/官方 SDK ZIP；PowerShell 用 `Invoke-WebRequest -Uri "下载地址" -OutFile sdk.zip`，再核对哈希 |
| `.h` 响应为空或 HTML | 查 HTTP 状态和 Content-Type；用发行版 `file?path=sdk/xapp/x622_xapp.h` JSON 或 GitHub contents API base64；不创建猜测头文件 |
| Python 打开商店 | Windows 用 `py -3 --version` 找真实解释器；需要 Python 3.10+ |
| Missing Zig/WABT | `python tools/bootstrap.py`，再 `python tools/doctor.py`；或显式 `--zig`/`--wabt` |
| 解压没有 zig.exe | 校验归档哈希，使用本 SDK Python bootstrap 解压；不要只看 Expand-Archive 成功提示 |
| 下载工具失败 | 按 toolchain.lock.json 官方 URL 单独下载，`python tools/bootstrap.py --archive-dir <归档目录>`；归档不能改名/改哈希来绕过验证 |
| macOS x64 无固定 WABT 预编译 | 官方 1.0.41 未提供该目标预编译；按官方源码构建同版本，指定 bin 目录。不能运行 arm64 文件冒充通过 |
| linker 报导入、WASI、libc 问题 | 采用 freestanding 示例；不用桌面标准库、malloc、线程或私有固件 API |
| xapp_event 不见/按键无效 | include 官方主头文件，按真实签名实现；检查最终报告 exports，声明 required_exports；用主机交互测试覆盖退出路径 |
| 缺 exit 导入 | 实现可到达的退出流程调用 x622_exit 并立即返回；不要靠声明一个未调用函数来充数 |
| 内存/图元超限 | 从最重页面计算静态内存和宿主资源；减少节点/缓存/纹理，分条带、裁剪脏区；不改上限绕过验收 |
| 中文乱码 | gfx TEXT 是 ASCII；中文需离线字形/纹理；包名称的 UTF-8 支持不代表正文 TEXT 自动支持中文 |
| 动画在电脑流畅，设备卡 | 电脑桩/预览不模拟 C3 带宽与系统堆；优先缓存纹理+原生 UI，用 ui_stats 和真机观测分析 |
| HTTPS/TLS 失败 | 保留完整 transport/native_error 与设备堆日志；证书、时间、算法、系统堆均可能影响；不直接归因于证书文件，不关闭验签 |

## 工具定位顺序

构建参数 → `XAPP_ZIG`（可执行文件）/`XAPP_WABT`（bin 目录）→ PATH → SDK `.tools/` → 已验证共享缓存。显式参数/环境变量版本错误时必须修正，不静默替换；自动找到的错误版本可继续寻找匹配工具。
Zig 固定 0.15.2、WABT 固定 1.0.41。工具目录与缓存不进入 Git，也不进入 SDK 发行包。
锁文件包含 Windows x64、Linux x64/arm64、macOS arm64 的官方归档与 SHA256。
这些归档由上游提供，遵循其各自许可证；本仓库未重新打包工具二进制。

五套默认模板带许可与原生资源缓存，缺可选 Pillow/fontTools 不阻止创建/构建；修改图标或生成新字形再运行 `bootstrap.py --features launcher`。共享缓存与离线准备见[环境说明](environment-cache.md)。
不要自动删除任意用户目录。构建临时文件位于系统临时目录，产物由输出参数指定；准备工具的临时目录在经过边界检查的共享缓存内，完成验证后原子发布。

SDK 2026.10.20.1 不修改 API。api.json 的 sdk_release 仍是 API 快照来源 2026.10.19.2，由 SDK-SNAPSHOT.json 的 api_snapshot_release 记录；当前 SDK 发行与工具版本分别查 sdk-release.json、toolchain.lock.json。
