# Hello Five

最小 XApp：两个选项，按键选择，确认执行；画面静止时不绘制。

- 上键选择 Hello，下键选择 Exit APP。
- 在 Hello 上短按确认改变文字颜色；选择 Exit APP 后短按确认退出。
- 启动后等待按键松开，防止进入应用的按键被重复消费。
- 如绘制失败，短按确认仍可退出。
- 不使用中键、不联网、不写存储，权限为 INPUT | DISPLAY_FOREGROUND（3）。

构建见 [快速开始](../../docs/quickstart.md)。新示例尚未做实机验收；主机检查范围见生成的 validation.json。
