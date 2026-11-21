#!/usr/bin/env python3
"""Build a local, browsable Arc brand book from vault/extracted.

Shows every named color (light/dark), every bundled font, every icon/image,
the Lottie animations (playing), sounds and videos, all in one HTML page.
The page references the extracted files by relative path, so it only works
next to vault/extracted and is never published: it shows Arc's copyrighted
artwork.

usage: brand_book.py <vault-dir>      ->  <vault-dir>/brand-book.html
"""
import glob
import json
import os
import sys
from html import escape

VAULT = os.path.abspath(sys.argv[1])
EX = os.path.join(VAULT, "extracted", "bundles")
rel = lambda p: os.path.relpath(p, VAULT)


def bundle_label(path):
    b = os.path.relpath(path, EX).split(os.sep)[0]
    return b.split("_", 1)[1] if "_" in b and not b.startswith("_") else b.lstrip("_")


# --- colors --------------------------------------------------------------------
colors_html = []
n_colors = 0
for f in sorted(glob.glob(f"{EX}/*/assets/colors.json")):
    data = json.load(open(f))
    cells = []
    for name, v in sorted(data.items()):
        l, d = v.get("light", {}), v.get("dark", {})
        def css(x):
            return f"color-mix(in srgb, {x['hex']} {float(x['alpha']) * 100:.0f}%, transparent)" if x else "transparent"
        def lab(x):
            return f"{x['hex']}" + ("" if not x or float(x["alpha"]) >= 1 else f" · {float(x['alpha']) * 100:.0f}%")
        cells.append(f'<div class="sw"><div class="chip"><span style="background:{css(l)}"></span><span class="dk" style="background:{css(d)}"></span></div>'
                     f'<b>{escape(name)}</b><code>{escape(lab(l))}</code><code class="mut">{escape(lab(d))}</code></div>')
        n_colors += 1
    colors_html.append(f'<h3>{escape(bundle_label(f))} <small>{len(data)}</small></h3><div class="grid sw-grid">{"".join(cells)}</div>')

# --- icons / images --------------------------------------------------------------
icons_html = []
n_icons = 0
for d in sorted(glob.glob(f"{EX}/*/assets/images")):
    files = sorted(p for p in glob.glob(f"{d}/*@2x.png") if not p.endswith("-dark@2x.png"))
    if not files:
        continue
    cells = []
    for p in files:
        name = os.path.basename(p)[:-7]
        dark = p.replace("@2x.png", "-dark@2x.png")
        tpl = "Template" in name or name.endswith("Template")
        img = f'<img loading="lazy" src="{escape(rel(p))}" alt="">'
        if os.path.exists(dark):
            img += f'<img loading="lazy" class="dark-only" src="{escape(rel(dark))}" alt="">'
        cells.append(f'<figure class="ic{" tpl" if tpl else ""}"><div class="well">{img}</div><figcaption>{escape(name)}</figcaption></figure>')
        n_icons += 1
    icons_html.append(f'<h3>{escape(bundle_label(d))} <small>{len(files)}</small></h3><div class="grid ic-grid">{"".join(cells)}</div>')

# app icon
iconset = sorted(glob.glob(f"{EX}/_App/AppIcon.iconset/*.png"), key=os.path.getsize)
app_icon = rel(iconset[-1]) if iconset else ""

# --- fonts --------------------------------------------------------------------------
faces, fonts_html = [], []
font_files = sorted(glob.glob(f"{EX}/*/raw/**/*.[ot]tf", recursive=True))
for i, p in enumerate(font_files):
    fam = f"f{i}"
    fmt = "opentype" if p.endswith(".otf") else "truetype"
    faces.append(f'@font-face{{font-family:"{fam}";src:url("{rel(p)}") format("{fmt}");}}')
    name = os.path.basename(p).rsplit(".", 1)[0]
    if name in ("icomoon", "ionicons"):
        sample = "".join(chr(c) for c in range(0xE000, 0xE030)) if name == "icomoon" else "".join(chr(c) for c in range(0xF100, 0xF130))
    else:
        sample = None
    fonts_html.append(
        f'<div class="font"><div class="fmeta"><b>{escape(name)}</b><code>{escape(bundle_label(p))}</code></div>'
        f'<div class="fs" style="font-family:{fam}" contenteditable spellcheck="false">'
        f'{escape(sample) if sample else "Tabs that tidy themselves. Aa Gg 0123"}</div></div>')

# --- lottie ------------------------------------------------------------------------------
lotties = []
for p in sorted(glob.glob(f"{EX}/*/raw/*.json")):
    try:
        d = json.load(open(p))
    except Exception:
        continue
    if isinstance(d, dict) and "layers" in d:
        dur = (d.get("op", 0) - d.get("ip", 0)) / (d.get("fr") or 30)
        lotties.append({"id": f"l{len(lotties)}", "name": os.path.basename(p)[:-5], "bundle": bundle_label(p),
                        "size": f'{d.get("w")}×{d.get("h")}', "dur": f"{dur:.1f}s", "data": d})
lottie_html = "".join(
    f'<figure class="lot"><div class="well" id="{l["id"]}"></div><figcaption><b>{escape(l["name"])}</b>'
    f'<code>{escape(l["bundle"])} · {l["size"]} · {l["dur"]}</code></figcaption></figure>' for l in lotties)
lottie_data = json.dumps({l["id"]: l["data"] for l in lotties})

# --- media -----------------------------------------------------------------------------------
sounds, videos = [], []
for p in sorted(glob.glob(f"{EX}/*/raw/*")):
    ext = p.rsplit(".", 1)[-1].lower()
    cap = f'<figcaption><b>{escape(os.path.basename(p))}</b><code>{escape(bundle_label(p))} · {os.path.getsize(p) / 1e6:.1f} MB</code></figcaption>'
    if ext in ("wav", "mp3", "m4a"):
        sounds.append(f'<figure class="snd"><audio controls preload="none" src="{escape(rel(p))}"></audio>{cap}</figure>')
    elif ext in ("mp4", "mov"):
        videos.append(f'<figure class="vid"><video controls muted loop playsinline preload="metadata" src="{escape(rel(p))}"></video>{cap}</figure>')

html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Arc Brand Book</title>
<style>
{''.join(faces)}
:root{{--bg:#FAFBFF;--card:#FFFFFF;--ink:#0E0F10;--mut:#6B6F80;--line:rgba(14,15,16,.08);--well:#F1F2F7;--blue:#3139FB}}
:root[data-theme=dark]{{--bg:#0F1117;--card:#171A22;--ink:#EDEEF2;--mut:#9A9EB0;--line:rgba(250,251,255,.08);--well:#232734}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 Inter,-apple-system,system-ui,sans-serif}}
header{{background:linear-gradient(135deg,#FF9396,#0048FF);color:#fff;padding:56px 48px 40px;display:flex;gap:28px;align-items:center}}
header img{{width:112px;height:112px;filter:drop-shadow(0 10px 24px rgba(0,0,0,.25))}}
header h1{{margin:0;font-size:44px;letter-spacing:-.02em}} header p{{margin:6px 0 0;opacity:.9}}
nav{{position:sticky;top:0;z-index:5;display:flex;gap:6px;flex-wrap:wrap;padding:12px 48px;background:color-mix(in srgb,var(--bg) 85%,transparent);backdrop-filter:blur(16px);border-bottom:1px solid var(--line)}}
nav a{{color:var(--ink);text-decoration:none;padding:6px 12px;border-radius:999px;background:var(--well);font-weight:600;font-size:13px}}
nav button{{margin-left:auto;border:0;border-radius:999px;padding:6px 14px;background:var(--blue);color:#fff;font-weight:600;cursor:pointer}}
main{{padding:8px 48px 80px;max-width:1500px}}
h2{{font-size:28px;margin:48px 0 4px;letter-spacing:-.01em}} h2+p{{color:var(--mut);margin:0 0 12px}}
h3{{margin:28px 0 10px;font-size:15px}} small{{color:var(--mut);font-weight:500}}
code{{font:12px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--mut)}}
.grid{{display:grid;gap:10px}}
.sw-grid{{grid-template-columns:repeat(auto-fill,minmax(170px,1fr))}}
.sw{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:10px;display:flex;flex-direction:column;gap:2px;min-width:0}}
.sw b{{font-size:12px;overflow-wrap:anywhere}}
.chip{{display:flex;height:56px;border-radius:10px;overflow:hidden;margin-bottom:6px;background:repeating-conic-gradient(#ddd 0 25%,#fff 0 50%) 0 0/12px 12px}}
.chip span{{flex:1}} .chip .dk{{border-left:1px solid rgba(0,0,0,.06)}}
.ic-grid{{grid-template-columns:repeat(auto-fill,minmax(112px,1fr))}}
figure{{margin:0}} .ic{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:8px}}
.ic .well{{height:84px;border-radius:10px;background:var(--well);display:grid;place-items:center;overflow:hidden}}
.ic img{{max-width:72px;max-height:64px}}
:root[data-theme=dark] .ic.tpl img{{filter:invert(1)}}
.dark-only{{display:none}} :root[data-theme=dark] .ic .dark-only{{display:block}} :root[data-theme=dark] .ic .dark-only~img, :root[data-theme=dark] .ic img:has(+.dark-only){{display:none}}
figcaption{{font-size:11px;margin-top:6px;overflow-wrap:anywhere;display:flex;flex-direction:column;gap:2px}}
.font{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 18px;margin-bottom:8px;display:grid;grid-template-columns:260px 1fr;gap:16px;align-items:center}}
.fmeta{{display:flex;flex-direction:column}} .fs{{font-size:30px;line-height:1.2;outline:none;overflow-wrap:anywhere}}
.lot-grid{{grid-template-columns:repeat(auto-fill,minmax(200px,1fr))}}
.lot{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:10px}}
.lot .well{{aspect-ratio:1;border-radius:10px;background:var(--well)}}
.vid-grid{{grid-template-columns:repeat(auto-fill,minmax(320px,1fr))}}
.vid,.snd{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:10px}}
video{{width:100%;border-radius:10px;background:#000}} audio{{width:100%}}
@media (max-width:700px){{header,nav,main{{padding-left:16px;padding-right:16px}} .font{{grid-template-columns:1fr}}}}
</style></head><body>
<header>{f'<img src="{escape(app_icon)}" alt="">' if app_icon else ''}<div><h1>Arc Brand Book</h1>
<p>Everything visual inside Arc for macOS 1.174.0: {n_colors} colors, {len(font_files)} fonts, {n_icons} images, {len(lotties)} animations, {len(sounds)} sounds, {len(videos)} videos.</p>
<p style="opacity:.75;font-size:12px">Local and private: The Browser Company's artwork, extracted from your own installed copy. Don't publish.</p></div></header>
<nav><a href="#colors">Colors</a><a href="#type">Type</a><a href="#icons">Icons</a><a href="#motion">Motion</a><a href="#sound">Sound</a><a href="#video">Video</a>
<button onclick="toggle()">Light / Dark</button></nav>
<main>
<h2 id="colors">Colors</h2><p>Every named color in every asset catalog. Left half of each chip is light appearance, right half dark.</p>{''.join(colors_html)}
<h2 id="type">Type</h2><p>Every bundled font file. Click a sample to type your own text.</p>{''.join(fonts_html)}
<h2 id="icons">Icons &amp; images</h2><p>Rendered from the asset catalogs. Template icons are tinted at runtime; they invert in dark mode here.</p>{''.join(icons_html)}
<h2 id="motion">Motion</h2><p>Lottie animations, looping.</p><div class="grid lot-grid">{lottie_html}</div>
<h2 id="sound">Sound</h2><p>Everything Arc can play.</p><div class="grid vid-grid">{''.join(sounds)}</div>
<h2 id="video">Video</h2><p>Onboarding and UI loops.</p><div class="grid vid-grid">{''.join(videos)}</div>
</main>
<script src="https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js"></script>
<script>
const LOTTIE = {lottie_data};
function toggle(){{const r=document.documentElement;r.dataset.theme=r.dataset.theme==='dark'?'light':'dark';try{{localStorage.setItem('theme',r.dataset.theme)}}catch(e){{}}}}
try{{const t=localStorage.getItem('theme');if(t)document.documentElement.dataset.theme=t}}catch(e){{}}
window.addEventListener('load',()=>{{ if(!window.lottie) return;
  for(const [id,data] of Object.entries(LOTTIE)) lottie.loadAnimation({{container:document.getElementById(id),renderer:'svg',loop:true,autoplay:true,animationData:data}});
}});
</script>
</body></html>
"""
out = os.path.join(VAULT, "brand-book.html")
open(out, "w").write(html)
print(f"wrote {out}: colors={n_colors} fonts={len(font_files)} images={n_icons} lottie={len(lotties)} sounds={len(sounds)} videos={len(videos)}")
