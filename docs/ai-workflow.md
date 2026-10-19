# 给 AI 的完整工作流

入口：[固定版本索引](https://site.flashbot5.com/developer/v1/index.json)。也可从 [GitHub](https://github.com/Yoriuml/five-robot-app-docs) 或 [Gitee](https://gitee.com/yorium/five-robot-app-docs) 获取同一标签的仓库。
`sdk-release.json` 的 SDK 发行号与 API 版本不同；不要因为 API 同为 2.15 就混用不同发行包内的工具。

## 可直接复制的提示词

```text
请为五号机器人开发一个 XApp，需求如下：【功能、界面风格、按键和声音/联网需求】。

开发资料入口 https://site.flashbot5.com/developer/v1/index.json
备用仓库 https://github.com/Yoriuml/five-robot-app-docs 和 https://gitee.com/yorium/five-robot-app-docs

1. 取索引，固定一个 SDK 发行版，下载完整 sdk.zip 并核验 checksums.json 中的 SHA256。
   若只能访问仓库，取相同发行标签。不要依靠搜索片段或记忆重建 SDK。
   Git/curl 失败一次就换 ZIP、另一镜像或 PowerShell Invoke-WebRequest；保存文件再读取，不盲目重复重试。
   .h 原文为空时用该发行版 file?path= 接口取 JSON 内容；或 GitHub contents API 的 base64。
   如果仍读不到所需声明，明确缺少哪个文件并停止对应功能，不自造结构、函数或最小替代头文件。
2. 阅读 README.md、AGENTS.md、docs/quickstart.md、docs/development-rules.md 和所用真实头文件。
   api.json 用于查符号、版本、权限；结构大小、所有权、单位和配额仍以头文件为准。
   列出页面、按键、可到达的退出方式、API/权限及最坏内存预算，然后开始实现。
3. 运行 tools/doctor.py；缺工具用 tools/bootstrap.py 下载固定版本并验哈希。
   下载失败改用 toolchain.lock.json 的官方地址，或让用户提供离线归档；解压后确认可执行文件存在。
   工具不能执行时准确报告阻塞，不能交付虚构的安装包或伪造通过报告。
4. 用 tools/create_app.py 从最接近的模板创建应用；修改源码和资源，只调用公开 API。
   静止不重绘；中文预制字形；动画优先 2.15 原生缓存节点，不每帧解析字体/读取资源/全屏逐像素计算。
   不改设备固件、API、分区，不自动烧录，不在源码内放账号密钥。
5. tools/build.py 构建，tools/validate.py 独立复核最终 .xapp。
   给 app.json 填实际需要的 required_exports 和 required_imports；确认 xapp_event 没被链接删除，退出路径保留 exit 导入。
   不要求无用的 random；导入表存在也不等于按键和退出流程真的可用。
   测试启动键松手、长/短按、连续操作、每个页面退出、最大文本/图元/资源配额、失败返回。
   超限应显式报错，不能静默吞命令。资源失败后仍应能退出。
6. 交付源码、app.json、实际 .xapp、validation.json、SHA256、按键和设备安装步骤。
   分开写明静态校验、主机桩测试、实际运行时、真机验收结果；未经实机测试的帧率不可宣称达标。
```

## 交付与修复循环

工具失败先保留首个具体错误、工具版本、命令、SDK 发行号、包哈希；只修对应问题后重建。
构建脚本先验证再替换旧产物，失败不能把旧包当本次成功。用户提供设备日志时区分启动失败、内存、网络/TLS、绘制和输入阻塞。
不要为了绕过证书失败关闭 TLS，也不要扩大权限来碰运气。

接口不支持的功能应提出通用 API 需求，交给主任务决定；不要偷偷链接私有固件符号。
只有聊天能力的 AI 可以交付设计/源码，但生成真实安装包需要运行编译工具。

## 服务端契约

见 [发行和镜像规范](releases.md)。客户端报告仅作参考，服务器从包字节独立验收；静态通过不等于真机通过。
在线构建是另一个服务，应隔离、限时限额、禁止默认外网与私密凭据，产物留在候选区；本 SDK 不要求上线在线任意代码执行。
