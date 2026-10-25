#!/usr/bin/env python3
"""Author the 66 clean tile challenges and certify a safe loop on every floor.

Layouts use deliberately placed obstacles on a two-tile grid. A spanning tree
of connected 2x2 floor blocks is expanded into one Hamiltonian cycle through
EVERY floor tile. This gives the real engine replay test a route that can
collect apples anywhere without dead ends, in either orientation. The route
is validation data, never an on-screen hint or an autoplayer in the game.

--check verifies the checked-in level source; both modes refresh derived
boards, route certificates and the design manifest under build/designed.
"""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import random
import struct

ROOT = Path(__file__).resolve().parents[1]
COLUMNS, ROWS = 40, 30
MW, MH = 19, 14
STAGES = (("meadow", 0, 14), ("leafwood", 14, 27), ("pinewood", 27, 40),
          ("lake", 40, 53), ("mountains", 53, 66))
# name, obstacle family, challenge tier, apples. Breathers are intentional.
BLUEPRINTS = [
 ('First Bite','orchard',1,5), ('Gentle Turn','orchard',1,5),
 ('Four Corners','islands',1,5), ('Wide Passage','bars',1,5),
 ('Pondside','ponds',1,5), ('Easy Weave','slalom',1,5),
 ('Meadow Lanes','lanes',2,5), ('Stepping Stones','steps',2,5),
 ('Open Courtyard','courtyard',2,6), ('Crossroads','crosses',2,5),
 ('Apple Islands','islands',2,6), ('Sunny Clearing','orchard',2,5),
 ('Meadow Rooms','rooms',2,6), ('Woodland Edge','bars',3,6),
 ('First Leaves','orchard',2,5), ('Oak Walk','slalom',3,6),
 ('Leaf Pools','ponds',3,5), ('Beech Aisles','lanes',3,6),
 ('Root Steps','steps',3,6), ('Canopy Doors','courtyard',3,7),
 ('Sunlit Glade','orchard',2,5), ('Leafy Rooms','rooms',3,6),
 ('Branching Paths','crosses',3,6), ('Brook Crossings','bridges',3,7),
 ('Long Branches','bars',4,6), ('Moss Islands','islands',3,6),
 ('Last Oaks','slalom',4,7),
 ('First Pines','orchard',3,5), ('Pine Pools','ponds',4,6),
 ('Fir Clearing','orchard',3,5), ('Needle Steps','steps',4,6),
 ('Evergreen Rooms','rooms',4,7), ('Pine Courtyard','courtyard',4,7),
 ('Quiet Needles','slalom',3,5), ('Forest Stream','ponds',3,6),
 ('Granite Islands','islands',4,6), ('Fir Bridges','bridges',4,7),
 ('Tall Pines','lanes',4,6), ('Deep Woods','rooms',4,7),
 ('Lakeside Light','crosses',3,5),
 ('First Shore','ponds',3,5), ('Reed Banks','bridges',4,6),
 ('Pebble Beach','islands',4,6), ('Lake Windows','bars',5,7),
 ('Still Water','ponds',4,5), ('Reed Channels','lanes',5,7),
 ('Shore Stones','islands',5,7), ('Island Crossing','bridges',5,8),
 ('Sandy Rest','orchard',4,5), ('Split Banks','crosses',5,7),
 ('Reed Walk','slalom',5,7), ('Upper Shore','steps',5,8),
 ('Mountain Foot','courtyard',5,7),
 ('First Climb','steps',4,6), ('Rock Windows','bars',5,7),
 ('Alpine Pools','ponds',5,6), ('Cliff Rooms','rooms',5,8),
 ('High Pass','bridges',5,8), ('Alpine Meadow','orchard',4,5),
 ('Ridge Lanes','lanes',5,7), ('Stone Slalom','slalom',5,7),
 ('Summit Paths','crosses',5,8), ('High Courtyard','courtyard',5,8),
 ('Last Terraces','steps',5,7), ('Summit Stones','islands',5,8),
 ('The Mountain','bridges',5,8),
]


def neighbours(point):
    x,y=point
    return ((x-1,y),(x+1,y),(x,y-1),(x,y+1))


def protected(x,y):
    # The outside ring and six-tile landing pads at all FOUR potential gates.
    return (x in (0,MW-1) or y in (0,MH-1) or
            (8<=x<=10 and (y<=2 or y>=11)) or
            (5<=y<=7 and (x<=2 or x>=16)))


def obstacles(number, family, tier, attempt):
    rng=random.Random(104729*number+7919*attempt)
    walls={}
    def rect(x,y,w,h,tile=20):
        for xx in range(x,x+w):
            for yy in range(y,y+h):
                if 0<=xx<MW and 0<=yy<MH and not protected(xx,yy):
                    walls[xx,yy]=tile
    shift=rng.choice((-1,0,1))
    if number==1:
        rect(4,5,2,2)
    elif number==2:
        rect(4,4,2,1);rect(13,8,2,1)
    elif family=='orchard':
        positions=[(4,3),(13,9),(4,9),(13,3),(8,6),(11,8)]
        rng.shuffle(positions)
        for i,(x,y) in enumerate(positions[:tier+1]):
            rect(x+shift,y,1+(i+tier)%2,1+(i+number)%2,21 if i%2 else 20)
    elif family=='islands':
        positions=[(4,3),(12,3),(4,9),(12,9),(8,6)]
        rng.shuffle(positions)
        for i,(x,y) in enumerate(positions[:min(5,2+tier)]):
            rect(x+shift,y+rng.choice((-1,0,1)),2+(tier>=4),1+(tier>=2),21)
    elif family=='bars':
        ys=[3,7,10] if tier<4 else [3,6,9,11]
        for i,y in enumerate(ys[:1+tier]):
            start=3+(i+number)%3
            rect(start,y,9+tier,1)
            gap=6+(i*3+number)%7
            for xx in range(gap,gap+max(2,4-tier//2)):
                walls.pop((xx,y),None)
    elif family=='lanes':
        xs=[3+rng.randrange(2),8+rng.randrange(2),13+rng.randrange(2)] if tier<5 else [3+rng.randrange(2),7+rng.randrange(2),11+rng.randrange(2),15+rng.randrange(2)]
        for i,x in enumerate(xs):
            rect(x,3,1,7+(tier>=3))
            gap=rng.randrange(4,8)
            for yy in range(gap,gap+2):walls.pop((x,yy),None)
    elif family=='ponds':
        positions=[(4,3),(12,4),(6,9),(12,9)]
        rng.shuffle(positions)
        for i,(x,y) in enumerate(positions[:min(4,1+tier)]):
            rect(x+shift,y,2+(tier>=4),1+(i+tier)%2,22)
    elif family=='courtyard':
        x,y=4+shift,2+rng.randrange(2)
        w,h=10+(tier>=4),7+(tier>=3)
        rect(x,y,w,1);rect(x,y+h-1,w,1)
        rect(x,y,1,h);rect(x+w-1,y,1,h)
        door=rng.randrange(2,w-3)
        for d in range(2):
            walls.pop((x+door+d,y),None)
            walls.pop((x+w-door-2+d,y+h-1),None)
            walls.pop((x,y+2+d),None)
            walls.pop((x+w-1,y+h-4+d),None)
    elif family=='crosses':
        cross_y=rng.choice((-1,0,1))
        rect(3+shift,5+cross_y,3+rng.randrange(3),1+(tier>=4));rect(12,7-cross_y,3+rng.randrange(2),1+(tier>=4))
        rect(8,3,1+(tier>=3),2);rect(10,9,1+(tier>=3),2)
        if tier>=4:rect(4,10,2,1,21);rect(14,3,1,2,21)
    elif family=='slalom':
        for i,x in enumerate((4,8,12,16)[:min(4,2+tier)]):
            y=3 if (i+number)%2 else 7
            rect(x+shift,y+rng.randrange(2),1,2+tier,20)
    elif family=='rooms':
        for i,(x,y) in enumerate(((3,3),(11,3),(4,9),(12,9))):
            length=3+(tier>=4)
            rect(x+shift,y,length,1,21 if i%2 else 20)
            rect(x+shift+(length-1 if (i+number)%2 else 0),y,1,2+(tier>=5))
    elif family=='steps':
        step_y=rng.choice((-1,0,1))
        for i in range(min(4,2+tier)):
            x=3+i*3+shift;y=2+i*2+(number%2)+step_y
            rect(x,y,2+(tier>=3),1+(tier>=4),21)
    elif family=='bridges':
        for i,y in enumerate((4,9)):
            gap=7+(number+i*3)%5
            rect(3+shift,y,gap-3,1+(tier>=4),22)
            rect(gap+3,y,16-gap-2,1+(tier>=3),22)
        if tier>=5:rect(7,7,2,1,21)
    else:raise ValueError(family)
    return walls


def connected(points):
    start=min(points);seen={start};queue=deque([start])
    while queue:
        for p in neighbours(queue.popleft()):
            if p in points and p not in seen:seen.add(p);queue.append(p)
    return seen==points


def safe_cycle(allowed, seed):
    # Start with a clockwise 4-cycle inside each 2x2 floor block.
    graph={}
    def link(a,b):graph.setdefault(a,set()).add(b);graph.setdefault(b,set()).add(a)
    def unlink(a,b):graph[a].remove(b);graph[b].remove(a)
    for mx,my in allowed:
        x,y=1+mx*2,1+my*2
        cells=((x,y),(x+1,y),(x+1,y+1),(x,y+1))
        for i in range(4):link(cells[i],cells[(i+1)%4])
    rng=random.Random(seed)
    # A deterministic randomized DFS tree changes the validation route,
    # never the authored geometry.
    start=min(allowed);seen={start};stack=[start];tree=[]
    while stack:
        a=stack[-1];choices=sorted(p for p in neighbours(a) if p in allowed and p not in seen)
        if not choices:stack.pop();continue
        b=rng.choice(choices);seen.add(b);stack.append(b);tree.append((a,b))
    assert seen==allowed
    for a,b in tree:
        if a[0]!=b[0]:
            if a[0]>b[0]:a,b=b,a
            x,y=1+a[0]*2,1+a[1]*2
            p,q=(x+1,y),(x+1,y+1);r,s=(x+2,y),(x+2,y+1)
        else:
            if a[1]>b[1]:a,b=b,a
            x,y=1+a[0]*2,1+a[1]*2
            p,q=(x,y+1),(x+1,y+1);r,s=(x,y+2),(x+1,y+2)
        unlink(p,q);unlink(r,s);link(p,r);link(q,s)
    assert all(len(n)==2 for n in graph.values())
    first=min(graph);cycle=[first];previous=None;current=first
    while True:
        options=sorted(graph[current]-({previous} if previous is not None else set()))
        following=options[0]
        if following==first:break
        cycle.append(following);previous,current=current,following
        assert len(cycle)<=len(graph)
    assert len(cycle)==len(graph) and len(set(cycle))==len(graph)
    return cycle


def geometry_key(walls):
    # Width/height swap is retained: rotation/reflection copies do not count
    # as another unique challenge.
    points={(x,y) for x,y in walls}
    images=[]
    for rotation in range(4):
        for reflected in (False,True):
            image=[]
            for x,y in points:
                a,b=x,y;w,h=MW,MH
                for _ in range(rotation):a,b,w,h=h-1-b,a,h,w
                if reflected:a=w-1-a
                image.append((a,b))
            images.append((w,h,tuple(sorted(image))))
    return min(images)


def campaign():
    assert len(BLUEPRINTS)==66
    levels=[];known=set()
    all_macros={(x,y) for x in range(MW) for y in range(MH)}
    for number,(name,family,tier,apples) in enumerate(BLUEPRINTS,1):
        apples = max(5, apples)
        for attempt in range(128):
            walls=obstacles(number,family,tier,attempt)
            allowed=all_macros-set(walls)
            key=geometry_key(walls)
            if key in known or not connected(allowed) or len(allowed)<150:continue
            known.add(key);break
        else:raise RuntimeError(f'No unique connected layout for {number} {name}')
        grid=[[20 if x in (0,39) or y in (0,29) else 0 for y in range(ROWS)] for x in range(COLUMNS)]
        for (mx,my),tile in walls.items():
            for dx in range(2):
                for dy in range(2):grid[1+mx*2+dx][1+my*2+dy]=tile
        cycle=safe_cycle(allowed,number*4099)
        blob=bytes([apples])+bytes(grid[x][y] for x in range(COLUMNS) for y in range(ROWS))+bytes(1200)
        levels.append(dict(number=number,name=name,family=family,tier=tier,apples=apples,
                           grid=grid,cycle=cycle,blob=blob,floors=len(cycle),walls=len(walls)*4))
    return levels


def encode(levels):
    values=sorted({tile for l in levels for col in l['grid'] for tile in col})
    alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    table={value:alphabet[i] for i,value in enumerate(values)}
    lines=['// Generated by tools/design_levels.py. 66 authored, certified tile challenges.',
           'DESIGNED_LEVEL_COUNT :: 66;',
           f'DesignedStageStarts: [{len(STAGES)+1}]s32 = .[' + ', '.join(str(first) for _,first,_ in STAGES) + f', {len(levels)}];',
           f'DesignedCodebook: [{len(values)}]u8 = .['+', '.join(map(str,values))+'];',
           'DesignedAlphabet :: "'+alphabet[:len(values)]+'";',
           'DesignedApples: [66]s32 = .['+', '.join(str(l['apples']) for l in levels)+'];','',
           'DesignedLevelText :: (level: s32) -> string {']
    for i,level in enumerate(levels):
        text=''.join(table[level['grid'][x][y]] for x in range(COLUMNS) for y in range(ROWS))
        lines.append(f'    if level == {i} {{ return "{text}" }}')
    lines += ['    return ""','}','','DesignedTile :: (level: s32, x: s32, y: s32) -> u8 {',
              '    text := DesignedLevelText(level)','    code := text[x * 30 + y]',
              '    for index: 0..DesignedAlphabet.count - 1 {',
              '        if DesignedAlphabet[index] == code { return DesignedCodebook[index] }',
              '    }','    return 20','}','']
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    levels=campaign();source=encode(levels);path=ROOT/'src/designed_levels.zi'
    if args.check:
        assert path.read_text()==source, 'src/designed_levels.zi differs from the authored campaign'
    else:path.write_text(source)
    out=ROOT/'build/designed';out.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for l in levels:
        (out/f"level{l['number']}.dat").write_bytes(l['blob'])
        indices=[y*COLUMNS+x for x,y in l['cycle']]
        (out/f"cycle{l['number']}.dat").write_bytes(struct.pack('<H'+'H'*len(indices),len(indices),*indices))
        entry={k:l[k] for k in ('number','name','family','tier','apples','floors','walls')}
        entry['stage']=next(name for name, first, end in STAGES if first <= l['number']-1 < end)
        manifest.append(entry)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('66 distinct tile challenges '+('verified' if args.check else 'written')+'; every floor has a complete safe-loop certificate.')


if __name__=='__main__':main()
