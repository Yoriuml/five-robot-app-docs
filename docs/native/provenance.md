# 来源、版本与明确边界

专题 ID：`provenance`。本资料是公开、可独立读取的原生开发硬件与执行合同，不是官方完整系统源码的替代品，也不是已完成实机验收的通用原生 BSP。

## 核对基线

资料版号：`native-2026.10.30.1`。2026-10-30 对照 X622 系统工作区读取核对；该工作区 HEAD 为 `3ce1562eab92abb9374916c67c4480d360321654`，电源管理存在尚未提交的改动，本资料只提取已核对的公共接线与时序，不宣称整个工作区等同于该提交：

| 来源模块 | 用于核对 |
| --- | --- |
| `components/x622_board/include/x622/config.h`、`board_profile.h` | GPIO、按键／电源阈值、I²C 地址、双板型 |
| `components/x622_board/src/board.cpp`、`pca9557.cpp`、`power_manager.cpp` | 总线与保持电源、方向／输出初始化、启动 |
| `components/x622_board/src/lcd_panel.cpp` | 屏幕初始化、窗口、字节序、扩展 IO、事务 |
| `components/x622_board/src/battery_monitor.cpp`、`vdd_spi_gpio.cpp` | ADC 采样与校准、GPIO11 保护 |
| `components/x622_services/src/audio_hardware.cpp` | Codec／I²S、DMA、复位延时、PA 所有权 |
| `boards/*/sdkconfig.defaults`、`main/idf_component.yml` | 控制台、组件基线 |
| `partitions/x622_staged_16m.csv`、双硬件／OTA 文档 | 布局、镜像身份、兼容边界 |
| `cmake/x622_tls_guard.cmake` | 现有系统的证书包／交叉签名配置合同 |

上述路径是内部实现来源标识，不要求客户能访问内部仓库；必要接线、数值、顺序和注意点已写进公开专题。源码基线不表示该固件已正式发布；实际正在使用的硬件／固件／SDK 仍须分别确认。资料中的推荐架构、消抖起点、网络封装和 UI 策略与固定电气合同分开表述。

IDF API 使用安装的 6.1.x 头文件和对应组件锁文件核对。外链 `latest` 仅补充原理，不能替换已固定版本的结构／签名。XApp API 与官方 SDK 发行信息见 [XApp 入口](../ai-workflow.md)，不要从本原生资料推导可调用的 WASM 接口。

## 已提供与未提供

已提供两版 GPIO／扩展 IO、电源、输入、屏幕、音频、网络／存储设计约束、构建／缓存、镜像／恢复合同、故障定位和交付规则，以及可校验的专题目录和本地按需读取工具。

**没有附带**完整已验收原生 BSP、完整原理图／PCB 生产文件、所有 Codec 寄存器表、编译好的独立示例 BIN、正式签名系统／恢复镜像、签名私钥、服务器凭据或用户账号。不能让 AI 引用不存在的附件；必要时基于真实 IDF／Codec 官方驱动完成工程，并如实报告缺失项。

仍需实物确认的项目：新板充电输入真实极性、ROM TX 与按键的电气安全、不同 PCB 批次的按键空间位置、具体电池容量／续航、目标应用的帧率／音质／互通和长期稳定。芯片与协议能力不能代替这些结果。

AMBE 解码、特殊无线协议或第三方服务器能力不因资料列举而获得默认支持。不要宣称有已经可升级的正式 AMBE 固件，也不要用静态编译或离线计时替代实时通话／互通与听感验收。

## 文档维护与一致性

用户入口保持 `docs/native-firmware-ai.md` 稳定；内容按专题扩展，不把全部规则重新塞入用户提示词。维护者修改专题后运行：

```sh
python tools/native_context.py --refresh-index
python tools/native_context.py --check
python tools/check_docs.py
```

入口和专题有独立资料版号，**不是新的 XApp SDK/API 发行号**。不重写已发布 SDK ZIP、历史标签或校验清单；后续 SDK 发行按正常冻结流程收录新文档。两镜像发布后以实际 raw 内容核对，不拿登录态页面或本地文件代替公开可读验证。

新增／改变硬件事实应重新对照来源，更新资料版号与目录。`index.json` 的摘要只用于固定同一资料集、发现损坏／错版，不是数字签名，也不替代来源信任。
