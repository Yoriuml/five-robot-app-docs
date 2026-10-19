# 从零构建 XApp

先下载完整 SDK，固定 sdk-release.json 中的发行版。可以 GitHub/Gitee clone，或从[官方索引](https://site.flashbot5.com/developer/v1/index.json)下载 sdk.zip 并检查 checksums.json 的哈希。只有模板 ZIP 不够，头文件和工具也要同版本。

## 准备工具

Python 3.10+，Zig 0.15.2，WABT 1.0.41。四套示例均无需 Python 第三方包。

```sh
python tools/bootstrap.py
python tools/doctor.py
```

bootstrap 按 toolchain.lock.json 选择官方归档、验证 SHA256、Python 解压到 .tools 并确认可执行文件和版本。已下载归档可用 `--archive-dir <目录>` 离线准备。
下载不通时按[诊断说明](troubleshooting.md)换镜像/Invoke-WebRequest，不反复盲试。

已有工具时设置 XAPP_ZIG 为编译器路径、XAPP_WABT 为 WABT bin 目录，也可将工具加入 PATH。
构建命令支持显式参数 `--zig <可执行文件> --wabt <bin目录>`；不依赖任何作者工作站目录。

## 创建与构建

```sh
python tools/create_app.py --template native-ui --id my-app --name "My App" --output dist/my-app
python tools/build.py --app dist/my-app -o dist/my-app.xapp
python tools/validate.py dist/my-app.xapp
python tools/xapp/xapp_tool.py inspect dist/my-app.xapp
```

模板可选 hello、native-ui、resources-zh、http。创建器拒绝覆盖已有目录。
修改生成目录内 main.c/app.json；资源放 resources/。多文件 C 工程用重复 `--source` 指定。
普通桌面 C++ 的构造器、异常和标准库不能直接搬进 freestanding 应用。

构建失败返回非零，并保留旧输出；不要把旧 .xapp 当本次成功。成功产生包和同名 .validation.json，含 SHA256、最终 imports/exports、静态内存、工具版本和检查范围。
清单 required_exports/required_imports 可防止事件或退出接口被链接消除，只要求本应用确实需要的符号。
validate 从最终包重新解析并运行 WABT，不相信现成报告；inspect 只查看包/ABI，不代替语义验证。

## SDK 自检

```sh
python tools/test_sdk.py
```

这会检查文档和快照、Python 负例、四模板真实编译、独立包验证及原生 C 状态桩测试。
输出 dist/template-check/。交互测试覆盖启动松手、空闲不重绘、极值/重复操作、网络失败/超时与退出。
原生桩不模拟设备渲染、TLS、音频或 C3 性能。Windows 可用 `py -3`，macOS/Linux 通常用 `python3` 替换命令前缀。

## 安装与验收

桌面 Chrome/Edge 打开[安装工作台](https://site.flashbot5.com/install)。设备进入“应用 → 应用安装 → 有线安装”，数据线连接后，由用户选择安装 .xapp。
无线安装按设备显示的地址操作。不要由 AI 自动连接、擦除或烧录。

hello：上下选择并中键确认 Exit；native-ui：上下/中键切换，长按中键 2 秒退出；中文资源：下键选择 Exit、中键退出；HTTP：中键退出。
K2 不是系统退出快捷键；必须先释放启动键。

按[验收清单](testing.md)记录实际设备启动、连按、进入退出、网络与声音、最坏资源和性能。未经验证不得将 runtime_tested/hardware_tested 改为 true。
