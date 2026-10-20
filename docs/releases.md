# SDK 发行和镜像规范

SDK 发行号：2026.10.20.3；API：2.15；XAPP 包格式：1。三个编号不能混用。旧 2026.10.19.2 保留，公共 API 声明不变。
GitHub 与 Gitee 发布相同 commit/tag；发行 ZIP 由同一份冻结字节生成，历史标签和资源不可原地覆盖。

## 下载契约

公开入口 `https://site.flashbot5.com/developer/v1/index.json` 指向完整、已验哈希的发行版。
建议路径：

```text
GET /developer/releases/<sdk_release>/sdk.zip
GET /developer/releases/<sdk_release>/templates.zip
GET /developer/releases/<sdk_release>/api.json
GET /developer/releases/<sdk_release>/checksums.json
GET /developer/releases/<sdk_release>/files/<public-relative-path>
GET /developer/releases/<sdk_release>/file?path=<public-relative-path>
```

原文端点返回正确文本类型；JSON 文件接口包含 path、encoding=utf-8、content、sha256，供读不到 .h 的工具备用。
只可读取 checksums.files 允许的冻结文件；拒绝绝对路径、越界、反斜杠路径变体、符号链接、未列入清单的文件。
错误返回明确 4xx/5xx，不能以 200 空文件/登录页替代。公开资料免登录、免验证码、链接不过期。

`checksums.json` 含 `algorithm: sha256`、`sdk_release`、`artifacts` 与 `files`。
两个表均以相对路径为 key，值为 `{sha256, bytes}`。artifacts 为 sdk.zip/templates.zip/api.json；files 为完整公开文件白名单。
`release-ready.json` 提供 source_commit、git_tag、API、仓库地址及 checksums_sha256。
发布者完整上传并逐项验哈希之后，才能更新最新版本索引。

## 本地冻结

先运行 `python tools/test_sdk.py`，提交全部公开修改，再执行：

```sh
python tools/release.py --output dist/releases/2026.10.20.3
```

工具仅打包已提交且通过公开目录白名单的文件，拒绝覆盖现有发行目录；同一源码树可重复得到相同 ZIP 字节。
templates.zip 仅含示例；编译仍需要完整 SDK 的头文件和工具，不能单独取模板就猜测 API。
版本索引、SDK ZIP、校验器和头文件必须同一发行号配套。

## 对外范围

包含公开接口声明、协议配套校验器、文档、原创模板和测试。
不包含私有固件/驱动/宿主模拟器、网站后台、部署凭据、数据库、OTA 密钥、现有产品 APP 全套源码。
本次新增示例笔画资源为原创，无第三方字体依赖。工具链链接指向上游官方发行，许可证随上游归档保留。
公开仓库不代表获得第三方资源的授权；替换字体、音频、图标时应单独核实许可。

服务端独立运行包/ABI/语义检查，不能信任客户端 validation.json。
通过静态检查的包可成为待审核候选，不因此自动上架或声称真机验收通过。
