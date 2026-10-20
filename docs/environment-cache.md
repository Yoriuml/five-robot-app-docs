# 环境准备与跨项目缓存

SDK 发行版与 API 版本分别锁定。先读 [AI 执行契约](ai-workflow.md)，再检查环境；不要每次生成应用都重新下载 SDK、解压编译器或安装字体依赖。

## 默认流程

```sh
python tools/doctor.py --app examples/native-ui
# 仅在 doctor 报告缺少工具时：
python tools/bootstrap.py
python tools/doctor.py --app examples/native-ui
```

五个模板自带带许可证的字体子集、图标及原生资源缓存，默认创建与构建只需要 Python 标准库和锁定的 Zig/WABT。只有修改图标、生成新字形或重建这些资源时，才准备可选依赖：

```sh
python tools/bootstrap.py --features launcher
python tools/doctor.py --features launcher
```

可选 Pillow/fontTools 版本与 wheel 哈希见 [requirements-launcher.txt](../tools/requirements-launcher.txt)。它们安装在隔离缓存目录，不修改全局 Python。缺少合法字体或字形时明确报错；不得静默丢掉中文名、改为空白或从不明来源复制设备字体。

自定义中文标题超出默认小字库时，可准备公开 OFL 完整字体（只有第一次下载约 18 MB）：

```sh
python tools/font_cache.py
# 读取末行 JSON 的 font 与 license_file，再创建可移植子集：
python tools/create_app.py --template native-ui --id weather --name "Weather" --name-zh "天气预报" --font /reported/font.ttf --font-license /reported/LICENSE --output build/weather
```

字体与许可证固定到公开上游提交及 SHA，见 [font-assets.lock.json](../tools/font-assets.lock.json)。支持 `--offline`、`--archive-dir` 和 `--cache-dir`，复用相同共享缓存。创建器会生成改名后的轻量子集和原生字形缓存，后续构建无需完整大字体及第三方库。用户自己的合法字体也可通过同一参数提供；不能默认复制设备私有字体。

## 缓存布局与复用

默认根目录：

| 系统 | 根目录 |
| --- | --- |
| Windows | `%LOCALAPPDATA%/five-robot-xapp` |
| macOS | `~/Library/Caches/five-robot-xapp` |
| Linux | `$XDG_CACHE_HOME/five-robot-xapp`，未设置时为 `~/.cache/five-robot-xapp` |

`XAPP_CACHE_DIR` 或 `--cache-dir` 可指定共享目录。工具按操作系统、架构、版本和归档 SHA-256 隔离；Python 依赖另按解释器 ABI、平台和依赖锁哈希隔离。不同 SDK 目录可复用完全相同的工具，不混用不同发行锁。

显式 `--zig` / `--wabt`、`XAPP_ZIG` / `XAPP_WABT` 必须满足锁定版本。自动寻找还兼容 PATH、旧 SDK 的 `.tools` 与共享缓存。缓存使用前检查安装记录、可执行文件哈希、必要伴随文件与真实版本；这不等于对整个工具目录逐文件重新哈希。

同一工具的准备通过进程锁串行，先在临时目录验证再发布；失败不留下可被当成完整安装的半成品。不要让 AI 手写递归删除用户的缓存根目录。

## 下载、镜像与离线

下载源及 SHA-256 以 [toolchain.lock.json](../toolchain.lock.json) 为准。镜像若有配置，必须与官方归档逐字节相同；只允许 HTTPS，验证长度及哈希后才解压，下载有超时和明确错误。不能把 HTML 错误页当 ZIP，也不能无限重试。

```sh
# 已有官方归档：校验后直接准备，不出网
python tools/bootstrap.py --archive-dir /path/to/archives --offline
# 缓存已准备好：快速验证并复用
python tools/bootstrap.py --offline
# 可选资源依赖也有离线 wheel 目录入口
python tools/bootstrap.py --features launcher --wheel-dir /path/to/wheels --offline
```

`--archive-dir` 中文件名需与锁文件归档名一致。缓存不齐且 `--offline` 时明确失败，不偷偷访问网络。SDK ZIP 与镜像仓库也应固定发行标签、核对版本及文件清单；不要重复 clone 整个设备仓库。

`bootstrap` 输出 JSON 阶段、缓存命中和耗时，可保存为诊断日志。分开记录 SDK 获取、工具准备、资产生成、编译、独立验包和预览耗时；总耗时不能都算作“AI 开发时间”。

## 范围

缓存检查、编译、产品静态检查、主机测试、最终 WASM 预览及真机验收是不同证据。缓存命中不证明应用能运行；桌面音频和网络也不证明 C3 上的资源占用与流畅度。
