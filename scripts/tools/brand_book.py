#!/usr/bin/env python3
"""Build a local Arc brand book from vault/extracted.

The page is laid out like an Arc window: a Space-colored frame with grain, a
sidebar of "pinned" sections, and one white content card. Pick a Space color
and the whole page re-themes, just like switching Spaces.

It references the extracted files by relative path and shows Arc's
copyrighted artwork, so it lives in vault/ and is never published.

usage: brand_book.py <vault-dir>      ->  <vault-dir>/brand-book.html
"""
import glob
import json
import os
import re
import sys

from PIL import Image, ImageFont

VAULT = os.path.abspath(sys.argv[1])
EX = os.path.join(VAULT, "extracted", "bundles")
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brand_book.html")
rel = lambda p: os.path.relpath(p, VAULT)


def label(path):
    b = os.path.relpath(path, EX).split(os.sep)[0]
    return b.split("_", 1)[1] if "_" in b and not b.startswith("_") else b.lstrip("_")


def pixels(path):
    """-> (blank, mono): blank = nothing visible, mono = single-ink glyph to tint."""
    try:
        im = Image.open(path).convert("RGBA")
    except Exception:
        return True, False
    im.thumbnail((64, 64))
    raw = im.tobytes()
    px = [tuple(raw[i:i + 4]) for i in range(0, len(raw), 4) if raw[i + 3] > 40]
    if len(px) < 4:
        return True, False
    spread = sum(max(p[:3]) - min(p[:3]) for p in px) / len(px)
    return False, spread < 14


def humanize(name):
    name = re.sub(r"(Template|Icon|Favicon)$", "", name)
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name).strip() or name


# --- colors ---------------------------------------------------------------------
colors = []
for f in sorted(glob.glob(f"{EX}/*/assets/colors.json")):
    data = json.load(open(f))
    group = []
    for name, v in sorted(data.items()):
        def c(x):
            return [x["hex"], round(float(x["alpha"]), 3)] if x else None
        group.append({"n": name, "l": c(v.get("light")), "d": c(v.get("dark"))})
    def hue_key(c):
        import colorsys
        h = (c["l"] or c["d"] or ["#000000", 1])[0]
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
        hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
        return (0, ll, 0) if ss < .12 or ll < .04 or ll > .97 else (1, round(hh * 12), ll)
    group.sort(key=hue_key)
    colors.append({"bundle": label(f), "colors": group})

# --- images ---------------------------------------------------------------------------
meta = {}
for f in glob.glob(f"{EX}/*/assets-info.json"):
    for a in json.load(open(f))[1:]:
        n = a.get("Name")
        if not n:
            continue
        m = meta.setdefault((label(f), n), {"w": 0, "tpl": False})
        m["w"] = max(m["w"], int(a.get("PixelWidth", 0) or 0))
        m["tpl"] |= a.get("Template Mode") == "template" or n.endswith("Template")

app_icons, dia_icons, art, glyphs, marks = [], [], [], [], []
seen_names = set()
APP_ORDER = ["AppIconOriginal", "AppIconCanary", "AppIconCandy", "AppIconColorful", "AppIconNeon", "AppIconHologram",
             "AppIconFlutedGlass", "AppIconSchoolbook", "AppIconEarlyBirds", "AppIconDev"]
for d in sorted(glob.glob(f"{EX}/*/assets/images")):
    b = label(d)
    for p in sorted(glob.glob(f"{d}/*@2x.png")):
        if p.endswith("-dark@2x.png"):
            continue
        name = os.path.basename(p)[:-7]
        dark = p.replace("@2x.png", "-dark@2x.png")
        item = {"n": name, "h": humanize(name), "src": rel(p), "b": b}
        if os.path.exists(dark):
            item["dark"] = rel(dark)
        m = meta.get((b, name), {"w": 0, "tpl": name.endswith("Template")})
        if name in seen_names and (name in APP_ORDER or name.startswith("DiaAppIcon")):
            continue
        seen_names.add(name)
        if name in APP_ORDER:
            item["h"] = humanize(name.replace("AppIcon", "")).replace("Fluted Glass", "Fluted Glass")
            app_icons.append(item)
        elif re.fullmatch(r"DiaAppIcon\w*", name):
            item["h"] = "Dia " + humanize(name.replace("DiaAppIcon", "")) if name != "DiaAppIcon" else "Dia"
            dia_icons.append(item)
        elif name.startswith(("AppIcon", "ZZZZ")):
            continue
        else:
            blank, mono = pixels(p)
            if blank or re.search(r"^Shape\d*$|Mask|Cutout|Backdrop|Placeholder|Scrim|Shadow", name):
                continue
            if "Preview" in name or "Thumbnail" in name or m["w"] >= 400:
                art.append(item)
            elif mono:
                item["mono"] = True
                glyphs.append(item)
            else:
                marks.append(item)
app_icons.sort(key=lambda x: APP_ORDER.index(x["n"]))
art.sort(key=lambda x: ("Preview" not in x["n"], x["h"]))
iconset = sorted(glob.glob(f"{EX}/_App/AppIcon.iconset/*.png"), key=os.path.getsize)

# --- fonts ---------------------------------------------------------------------------------
FOUNDRY = [("ABC", "Dinamo"), ("GT", "Grilli Type"), ("Marlin", "Fontmesa"), ("National", "Klim · trial"),
           ("Söhne Breit", "Klim"), ("Sohne Breit", "Klim"), ("Söhne", "Klim · trial"), ("Soehne", "Klim · trial"),
           ("Pitch", "Klim"), ("Inter", "Open source"), ("EB Garamond", "Open source"), ("Space Mono", "Open source"),
           ("Nunito", "Open source"), ("Inconsolata", "Open source")]
WEIGHTS = [("thin", 100), ("hairline", 100), ("extralight", 200), ("ultralight", 200), ("leicht", 300), ("light", 300),
           ("book", 400), ("buch", 400), ("regular", 400), ("medium", 500), ("semibold", 600), ("halbfett", 600),
           ("dreiviertelfett", 700), ("extrabold", 800), ("extrafett", 800), ("bold", 700), ("black", 900), ("ultra", 900)]
families, font_faces = {}, []
for i, p in enumerate(sorted(glob.glob(f"{EX}/*/raw/**/*.[ot]tf", recursive=True))):
    base = os.path.basename(p).rsplit(".", 1)[0]
    if base in ("icomoon", "ionicons"):
        continue
    try:
        fam, style = ImageFont.truetype(p, 12).getname()
    except Exception:
        fam, style = base, "Regular"
    fam = fam.replace(" Test", "")
    fam = re.sub(r"^S\W?o?e?hne|^S.hne", "Söhne", fam)   # legacy-encoded "ö" in the name table
    s = style.lower().replace(" ", "").replace("-", "")
    w = next((v for k, v in WEIGHTS if k in s), 400)
    alias = f"bb{i}"
    font_faces.append({"alias": alias, "src": rel(p), "fmt": "opentype" if p.endswith(".otf") else "truetype"})
    families.setdefault(fam, []).append({"alias": alias, "style": style, "w": w, "it": "italic" in s or "kursiv" in s})
type_families = []
for fam, styles in sorted(families.items()):
    styles.sort(key=lambda x: (x["it"], x["w"]))
    regular = min((s for s in styles if not s["it"]), key=lambda s: abs(s["w"] - 500), default=styles[0])
    foundry = next((f for k, f in FOUNDRY if fam.startswith(k)), "")
    type_families.append({"family": fam, "foundry": foundry, "styles": styles, "main": regular["alias"]})
EASEL = {"Space Mono": "Easel · mono", "EB Garamond": "Easel · fancy", "Inter": "Easel · hip"}
for t in type_families:
    t["role"] = EASEL.get(t["family"], "")


def ui_font(prefix, want):
    """alias of a bundled file to style the page itself."""
    for t in type_families:
        if t["family"].startswith(prefix):
            for s in t["styles"]:
                if s["w"] == want and not s["it"]:
                    return s["alias"]
    return None


# --- motion & media ------------------------------------------------------------------------------
lotties = []
PURPOSE = {"logo-wave": "The Arc logo, drawn", "archive": "Library · Archive", "boosts": "Library · Boosts",
           "downloads": "Library · Downloads", "easels": "Library · Easels", "screenshots": "Library · Screenshots",
           "spaces": "Library · Spaces", "sun": "Light theme", "moon": "Dark theme", "automatic": "Automatic theme",
           "update-heart-animation": "“Arc updated” banner", "smiley": "Settings"}
for p in sorted(glob.glob(f"{EX}/*/raw/*.json")):
    try:
        d = json.load(open(p))
    except Exception:
        continue
    if isinstance(d, dict) and "layers" in d:
        n = os.path.basename(p)[:-5]
        lotties.append({"n": n, "h": PURPOSE.get(n, n), "dur": round((d["op"] - d["ip"]) / d["fr"], 1), "data": d})
order = ["logo-wave", "spaces", "archive", "easels", "boosts", "downloads", "screenshots", "sun", "moon", "automatic",
         "update-heart-animation", "smiley"]
lotties.sort(key=lambda l: order.index(l["n"]) if l["n"] in order else 99)

SOUND = {"capture": "Capture shutter", "event": "Event chime", "intro-music": "Onboarding music"}
VIDEO = {"pinning": "Pinning tabs", "space_swiping": "Swiping between Spaces", "new_tab": "New tab",
         "split_view": "Split View", "demo": "Sign-in demo", "orb": "Orb", "background": "Background loop"}
sounds, videos = [], []
for p in sorted(glob.glob(f"{EX}/*/raw/*")):
    stem, ext = os.path.splitext(os.path.basename(p))
    if ext.lower() in (".wav", ".mp3", ".m4a"):
        sounds.append({"h": SOUND.get(stem, stem), "src": rel(p)})
    elif ext.lower() in (".mp4", ".mov"):
        videos.append({"h": VIDEO.get(stem, stem), "src": rel(p), "big": os.path.getsize(p) > 1e6})
videos.sort(key=lambda v: not v["big"])

DATA = {
    "version": "1.174.0", "build": "91305",
    "appIcon": rel(iconset[-1]) if iconset else None,
    "colors": colors, "appIcons": app_icons, "diaIcons": dia_icons, "art": art, "glyphs": glyphs, "marks": marks,
    "fonts": font_faces, "type": type_families, "lottie": lotties, "sounds": sounds, "videos": videos,
    "ui": {"display": ui_font("Marlin Soft SQ", 700) or ui_font("Marlin", 700),
           "displayBlack": ui_font("Marlin Soft SQ", 900) or ui_font("Marlin Soft SQ", 800),
           "mono": ui_font("ABC Favorit Mono", 400), "body": ui_font("Inter", 400),
           "bodyMedium": ui_font("Inter", 500), "bodySemi": ui_font("Inter", 600)},
    "counts": {"colors": sum(len(g["colors"]) for g in colors),
               "fonts": len(font_faces), "families": len(type_families),
               "images": len(app_icons) + len(dia_icons) + len(art) + len(glyphs) + len(marks),
               "lottie": len(lotties), "sounds": len(sounds), "videos": len(videos)},
}

html = open(TEMPLATE).read().replace("/*__DATA__*/null", json.dumps(DATA, ensure_ascii=False))
out = os.path.join(VAULT, "brand-book.html")
open(out, "w").write(html)
print(f"wrote {out}", DATA["counts"], f"app={len(app_icons)} dia={len(dia_icons)} art={len(art)} glyphs={len(glyphs)} marks={len(marks)}")
