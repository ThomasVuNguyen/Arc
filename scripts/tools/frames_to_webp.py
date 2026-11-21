#!/usr/bin/env python3
"""Assemble PNG frames into a seamlessly looping animated WebP.

The last `overlap` frames are cross-faded into the first ones, so loops whose
motion has no common period still wrap without a visible jump.

usage: frames_to_webp.py <frames-dir> <out.webp> <fps> <overlap-frames> [quality]
"""
import glob
import os
import sys

from PIL import Image

src, out, fps, overlap = sys.argv[1], sys.argv[2], float(sys.argv[3]), int(sys.argv[4])
quality = int(sys.argv[5]) if len(sys.argv) > 5 else 72
frames = [Image.open(p).convert("RGBA") for p in sorted(glob.glob(os.path.join(src, "*.png")))]
if len(frames) <= overlap:
    raise SystemExit("not enough frames")

body, tail = frames[:-overlap] if overlap else frames, frames[-overlap:] if overlap else []
loop = []
for i, f in enumerate(body):
    if i < len(tail):
        k = (i + 1) / (len(tail) + 1)          # tail -> head
        f = Image.blend(tail[i], f, k)
    loop.append(f)

loop[0].save(out, save_all=True, append_images=loop[1:], duration=int(1000 / fps), loop=0,
             quality=quality, method=6, lossless=False,
             kmin=0, kmax=1)   # every frame a keyframe: no lossy sub-frame drift on smooth gradients
print(f"{os.path.basename(out)}: {len(loop)} frames, {os.path.getsize(out) / 1e6:.2f} MB")
