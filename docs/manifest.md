# 应用清单 app.json

```json
{
  "id": "hello-five", "name": "Hello Five", "version": "1.0.0",
  "api_major": 2, "api_minor": 15, "permissions": 3,
  "linear_memory": 0, "stack": 4096, "event_queue": 8, "tick_ms": 100
}
```

| 字段 | 含义 |
| --- | --- |
| id | 1..23 个小写 ASCII 字母、数字、下划线、连字符；同 ID 表示更新 |
| name | 1..47 UTF-8 字节 |
| version | 1..15 UTF-8 字节；应用版本与 API 版本分开 |
| api_major / api_minor | SDK 为 2.15；声明不能低于实际使用的导入版本 |
| permissions | 最小权限位图；3 表示按键与前台显示 |
| linear_memory | 必须为 0；不是可自由申请的 WASM 页数 |
| stack | 解释器栈 4096..8192 字节 |
| event_queue / tick_ms | 队列 1..16；调度间隔 10..1000 ms |

Schema 位于 [manifest.schema.json](../tools/xapp/manifest.schema.json)。Schema 长度计数不代替 UTF-8 字节长度验证；最终使用打包器检查。

可选 `launcher` 包含英文/中文名称、方形 PNG 图标、字体路径。中文名必须有你有权使用的 TTF/TTC/OTF，生成器做原生大小的字形子集；不要把私有字体、下载缓存或无权分发的资源直接提交仓库。
SDK 常量 `X622_XAPP_API_MINOR=15` 表示头文件版本，不会自动修改 app.json；两者由开发者保持一致。
