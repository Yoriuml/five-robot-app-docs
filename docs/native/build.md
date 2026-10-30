# 原生工程、环境复用与构建

专题 ID：`build`。新工程必读。本页是工程合同，不是已经编译验收过的公开 BSP 模板。屏幕、Codec 与电源实现必须按对应专题写完整。

## 先用现有环境

目标 `esp32c3`，使用 ESP-IDF 6.1.x 和对应 RISC-V 工具链、Python 环境、CMake、Ninja。先在已激活的 IDF 终端检查 `idf.py --version` 与 `python --version`；不要为一个新 APP 重装 IDF、下载 Zig／WABT 或克隆 XApp SDK。未激活则使用用户已安装 IDF 的 export 脚本，不修改全局 PATH。

缺少工具时只从官方来源补齐与目标版本匹配的内容，固定版本并校验可得的官方摘要。一个地址失败不反复尝试；从本地缓存、另一官方镜像或离线归档继续。无可用编译器时仍交付完整源码，并明确没有生成实际 BIN。

同 IDF／芯片／编译器的下载归档和组件缓存可复用；不同板型、工程路径、编译配置使用不同构建目录。工程移动后 CMake 缓存中的绝对路径失效，使用新的目录，不能为“清理缓存”递归删除用户工程。

## 工程必须包含

```text
project/
  CMakeLists.txt
  sdkconfig.defaults
  partitions.csv
  boards/ch343-v1.defaults
  boards/native-usb-v2.defaults
  main/CMakeLists.txt
  main/idf_component.yml       # 仅在用 managed components 时
  main/app_main.cpp
  components/board/            # 完整 GPIO、PCA、电源、LCD；按需音频
  assets/                     # 实际资源和许可证
  dependencies.lock           # 组件解析后保留
  README.md
```

顶层 CMake 使用 ESP-IDF 的 `tools/cmake/project.cmake`，通过 `idf_component_register` 注册源码和实际依赖。不引用开发者电脑的私人绝对路径，不依赖未交付的 `board.h`、二进制或私有仓库。不把 IDF 已自带的 FreeRTOS 再复制一份。

板型选择需由工程实际定义并接入 CMake／Kconfig：例如 `BOARD_PROFILE` 只是一种**自定义选项名**，不是 ESP-IDF 内置参数。它必须控制 [hardware](hardware.md) 的按键、PCA 方向、背光与控制台，未知值直接构建失败。只在 README 写选项而代码未读取不算支持双板型。

## 配置与可复制命令

公共 defaults 至少明确芯片、16 MiB Flash、DIO／80 MHz（基线）、自定义分区 CSV。保存构建实际生成的 sdkconfig，核对生成的 `config/sdkconfig.h`，不能仅凭 defaults 文件名认定已生效。

CH343 板：UART0 默认控制台 115200，关闭应用阶段 USB Serial/JTAG 主／次控制台及模块；按键保留 GPIO18／19。原生 USB 板：USB Serial/JTAG 控制台，不在 GPIO20／21 配置 UART0，按键保留 GPIO20／21。

在已创建完整工程并进入工程根目录的 IDF 终端，可使用 IDF 自带变量，不依赖私有脚本：

```sh
idf.py -B build/ch343-v1 -DSDKCONFIG=build/ch343-v1/sdkconfig -DSDKCONFIG_DEFAULTS="sdkconfig.defaults;boards/ch343-v1.defaults" -DIDF_TARGET=esp32c3 build
idf.py -B build/native-usb-v2 -DSDKCONFIG=build/native-usb-v2/sdkconfig -DSDKCONFIG_DEFAULTS="sdkconfig.defaults;boards/native-usb-v2.defaults" -DIDF_TARGET=esp32c3 build
idf.py -B build/ch343-v1 size
```

上述分板 defaults 必须与项目的板型宏实际绑定。顶层 CMake 不得无条件覆盖调用者传入的 `SDKCONFIG_DEFAULTS`。首次构建可以设置目标，已有板型目录不要用 `set-target` 来切换另一块板。

**defaults 不覆盖已有 sdkconfig。**改音频、TLS、板型或分区后，先核对实际配置，必要时使用新的构建目录。只改默认配置后复用旧 BIN 是常见假修复。Windows 若因长路径／内存导致构建失败，可缩短新工程路径、降低构建并行度；不要把构建 `-j1` 写成运行时性能要求。

## 按需组件与资产

- 不需要 GUI 库时可以直接条带渲染；需要时基线 LVGL 9.5，音频控制基线 `esp_codec_dev` 1.5.6。在组件清单固定具体解析版本并保存锁文件。
- 只做音效不自动加入全部流媒体解码器；不使用的 Wi-Fi、BLE、音频、文件系统不进入初始化链。
- 中文／图片／PCM 在电脑离线生成，生成器＋源资源＋许可证一并交付。只在源输入或生成器改变时重建，缓存按输入哈希和工具版本区分。
- 字体采用许可允许的 HarmonyOS Sans SC 或用户指定字体，不用 Noto Sans SC，也不偷偷换成其别名；缺字应明确失败。嵌入实际字形子集，不把完整大字库搬到 RAM。

## 最少下载与 AI 按需查阅

先下载入口，再取本次必读和所用专题；同版号／同哈希的本地文件复用。机器目录 [index.json](index.json) 给出相对路径和摘要。已有仓库时：

```sh
python tools/native_context.py --topics display-ui,audio
python tools/native_context.py --check
```

`--topics` 自动补硬件、电源、构建，只输出相关内容，不下载、不构建、不调用模型。目录是资料索引，不是 XApp 的 `api.json`，也不宣称提供原生 BSP API。

GitHub raw 根：`https://raw.githubusercontent.com/Yoriuml/five-robot-app-docs/main/`；Gitee raw 根：`https://gitee.com/yorium/five-robot-app-docs/raw/main/`。路径例如 `docs/native/audio.md`。一个镜像失败立即切换，下载检查 HTTP 状态、非空、不是 HTML；先获得 index 后可校验字节数和 SHA-256。

Git／curl 失败时，Windows 可用 `Invoke-WebRequest -Uri "完整 raw 地址" -OutFile "目标文件"`，再读取文件。raw 持续失败可读 GitHub `https://api.github.com/repos/Yoriuml/five-robot-app-docs/contents/docs/native/audio.md?ref=main`，按返回的 `encoding=base64` 解码 `content`。不要把错误页保存为头文件，也不要重建猜测头文件。一次任务固定入口版号和文件摘要；若目录／文件不匹配，重新获取同一提交，不能混用镜像缓存的不同修订。

构建结束交付实际产物、地址、哈希和分级证据，见 [images-recovery](images-recovery.md) 与 [troubleshooting](troubleshooting.md)。
