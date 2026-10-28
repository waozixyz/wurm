#!/usr/bin/env python3
"""Adapt the recovered Worm designs into five distinct 40-level chapters.

Every board cites two original design references. Their walls, chambers,
shorelines and patrol arenas are adapted to a two-tile-wide mobile grid;
minimal doors join enclosed floor and the four orientation-safe landings.
A floor-covering loop certifies the static geometry. The real engine replay
separately verifies winning with the original moving enemies still active.
"""
import argparse
from collections import Counter, deque
import heapq
import json
from pathlib import Path
import random
import struct
from authored_levels import generate as generate_authored
from meadow_levels import apply_meadow

ROOT=Path(__file__).resolve().parents[1]
COLUMNS,ROWS=40,30
MW,MH=19,14
STAGES=(("meadow",0,40),("leafwood",40,80),("pinewood",80,120),("lake",120,160),("mountains",160,200))
# Start with the recognisable first-game landmarks, then draw from all three
# original chapters. No source board is merely recoloured into a new stage.
REFERENCES=(1,2,3,4,5,6,8,9,12,13,15,19,25,26,7,10,14,21,22,23,27,28,30,32,35,37,41,39,43,44,45,46,48,49,51,52,53,54,55,56,
            16,20,24,31,33,36,40,42,47,50,58,60,62,63,64,65,66,68,71,72,73,74,76,77,78,79,80,81,82,83,84,85,87,88,89,90,91,92,94,95,96,97,98,99)
NAMES=("First Bite","Hedge Line","Crossing Paths","Four Gateways","Orchard Stones","Corner Gardens","Ember Hollow","Long Walk","Firefly Clearing","Tall Aisles",
       "Broad Canopy","Sheltered Corners","Stone Crosses","Open Windows","Walled Garden","Narrow Escape","Moss Courtyard","Forest Rooms","Winding Passage","Forked Trail",
       "Hidden Doorways","Linked Courts","Roundabout","Old Walls","Broken Ridge","Twin Paths","Branching Rooms","Quiet Clearing","Needle Crossing","Reed Channels",
       "Pebble Islands","Winding Shore","Double Crossing","High Terraces","Cliff Galleries","Rock Corridors","Alpine Refuge","Summit Spiral","Last Ascent","Beyond the Gate")
ALL={(x,y) for x in range(MW) for y in range(MH)}
GATES={(9,0),(9,1),(9,12),(9,13),(0,6),(0,7),(1,6),(1,7),(17,6),(17,7),(18,6),(18,7)}

def neighbours(point):
    x,y=point
    return ((x-1,y),(x+1,y),(x,y-1),(x,y+1))


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



def original(number):
    raw=(ROOT/f"assets/original/level{number}.dat").read_bytes()
    return [[raw[1+x*30+y] for y in range(30)] for x in range(40)]


def original_walls(number):
    source=original(number);walls={}
    for mx,my in sorted(ALL):
        solid=[]
        for dx in range(2):
            for dy in range(2):
                tile=source[1+mx*2+dx][1+my*2+dy]
                if 20<=tile<128 and not 40<=tile<=45:solid.append(tile)
        if solid:
            raw=Counter(solid).most_common(1)[0][0]
            walls[mx,my]=22 if raw==22 or 53<=raw<=58 else 21 if raw in (21,23,24,25) else 20
    return walls


def reachable(allowed,start):
    seen={start};todo=[start]
    while todo:
        for p in neighbours(todo.pop()):
            if p in allowed and p not in seen:seen.add(p);todo.append(p)
    return seen


def join_floor(walls):
    for p in GATES:walls.pop(p,None)
    # Keep original rooms recognisable: carve the least costly door between
    # disconnected components instead of blanking the walls into an open field.
    while True:
        allowed=ALL-set(walls);seen=reachable(allowed,(9,13))
        if seen==allowed:return walls
        costs={p:0 for p in seen};previous={};queue=[(0,p) for p in sorted(seen)];heapq.heapify(queue)
        target=None
        while queue:
            cost,p=heapq.heappop(queue)
            if cost!=costs[p]:continue
            if p in allowed and p not in seen:target=p;break
            for q in neighbours(p):
                if q not in ALL:continue
                new=cost+(4 if q in walls else 1)
                if new<costs.get(q,99999):costs[q]=new;previous[q]=p;heapq.heappush(queue,(new,q))
        assert target is not None
        while target not in seen:
            walls.pop(target,None);target=previous[target]


def signature(walls):
    # A rotated or reflected chapter is still the same layout.
    variants=[]
    for rotation in range(4):
        for flip in (False,True):
            shape=[]
            w,h=(MW,MH) if rotation%2==0 else (MH,MW)
            for a,b in walls:
                x,y=a,b;w,h=MW,MH
                for _ in range(rotation):x,y,w,h=h-1-y,x,h,w
                if flip:x=w-1-x
                shape.append((x,y))
            variants.append((w,h,tuple(sorted(shape))))
    return min(variants)


def layout(stage,within,attempt):
    index=(within+stage*17+attempt*7)%len(REFERENCES)
    source=REFERENCES[index]
    accent=REFERENCES[(within*11+stage*23+attempt*13+7)%len(REFERENCES)]
    primary=original_walls(source);secondary=original_walls(accent)
    walls=dict(primary)
    if stage>0 or within>=6 or attempt:
        variant=(within+stage+attempt)%5
        for x,y in sorted(ALL):
            use=(x>=12 if variant==0 else y>=8 if variant==1 else
                 x<7 and y<8 if variant==2 else x+y>=20 if variant==3 else 5<=x<=12 and 3<=y<=10)
            if use:
                walls.pop((x,y),None)
                if (x,y) in secondary:walls[x,y]=secondary[x,y]
        # The later stage's terrain affects what its original obstacles
        # become, not whether the same layout is repeated.
        if stage==3:walls={p:(21 if v==21 else 22) for p,v in walls.items()}
        elif stage==4:walls={p:(22 if v==22 and (p[0]+p[1])%3==0 else 21 if v==21 else 20) for p,v in walls.items()}
    if stage == 0 and within == 9 and attempt == 0:
        # Tall Aisles: four-cell lanes leave room for touch steering while
        # retaining the two tall hedges and the lower courtyard.
        walls = {(4, y): 20 for y in range(1, 9)}
        walls.update({(14, y): 20 for y in range(9)})
        walls.update({(x, y): 20 for x in (7, 11) for y in range(3, 9)})
        walls.update({(x, 8): 20 for x in range(7, 15)})
        walls.update({(x, y): 20 for x in (5, 13) for y in range(9, 12)})
        walls.update({(x, 10): 20 for x in (5, 6, 7, 8, 11, 12, 13)})
    walls=join_floor(walls)
    if stage==0 and within<6 and attempt==0:return source,accent,walls
    return source,accent,walls


# Mountain boards that close a corner room with a single doorway. The game
# seals that doorway, so a portal is the only way in; with the doorway open
# the room is ordinary floor for the certificate.
PORTAL_ROOMS=(181,183,185,189,191)


def portal_room(walls,number):
    # Each corner room is 4x3 blocks, walled toward the middle, with its door
    # on the side or the bottom; the boards try them in a per-level order.
    corners=[]
    for right in (False,True):
        for bottom in (False,True):
            xs=range(15,19) if right else range(0,4)
            ys=range(11,14) if bottom else range(0,3)
            wall_x=14 if right else 4
            wall_y=10 if bottom else 3
            ring=[(wall_x,y) for y in (range(10,14) if bottom else range(0,4))]+[(x,wall_y) for x in (range(14,19) if right else range(0,5))]
            side=(wall_x,12 if bottom else 1);outside_side=(wall_x+(-1 if right else 1),side[1])
            below=(16 if right else 2,wall_y);outside_below=(below[0],wall_y+(-1 if bottom else 1))
            for door,outside in ((side,outside_side),(below,outside_below)):
                corners.append(({(x,y) for x in xs for y in ys},ring,door,outside))
    tile=Counter(walls.values()).most_common(1)[0][0] if walls else 20
    order=list(range(len(corners)));random.Random(number*977).shuffle(order)
    for index in order:
        room,ring,door,outside=corners[index]
        shaped=dict(walls)
        for p in room:shaped.pop(p,None)
        for p in ring:shaped[p]=tile
        shaped.pop(door,None);shaped.pop(outside,None)
        allowed=ALL-set(shaped)
        if reachable(allowed,(9,13))==allowed and not (set(shaped)&GATES):
            return shaped,room
    return None,set()


def campaign():
    levels=[];known=set()
    for stage,(stage_name,first,end) in enumerate(STAGES):
        for within in range(40):
            number=first+within+1
            for attempt in range(512):
                source,accent,walls=layout(stage,within,attempt)
                room=set()
                if number in PORTAL_ROOMS:
                    walls,room=portal_room(walls,number)
                    if walls is None:continue
                floors=ALL-set(walls);key=signature(walls)
                if key in known or len(floors)<88 or (within>=6 and len(walls)<8):continue
                known.add(key);break
            else:raise RuntimeError(f"Could not adapt a unique level {number}")
            grid=[[20 if x in (0,39) or y in (0,29) else 0 for y in range(ROWS)] for x in range(COLUMNS)]
            for (mx,my),tile in walls.items():
                for dx in range(2):
                    for dy in range(2):grid[1+mx*2+dx][1+my*2+dy]=tile
            cycle=safe_cycle(floors,number*4099)
            count=0 if stage==0 and within<6 else min(8,1+stage+within//16)
            # Creatures stay out of a portal room, leaving it room for the ring.
            candidates=[p for p in cycle if 3<=p[0]<=36 and 3<=p[1]<=23 and
                        abs(p[0]-20)+abs(p[1]-27)>=14 and abs(p[0]-37)+abs(p[1]-14)>=10 and
                        ((p[0]-1)//2,(p[1]-1)//2) not in room]
            rng=random.Random(number*65537);rng.shuffle(candidates);placed=[];kinds=[]
            for x,y in candidates:
                if len(placed)>=count:break
                if any(abs(x-a)+abs(y-b)<5 for a,b in placed):continue
                index=len(placed)
                kind=40 if (within+index)%3==0 and (stage>0 or within>=8) else 45 if stage>=1 and (within+index)%5==0 else 41+(within+index)%4
                grid[x][y]=kind;placed.append((x,y));kinds.append(kind-39)
            assert len(placed)==count
            apples=5+stage+(1 if within%10 in (7,8,9) else 0)
            portrait_grid=None;portrait_cycle=None
            if number==2:
                # Keep this introductory divider across the narrow display;
                # a quarter-turn would put it along the worm's approach.
                allowed={(x,y) for x in range(14) for y in range(19)}-{(x,9) for x in range(10)}
                portrait_grid=[[20 if x in (0,29) or y in (0,39) else 0 for y in range(40)] for x in range(30)]
                for mx in range(10):
                    for dx in range(2):
                        for dy in range(2):portrait_grid[1+mx*2+dx][19+dy]=20
                portrait_cycle=safe_cycle(allowed,number*4099)
            blob=bytes([apples])+bytes(grid[x][y] for x in range(COLUMNS) for y in range(ROWS))+bytes(1200)
            levels.append(dict(number=number,name=stage_name.title()+" — "+NAMES[within],family="original-"+str(source),tier=stage+1,
                apples=apples,original=source,accent=accent,enemies=count,enemy_kinds=kinds,grid=grid,cycle=cycle,blob=blob,
                floors=len(cycle),walls=len(walls)*4,portrait_grid=portrait_grid,portrait_cycle=portrait_cycle))
    assert len(levels)==200 and len(known)==200
    # Keep the other four chapters byte-for-byte stable. Meadow shares a
    # gentler portrait-oriented garden plan between both screen shapes.
    apply_meadow(levels, ROOT, safe_cycle)
    actual_shapes = {signature({(x,y): level['grid'][1+x*2][1+y*2]
                               for y in range(MH) for x in range(MW)
                               if 20 <= level['grid'][1+x*2][1+y*2] < 40}) for level in levels}
    assert len(actual_shapes) == 200, 'Meadow must keep every campaign layout distinct'
    return levels


def encode(levels):
    values=sorted({tile for l in levels for col in l['grid'] for tile in col})
    alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    table={value:alphabet[i] for i,value in enumerate(values)}
    lines=['// Generated by tools/design_levels.py. 200 original-inspired challenges with active enemies.',
           'DESIGNED_LEVEL_COUNT :: 200;',
           f'DesignedStageStarts: [{len(STAGES)+1}]s32 = .[' + ', '.join(str(first) for _,first,_ in STAGES) + f', {len(levels)}];',
           'DesignedMeadowPortals: [6]s32 = .[' + ', '.join(str(level['number'] - 1) for level in levels[:40] if level['meadow_portal']) + '];',
           f'DesignedCodebook: [{len(values)}]u8 = .['+', '.join(map(str,values))+'];',
           'DesignedAlphabet :: "'+alphabet[:len(values)]+'";',
           'DesignedApples: [200]s32 = .['+', '.join(str(l['apples']) for l in levels)+'];','',
           'DesignedLevelText :: (level: s32) -> string {']
    for i,level in enumerate(levels):
        text=''.join(table[level['grid'][x][y]] for x in range(COLUMNS) for y in range(ROWS))
        lines.append(f'    if level == {i} {{ return "{text}" }}')
    lines += ['    return ""','}','','DesignedPortraitText :: (level: s32) -> string {']
    for i,level in enumerate(levels):
        if level['portrait_grid'] is not None:
            text=''.join(table[level['portrait_grid'][x][y]] for x in range(30) for y in range(40))
            lines.append(f'    if level == {i} {{ return "{text}" }}')
    lines += ['    return ""','}','','DesignedTile :: (level: s32, x: s32, y: s32) -> u8 {',
              '    text := DesignedLevelText(level)','    code := text[x * 30 + y]',
              '    for index: 0..DesignedAlphabet.count - 1 {',
              '        if DesignedAlphabet[index] == code { return DesignedCodebook[index] }',
              '    }','    return 20','}','']
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    generate_authored(args.check)
    levels=campaign();source=encode(levels);path=ROOT/'src/designed_levels.zi'
    cases=json.loads((ROOT/'tests/campaign_cases.json').read_text())
    assert len(cases)==200 and all(len(pair)==2 for pair in cases)
    fixture='// Generated from campaign_cases.json by tools/design_levels.py.\n'
    for name,key,kind in (('CampaignSeeds','seed','u32'),('CampaignRoutes','route','s32'),('CampaignReverse','reverse','s32')):
        fixture+=name+': [400]'+kind+' = .['+', '.join(str(c[key]) for pair in cases for c in pair)+'];\n'
    fixture_path=ROOT/'tests/campaign_replay.zi'
    text=fixture_path.read_text()
    first=text.index('// campaign-cases:begin')+len('// campaign-cases:begin')+1
    last=text.index('// campaign-cases:end')
    if args.check:assert text[first:last]==fixture, 'campaign case fixture is stale'
    else:fixture_path.write_text(text[:first]+fixture+text[last:])
    if args.check:
        assert path.read_text()==source, 'src/designed_levels.zi differs from the authored campaign'
    else:path.write_text(source)
    out=ROOT/'build/designed';out.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for l in levels:
        (out/f"level{l['number']}.dat").write_bytes(l['blob'])
        indices=[y*COLUMNS+x for x,y in l['cycle']]
        (out/f"cycle{l['number']}.dat").write_bytes(struct.pack('<H'+'H'*len(indices),len(indices),*indices))
        for variant in sorted({case['route'] for case in cases[l['number']-1]}-{0}):
            floor={(x,y) for x in range(40) for y in range(30) if l['grid'][x][y]<20 or 40<=l['grid'][x][y]<=45}
            allowed={((x-1)//2,(y-1)//2) for x,y in floor}
            route=safe_cycle(allowed,l['number']*4099+variant*65537)
            cells=[y*COLUMNS+x for x,y in route]
            (out/f"cycle{l['number']}-{variant}.dat").write_bytes(struct.pack('<H'+'H'*len(cells),len(cells),*cells))
        if l['portrait_cycle'] is not None:
            cells=[y*30+x for x,y in l['portrait_cycle']]
            (out/f"cycle{l['number']}-portrait.dat").write_bytes(struct.pack('<H'+'H'*len(cells),len(cells),*cells))
            blob=bytes([l['apples']])+bytes(l['portrait_grid'][x][y] for x in range(30) for y in range(40))+bytes(1200)
            (out/f"level{l['number']}-portrait.dat").write_bytes(blob)
        entry={k:l[k] for k in ('number','name','family','tier','apples','floors','walls','original','accent','enemies','enemy_kinds')}
        entry['stage']=next(name for name, first, end in STAGES if first <= l['number']-1 < end)
        manifest.append(entry)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('200 distinct original-inspired challenges '+('verified' if args.check else 'written')+'; every floor has a complete safe-loop certificate.')


if __name__=='__main__':main()
