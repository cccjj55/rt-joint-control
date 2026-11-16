# 上位机 ↔ 控制器 帧协议

固定 8 + N 字节，小端。选这种格式的原因：**接收端能重新同步**，而不是错一帧就整条流报废。

```
offset  size  field
0       2     header = 0xAA 0x55
2       2     seq    uint16（回绕）
4       1     cmd    uint8
5       1     len    uint8（payload 0..32）
6       len   payload
6+len   2     crc16  CRC-16/CCITT-FALSE，覆盖 seq..payload
```

## 为什么 CRC 覆盖 seq

只对 payload 做校验，无法发现"重复帧"和"乱序帧"。把 `seq` 纳入 CRC，
接收端可以用 `(seq, crc)` 双条件判定重复，避免同一目标位置被执行两次。

## 命令表

| cmd | 名称 | payload | 方向 |
| --- | --- | --- | --- |
| 0x01 | `SET_TARGET` | f32 目标位置 [rad] | 上位机 → 控制器 |
| 0x02 | `SET_GAINS` | f32 kp, f32 ki, f32 kd | 上位机 → 控制器 |
| 0x03 | `SET_MODE` | u8（0 idle / 1 position / 2 velocity） | 上位机 → 控制器 |
| 0x10 | `TELEMETRY` | f32 pos, f32 vel, f32 iq | 控制器 → 上位机 |
| 0x7F | `NOP` | — | 双向，用于保活与链路自检 |

## 带宽预算

1 kHz × (8 + 12) B = 20 kB/s，115200 8N1（≈11.5 kB/s）不够 → 用 921600 或换 CAN。
**这条预算要写进 README**，因为它决定了"为什么不用 JSON"。

## 错误处理

| 情况 | 处理 |
| --- | --- |
| 头部不匹配 | 逐字节前移重同步（`iter_frames`） |
| 长度 > 32 | 丢弃并计一次 `bad_len` |
| CRC 失败 | 丢弃并计一次 `crc_err`，连续 100 次则上报链路故障 |
| 帧截断 | 保留缓冲，等下一批字节 |
