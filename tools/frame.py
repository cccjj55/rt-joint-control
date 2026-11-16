"""Binary frame codec for the 1 kHz joint servo link.

Frame layout (little endian)
----------------------------
===  ====  ==================================================
off  size  field
===  ====  ==================================================
0    2     header, constant 0xAA 0x55
2    2     seq, uint16, wraps at 65536
4    1     cmd, uint8
5    1     len, uint8, payload length (0..32)
6    len   payload
6+len 2    crc16 (CRC-16/CCITT-FALSE) over seq..payload
===  ====  ==================================================

Design notes
------------
* A constant header + CRC lets the receiver resynchronise after line noise
  instead of dropping every following frame.
* CRC covers ``seq`` as well: a duplicated or reordered frame is detected
  rather than silently accepted.
* ``iter_frames`` is a byte-at-a-time state machine so the same parser works
  on a serial stream and on a recorded log.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Iterator, List

HEADER = b'\xaa\x55'
MAX_PAYLOAD = 32

# cmd -> meaning; keep in sync with docs/protocol.md
CMD = {
    0x01: 'SET_TARGET',   # payload: f32 position [rad]
    0x02: 'SET_GAINS',    # payload: f32 kp, f32 ki, f32 kd
    0x03: 'SET_MODE',     # payload: u8 mode (0=idle, 1=position, 2=velocity)
    0x10: 'TELEMETRY',    # payload: f32 pos, f32 vel, f32 iq
    0x7F: 'NOP',
}


class FrameError(ValueError):
    """Raised when a buffer cannot be parsed into a frame."""


def crc16_ccitt(data: bytes, init: int = 0xFFFF) -> int:
    """CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF, no reflection, no xorout."""
    crc = init
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


@dataclass(frozen=True)
class Frame:
    seq: int
    cmd: int
    payload: bytes = b''

    @property
    def name(self) -> str:
        return CMD.get(self.cmd, f'UNKNOWN_0x{self.cmd:02X}')


def encode(seq: int, cmd: int, payload: bytes = b'') -> bytes:
    if not 0 <= seq <= 0xFFFF:
        raise ValueError(f'seq out of range: {seq}')
    if not 0 <= cmd <= 0xFF:
        raise ValueError(f'cmd out of range: {cmd}')
    if len(payload) > MAX_PAYLOAD:
        raise ValueError(f'payload too long: {len(payload)} > {MAX_PAYLOAD}')
    body = struct.pack('<HBB', seq, cmd, len(payload)) + payload
    return HEADER + body + struct.pack('<H', crc16_ccitt(body))


def decode(buf: bytes) -> Frame:
    """Decode exactly one frame. Raises FrameError on any inconsistency."""
    if not buf.startswith(HEADER):
        raise FrameError(f'bad header: {buf[:2]!r}')
    if len(buf) < 8:
        raise FrameError(f'short frame: {len(buf)} bytes')
    seq, cmd, length = struct.unpack('<HBB', buf[2:6])
    if length > MAX_PAYLOAD:
        raise FrameError(f'bad length: {length}')
    end = 6 + length
    if len(buf) < end + 2:
        raise FrameError(f'short frame: need {end + 2}, got {len(buf)}')
    payload = buf[6:end]
    (crc_rx,) = struct.unpack('<H', buf[end:end + 2])
    crc_calc = crc16_ccitt(buf[2:end])
    if crc_rx != crc_calc:
        raise FrameError(f'crc mismatch: rx=0x{crc_rx:04X} calc=0x{crc_calc:04X}')
    return Frame(seq=seq, cmd=cmd, payload=payload)


def iter_frames(stream: bytes) -> Iterator[Frame]:
    """Resynchronising parser: skips garbage and truncated tails."""
    buf = stream
    idx = 0
    while True:
        start = buf.find(HEADER, idx)
        if start < 0 or len(buf) - start < 8:
            return
        try:
            frame = decode(buf[start:])
        except FrameError:
            idx = start + 1          # false header: advance one byte, retry
            continue
        yield frame
        idx = start + 8 + len(frame.payload)


def _demo() -> None:
    frames = [Frame(1, 0x01, struct.pack('<f', 0.5)),
              Frame(2, 0x02, struct.pack('<fff', 12.0, 0.5, 0.02)),
              Frame(3, 0x7F)]
    blob = b'\x00\xff' + b''.join(encode(f.seq, f.cmd, f.payload) for f in frames)
    for parsed in iter_frames(blob):
        print(f'seq={parsed.seq:5d} cmd=0x{parsed.cmd:02X} {parsed.name:<12} '
              f'payload={parsed.payload.hex()}')


if __name__ == '__main__':
    _demo()
