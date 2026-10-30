# 故障自查、交付与证据

专题 ID：`troubleshooting`。先读取与错误所属功能对应的专题；不要把整库和全量历史日志反复交给模型。

## 按症状定位

| 症状 | 第一批检查 | 继续读取 |
| --- | --- | --- |
| 松手就断电／反复重启 | PCA IO1 是否保持、是否被 LCD 更新清除、冷启动条件、实际复位原因 | [power-input](power-input.md) |
| 亮背光但无内容／白屏 | PCA 方向、RESET／DC／CS、初始化返回值、RAMWR、DMA 完成、首帧提交 | [display-ui](display-ui.md) |
| 花屏／颜色颠倒／边缘错位 | RGB565 字节序是否只换一次、窗口端点、源 stride、缓冲寿命、方向／反色 | [display-ui](display-ui.md) |
| 按键错位／USB 消失 | 实物板型与实际编译宏；GPIO18／19 与 20／21 是否冲突 | [hardware](hardware.md) |
| 立即退出／OOM／最大块不够 | 最后成功阶段、分配大小／能力、静态区、堆总量与 largest、初始化峰值 | [performance](performance.md) |
| 只有画面卡，其他输入仍有反应 | GUI 状态／帧队列、长持锁、资源重载、阻塞回调、逐帧堆分配 | [performance](performance.md) |
| 无声／开头音被吃／按键抢音 | PA 时序、单一 I²S owner、Codec 地址、数字数据、音量与采样率 | [audio](audio.md) |
| 录音全零／杂音／声音不连续 | DIN、槽／格式、增益、采集是否连续、DMA 时长、丢帧／队列欠载 | [audio](audio.md) |
| 已连 Wi-Fi 却请求失败 | IP 事件、DNS、时间、HTTP 状态、TLS 错误／连续内存、真实服务是否可达 | [network-storage](network-storage.md) |
| 蓝牙能看见却连不上／通知无数据 | 广播与连接区别、GATT UUID、订阅、MTU、旧句柄、配对／权限状态 | [network-storage](network-storage.md) |
| 改 defaults 但行为没变 | 实际 sdkconfig／生成头、构建目录、产物时间／哈希、是否混用了旧 BIN | [build](build.md) |
| 一直 Connecting／提速后失败 | 端口占用、板型、复位、真实速率、每阶段超时和清理、换低速有限重试 | [images-recovery](images-recovery.md) |
| 文件系统挂不上／旧应用丢失 | 当前真实分区表、是否误写完整镜像／格式化、原布局与备份 | [images-recovery](images-recovery.md) |

故障按最早失败阶段定位，不把后续连带错误当根因；例如音频初始化失败后出现的停止错误，不一定是首次故障。OOM、TLS 验签和 DMA 错误需要保留真实返回值，不能一句“证书不对”包打天下。

## AI 应先自动收集，避免反复问客户

能从工程／日志得到的信息自己读取：资料版号、板型宏、IDF／组件锁版本、实际 sdkconfig、分区表、构建目录与产物 SHA、最后成功阶段、native 错误码、free／largest／DMA、队列峰值和任务栈记录。

只有用户环境才能确定的信息一次问清：实际板型／连接方式、具体重现操作、私有服务凭据、明确的数据保留与刷写授权。普通技术参数不让客户从聊天记录拼凑。

确需转交人工支持时，生成这一份脱敏记录，不要让用户逐项手填已有数据：

```json
{
  "docs_revision": "native-2026.10.30.1",
  "target": "native-firmware",
  "board": "ch343-v1 or native-usb-v2 or unconfirmed",
  "idf_version": "actual",
  "source_revision": "actual commit or source digest",
  "artifact_sha256": "actual final image digest",
  "partition_table": "actual CSV or decoded table",
  "phase": "last successful -> first failing phase",
  "error": {"name": "actual", "code": "actual"},
  "memory": {"free_8bit": null, "largest_8bit": null, "free_dma": null},
  "reproduce": ["minimal observed steps"],
  "evidence": {"compiled": false, "host": false, "preview": false, "hardware": false},
  "missing_external_information": [],
  "actions_already_taken": []
}
```

不知道的值保留 null／明确未测，不填估计值冒充测量；不附密码、token、私钥、用户录音或无关个人数据。

## 交付必须完整

1. 独立可重建工程：源码、CMake、板型 defaults／选择实现、分区 CSV、组件清单／锁文件、资源生成器、资源与许可证。没有私人 include 路径或未提供的 BSP 依赖。
2. 功能：离线完整首屏、明确中键主动作与左键返回、启动松手、失败和停止清理；仅启用所需外设。按需求完成 PC／服务器对端，不把未部署的服务写成现成接口。
3. 实际构建：每个声称支持的板型的 BIN／ELF／map、构建命令、生成的地址清单、大小与 SHA-256。未构建成功就明确“源码交付，BIN 未生成”。
4. 用户可执行说明：打开哪一工程、选哪一板型、如何重建、哪些文件用于何种安装路径、覆盖范围、错误日志在哪里。操作说明放文档，设备画面不塞小字教程。
5. 针对功能的验证记录：最重资源／文本／帧分支、错误注入、取消、反复进入退出；声音与网络分别记录数字／真实端到端／听感证据。

## 证据分级与停止条件

| 类别 | 可以说明 | 不能替代 |
| --- | --- | --- |
| 静态／编译 | 语法、链接、静态大小、资源和地址一致 | 开机、真实 DMA／外设、声学 |
| 主机测试 | 逻辑、边界、协议／清理分支 | C3 调度、连续内存、USB／BLE 兼容 |
| 桌面预览 | UI 布局、帧序列、交互 | 实机帧率、音频、功耗 |
| 实机 | 本板、本镜像、本条件下的观察 | 其他板型、不同网络、长期稳定和互通 |

验证与改动相称，检查通过后直接交付，不重复跑无关回归。不得自动升级证据等级、制造硬件日志或承诺“一定一次成功”。还缺实机时提供准确的最小验证步骤；用户说先交付／暂停测试就停止设备操作。
