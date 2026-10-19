# SDK 2026.10.19.1 验证记录

2026-10-19，在 Windows x64 运行 Python 3.11.15、Zig 0.15.2、WABT 1.0.41。

- 官方归档 SHA256 校验、Python 解压、可执行文件完整性、版本检测及自动工具定位通过。
- 四个模板真实编译为 .xapp，分别通过 WABT 指令语义、固定内存/ABI、权限/API、CRC32/SHA256 与独立复核。
- 11 项 Python 测试覆盖损坏包、清单边界、资源越界、归档越界/符号链接、模板防覆盖、真实 API 索引、错误签名/内存/权限，以及不要求未使用 random。
- 四套原生 C 桩覆盖启动键松手、空闲不重绘、重复切换、图元数量、退出、绘制失败、HTTP 忙/失败/超时。
- 最终 WASM 保留事件回调及 exit 导入；联网模板静态内存 7440B，其余模板约 4.2KiB（均包含 4096B C 栈）。宿主 UI/Wi-Fi/TLS 开销不在该数值内。

复现命令：`python tools/test_sdk.py`。结果与包输出在 dist/template-check/，不作为源码进入镜像。
新增 Windows/Linux CI 配置；本记录不声称尚未运行的其他平台已经通过。

未进行真实 WAMR 宿主运行、设备安装、联网、声音或帧率验收；runtime_tested/hardware_tested 保持 false。
