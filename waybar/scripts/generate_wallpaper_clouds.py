#!/usr/bin/env python3
"""Generate seamless blue/purple clouds with the Python standard library."""
import base64
import math
import random
import statistics
import struct
import sys
import zlib
from pathlib import Path

SIZE = 128
PALETTES = {
    "blue": (19, (184, 214, 234), 144.67, 62.26),
    "lavender": (43, (194, 177, 222), 137.18, 62.90),
}

def smooth(t):
    return t*t*t*(t*(t*6-15)+10)

def noise(grid, n, u, v):
    x, y = u*n, v*n
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = smooth(x-ix), smooth(y-iy)
    a, b = grid[iy%n][ix%n], grid[iy%n][(ix+1)%n]
    c, d = grid[(iy+1)%n][ix%n], grid[(iy+1)%n][(ix+1)%n]
    return (a+(b-a)*fx)*(1-fy)+(c+(d-c)*fx)*fy

def texture(seed, rgb, mean, deviation):
    rng = random.Random(seed)
    grids = [(n, weight, [[rng.uniform(-1, 1) for _ in range(n)] for _ in range(n)])
             for n, weight in ((4, .62), (8, .27), (16, .11))]
    values = []
    for y in range(SIZE):
        for x in range(SIZE):
            u, v = x/(SIZE-1), y/(SIZE-1)
            # Periodic domain warping avoids an axis-aligned lattice appearance.
            a = u+.09*math.sin(2*math.pi*(u+2*v))+.04*math.cos(2*math.pi*3*v)
            b = v+.08*math.cos(2*math.pi*(2*u-v))+.04*math.sin(2*math.pi*3*u)
            values.append(sum(weight*noise(grid,n,a,b) for n,weight,grid in grids))
    center, spread = statistics.mean(values), statistics.pstdev(values)
    alpha = [round(max(0,min(255,mean+(v-center)*deviation/spread))) for v in values]
    for y in range(SIZE): alpha[y*SIZE+SIZE-1] = alpha[y*SIZE]
    alpha[-SIZE:] = alpha[:SIZE]
    assert all(alpha[y*SIZE] == alpha[y*SIZE+SIZE-1] for y in range(SIZE))
    assert alpha[:SIZE] == alpha[-SIZE:]
    raw = b"".join(b"\x00"+b"".join(bytes((*rgb,alpha[y*SIZE+x])) for x in range(SIZE))
                   for y in range(SIZE))
    def chunk(kind, data):
        return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
    return (b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",SIZE,SIZE,8,6,0,0,0))
            +chunk(b"IDAT",zlib.compress(raw,9))+chunk(b"IEND",b""))

def main():
    output = Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
    for name, settings in PALETTES.items():
        data = base64.b64encode(texture(*settings)).decode("ascii")
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
               'width="128" height="128" viewBox="0 0 128 128">\n'
               '  <!-- Periodic clouds; regenerate with scripts/generate_wallpaper_clouds.py. -->\n'
               '  <image width="128" height="128" xlink:href="data:image/png;base64,'+data+'"/>\n'
               '</svg>\n')
        (output/("wallpaper-cloud-"+name+".svg")).write_text(svg)
        print(name+": generated matching opposite edges")

if __name__ == "__main__":
    main()
