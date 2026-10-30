# X622 原生固件：AI 开发入口

资料版号：`native-2026.10.30.1`。目标：五号机器人／X622 的独立 ESP-IDF 工程与 `.bin`。本入口与专题资料一起使用；不要求一次读完整资料库。

若需求是在官方系统中安装 `.xapp`，转到 [XApp 自动工作流](ai-workflow.md)，使用官方索引锁定的同发行 SDK。`native-ui` 是 XApp 模板，不是独立固件。本资料不改变 XApp API，也不将原生驱动函数当成 XApp 导入。

## 给用户的一句话

> 读取 https://gitee.com/yorium/five-robot-app-docs/raw/main/docs/native-firmware-ai.md ，按索引按需查资料，为五号机器人开发独立原生固件，交付完整工程和实际编译的 BIN。需求：【填写需求】。Gitee 失败时将 raw 根前缀换为 https://raw.githubusercontent.com/Yoriuml/five-robot-app-docs/main/ 。

## AI 首次执行

1. 先读本文，以及 [硬件合同](native/hardware.md)、[电源与按键](native/power-input.md)、[环境与构建](native/build.md)。以后只补读功能涉及的专题；读取过且哈希相同的资料直接复用。不要为了查接线下载整个 XApp SDK。
2. 默认：中文、中键主动作、左键返回、上下键选择；清晰大主体、少说明文字、非线性动画、不用 Noto Sans SC。具体方案自行完成，用户的明确需求优先。
3. 默认离线首屏可用；网络、音频和 BLE 用到才申请，退出、取消、失败均清理。实现完整功能，不交空壳、伪代码或冒充硬件的预览。
4. 原生工程放独立目录。只构建不代表授权连接、擦除、烧录、改 eFuse 或覆盖官方工程。板型未知时生成双板型目标；只在实际安装前确认物理板型和写入范围。
5. 完整功能所需的外部凭据、用户私有服务地址确实缺失时，一次询问必要信息；先完成不依赖它的部分。已知硬件、接线、音频参数、构建和恢复信息按本资料查询，不再逐项要求客户提供。
6. 无法从资料得出结论时标明缺口和具体影响，不猜硬件、不编造 API／可用签名固件。资料范围和尚未验证的边界见 [来源与能力边界](native/provenance.md)。

## 按需查询

| 需求／错误 | 读取 |
| --- | --- |
| MCU、GPIO、两版 USB、芯片地址、扩展 IO | [hardware](native/hardware.md) |
| 电源保持、启动、关机、四键、ADC／充电 | [power-input](native/power-input.md) |
| 安装 IDF、缓存、工程结构、双板型构建、依赖 | [build](native/build.md) |
| 首屏、屏幕时序、字节序、中文、动画、LVGL | [display-ui](native/display-ui.md) |
| 扬声器、录音、ES8311、音频队列／抢占 | [audio](native/audio.md) |
| Wi-Fi、TLS、BLE、电脑连接、时间、数据存储 | [network-storage](native/network-storage.md) |
| 内存不足、DMA、卡顿、调度和资源生命周期 | [performance](native/performance.md) |
| 分区、完整 BIN／APP BIN、备份、恢复、下载失败 | [images-recovery](native/images-recovery.md) |
| 黑屏、复位、无声、证书失败、交付／验收记录 | [troubleshooting](native/troubleshooting.md) |
| 资料依据、已知缺口、可用与未验收的区别 | [provenance](native/provenance.md) |

机器可读导航：[native/index.json](native/index.json)，包含专题 ID、触发词、路径、字节数和 SHA-256。已有本地资料时，一次读取相关内容：

```sh
python tools/native_context.py --topics display-ui,audio
```

工具自动带上三个必读专题，不联网、不下载工具、不调用模型、不操作设备。`--list` 仅列目录；`--check` 校验专题完整性。没有 Python 也可直接读取上表链接。

## 获取与交付

远程读取时，以当前成功镜像的仓库 raw 根 URL 拼接 `docs/native/...`；不要拿 GitHub/Gitee 的 HTML 页面当源码。一次失败即切镜像，仍失败可用 GitHub contents API 的 base64；见 [build](native/build.md)。先冻结本次资料版号和哈希，不混合更新后的其他版本。

交付源码、资源及许可证、锁定依赖、板型配置、分区表、构建命令、实际 BIN/ELF、构建生成的地址清单和 SHA-256；验收表分开记录编译、主机、预览、实机。未实机验证的声音、网络、帧率和续航不得写成通过。详细清单见 [troubleshooting](native/troubleshooting.md)。
