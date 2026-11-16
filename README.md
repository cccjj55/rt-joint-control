# rt-joint-control

**1 kHz 关节伺服回路的实时性与时延分解。**
*1 kHz joint servo loop — jitter and end-to-end latency decomposition.*

这个仓库解决一个具体问题：**你说「跑 1 kHz」，凭什么？**
答案不是"我用了定时器"，而是三张表：周期抖动（P99）、端到端时延的四段分解、以及三种调度配置的对比。

---

## 目录 / Layout

```
rt-joint-control/
├── docs/protocol.md          # 帧格式（含 CRC16）与命令表
├── tools/frame.py            # 帧编解码（可离线单测，无需硬件）
├── tools/jitter_report.py    # CSV → P50/P90/P99 抖动表（Markdown）
├── tools/make_sample_csv.py  # 生成示例数据（用于验证工具链）
├── tests/test_frame.py       # 编解码往返 / CRC 失败 / 流式切帧
└── firmware/                 # STM32 固件（待补：1 kHz TIM 中断 + 编码器 + PWM）
```

## 快速开始

```bash
python tools/make_sample_csv.py            # 生成 sample_jitter.csv
python tools/jitter_report.py sample_jitter.csv
python -m pytest tests -q                  # 帧编解码单测
```

## 实验设计（要填的表）

| 配置 | 内核 | 调度 | 期望 jitter P99 | 实测 |
| --- | --- | --- | --- | --- |
| ① | Ubuntu 普通内核 | CFS（默认） | 数百 μs ~ ms | _待填_ |
| ② | Ubuntu 普通内核 | `SCHED_FIFO` + `mlockall` | 几十 μs | _待填_ |
| ③ | PREEMPT_RT 内核 | `SCHED_FIFO` + CPU 隔离 | 个位数 μs | _待填_ |

端到端时延分解（面试必问）：

```
编码器采样 → 总线传输 → 控制计算 → PWM 更新 → 机械响应
  __ μs        __ μs       __ μs       __ μs       __ ms
```

## 状态

- [x] 帧协议 + 编解码（含 CRC16）+ 单测
- [x] jitter 报告工具（CSV → Markdown 表）
- [ ] STM32 固件（1 kHz 位置-速度双环）
- [ ] 逻辑分析仪测点（GPIO 翻转）+ 实测三配置对比
- [ ] 端到端时延分解（四段）

> 数据口径：所有数字由 `tools/jitter_report.py` 从原始 CSV 复算，README 不手填。
> **仓库内的 `sample_jitter.csv` 是 `tools/make_sample_csv.py` 生成的合成数据**，只用于验证工具链；
> 真实三配置对比要等固件上板后用逻辑分析仪采。上面那张表的实测列在拿到真实数据前保持"待填"。

## License

MIT
