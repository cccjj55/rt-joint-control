"""Unit tests for the frame codec (no hardware, no serial port)."""

import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))

from frame import (  # noqa: E402
    Frame,
    FrameError,
    crc16_ccitt,
    decode,
    encode,
    iter_frames,
)


def test_crc_ccitt_false_check_value():
    # The canonical check value for CRC-16/CCITT-FALSE over "123456789".
    assert crc16_ccitt(b'123456789') == 0x29B1


def test_roundtrip_with_payload():
    payload = struct.pack('<fff', 12.0, 0.5, 0.02)
    frame = decode(encode(7, 0x02, payload))
    assert (frame.seq, frame.cmd, frame.payload) == (7, 0x02, payload)
    assert frame.name == 'SET_GAINS'


def test_roundtrip_empty_payload_is_eight_bytes():
    buf = encode(1, 0x7F)
    assert len(buf) == 8
    assert decode(buf).cmd == 0x7F


def test_crc_mismatch_is_detected():
    buf = bytearray(encode(3, 0x01, struct.pack('<f', 1.0)))
    buf[-1] ^= 0xFF
    with pytest.raises(FrameError, match='crc mismatch'):
        decode(bytes(buf))


def test_bad_header_and_bad_length_are_rejected():
    with pytest.raises(FrameError, match='bad header'):
        decode(b'\x00\x00' + b'\x00' * 8)
    buf = bytearray(encode(1, 0x01))
    buf[5] = 200  # len > MAX_PAYLOAD
    with pytest.raises(FrameError, match='bad length'):
        decode(bytes(buf))


def test_encode_validates_inputs():
    with pytest.raises(ValueError):
        encode(70000, 0x01)
    with pytest.raises(ValueError):
        encode(1, 0x01, b'\x00' * 40)


def test_stream_parser_skips_garbage_and_resyncs():
    good = encode(1, 0x10, struct.pack('<fff', 0.1, 0.2, 0.3))
    stream = b'\xaa\x55\xff' + good + b'junk' + encode(2, 0x7F)
    frames = list(iter_frames(stream))
    assert [f.seq for f in frames] == [1, 2]


def test_stream_parser_survives_truncated_tail():
    stream = encode(1, 0x7F) + encode(2, 0x7F)[:5]
    frames = list(iter_frames(stream))
    assert [f.seq for f in frames] == [1]


def test_frame_is_frozen():
    frame = Frame(1, 0x7F)
    with pytest.raises(Exception):
        frame.seq = 2  # type: ignore[misc]
