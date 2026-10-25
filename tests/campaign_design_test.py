#!/usr/bin/env python3
"""Independently validate the emitted campaign boards and loop certificates."""
from collections import deque,Counter
import json
from pathlib import Path
import re
import struct

ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'build/designed/manifest.json').read_text())
assert len(manifest)==66
assert len({entry['name'] for entry in manifest})==66
assert len({entry['family'] for entry in manifest})>=10
assert manifest[0]['apples']==manifest[1]['apples']==5 and manifest[1]['walls']<=24, 'five apples and a gentle, open level 2'
assert all(5<=entry['apples']<=8 for entry in manifest)
assert sum(e['apples'] for e in manifest[:8])/8 < sum(e['apples'] for e in manifest[-8:])/8
assert sum(b['apples']<a['apples'] for a,b in zip(manifest,manifest[1:]))>=8, 'retain natural breathing room'
seen_shapes=set()
for entry in manifest:
    n=entry['number'];raw=(ROOT/f'build/designed/level{n}.dat').read_bytes()
    assert len(raw)==2401 and raw[0]==entry['apples'] and not any(raw[1201:]), n
    board={(x,y):raw[1+x*30+y] for x in range(40) for y in range(30)}
    assert set(board.values())<={0,20,21,22}, (n,'only clear floor and solid tile hazards')
    floor={p for p,v in board.items() if v==0}
    assert len(floor)==entry['floors'] and len(floor)>=600
    variants=[]
    for rotation in range(4):
        for reflection in (False,True):
            image=[]
            for x,y in floor:
                w,h=40,30
                for _ in range(rotation):x,y,w,h=h-1-y,x,h,w
                if reflection:x=w-1-x
                image.append((x,y))
            variants.append((w,h,tuple(sorted(image))))
    signature=min(variants);assert signature not in seen_shapes, (n,'duplicate or rotated copy')
    seen_shapes.add(signature)
    certificate=(ROOT/f'build/designed/cycle{n}.dat').read_bytes()
    count=struct.unpack_from('<H',certificate)[0]
    indices=struct.unpack_from('<'+'H'*count,certificate,2)
    cycle=[(i%40,i//40) for i in indices]
    assert len(certificate)==count*2+2 and len(set(cycle))==count and set(cycle)==floor
    assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(cycle,cycle[1:]+cycle[:1]))
    assert count*4>(2+4*raw[0])*16+256, (n,'safe route is too short for the grown worm')
    # Every floor cell belongs to a full 2x2 patch: no one-tile corridors.
    for mx in range(19):
        for my in range(14):
            values=[board[1+mx*2+dx,1+my*2+dy] for dx in range(2) for dy in range(2)]
            assert all(v==0 for v in values) or all(v>=20 for v in values)
    for portrait in (False,True):
        transformed={(29-y,x) for x,y in floor} if portrait else floor
        columns,rows=(30,40) if portrait else (40,30)
        assert (columns//2,rows-3) in transformed and (columns//2,1) in transformed
        start=(columns//2,rows-2);reached={start};todo=deque([start])
        while todo:
            x,y=todo.popleft()
            for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if p in transformed and p not in reached:reached.add(p);todo.append(p)
        assert reached==transformed, (n,portrait,'unreachable apple floor')
print('Campaign local test: 66 unique layouts, no rotated copies, complete reachability and wide routes in both orientations; gentle level 2 and natural difficulty breaks.')
