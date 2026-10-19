# XApp API 查阅手册（2.1—2.15）

原生动画接口更新：2026-10-10。当前SDK版本2.15；新APP提供退出入口并声明至少minor=11。
本手册解释参数和行为，不取代 [C 声明](../sdk/xapp/x622_xapp.h)。
完整结构定义还包括 [BLE](../sdk/xapp/x622_ble.h) 与 [HTTP](../sdk/xapp/x622_http.h)。

## 1. 版本、返回值与所有权

| 最低版本 | 能力 |
|---|---|
| 2.1 | Core、动作事件、图形、资源/存储、Wi-Fi、同步 HTTP、网络 MP3 |
| 2.2 | 新增 `x622_input_state()` |
| 2.3 | 本地音频、BLE外设、私有Wi-Fi/停止、异步HTTP、串口、堆快照 |
| 2.4 | 包内双音轨PCM混音、循环背景与优先级音效 |
| 2.5 | APP小画布无分配光栅、纹理条带、整数倍最近邻显示 |
| 2.6 | 有界ESP-NOW收发、RSSI/时间戳、独占无线租约 |
| 2.7 | 按需半双工PCM采集/播放、四帧队列、无分配有配额NCF |
| 2.8 | 包内MOD/XMR1异步合成、播放/暂停/音量、谱面及耗时快照 |
| 2.9 | 扩展异步HTTP、记录型GATT、SHA-256/AES-GCM/安全随机数、临时AP+STA网关 |
| 2.10 | 有界16kHz语音活动检测，按需实例、工作配额与退出释放 |
| 2.11 | 应用内主动退出x622_exit()，K2交给应用 |
| 2.12 | 可选双输入报告BLE HID：两个独立Report characteristic及订阅门禁 |
| 2.13 | appfs 私有文件顺序读写/原子覆盖；PCM 播放共享音量读写 |
| 2.14 | [BLE HID 触摸屏 Feature Report](api-extensions.md)，主触点订阅即可就绪 |
| 2.15 | [原生缓存场景、动画、局部合成与帧耗时统计](api-extensions.md)，旧图形 ABI 不变 |

固件拒绝 V1/2.0 和高于当前支持范围的版本。导入名为 `x622` 模块内不带 `x622_`
前缀的名字；SDK 的 C 函数带此前缀。不要手写不匹配的导入签名。

- 长度/容量单位默认是**字节**，不是字符数或元素数。输入字符串显式长度通常不含 NUL；
  固定结构中的字符串必须 NUL 结尾。UTF-8 名称按编码后字节计算。
- `int32_t` 返回负数是 X622 错误；成功可能是 0、字节数、记录数或状态位，逐项区分。
- 输入/输出指针位于 APP 固定线性内存；宿主不向 APP 暴露真实地址、驱动对象或密钥。
- “已排队”“已申请服务”“Wi-Fi已启动”均不代表数据已经发送、播放或取得 IP。
- 单前台 APP 与安装器互斥；退出/trap 宿主统一回收，不能依赖 shutdown 必定执行。

## 2. 权限

| 名称（SDK中前缀为 `X622_PERMISSION_`） | 值 | 用途 |
|---|---:|---|
| INPUT | 1 | 动作事件/按键状态 |
| DISPLAY_FOREGROUND | 2 | 前台图形 |
| STORAGE_PRIVATE | 4 | APP 私有 NVS Blob 与 2.13 appfs 文件 |
| BATTERY_READ | 8 | 电池快照 |
| BACKLIGHT | 16 | 背光，另需 DISPLAY_FOREGROUND，因此组合为18 |
| WIFI_CONNECT | 32 | Wi-Fi 与已保存网络 |
| NETWORK_HTTP | 64 | HTTP，另需 WIFI_CONNECT，因此组合为96 |
| BLE_ADVERTISE | 256 | 2.3 BLE 外设/HID，不含 Central 扫描 |
| AUDIO_PLAYBACK | 512 | 网络/本地音频；`media_play` 另需 Wi-Fi+HTTP，总计608 |
| AUDIO_CAPTURE | 1024 | 2.7麦克风PCM采集；声明不等于自动启动采音 |
| POWER_CONTROL | 2048 | 请求系统正常关机 |
| SERIAL | 4096 | 2.3 应用业务串口；物理通道以目标固件与头文件为准 |
| ESPNOW | 8192 | 2.6明文ESP-NOW数据报，与普通Wi-Fi/BLE/安装器互斥 |

未定义的位不可使用。权限通过不保证资源申请成功。只要声明 Wi-Fi且不声明BLE/ESP-NOW，
当前运行时会在实例化后、`xapp_init`前启动共享Wi-Fi；有已保存凭据时会尝试连接。
多种无线权限同时声明时不预启Wi-Fi，APP自行选择；运行时不允许同时占有。
ESP-NOW五个导入、8/272/48 B结构、250 B包/16包队列/48KiB线性内存上限，
见[API2.6](api-extensions.md)。它不需要WIFI_CONNECT，不提供互联网或认证/加密。
原始音频的六个导入及`signal_ncf`见[API2.7](api-extensions.md)。输入/输出不能同时使用；
该PCM通道与所有其他音频播放器互斥，stop后再交接。NCF每入口工作量有独立配额。
模块音乐四个导入及96/216 B结构见[API2.8](api-extensions.md)，需AUDIO_PLAYBACK。
暂停/失败仍保留模块服务所有权；先tracker_stop，再启动其他播放器。
扩展控制面十一项导入及限额见[API2.9](api-extensions.md)：HTTP需要权限96、GATT需要256、网关需要32。
密码操作有每入口配额；私有Wi-Fi网关仍不与BLE/ESP-NOW并发，不是无限制路由器。
VAD两个导入见[API2.10](api-extensions.md)，需AUDIO_CAPTURE；它不启动采音，每入口最多1,280采样工作量。

## 3. 生命周期、时间与输入

```c
void xapp_init(void);                                      /* 必须 */
void xapp_tick(uint64_t now_ms);                            /* 必须 */
void xapp_event(uint32_t type, uint32_t action, uint32_t phase,
                uint32_t held_ms, uint32_t pressed_mask);   /* 可选 */
void xapp_shutdown(void);                                  /* 可选 */
X622_EXPORT("xapp_startup_ready") int32_t xapp_startup_ready(void); /* 可选，() -> i32 */
```

入口在同一个 APP 任务执行，不能阻塞等待另一个入口。`tick_ms`为目标调度周期，
不是固定帧率；每次入口有8,000,000条解释器指令预算，但原生调用耗时不在该预算内。

`xapp_startup_ready` 是可选APP导出，不新增原生导入或升级包ABI。分步首屏返回0，完整首屏
（也可是一张完整加载页）返回1；系统在成功tick后查询，集中送出无损合成后的最终条带。
首屏期间不清LCD、不切断背光、不显示空白占位。无此导出的旧包默认首tick后提交；
分多tick绘制的旧包应安装含该导出的新版。查询签名错误、非0/1返回、10秒未完成或缓存失败
会停止APP并归还系统画面；详细内存和刷新规则见[制作规则](development-rules.md)。

| 函数 | 返回/说明 |
|---|---|
| `x622_millis()` | `uint64_t` 单调毫秒，不是日期或 Unix 时间 |
| `x622_random()` | `uint32_t` 随机值 |
| `x622_log(text,bytes)` | 最多512 B；成功0。限频，不能记录密码/token |
| `x622_memory_available()` | 2.3；瞬时8-bit堆字节数，不是最大连续块/DMA余量 |
| `x622_input_state()` | 2.2；bit0上、bit1下、bit2确认，1为按住，失败负数 |

动作事件 `type=1`，`action=1/2/3/4` 分别为上/下/确认/返回，当前发出 trigger 阶段。
K4上、K3下；导航按下时先发事件，按住≥600ms松开还会带时长再发一次；按需求处理，
不要误当一次短按被重复。K1确认在松开时发出；K2也在松开时带时长发给APP，由APP定义功能。
input_state新增bit3表示K2；x622_exit()无需权限，正常回调返回后清理资源，见[退出契约](api-extensions.md)。
确认键（K1）按满2秒在待机页关机，在其他系统页动画返回待机；活动APP收到带时长的确认事件，通常调用`x622_exit()`返回应用列表。若确认键长按是应用核心操作（例如录音），可提供明确的其他物理键长按退出入口。连续按满6秒触发系统全局应急强制关机，APP不能拦截，不因页面切换重新计时。`pressed_mask`为物理K1..K4的bit0..3，
**不同于** `input_state` 的逻辑位图。使用轮询时不再对同一次操作重复消费动作事件。

## 4. 设备、私有存储与包资源

| 函数 | 返回/限制 |
|---|---|
| `x622_battery(out,bytes)` | 至少12 B；成功12，三个i32为百分比、mV、有效标志（bit0百分比，bit1电压） |
| `x622_backlight(percent)` | 0—100；0 关闭两路背光，非 0 使用系统设置的两路背光组合；不是 PWM 连续调光 |
| `x622_power_off()` | 接受返回0；请求系统关机，不直接写IO或复位 |
| `x622_storage_size(key,len)` | 返回Blob字节数，不存在为负错误 |
| `x622_storage_read(key,len,out,capacity)` | 成功返回完整Blob长度；不足时返回错误，不做部分读取 |
| `x622_storage_write(key,len,data,bytes)` | 单项最多8192 B；成功0，同步持久化，需防抖限写 |
| `x622_storage_erase(key,len)` | 成功0；只影响本APP命名空间 |
| `x622_file_open/read/write/close` | 2.13；appfs 私有顺序文件、2 MiB/文件、4 KiB/调用，写入临时文件后原子替换；详见[2.13](api-extensions.md) |
| `x622_resource_size(path,len)` | 返回当前包内资源长度，不需要存储权限 |
| `x622_resource_read(path,len,offset,out,capacity)` | 返回实际读取长度；EOF为0，越界/缺失为负错误 |

NVS key为1—15字节ASCII；APP总存储配额尚未完善，不能以单项8KiB推断可无限写入。
卸载包目前不自动删除私有NVS。资源路径1—255 UTF-8字节，禁止越界或任意文件访问。

## 5. 图形

完整前台表面为240×240，系统Shell暂停刷新。调用为同步传输，完成后才能复用提交缓冲。

- `x622_gfx_submit(commands,command_bytes,x,y,w,h)`：1—96条，成功0。
  每次重建指定脏区，底色从黑色开始；应包含背景和所有覆盖该区域的元素。
- `x622_gfx_resource(path,path_bytes,commands,command_bytes,x,y,w,h)`：2.4，
  相同指令覆盖在包内240×240 RGB565LE背景上，资源必须恰好115,200 B；无需全屏RAM。
  仅显示背景可传一条零指令；CLEAR会覆盖背景。细节见[2.4](api-extensions.md)。
- `x622_gfx_blit(x,y,w,h,rgb565,bytes)`：必须 `bytes=w*h*2`，像素指针2字节对齐，成功0。
  使用小条带，不申请全屏数组。
- 三个入口的脏矩形/目标矩形都必须正尺寸且完全在屏幕内；图元在脏区内裁剪，
  不等于允许调用者传越界矩形。传输/提交错误可能触发APP停止和回收。

2.5另提供 `x622_gfx_raster` / `x622_gfx_sample` / `x622_gfx_blit_scaled`。
前两者只写APP画布、不操作LCD；最后一个复用既有显示条带。结构、工作量、
别名和指针限制见[API2.5](api-extensions.md)，不要将它们与44 B的场景命令混用。

`x622_gfx_command_t`固定44 B；颜色是主机序RGB565，不是RGB888。
未使用字段清零，TEXT保持NUL结尾。没有持久宿主场景树。

| opcode | 字段意义 |
|---|---|
| CLEAR=1 | `color`清脏区 |
| FILL_RECT=2 | `x,y,w,h,color` |
| STROKE_RECT=3 | `x,y,w,h,color`，`arg0`线宽 |
| LINE=4 | 起点`x,y`，终点`w,h`（这里不是宽高） |
| TEXT=5 | `x,y,text[24],color`，`arg0`为1—4倍；flags=1居中/2右对齐 |
| FILL_CIRCLE=6 | 圆心`x,y`，`w`为半径，`color` |

TEXT最多23个ASCII字符。中文走包内字形+局部blit，见[字体规则](development-rules.md)。
宿主DMA条带上限3840 B；APP不能把这一数字当作额外可用WASM RAM。

## 6. Wi-Fi

| 函数 | 返回/行为 |
|---|---|
| `x622_wifi_start()` | 申请共享服务，成功0；不是联网完成 |
| `x622_wifi_status(out,bytes)` | 至少8 B，成功8；`{state,rssi_dbm}` |
| `x622_wifi_scan(networks,bytes)` | 同步全信道扫描，成功返回记录数，最多16条，可能耗时数秒 |
| `x622_wifi_connect(ssid,n,password,m)` | 提交连接/保存共享凭据；结果用status轮询 |
| `x622_wifi_saved_count()` | 返回保存网络数量 |
| `x622_wifi_saved_get(index,out,capacity)` | 成功0；复制NUL结尾SSID，不返回密码；建议33 B缓冲 |
| `x622_wifi_saved_set_default(index)` | 选择默认网络，成功0 |
| `x622_wifi_saved_remove(index)` | 删除保存项，成功0；删除后重新枚举索引 |
| `x622_wifi_stop()` | 2.3；归还本APP租约；媒体未停止时返回BUSY |
| `x622_wifi_private_connect(ssid,n,password,m)` | 2.3；需先释放现有Wi-Fi/BLE，不写入共享凭据 |

state：0关闭、1启动中、2需APP选网/输密码、3连接中、4已连接、5错误。
**状态2不是系统已开启配网热点**。未连接时RSSI可能为-127，不可当作有效测量。
`x622_wifi_network_t`为37 B：SSID[33]、有符号RSSI、secure、保留字段；没有BSSID/信道，
不扫描隐藏SSID，无法可靠区分同名AP。全列表扫描不是瞬时实时信号采样。

## 7. HTTP

| 函数 | 返回/行为 |
|---|---|
| `x622_http_get(url,len,out,capacity)` | 2.1同步GET，URL少于512 B；成功返回不含NUL的正文长度；溢出返回QUOTA_EXCEEDED |
| `x622_http_request(request,bytes)` | 2.3；固定968 B请求，接受返回0，一次一个在途请求 |
| `x622_http_poll(out,capacity)` | 2.3；状态头12 B，完成时追加≤2048 B正文和NUL；建议缓冲2061 B |

同步GET可能因按键待处理而返回BUSY；仅用于小型JSON等控制面，不用于流音频。
异步请求要求已联网，不会替APP选择网络。GET/POST、Bearer、响应头、HTTPS和私网
限制见[2.3详细说明](api-extensions.md)。检查transport_error与HTTP状态之后再解析正文。

## 8. 网络媒体与本地音频

| 函数 | 返回/行为 |
|---|---|
| `x622_media_play(url,bytes)` | 网络HTTP/HTTPS MP3，接受成功0；再次请求切换流 |
| `x622_media_stop()` | 请求异步停止，成功返回不代表已经释放 |
| `x622_media_volume(percent)` | 0—100，合并目标值后在音频线程应用 |
| `x622_media_status(out,bytes)` | 至少12 B；成功12，`{state, sample_rate_hz, reconnect_count}` |
| `x622_media_levels(out,bytes)` | 返回复制数量，最多18路归一化电平，不等于精确FFT频谱 |
| `x622_audio_resource(path,len,offset,bytes,format,rate)` | 2.3包内音频，范围校验后排队，新片段替换旧片段 |
| `x622_audio_stop()` | 2.3异步请求停止 |
| `x622_audio_volume(percent)` | 2.3，0—100 |
| `x622_audio_status(out,bytes)` | 2.3，成功16；`{state,native_error,samples,rate}` |
| `x622_audio_track(command,bytes)` | 2.4，100 B描述符，voice0/1、PCM16LE/16kHz、循环/优先级/duck |
| `x622_audio_mix_status(out,bytes)` | 2.4，成功24；状态/错误/active mask/已提交采样/双轨字节位置 |

media state：0停止、1等待网络、2连接、3缓冲、4播放、5重连、6错误。
audio state：0空闲、1排队、2播放、3失败。
本地只支持16kHz单声道PCM16LE或带u16le包长的Opus包流；不是任意WAV/MP3/Ogg。
网络、单片段、混音三种播放路径互斥；保留系统codec不代表每个格式都已经暴露API。
开销/格式详见[2.3说明](api-extensions.md)、[2.4混音与生命周期](api-extensions.md)。
`audio_status`只查询旧的单片段播放器；混音必须查询`audio_mix_status`。

## 9. BLE与串口（2.3）

| 函数 | 返回/行为 |
|---|---|
| `x622_ble_start(profile,bytes)` | 220 B描述，APP专属GATT或HID外设；不能同时持有Wi-Fi |
| `x622_ble_stop()` | 停止外设并归还租约 |
| `x622_ble_status(out,bytes)` | 36 B状态，含配对码/epoch，不含密钥 |
| `x622_ble_read(out,capacity)` | 非阻塞读取，返回字节数，无数据为0 |
| `x622_ble_send(data,bytes)` | 接受最多768 B，按MTU拆分；需处理BUSY/QUEUE_FULL |
| `x622_ble_sequence(frames,bytes)` | 原子提交1—16个24 B帧；每帧1—20 B，帧后延时≤1000ms |
| `x622_ble_forget()` | 仅停止后清除本APP绑定，不清除系统或其他APP数据 |
| `x622_serial_read(out,capacity)` | 非阻塞，单次1—768 B，返回读取数 |
| `x622_serial_write(data,bytes)` | 单次1—768 B，有界同步写，返回写入数，需处理短写 |

BLE参数、队列、认证和绑定隔离见[2.3说明](api-extensions.md)。当前不是BLE Central接口。
当前主头文件声明 APP 业务串口使用原生 USB Serial/JTAG CDC，不使用 K2/K3 引脚。
APP 没有修改引脚或波特率的 API；安装器传输协议是独立流程，不可把它的串口设置用于推断 APP 通道。

## 10. 错误码速查

| 值 | `X622_ERR_`后缀 |
|---:|---|
| -1 | INVALID_ARGUMENT |
| -2 | INVALID_STATE |
| -3 | NOT_SUPPORTED |
| -4 | NO_MEMORY |
| -5 | PERMISSION_DENIED |
| -6 | NOT_FOUND |
| -7 | BUSY |
| -8 | TIMEOUT |
| -9 | QUEUE_FULL |
| -10 | QUOTA_EXCEEDED |
| -11 | IO |
| -12 | VERSION_MISMATCH |
| -13 | CORRUPT |
| -14 | BUFFER_TOO_SMALL |

少数状态结构的`native_error`/`transport_error`保留底层诊断码；与API的负返回值、
串口安装协议中的`esp_err_t`是不同字段，不能混用。

当前没有向XApp开放任意GPIO/任务、BLE Central、日期时钟、
固件OTA或系统LVGL对象。需要新能力先做通用API设计和资源审查，不通过私有符号绕过。
