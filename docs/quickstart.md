# 从零构建一个 XApp

## 1. 工具

准备 Python 3.10+、[Zig 0.15.2](https://ziglang.org/download/)、[WABT 1.0.41](https://github.com/WebAssembly/wabt/releases/tag/1.0.41)。使用官方发布文件，并核对下载来源。按你的系统选择可执行文件；这里不自动下载或安装工具。

最小示例只用 Python 标准库。需要制作中文启动器名称或 PNG 图标时，再安装 `Pillow` 和 `fonttools`，并准备有合法使用权限的字体。

```sh
git clone https://github.com/Yoriuml/five-robot-app-docs.git
cd five-robot-app-docs
```

## 2. 构建示例

把命令中的工具路径改成自己的路径。命令可写在一行，不依赖 PowerShell / Bash 的续行符。

```sh
python tools/build.py --app examples/hello --zig /path/to/zig --wabt /path/to/wabt/bin -o dist/hello.xapp
python tools/xapp/xapp_tool.py inspect dist/hello.xapp
```

Windows 示例：`--zig C:/tools/zig/zig.exe --wabt C:/tools/wabt/bin`。macOS/Linux 示例不带 `.exe`。如果你的 Python 命令为 `python3`，替换命令前缀。

得到 `dist/hello.xapp` 与 `dist/hello.validation.json`。报告包含包大小、SHA-256、内存布局与检查结果。工具必须找到 `wasm-validate` 与 `wasm2wat`，校验失败不覆盖旧的输出包。

## 3. 运行仓库检查

```sh
python tools/check_docs.py
python -m unittest discover -s tests -p "test_*.py"
python tests/check_package.py dist/hello.xapp
```

示例按键的原生桩测试（不会访问设备）：

```sh
zig cc -std=c11 -I sdk/xapp tests/hello_test.c -o dist/hello-test
```

再运行生成的 `dist/hello-test`（Windows 为 `dist/hello-test.exe`）。这里的桩仅验证示例状态与退出，不是宿主渲染器模拟。

## 4. 安装到设备

用桌面 Chrome/Edge 打开[安装工作台](https://site.flashbot5.cn/install)。设备进入「应用 → 应用安装 → 有线安装」，用数据线连接，选择 `.xapp` 后由你确认安装。
支持本机无线安装时，也可进入「无线安装」，按设备显示的地址用浏览器上传文件。

示例操作：上/下选择 Hello 与 Exit APP；短按确认执行当前项。选择 Exit APP 后确认退出。示例不用 K2，也不依赖隐藏的系统退出手势。

## 5. 改成自己的应用

复制 `examples/hello`，修改 app.json 的 id、name、version；编辑 main.c。额外资源放 `resources/`。多 C 文件项目可使用 `--source` 多次指定文件。此构建工具按 C 应用配置；C++ 需要另行处理导出、构造器、异常与 freestanding 约束，不应直接套用普通桌面 C++ 项目。

## 校验边界

构建执行 Zig、WABT 指令语义、固定内存/导入白名单/权限/API、包 CRC32 与 SHA-256 检查。报告中的 `runtime_tested` 和 `hardware_tested` 默认 false：本仓库没有私有 WAMR 宿主与设备驱动模拟。
真实安装、启动、退出和功能测试由开发者在设备上完成。共享作品前记录[验收清单](testing.md)，不要只凭打包成功声称功能通过。
