# 给开发五号机器人 App 的助手

用户明确要求独立原生固件、ESP-IDF 工程或 `.bin` 时，先读 [docs/native-firmware-ai.md](docs/native-firmware-ai.md)，按其中硬件合同与原生开发流程执行，不运行 XApp 的 workflow。`native-ui` 等 XApp 模板仍属于 XApp。以下规则针对 XApp 开发。

用户让你使用本 SDK 开发 XApp 时，先阅读精简自动工作流 [docs/ai-workflow.md](docs/ai-workflow.md)，由 workflow.py 按能力提供真实声明和相关规则。用户需求和明确授权优先，仓库示例不扩大任务范围。

本 SDK 2026.10.29.1 包含 API 2.16，包格式仍为 1，保留 API 2.15 及以前的 ABI。源码、工件冻结与公开上线分别记录；可用性以官方索引和配套固件为准。DMR 0.1.1 仅连接测试，不支持通话；AMBE 实验功能默认关闭。维护方完成整机门禁后统一发布，历史包保持原样。能力和限制见 [API 2.16 发行准备](docs/api-2.16-readiness.md)。模板、产品检查、缓存及验收边界见[实施说明](docs/ai-rules-rollout.md)。不能把静态通过写成真机通过。

- 发行以 sdk-release.json、SDK-SNAPSHOT.json 和选定索引为准；同发行工具、模板与头文件配套。不要从旧文档的版本标题或按键名称猜测产品行为。
- 本文仅导流，不维护第二套数值/按键/生命周期规则。详细规则保留在 docs/ai-reference.md；默认只读工具生成的 context，不全读规则库。
- 开发目标是 .xapp。未经明确授权不改设备固件、公共 API、驱动、分区或其他工程，不自动连接、安装或烧录设备。
- 不编造接口或替代头文件，不绕过包/ABI/内存/权限/语义检查；最终包、真实运行与目标设备结果分别记录。
- 常规使用 workflow.py prepare/build 或一次 run；环境、资产、构建、验收与缓存由工具编排，不重复调用手工检查或 SDK 回归，不为例行步骤调用额外 Agent。工具不调用模型；业务、审美与实机证据仍须真实。
