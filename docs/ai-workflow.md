# AI 开发 XApp：自动工作流

用户的一句话保持不变：

```text
按 https://site.flashbot5.com/developer/v1/index.json 对应 SDK 的 docs/ai-workflow.md 开发 XApp：【需求】。
```

使用选定索引的同一发行 SDK；完整 ZIP 只下载一次，校验索引大小与 SHA-256，匹配副本直接复用。不逐文件联网、反复 clone 或重建工具链。在 SDK 根目录运行，需要 Python 3.10+。

## 常规只做两步

1. 选最接近的模板和实际能力，一次准备：

```sh
python tools/workflow.py prepare --app work/my-app --id my-app --name "My App" --name-zh "应用" --template native-ui --capabilities ui --inline-context
```

直接使用响应的 `context_text` 与 `editable_files`，不重复读文件。工具提供相关规则、真实 API 声明与结构；不全读历史或未用能力。自定义中文名缺字时自动准备锁定的公开字体与隔离依赖。只补业务、UI、资源生成和测试，沿用模板的启动松手、退出、首屏与清理。能力：ui/gfx/audio/http/net/ble/stream/tracker/signal/datagram/crypto/gateway/storage/device。

首次写全业务、资源生成器和最坏分支测试，不拆成计划、骨架、补资源等多轮。JSON 请求的 `imports` 追加实际业务接口，工具核对存在性并计算权限和 API 版本；不自动放宽显式限制。

2. 编写完成后，一次交付：

```sh
python tools/workflow.py build --app work/my-app
```

工具自动补齐工具、生成变化资源、编译、检查最终 WASM/权限/内存/展示元数据、运行 `workflow.json` 的 APP 测试，交付包、源码 ZIP 和报告。相同输入复用验证；失败只读错误和日志，修正后重试本步。不重复运行 doctor、validate、check_product、inspect 或 SDK 全套回归。

已掌握契约且有源码时，将源码与元数据合为 JSON，一次 `run` 完成创建到交付，见[自动化接口](workflow-automation.md)。工具不调用模型；计划、复述、例行检查不另起 Agent。

## 每个 APP 都必须保留

- 只修改当前 APP；不编造 API，不擅改固件/API/分区，不自动安装或烧录。
- 离线完整首屏、启动松手、中键动作、左键返回；所有状态都能退出。接口错误、异步停止和迟到结果须处理。
- 有界回调；按时间推进非线性动效；静态文字与纹理复用，不能每帧重载或无变化全屏刷新。
- 中文 UI 优先 HarmonyOS Sans SC；禁止 Noto Sans SC 及其别名，不得缺字时静默回退。具体字体规则由 context 的 GFX-10 提供。
- 同时计算 WASM、UI、音频、Wi-Fi/TLS 的峰值和连续块；Flash 不是 RAM。不开关证书验证来掩盖联网问题，不抢系统声音。
- BLE选 `ble`，IP UDP/WebSocket选 `net`，UTC选 `device`。新增入口需配套API2.16固件，可用性以所选索引为准。普通Beacon仅自有UUID/有界服务数据，不是任意广播或手机弹窗。AMBE仅有默认关闭、未通过实时性/独立向量的实验接口，不自动使用；APP HTTP服务器未提供。
- `stream` 的 PCM 导入最低 API 2.7 仍保留：16 kHz 采集／播放不变；8 kHz 仅 API 2.16 播放可用，不能按导入名的最低版本放行旧固件。按真实输入速率配置，不为原生 8 kHz 源额外升采样。详见 context 的 IO-08。
- 遵守用户的视觉和功能需求；按最坏分支编写有意义的业务测试，不能只改模板名称就宣称完成。
- `candidate` 只表示候选包。静态、主机、最终 WASM 与实机分别记录，缺少的运行/预览/实机项保持未测。交付简要写明版本、按键、已测与限制。

完整规则保存在[规则库](ai-reference.md)，按能力或具体错误查阅，不再默认全读。用户明确要求的步骤和授权优先。
