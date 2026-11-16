"""Turn a jitter CSV into a Markdown table.

Input CSV columns (header required):
    config,period_us,calc_us

``config`` is a free-form label (e.g. ``cfs``, ``fifo``, ``rt``), one row per
control-loop iteration. Jitter is defined against the *target* period given on
the command line, not against the measured mean -- otherwise a systematically
late loop would report zero jitter.

Usage:
    python tools/jitter_report.py sample_jitter.csv --target-us 1000
"""

from __future__ import annotations

import argparse
import csv
import statistics
from collections import OrderedDict
from typing import Dict, List


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * (p / 100.0)
    lo = int(rank)
    hi = min(lo + 1, len(ordered) - 1)
    return float(ordered[lo] * (1 - (rank - lo)) + ordered[hi] * (rank - lo))


def load(path: str) -> "OrderedDict[str, Dict[str, List[float]]]":
    groups: "OrderedDict[str, Dict[str, List[float]]]" = OrderedDict()
    with open(path, newline='', encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            config = row.get('config') or 'default'
            bucket = groups.setdefault(config, {'period': [], 'calc': []})
            bucket['period'].append(float(row['period_us']))
            if row.get('calc_us'):
                bucket['calc'].append(float(row['calc_us']))
    return groups


def report(path: str, target_us: float) -> str:
    groups = load(path)
    lines = [
        '| 配置 | n | jitter P50 | jitter P90 | jitter P99 | jitter max | calc P99 |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    for config, data in groups.items():
        jitter = [abs(p - target_us) for p in data['period']]
        calc = data['calc'] or [0.0]
        lines.append(
            f'| {config} | {len(jitter)} | {percentile(jitter, 50):.1f} µs | '
            f'{percentile(jitter, 90):.1f} µs | {percentile(jitter, 99):.1f} µs | '
            f'{max(jitter):.1f} µs | {percentile(calc, 99):.1f} µs |'
        )
    spread = ', '.join(
        f'{c}: σ={statistics.pstdev(d["period"]):.1f} µs' for c, d in groups.items()
    )
    return '\n'.join(lines) + f'\n\n周期标准差 — {spread}\n'


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('csv_path')
    ap.add_argument('--target-us', type=float, default=1000.0)
    args = ap.parse_args()
    print(report(args.csv_path, args.target_us))


if __name__ == '__main__':
    main()
