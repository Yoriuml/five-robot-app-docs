# 原生 UI＋双轨 PCM 音画模板

完整原生场景、包内 A4 标题、三项菜单和原创简短旋律，无网络和私有驱动。
完整首屏后续 tick 才请求背景音乐；中键确认 Music 开关背景轨、Effect 播放效果轨。
效果轨有 duck 和优先级，不重启背景轨。Exit 或左键退出；退出统一停止本地声音并释放场景。
上/下选择，启动键先松手。同一操作只由 input_state 解释，不再消费重复事件。
PCM 为 16000Hz、单声道、PCM16LE；music.pcm 1.2 秒，effect.pcm 0.15 秒，低增益避免模板叠加削波。
8192 字节纹理预算，8 行 DMA；运行时额外音频/系统堆仍需目标设备确认。
api_major=2/api_minor=15，权限 INPUT|DISPLAY_FOREGROUND|AUDIO_PLAYBACK。
系统按键音由固件仲裁，模板不关闭系统声音、不改变系统音量、不直接操作 I2S。

启动器图标和 PCM 演示资源按 CC0-1.0 提供；字体按 launcher/OFL.txt。
默认资源可直接构建；再生器 tools/make_template_assets.py 需要 Pillow/fontTools 和固定哈希的合法上游字体。
测试桩不产生真实音频，报告 runtime_tested/hardware_tested 保持 false。
