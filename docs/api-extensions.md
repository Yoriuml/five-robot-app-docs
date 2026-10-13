# API 扩展导航

所有结构、大小、常量与函数签名以对应头文件为准。不要从能力名称推断没有声明的接口。

| API | 新增能力 | 声明 |
| --- | --- | --- |
| 2.1 | 生命周期、绘图、存储、网络 | [主 SDK](../sdk/xapp/x622_xapp.h) |
| 2.2 | 按键状态 input_state | [主 SDK](../sdk/xapp/x622_xapp.h) |
| 2.3 | 本地音频、BLE 外设、异步 HTTP、串口 | [音频](../sdk/xapp/x622_audio.h)、[BLE](../sdk/xapp/x622_ble.h)、[HTTP](../sdk/xapp/x622_http.h) |
| 2.4 | 双音轨与资源背景 | [音频](../sdk/xapp/x622_audio.h)、[主 SDK](../sdk/xapp/x622_xapp.h) |
| 2.5 | 有界光栅、纹理与缩放 | [光栅](../sdk/xapp/x622_raster.h) |
| 2.6 | ESP-NOW 有界收发 | [数据报](../sdk/xapp/x622_datagram.h) |
| 2.7 | PCM 采音/播放、信号计算 | [音频流](../sdk/xapp/x622_audio_stream.h)、[信号](../sdk/xapp/x622_signal.h) |
| 2.8 | 模块音乐 | [Tracker](../sdk/xapp/x622_tracker.h) |
| 2.9 | 扩展 HTTP、GATT、加密、临时网关 | [HTTP](../sdk/xapp/x622_http_ex.h)、[GATT](../sdk/xapp/x622_ble_gatt.h)、[加密](../sdk/xapp/x622_crypto.h)、[网关](../sdk/xapp/x622_gateway.h) |
| 2.10 | 有界 VAD | [信号](../sdk/xapp/x622_signal.h) |
| 2.11 | 应用自主退出 x622_exit | [主 SDK](../sdk/xapp/x622_xapp.h) |
| 2.12 | 双输入报告 HID | [BLE](../sdk/xapp/x622_ble.h) |
| 2.13 | 私有文件流、PCM 音量 | [主 SDK](../sdk/xapp/x622_xapp.h)、[音频流](../sdk/xapp/x622_audio_stream.h) |
| 2.14 | HID 触摸屏 Feature Report | [BLE](../sdk/xapp/x622_ble.h) |
| 2.15 | 原生缓存 UI、纹理、动画与统计 | [UI](../sdk/xapp/x622_ui.h) |

## API 2.15 绘制顺序

1. ui_config 配置背景、帧周期、纹理预算与 DMA 条带。
2. 字体/图标预先上传为 A4 或 RGB565 纹理，不反复读取或每帧重建。
3. ui_scene 提交完整有序节点数组。节点使用稳定 ID，原生侧计算脏区和插值。
4. 改变同 ID 节点的目标位置/颜色/透明度即可动画；不要用 WASM 逐像素追帧。
5. 通过 ui_stats 读取实际耗时；frame_ms 是目标周期，不是硬件帧率承诺。

配置结构 16 B，节点 32 B；每场景 1..32 节点，最多 16 个纹理槽，A4 高半字节在先。
使用 ui_* 时，app.json 必须声明 api_minor 至少 15。配置和节点结构必须正确填 size/version 与保留字段。
