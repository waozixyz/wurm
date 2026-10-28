#!/usr/bin/env python3
"""Validate actual emitted Meadow records in both orientations independently."""
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for number in range(1, 41):
    for portrait in (False, True):
        columns, rows = (30, 40) if portrait else (40, 30)
        suffix = '-portrait' if portrait else ''
        name = f'level{number}{suffix}.dat'
        path = ROOT / 'assets/authored-levels' / name
        if not path.exists():
            path = ROOT / 'build/designed' / name
        raw = path.read_bytes()
        floor = {(x, y) for x in range(columns) for y in range(rows)
                 if raw[1 + x * rows + y] < 20 or 40 <= raw[1 + x * rows + y] <= 45}
        assert len(floor) >= 760, (number, portrait, 'generous floor area')
        assert raw[0] in (5, 6)
        enemies = [tile for tile in raw[1:1201] if 40 <= tile <= 45]
        assert len(enemies) <= 1 and all(41 <= tile <= 44 for tile in enemies)
        if number <= 20 or number in (10, 12, 16, 23, 31, 38):
            assert not enemies
        reached = {(columns // 2, rows - 2)}
        pending = deque(reached)
        while pending:
            x, y = pending.popleft()
            for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if point in floor and point not in reached:
                    reached.add(point)
                    pending.append(point)
        assert reached == floor, (number, portrait, 'every apple location is reachable')
        assert (columns // 2, 1) in floor
        for x, y in floor:
            assert any({(a, b), (a + 1, b), (a, b + 1), (a + 1, b + 1)} <= floor
                       for a in (x - 1, x) for b in (y - 1, y)), (number, portrait, 'wide route')
print('Meadow local test: 80 spacious, connected gardens, gentle goals and predictable hazards.')
