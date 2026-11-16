"""Generate a synthetic jitter CSV so the tooling can be tested without hardware.

The three groups mimic what the real experiment should look like; the numbers
are placeholders until the STM32 loop is measured. Delete this file's output
before publishing real results.
"""

from __future__ import annotations

import argparse
import csv
import random

# (config, base_period_us, jitter_sigma_us, calc_mean_us)
CONFIGS = [
    ('cfs', 1000.0, 180.0, 45.0),
    ('fifo', 1000.0, 25.0, 40.0),
    ('rt', 1000.0, 3.0, 38.0),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='sample_jitter.csv')
    ap.add_argument('--n', type=int, default=5000, help='iterations per config')
    ap.add_argument('--seed', type=int, default=7)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    with open(args.out, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh)
        writer.writerow(['config', 'period_us', 'calc_us'])
        for name, base, sigma, calc in CONFIGS:
            for _ in range(args.n):
                period = rng.gauss(base, sigma)
                writer.writerow([name, f'{period:.1f}', f'{rng.gauss(calc, 5):.1f}'])
    print(f'wrote {args.out} ({len(CONFIGS)} configs x {args.n} rows)')


if __name__ == '__main__':
    main()
