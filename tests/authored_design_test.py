#!/usr/bin/env python3
"""Validate the playable geometry of the owner's published editor boards."""
from collections import deque
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
count = 0
for path in sorted((ROOT / 'assets/authored-levels').glob('*.dat')):
    assert re.fullmatch(r'level(\d+)(-portrait)?\.dat', path.name), path
    raw = path.read_bytes()
    assert len(raw) in (1201, 2401) and 1 <= raw[0] <= 12, path
    columns, rows = (30, 40) if '-portrait' in path.name else (40, 30)
    floor = {(x, y) for x in range(1, columns - 1) for y in range(1, rows - 1)
             if raw[1 + x * rows + y] < 20 or 40 <= raw[1 + x * rows + y] <= 45}
    start = (columns // 2, rows - 2)
    assert start in floor and (columns // 2, rows - 3) in floor, (path, 'blocked approach')
    seen = {start}
    todo = deque([start])
    while todo:
        x, y = todo.popleft()
        for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if point in floor and point not in seen:
                seen.add(point)
                todo.append(point)
    assert (columns // 2, 1) in seen, (path, 'unreachable exit')
    assert seen == floor, (path, 'unreachable floor')
    count += 1
assert count
print(f'Published geometry local test: all floor cells and exits reachable in {count} editor layouts.')
