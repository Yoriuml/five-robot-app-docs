# 自动化接口与维护说明

SDK 2026.10.28.1。可用性以官方索引与配套固件为准。用户的一句话及 `docs/ai-workflow.md` 入口保持不变。
常规 AI 只读[短入口](ai-workflow.md)、工具生成的 context 和目标模板源码。
完整规则移至 [ai-reference.md](ai-reference.md)，保留稳定编号，不再全量注入每个任务。

## 一次准备、一次交付

```sh
python tools/workflow.py prepare --app work/demo --id demo --name "Demo" --template native-ui --capabilities ui --inline-context
# AI 读取返回的 context 与模板，一次写业务、资源生成器和相关测试。
python tools/workflow.py build --app work/demo
```

`prepare` 自动复制模板、准备需要的新中文名资产并生成能力上下文。默认模板不下载字体依赖；
名称超出随包小字库时才调用锁定的 HarmonyOS Sans SC 与隔离依赖缓存，禁止 Noto Sans SC 回退。字体文件保持原字节，渲染字形缓存入包。禁止覆盖既有目录，失败不会留下半个 APP。
生成前检查身份、名称、内存/调度配置和实际 API；JSON 请求可声明业务 imports，自动推导权限与最低 API。
这些检查在字体或工具下载之前完成；业务代码保留模板已验证的首屏、松手、按键和释放路径，降低首轮失败概率。
`build` 自动查找工具，缺项才有界调用 bootstrap；支持原有显式路径/环境变量和共享缓存。
`--offline` 禁止自动准备阶段出网。开发机不修改全局 Python；安装器、串口、固件不参与。

普通构建已在同一流水线中检查 WABT 语义、固定内存、实际导入导出、权限、API、包完整性、
图标和中英文标题。不要再运行同义的四条手工命令。SDK 全套回归仍由 SDK 维护者/CI 运行；
发布服务器仍从最终包独立复验，不复用客户端的“通过”结论。

## 单次提交接口

已经获得本能力契约的 AI 或网页生成器可以一次提交源码和元数据：

```sh
python tools/workflow.py run --request request.json --app work/demo
```

请求结构如下，`files` 的完整业务源码由 AI 提供，工具不会调用另一个模型补写功能：

```json
{
  "id": "demo",
  "name": "Demo",
  "name_zh": "应用",
  "template": "native-ui",
  "capabilities": ["ui"],
  "imports": [],
  "files": {
    "main.c": "这里放完整业务源码",
    "tests/app_test.c": "这里放包含真实业务实现的测试源码"
  },
  "manifest": {"version": "1.0.0", "permissions": 3},
  "workflow": {
    "sources": ["main.c"],
    "assets": [],
    "tests": [{"kind": "c", "path": "tests/app_test.c"}],
    "preview": null
  }
}
```

此段是接口示意，两个中文占位字符串不是可构建的 C。文本文件按 UTF-8 写入，二进制文件
可以使用 `{"base64":"..."}`。所有路径限定于当前 APP；拒绝目录穿越、符号链接和公共 SDK 头文件替身。
`imports` 是业务用到的真实导入名，追加到模板的必需接口；不要求加入未使用的 random。
工具从固定 api.json 推导权限/API；显式 permissions 或 api_minor 不够时立即报错，不越过开发者限制。
若完整替换模板实现，按真实代码设置 manifest.required_imports；最终 WASM 仍须独立通过完整 ABI/产品检查。
既有 APP 用 `build`，不重复提交 `run` 覆盖用户源码。
请求也可用 `--request -` 从标准输入提交，不必额外写请求文件。`prepare --inline-context` 直接返回相关契约与模板源码，减少一次文件读取往返。
独立获取上下文可用 `context --template native-ui --capabilities ui,http -o context.md`。

## 自动资源、测试与预览

APP 根目录的 `workflow.json` 由 prepare 生成，AI 按需要一次填写：

```json
{
  "version": 1,
  "template": "native-ui",
  "capabilities": ["ui"],
  "sources": ["main.c"],
  "assets": [{"kind":"python", "path":"prepare.py", "inputs":["strings.json"], "outputs":["resources/text.bin"]}],
  "tests": [{"kind":"c", "path":"tests/app_test.c", "args":["{app}/resources"]}],
  "preview": null
}
```

资产脚本按内容缓存，必须同时声明输入与输出才能跳过生成；脚本、输入、SDK 工具或输出变化即失效。
脚本的全部依赖都应列在 inputs 中；未声明输入的脚本每次完整构建都运行，不能凭一个时间戳认定有效。
测试支持 Python 与原生 C，直接运行实际 APP 的相关测试，不强加所有模板的测试。
APP 需要的逻辑、极值、失败、清理测试仍由实现者提供；空列表明确记 `not_run`，不冒充通过。
hook 默认 60 秒，最大 120 秒，不使用 shell；`{app}`、`{work}`、`{package}` 可传入真实路径。
输出应写入 `{work}` 或 `XAPP_WORK_DIR`，测试期间改源码会拒绝交付。

预览 hook 不是运行时能力本身：只有实际执行最终 WASM 的宿主才能给出对应运行证据。
公开 SDK 当前不含私有 WAMR/设备服务模拟器，因此默认 preview/runtime/hardware 都是未测。
不能用重新实现的 HTML/C/Python 模型伪称最终包流畅；审美、音画网络和 C3 峰值仍需对应验证。

## 缓存、失败与输出

同 APP 的源码、资源、清单、测试、工作流与 SDK 代码内容一致时，复用上次已验证的包和 APP 测试证据。
命中前复核包、源码 ZIP、报告的 SHA 以及最终包格式；损坏即重建，缺少工具并不伪造首次校验。
`--fresh` 强制重跑，仍不改变独立验包标准。缓存只加速本机工作，不是发行者签名或服务器信任依据。

默认输出到 SDK `dist/<id>.xapp`、`.source.zip`、`.validation.json`；可通过 `-o` 选当前 APP 源目录外的目标。
最终包先在候选目录构建，所有配置的 APP 测试完成后才替换交付包；失败返回非零和紧凑 JSON，
原包不算本次成功。完整日志、上下文、阶段耗时、失败报告保存在 APP 的 `.xapp-workflow/` 中，不进源码 ZIP。
交付更名中途遇到本地 I/O 错误会回滚原文件；这不是跨进程/断电事务，工厂或服务器仍应使用其正式发布机制。
`status=candidate` 始终表示候选；没有实机验收时 `hardware_tested=false`。
只读共享的启动器字体/图标可在平台挂载；其新生成缓存写 APP 的 `.xapp-workflow/launcher-cache/`，不写共享目录。外部源内容参与构建缓存指纹，变动会重建。报告 `source_external_dependencies` 列出不在源码 ZIP 中的外部资产；平台导出须附同版来源/哈希、许可证和可执行的依赖恢复步骤，不能把服务器绝对路径当成可移植源码。
工具自身的 `model_calls_by_tool=0`，不表示外部 AI 从未产生模型调用，也不保证总调用次数固定。
以首轮候选包可构建为目标：固定模板、提前预检、锁定缓存和一次验收消除确定性返工；
任意复杂业务、最终 WASM 执行、联网音画与实机性能仍需相应证据，不能承诺所有 APP 一次实机通过。

## 服务器接入边界

服务器可把一次源码 JSON 请求适配为同一个 run/build 进程，长驻复用固定 SDK/工具/字体缓存，
把完整规则留在磁盘、只按能力注入 context。这里交付的是本地 CLI，不是已部署的在线生成接口。
服务端接收任意 APP 源码/资源脚本时必须放到独立隔离执行环境，设 CPU/内存/磁盘/时间限额，
不得给生成任务站点凭据、发布权限或宿主文件访问；本地路径检查不是代码沙箱。
生成与上架分开，原有一句话提示词不变；本次不部署、不推送、不自动上架。
