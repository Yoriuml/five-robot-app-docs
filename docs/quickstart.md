# 从零构建 XApp

AI 先完整读[统一执行契约](ai-workflow.md)；本页提供现有命令。模板、工具与证据范围见[实施说明](ai-rules-rollout.md)。

先下载完整 SDK，固定 sdk-release.json 中的发行版。可以 GitHub/Gitee clone，或从[官方索引](https://site.flashbot5.com/developer/v1/index.json)下载 sdk.zip 并检查 checksums.json 的哈希。只有模板 ZIP 不够，头文件和工具也要同版本。

## 准备工具

Python 3.10+，Zig 0.15.2，WABT 1.0.41。五套默认模板带合法资产缓存，无需 Python 第三方包。自定义资产再按[环境说明](environment-cache.md)准备依赖。

```sh
python tools/doctor.py --app examples/native-ui
```

doctor 报告缺少锁定版本工具时再运行 `python tools/bootstrap.py`，完成后重新执行 doctor；已有匹配工具不重复下载或准备。

bootstrap 按 toolchain.lock.json 选择归档、验证 SHA256、安全解压到跨 SDK 共享缓存并确认可执行文件和版本。兼容旧 .tools；已下载归档可用 `--archive-dir <目录> --offline` 准备。
下载不通时按[诊断说明](troubleshooting.md)换镜像/Invoke-WebRequest，不反复盲试。

已有工具时设置 XAPP_ZIG 为编译器路径、XAPP_WABT 为 WABT bin 目录，也可将工具加入 PATH。
构建命令支持显式参数 `--zig <可执行文件> --wabt <bin目录>`；不依赖任何作者工作站目录。

## 创建与构建

```sh
python tools/create_app.py --template native-ui --id my-app --name "My App" --output dist/my-app
python tools/build.py --app dist/my-app -o dist/my-app.xapp
python tools/validate.py dist/my-app.xapp --product
python tools/check_product.py dist/my-app.xapp --report dist/my-app.product.json
python tools/xapp/xapp_tool.py inspect dist/my-app.xapp
```

模板可选 hello、native-ui、native-ui-audio、resources-zh、http。创建器拒绝覆盖已有目录；`--name-zh` 指定中文展示名，超出默认子集时使用有许可且覆盖字符的字体，不能省略中文标题。
修改生成目录内 main.c/app.json；资源放 resources/。多文件 C 工程用重复 `--source` 指定。
普通桌面 C++ 的构造器、异常和标准库不能直接搬进 freestanding 应用。

构建失败返回非零，并保留旧输出；不要把旧 .xapp 当本次成功。成功产生包和同名 .validation.json，含 SHA256、最终 imports/exports、静态内存、工具版本和检查范围。
清单 required_exports/required_imports 可防止事件或退出接口被链接消除，只要求本应用确实需要的符号。
validate 从最终包重新解析并运行 WABT，不相信现成报告；inspect 只查看包/ABI，不代替语义验证。

## SDK 自检

```sh
python tools/test_sdk.py
```

这会检查文档和快照、Python 负例、五模板真实编译、独立产品包验证及原生 C 状态桩测试。
输出 build/template-check/。交互测试覆盖启动松手、空闲不重绘、极值/重复操作、网络失败/超时与退出。
原生桩不模拟设备渲染、TLS、音频或 C3 性能。Windows 可用 `py -3`，macOS/Linux 通常用 `python3` 替换命令前缀。

## 安装与验收

桌面 Chrome/Edge 打开[安装工作台](https://site.flashbot5.com/install)。设备进入“应用 → 应用安装 → 有线安装”，数据线连接后，由用户选择安装 .xapp。
无线安装按设备显示的地址操作。不要由 AI 自动连接、擦除或烧录。

模板通过 product_input.h 将产品的中键动作、左键返回映射到历史 ABI 原值。实际按键映射、事件位图与状态位图的差别见[输入契约](ai-workflow.md#6-按键与退出)，不能把旧 CONFIRM 名字直接解释为物理中键。
K2 不是系统退出快捷键；必须先释放启动键。

按[验收清单](testing.md)记录实际设备启动、连按、进入退出、网络与声音、最坏资源和性能。未经验证不得将 runtime_tested/hardware_tested 改为 true。
