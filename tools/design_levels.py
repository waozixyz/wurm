#!/usr/bin/env python3
"""Design the playable Garden levels, inspired by the recovered originals.

Each of the 33 levels keeps its original's apple goal, monster count and
wall density, then rebuilds a fresh layout in the classic Worm idiom:
hedge runs with gaps, water ponds off the critical path, and decoration
objects (flowers, logs, rocks, mushrooms, butterflies, snails, birds).
Every layout is flood-fill verified from the entrance before it is kept,
and the two feed cells above the gates are always open.

Writes src/designed_levels.zi (the playable base) and build/designed/
level<N>.dat (apple count, tiles, objects; archive column order) for the
preview renderer. Deterministic; rerun to regenerate."""
import random
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLUMNS, ROWS, CELLS = 40, 30, 1200
GRASS, DIRT, SAND, WATER = 0, 1, 2, 22
MARKERS = range(40, 46)
FLOORS = (GRASS, DIRT, SAND)
LOG, FLOWERS, MUSHROOM, ROCK, BUTTERFLY, SNAIL, BIRD = 1, 2, 3, 4, 5, 6, 7


def original(number):
    raw = (ROOT / "assets/original" / f"level{number}.dat").read_bytes()
    grid = [[raw[1 + x * 30 + y] for y in range(30)] for x in range(40)]
    monsters = sum(1 for column in grid for value in column if 40 <= (value & 127) <= 45)
    walls = sum(1 for column in grid for value in column if 20 <= value < 128)
    return raw[0], monsters, walls / CELLS


def is_wall(value):
    return 20 <= value < 128


def solid(grid, x, y):
    if not (0 <= x < COLUMNS and 0 <= y < ROWS):
        return True
    value = grid[x][y]
    if 40 <= (value & 127) <= 45:
        return False
    return is_wall(value)


def auto_hedge(grid, x, y):
    north = not solid(grid, x, y - 1)
    east = not solid(grid, x + 1, y)
    south = not solid(grid, x, y + 1)
    west = not solid(grid, x - 1, y)
    open_sides = north + east + south + west
    if open_sides == 0:
        return 50
    if open_sides == 1:
        return 51 if north else 52 if east else 53 if south else 54
    if open_sides == 2:
        if north and east:
            return 55
        if north and west:
            return 56
        if south and east:
            return 57
        if south and west:
            return 58
    return 20


def reachable(grid):
    start = (20, ROWS - 2)
    seen = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) in seen or solid(grid, nx, ny):
                continue
            seen.add((nx, ny))
            queue.append((nx, ny))
    return seen


def design(number):
    apples, monsters, density = original(number)
    rng = random.Random(1000 + number)
    for _ in range(24):
        grid = [[GRASS for _ in range(ROWS)] for _ in range(COLUMNS)]
        for x in range(COLUMNS):
            grid[x][0] = 20
            grid[x][ROWS - 1] = 20
        for y in range(ROWS):
            grid[0][y] = 20
            grid[COLUMNS - 1][y] = 20
        # Hedge runs with gaps; denser originals earn more runs.
        for _ in range(3 + int(density * 12)):
            if rng.random() < 0.65:
                x = rng.randrange(3, COLUMNS - 3)
                y0, y1 = rng.randrange(2, 8), rng.randrange(ROWS - 8, ROWS - 2)
                for y in range(y0, y1):
                    grid[x][y] = 20
                for _ in range(rng.randrange(2, 4)):
                    gap = rng.randrange(y0 + 1, max(y0 + 2, y1 - 1))
                    grid[x][gap] = GRASS
                    grid[x][min(gap + 1, y1 - 1)] = GRASS
            else:
                y = rng.randrange(3, ROWS - 3)
                x0, x1 = rng.randrange(2, 10), rng.randrange(COLUMNS - 10, COLUMNS - 2)
                for x in range(x0, x1):
                    grid[x][y] = 20
                for _ in range(rng.randrange(1, 3)):
                    gap = rng.randrange(x0 + 1, max(x0 + 2, x1 - 1))
                    grid[gap][y] = GRASS
                    grid[min(gap + 1, x1 - 1)][y] = GRASS
        # A few floor patches for material variety.
        for _ in range(4):
            x, y = rng.randrange(2, COLUMNS - 6), rng.randrange(2, ROWS - 6)
            for dx in range(4):
                for dy in range(3):
                    grid[x + dx][y + dy] = rng.choice((GRASS, GRASS, GRASS, DIRT, SAND))
        # The gate columns stay open, and the centre column stays a clear
        # spine so the rising worm is never born into a wall.
        for x in range(18, 23):
            grid[x][ROWS - 2] = GRASS
            grid[x][1] = GRASS
        for y in range(1, ROWS - 1):
            if grid[20][y] != WATER:
                grid[20][y] = GRASS
        seen = reachable(grid)
        floors = sum(1 for x in range(COLUMNS) for y in range(ROWS) if not solid(grid, x, y))
        if (20, 1) not in seen or len(seen) < floors * 0.55:
            continue
        # Water ponds, each kept only if the exit stays reachable.
        for _ in range(rng.randrange(1, 4)):
            for _ in range(20):
                px, py = rng.randrange(2, COLUMNS - 2), rng.randrange(2, ROWS - 2)
                cells = [(px, py)]
                for _ in range(rng.randrange(3, 8)):
                    last = cells[-1]
                    cells.append((last[0] + rng.choice((-1, 0, 1)), last[1] + rng.choice((-1, 0, 1))))
                cells = [(x, y) for x, y in cells
                         if 1 <= x < COLUMNS - 1 and 1 <= y < ROWS - 1 and grid[x][y] in FLOORS]
                if len(cells) < 3:
                    continue
                for x, y in cells:
                    grid[x][y] = WATER
                if (20, 1) not in reachable(grid):
                    for x, y in cells:
                        grid[x][y] = GRASS
                    continue
                break
        # Monsters on open ground away from the entrance.
        open_cells = [(x, y) for x in range(COLUMNS) for y in range(ROWS)
                      if grid[x][y] in FLOORS and abs(x - 20) + abs(y - (ROWS - 2)) > 8]
        rng.shuffle(open_cells)
        for index in range(min(monsters, len(open_cells))):
            x, y = open_cells[index]
            grid[x][y] = MARKERS[index % 6]
        # Fit hedge pieces last so neighbours agree.
        for y in range(ROWS):
            for x in range(COLUMNS):
                if is_wall(grid[x][y]):
                    grid[x][y] = auto_hedge(grid, x, y)
        # Decorations on the remaining open ground.
        objects = [[0 for _ in range(ROWS)] for _ in range(COLUMNS)]
        floors = [(x, y) for x in range(COLUMNS) for y in range(ROWS) if grid[x][y] in FLOORS]
        rng.shuffle(floors)
        spots = iter(floors)

        def spot():
            return next(spots, (1, 1))

        for _ in range(rng.randrange(2, 5)):
            x, y = spot()
            objects[x][y] = FLOWERS
            nx, ny = x + rng.choice((-1, 1)), y + rng.choice((-1, 0, 1))
            if 0 <= nx < COLUMNS and 0 <= ny < ROWS and grid[nx][ny] in FLOORS:
                objects[nx][ny] = FLOWERS
        for _ in range(rng.randrange(2, 5)):
            x, y = spot()
            objects[x][y] = LOG
        for _ in range(rng.randrange(1, 4)):
            x, y = spot()
            objects[x][y] = rng.choice((ROCK, MUSHROOM))
        for _ in range(rng.randrange(2, 5)):
            x, y = spot()
            objects[x][y] = rng.choice((BUTTERFLY, SNAIL, BIRD))
        return grid, objects, apples
    raise RuntimeError(f"could not design level {number}")


def main():
    levels = [design(number) for number in range(1, 34)]
    values = sorted({value for grid, _, _ in levels for column in grid for value in column})
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    table = {value: alphabet[index] for index, value in enumerate(values)}
    lines = ["// Generated by tools/design_levels.py from assets/original. Do not hand-edit.",
             "DESIGNED_LEVEL_COUNT :: 33;",
             f"DesignedCodebook: [{len(values)}]u8 = .[" + ', '.join(str(v) for v in values) + "];",
             "DesignedAlphabet :: \"" + alphabet[:len(values)] + "\";",
             "DesignedApples: [33]s32 = .[" + ", ".join(str(apples) for _, _, apples in levels) + "];",
             "",
             "DesignedLevelText :: (level: s32) -> string {"]
    for index, (grid, _, _) in enumerate(levels):
        text = ''.join(table[grid[x][y]] for x in range(COLUMNS) for y in range(ROWS))
        lines.append(f'    if level == {index} {{ return "{text}" }}')
    lines.extend(['    return ""', "}", "",
                  "DesignedTile :: (level: s32, x: s32, y: s32) -> u8 {",
                  "    text := DesignedLevelText(level)",
                  "    code := text[x * 30 + y]",
                  "    for index: 0..DesignedAlphabet.count - 1 {",
                  "        if DesignedAlphabet[index] == code { return DesignedCodebook[index] }",
                  "    }",
                  "    return 20",
                  "}", "",
                  "DesignedObjectText :: (level: s32) -> string {"])
    for index, (_, objects, _) in enumerate(levels):
        text = ''.join(str(objects[x][y]) for x in range(COLUMNS) for y in range(ROWS))
        lines.append(f'    if level == {index} {{ return "{text}" }}')
    lines.extend(['    return ""', "}", "",
                  "DesignedObject :: (level: s32, x: s32, y: s32) -> u8 {",
                  "    text := DesignedObjectText(level)",
                  "    return cast(u8)(text[x * 30 + y] - 48)",
                  "}", ""])
    (ROOT / "src/designed_levels.zi").write_text("\n".join(lines) + "\n")

    destination = ROOT / "build/designed"
    destination.mkdir(parents=True, exist_ok=True)
    for number, (grid, objects, apples) in enumerate(levels, 1):
        blob = bytearray([apples])
        for plane in (grid, objects):
            for x in range(COLUMNS):
                for y in range(ROWS):
                    blob.append(plane[x][y])
        (destination / f"level{number}.dat").write_bytes(blob)
    print("Designed 33 levels; wrote src/designed_levels.zi and build/designed.")


if __name__ == "__main__":
    main()
