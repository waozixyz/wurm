"""Build matching, spacious Meadow gardens from portrait-oriented motifs."""
import heapq
import json
import random


TILES = {"#": 20, "t": 21, "r": 22}


def read_plans(root):
    document = json.loads((root / "assets/meadow-gardens.json").read_text())
    assert document["schema"] == "wurm.meadow.gardens.v1"
    assert (document["columns"], document["rows"]) == (14, 19)
    plans = document["levels"]
    assert [plan["number"] for plan in plans] == list(range(1, 41))
    assert document["portal_levels"] == [10, 12, 16, 23, 31, 38]
    for plan in plans:
        assert len(plan["rows"]) == 19
        assert all(len(row) == 14 and set(row) <= set(".#tr") for row in plan["rows"])
        assert plan["apples"] in (5, 6) and plan["enemies"] in (0, 1)
        plan["portal"] = plan["number"] in document["portal_levels"]
        assert not plan["portal"] or plan["enemies"] == 0
    return plans


def neighbours(point):
    x, y = point
    return (x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)


def connect(walls, width, height):
    """Open a small hedge gap if resizing enclosed a courtyard."""
    all_cells = {(x, y) for y in range(height) for x in range(width)}
    start = width // 2, height - 1
    while True:
        floor = all_cells - walls.keys()
        reached = {start}
        pending = [start]
        for point in pending:
            for neighbour in neighbours(point):
                if neighbour in floor and neighbour not in reached:
                    reached.add(neighbour)
                    pending.append(neighbour)
        if reached == floor:
            return walls
        costs = {point: 0 for point in reached}
        previous = {}
        queue = [(0, point) for point in sorted(reached)]
        heapq.heapify(queue)
        while queue:
            cost, point = heapq.heappop(queue)
            if cost != costs[point]:
                continue
            if point in floor and point not in reached:
                break
            for neighbour in neighbours(point):
                x, y = neighbour
                if not (0 <= x < width and 0 <= y < height):
                    continue
                candidate = cost + (5 if neighbour in walls else 1)
                if candidate < costs.get(neighbour, 10000):
                    costs[neighbour] = candidate
                    previous[neighbour] = point
                    heapq.heappush(queue, (candidate, neighbour))
        while point not in reached:
            walls.pop(point, None)
            point = previous[point]


def landscape_walls(portrait):
    # Forward coverage preserves thin horizontal hedges on the shorter board.
    # Both modes keep the same top/bottom direction and broad entrance area.
    result = {}
    for (source_x, source_y), tile in portrait.items():
        left = round(source_x * 19 / 14)
        right = max(left + 1, round((source_x + 1) * 19 / 14))
        top = round(source_y * 14 / 19)
        bottom = max(top + 1, round((source_y + 1) * 14 / 19))
        for y in range(top, min(14, bottom)):
            for x in range(left, min(19, right)):
                if x in (0, 18) or y in (0, 13) or (7 <= x <= 11 and y >= 10):
                    continue
                result[x, y] = tile
    return connect(result, 19, 14)


def expand(walls, width, height):
    columns, rows = width * 2 + 2, height * 2 + 2
    grid = [[20 if x in (0, columns - 1) or y in (0, rows - 1) else 0
             for y in range(rows)] for x in range(columns)]
    for (x, y), tile in walls.items():
        for dx in (0, 1):
            for dy in (0, 1):
                grid[1 + x * 2 + dx][1 + y * 2 + dy] = tile
    return grid


def patrol(grid, number, count):
    if not count:
        return []
    columns, rows = len(grid), len(grid[0])
    candidates = [(x, y) for x in range(3, columns - 3) for y in range(3, rows - 5)
                  if grid[x][y] < 20 and abs(x - columns // 2) + abs(y - rows + 3) >= 14]
    random.Random(number * 65537).shuffle(candidates)
    assert candidates
    x, y = candidates[0]
    kind = 41 + (number - 1) % 4  # One predictable bouncing patrol; no chase/fire.
    grid[x][y] = kind
    return [kind - 39]


def apply_meadow(levels, root, make_cycle):
    for plan, level in zip(read_plans(root), levels[:40]):
        number = plan["number"]
        portrait = {(x, y): TILES[code] for y, row in enumerate(plan["rows"])
                    for x, code in enumerate(row) if code != "."}
        connect(portrait, 14, 19)
        wide = landscape_walls(portrait)
        floor = {(x, y) for y in range(14) for x in range(19)} - wide.keys()
        portrait_floor = {(x, y) for y in range(19) for x in range(14)} - portrait.keys()
        grid = expand(wide, 19, 14)
        portrait_grid = expand(portrait, 14, 19)
        kinds = patrol(grid, number, plan["enemies"])
        patrol(portrait_grid, number, plan["enemies"])
        cycle = make_cycle(floor, number * 4099)
        level.update(apples=plan["apples"], enemies=plan["enemies"], enemy_kinds=kinds,
                     grid=grid, cycle=cycle, floors=len(cycle), walls=len(wide) * 4,
                     portrait_grid=portrait_grid, portrait_cycle=make_cycle(portrait_floor, number * 4099),
                     meadow_portal=plan["portal"])
        level["blob"] = bytes([plan["apples"]]) + bytes(grid[x][y] for x in range(40)
                                                        for y in range(30)) + bytes(1200)
