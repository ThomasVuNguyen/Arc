#!/usr/bin/env python3
"""Draw the README brand-brief boards from docs/design-tokens.json.

Every board is drawn from token *values* (hex colors, names, sizes). No Arc
artwork is copied: icons, logos and commercial fonts stay in vault/.
Type specimens are rendered only from the SIL Open Font License families Arc
bundles (Space Mono, EB Garamond, Inter, Nunito, Inconsolata).

usage: brand_board.py <design-tokens.json> <out-dir> [<fonts-dir>]
"""
import json
import os
import sys
from html import escape

TOK = json.load(open(sys.argv[1]))
OUT = sys.argv[2]
FONTS = sys.argv[3] if len(sys.argv) > 3 else None
os.makedirs(OUT, exist_ok=True)

C = TOK["color"]
SANS = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'SF Mono', 'Space Mono', Menlo, Consolas, monospace"
PAPER, INK, MUTED, BLUE = "#FAFBFF", "#0E0F10", "#6B6F80", "#3139FB"
W = 1200


def col(module, name, mode="light"):
    v = C[module][name]
    return v if isinstance(v, str) else v[mode]


def rgba(hex_):
    h = hex_.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    return r, g, b, a


def fill(hex_):
    r, g, b, a = rgba(hex_)
    return f'fill="#{hex_.lstrip("#")[:6]}"' + (f' fill-opacity="{a:.2f}"' if a < 1 else "")


def on(hex_, bg=(250, 251, 255)):
    """Readable text color over a (possibly translucent) swatch."""
    r, g, b, a = rgba(hex_)
    r, g, b = (r * a + bg[0] * (1 - a), g * a + bg[1] * (1 - a), b * a + bg[2] * (1 - a))
    lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    return INK if lum > 0.55 else "#FFFFFF"


def short(hex_):
    r, g, b, a = rgba(hex_)
    s = "#" + hex_.lstrip("#")[:6].upper()
    return s if a >= 1 else f"{s} · {round(a * 100)}%"


def svg(name, h, body, bg=PAPER):
    doc = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}">'
           f'<rect width="{W}" height="{h}" rx="24" fill="{bg}"/>{body}</svg>\n')
    open(os.path.join(OUT, name), "w").write(doc)
    print("wrote", name)


def text(x, y, s, size=14, color=INK, weight=400, family=SANS, anchor="start", opacity=1):
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'fill="{color}" text-anchor="{anchor}" opacity="{opacity}">{escape(s)}</text>')


def header(title, sub):
    return text(48, 64, title, 28, INK, 700) + text(48, 92, sub, 15, MUTED)


def swatch_row(items, x0, y0, sw, sh, gap=12, labels=True):
    """items: [(label, hex)]"""
    out = []
    for i, (label, hx) in enumerate(items):
        x = x0 + i * (sw + gap)
        out.append(f'<rect x="{x}" y="{y0}" width="{sw}" height="{sh}" rx="14" {fill(hx)} '
                   f'stroke="#0E0F10" stroke-opacity="0.08"/>')
        if labels:
            t = on(hx)
            out.append(text(x + 12, y0 + sh - 30, label, 13, t, 600))
            out.append(text(x + 12, y0 + sh - 12, short(hx), 12, t, 400, MONO, opacity=0.85))
    return "".join(out)


# --- 1. hero -------------------------------------------------------------------
def hero():
    peach, blue = TOK["colorAliases"]["gradientPeach"], TOK["colorAliases"]["gradientBlue"]
    h = 420
    body = f'''
<defs>
  <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{peach}"/><stop offset="1" stop-color="{blue}"/>
  </linearGradient>
  <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch"/>
    <feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.10 0"/></filter>
</defs>
<rect width="{W}" height="{h}" rx="24" fill="url(#g)"/>
<rect width="{W}" height="{h}" rx="24" filter="url(#grain)"/>
{text(64, 120, "ARC FOR MACOS · BRAND BRIEF", 15, "#FFFFFF", 700, opacity=0.85)}
{text(64, 210, "A browser that", 64, "#FFFFFF", 800)}
{text(64, 284, "felt like a place.", 64, "#FFFFFF", 800)}
{text(64, 350, "Colors, type, motion and sound, reconstructed from build 1.174.0 (91305).", 18, "#FFFFFF", 500, opacity=0.9)}
{text(W - 64, 350, f"{peach} → {blue}", 15, "#FFFFFF", 500, MONO, "end", 0.85)}
'''
    svg("hero.svg", h, body, bg=blue)


# --- 2. core palette -------------------------------------------------------------
def core():
    a = TOK["colorAliases"]
    def v(k):
        x = a[k]
        return x["value"] if isinstance(x, dict) else x
    rows = [
        [("Arc Blue", v("arcBlue")), ("Hover", v("arcBlueHover")), ("Pressed", v("arcBluePressed")),
         ("Focus Ring", v("focusRing")), ("Loading · light", v("loadingBorderLight")), ("Loading · dark", v("loadingBorderDark"))],
        [("Popover Light", v("popoverLight")), ("Ink", v("inkDark")), ("Navy", v("navyDark")),
         ("Popover Dark", v("popoverDark")), ("Notes Ink", v("notesInk")), ("Notes Title", v("notesTitle"))],
        [("Gradient Peach", v("gradientPeach")), ("Gradient Blue", v("gradientBlue")), ("Destructive", v("destructive")),
         ("Destructive Hover", v("destructiveHover")), ("Error · light", "#C93333"), ("Error · dark", "#FF5A5F")],
    ]
    sw, sh, gap = 172, 120, 12
    body = header("Core palette", "The values that recur across Arc's 30 asset catalogs. Arc Blue appears in 21 color slots.")
    for i, r in enumerate(rows):
        body += swatch_row(r, 48, 124 + i * (sh + 20), sw, sh, gap)
    svg("palette-core.svg", 124 + 3 * (sh + 20) + 28, body)


# --- 3. brand palette --------------------------------------------------------------
def brand():
    b = C["BaseAssets"]
    names = ["Blue", "Red", "Yellow", "Green", "LightGreen", "LightBlue", "Magenta", "Gray"]
    primary = [(n, col("BaseAssets", "Brand" + n)) for n in names]
    ext = [(n, col("BaseAssets", "BrandExtended" + n)) for n in
           ["Cream", "LightPink", "Purple", "Orange", "Teal", "BlueGray", "Navy", "Brown", "BrownPink", "VibrantRed"]]
    body = header("Brand colors", "8 brand colors and 10 extended ones (BaseAssets › Brand*, BrandExtended*). Several are authored in Display P3.")
    body += swatch_row(primary, 48, 124, 128, 150, 9)
    body += text(48, 312, "EXTENDED", 12, MUTED, 700)
    body += swatch_row(ext, 48, 326, 100, 120, 10.4)
    svg("palette-brand.svg", 476, body)


# --- 4. space color picker ----------------------------------------------------------
def space_picker():
    groups = TOK["spaceTheme"]["pickerPresetGroups"]
    body = header("Space color picker", "The four preset rows of the Space style editor. Each pick seeds a 4-tone palette and a 12-role light/dark palette.")
    y = 128
    for g, keys in groups.items():
        body += text(48, y + 40, g.capitalize(), 16, INK, 700)
        for i, k in enumerate(keys):
            hx = col("BaseAssets", k)
            cx = 230 + i * 104
            body += f'<circle cx="{cx}" cy="{y + 34}" r="34" {fill(hx)} stroke="#0E0F10" stroke-opacity="0.10"/>'
            body += text(cx, y + 92, short(hx), 11, MUTED, 400, MONO, "middle")
        y += 120
    # palette roles
    roles = TOK["spaceTheme"]
    body += text(48, y + 26, "Derived tones", 13, MUTED, 700)
    body += text(48, y + 50, "  ·  ".join(roles["primaryColorPalette"]), 15, INK, 500, MONO)
    body += text(48, y + 80, "Overlays", 13, MUTED, 700)
    body += text(48, y + 104, "  ·  ".join(roles["overlay"]), 15, INK, 500, MONO)
    body += text(48, y + 134, "Gradient wheel", 13, MUTED, 700)
    body += text(48, y + 158, "  ·  ".join(roles["gradientWheel"]), 15, INK, 500, MONO)
    svg("space-picker.svg", y + 190, body)


# --- 5. scales ------------------------------------------------------------------------
def scales():
    body = header("Gray & Indigo scales", "ARCUI ships 12-step scales. Gray tracks Radix Colors step for step; Indigo is built around Arc Blue at step 9.")
    sw, sh, gap = 76, 72, 8   # 160 + 12 * 84 = 1168 < W
    y = 124
    for scale in ["Gray", "Indigo"]:
        for mode in ["light", "dark"]:
            items = [(str(i), col("ARCUI", f"{scale}{i}", mode)) for i in range(1, 13)]
            body += text(48, y + 44, f"{scale}", 15, INK, 700) + text(48, y + 62, mode, 12, MUTED)
            for i, (lab, hx) in enumerate(items):
                x = 160 + i * (sw + gap)
                body += f'<rect x="{x}" y="{y}" width="{sw}" height="{sh}" rx="10" {fill(hx)} stroke="#0E0F10" stroke-opacity="0.06"/>'
                body += text(x + 8, y + 20, lab, 12, on(hx), 700)
                body += text(x + 8, y + sh - 10, short(hx), 10, on(hx), 400, MONO, opacity=0.85)
            y += sh + 14
        y += 12
    svg("scales.svg", y + 20, body)


# --- 6. easel palettes ---------------------------------------------------------------------
def easel():
    keys = ["Black", "Grey", "Yellow", "Pink", "Red", "Purple", "LightBlue", "DarkBlue", "LightGreen", "DarkGreen"]
    body = header("Easel palettes", "Two named sets, Vibrant and Chill, used for Easel shapes, ink and text. Black/White invert in dark mode.")
    y = 128
    for pal in ["Vibrant", "Chill"]:
        body += text(48, y + 56, pal, 18, INK, 700)
        for i, k in enumerate(keys):
            hx = col("BaseAssets", f"{pal}.Easel{k}")
            x = 180 + i * 96
            body += f'<rect x="{x}" y="{y}" width="84" height="84" rx="42" {fill(hx)} stroke="#0E0F10" stroke-opacity="0.08"/>'
            body += text(x + 42, y + 106, k, 12, INK, 600, anchor="middle")
            body += text(x + 42, y + 124, short(hx), 10, MUTED, 400, MONO, "middle")
        y += 156
    svg("easel-palettes.svg", y + 8, body)


# --- 7. window anatomy mock -------------------------------------------------------------------
def window():
    """An illustrative window built only from token values (not a screenshot)."""
    h = 640
    s1, s2 = col("BaseAssets", "ColorPickerBrand2"), col("BaseAssets", "ColorPickerBrand8")
    item = "#FFFFFF"
    pad = 28
    sx, sy, sw = 48, 48, 300
    rows = [("Inbox", 0.0), ("Design review", 0.85), ("Release notes", 0.0), ("Recipes", 0.0)]
    body = f'''
<defs>
  <linearGradient id="sp" x1="0" y1="0" x2="0.4" y2="1"><stop offset="0" stop-color="{s1}"/><stop offset="1" stop-color="{s2}"/></linearGradient>
  <filter id="gr"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" stitchTiles="stitch"/>
    <feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.10 0"/></filter>
  <filter id="sh" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="6" stdDeviation="12" flood-color="#0E0F10" flood-opacity="0.18"/></filter>
</defs>
<rect x="24" y="24" width="{W-48}" height="{h-48}" rx="22" fill="url(#sp)"/>
<rect x="24" y="24" width="{W-48}" height="{h-48}" rx="22" filter="url(#gr)"/>
'''
    # traffic lights
    for i, c in enumerate(["#FF5F57", "#FEBC2E", "#28C840"]):
        body += f'<circle cx="{sx + 16 + i * 20}" cy="{sy + 18}" r="6" fill="{c}"/>'
    # url pill
    body += f'<rect x="{sx}" y="{sy + 44}" width="{sw - pad}" height="40" rx="12" fill="{item}" fill-opacity="0.32"/>'
    body += text(sx + 16, sy + 69, "arc.net", 14, INK, 500, opacity=0.7)
    # favorites grid
    for i in range(4):
        fx = sx + i * ((sw - pad) / 4)
        body += f'<rect x="{fx}" y="{sy + 100}" width="{(sw - pad) / 4 - 8}" height="56" rx="12" fill="{item}" fill-opacity="0.32"/>'
        body += f'<circle cx="{fx + ((sw - pad) / 4 - 8) / 2}" cy="{sy + 128}" r="10" fill="{INK}" fill-opacity="0.55"/>'
    # pinned label + rows
    body += text(sx + 6, sy + 192, "Pinned", 12, INK, 600, opacity=0.55)
    for i, (label, a) in enumerate(rows):
        ry = sy + 204 + i * 42
        if a:
            body += f'<rect x="{sx}" y="{ry}" width="{sw - pad}" height="36" rx="10" fill="#FFFFFF" fill-opacity="{a}" filter="url(#sh)"/>'
        body += f'<rect x="{sx + 12}" y="{ry + 11}" width="14" height="14" rx="4" fill="{INK}" fill-opacity="0.5"/>'
        body += text(sx + 36, ry + 23, label, 14, INK, 500 if a else 400, opacity=0.9 if a else 0.72)
    # divider + today
    body += f'<rect x="{sx + 4}" y="{sy + 384}" width="{sw - pad - 8}" height="1" fill="{INK}" fill-opacity="0.12"/>'
    body += text(sx + 6, sy + 410, "+ New Tab", 14, INK, 400, opacity=0.6)
    body += f'<rect x="{sx}" y="{sy + 424}" width="{sw - pad}" height="36" rx="10" fill="{INK}" fill-opacity="0.05"/>'
    body += text(sx + 36, sy + 447, "Hovered tab", 14, INK, 400, opacity=0.72)
    # space dots
    for i in range(4):
        body += f'<circle cx="{sx + (sw - pad) / 2 - 36 + i * 24}" cy="{h - 72}" r="{5 if i else 6}" fill="{INK}" fill-opacity="{0.75 if i == 0 else 0.25}"/>'
    # content card
    cx, cy = sx + sw, 40
    body += f'<rect x="{cx}" y="{cy}" width="{W - cx - 40}" height="{h - 80}" rx="12" fill="#FFFFFF" filter="url(#sh)"/>'
    body += text(cx + 48, cy + 96, "Your Space's color is the window.", 30, INK, 700)
    body += text(cx + 48, cy + 132, "The sidebar has no fill of its own: tabs are white or ink at low alpha,", 16, MUTED)
    body += text(cx + 48, cy + 156, "so the Space gradient (plus grain) shows through everything.", 16, MUTED)
    notes = [("Current tab", "#FFFFFF · 85%"), ("Hovered tab", "#0E0F10 · 10%"), ("Sidebar item", "#0E0F10 · 5%"),
             ("Space theme", f"{s1} → {s2}"), ("Content corner", "rounded, inset from window"), ("Overlay", "grain / sand / denim / tweed")]
    for i, (k, v) in enumerate(notes):
        y = cy + 216 + i * 46
        body += f'<rect x="{cx + 48}" y="{y - 22}" width="{W - cx - 136}" height="36" rx="10" fill="{PAPER}"/>'
        body += text(cx + 64, y + 2, k, 14, INK, 600) + text(W - 104, y + 2, v, 13, MUTED, 400, MONO, "end")
    body += text(W - 56, h - 44, "Illustration drawn from tokens, not a screenshot", 11, "#FFFFFF", 500, anchor="end", opacity=0.85)
    svg("window-anatomy.svg", h, body, bg=s2)


# --- 8. type specimens (OFL fonts only) ---------------------------------------------------------
def specimens():
    if not FONTS or not os.path.isdir(FONTS):
        print("skip specimens: no fonts dir (run scripts/extract-app.sh first)")
        return
    from PIL import Image, ImageDraw, ImageFont

    S = 2  # retina
    specs = [
        ("mono", "Space Mono", "SpaceMono-Bold.ttf", "SpaceMono-Regular.ttf", None, "Easel › mono · line-height 1.48"),
        ("fancy", "EB Garamond", "EBGaramond-VariableFont_wght.ttf", "EBGaramond-VariableFont_wght.ttf", (b"SemiBold", b"Regular"), "Easel › fancy · line-height 1.32"),
        ("hip", "Inter", "Inter-Bold.ttf", "Inter-Regular.ttf", None, "Easel › hip · line-height 1.28"),
        ("display", "Nunito", "Nunito-Black.ttf", "Nunito-Regular.ttf", None, "FontsManager · referenced in code (Nunito-Bold)"),
        ("code", "Inconsolata", "Inconsolata-Bold.ttf", "Inconsolata-Regular.ttf", None, "FontsManager · chrome-font experiment option"),
    ]
    w, h = W * S, 300 * S
    for key, family, bold_f, reg_f, var, note in specs:
        bp, rp = os.path.join(FONTS, bold_f), os.path.join(FONTS, reg_f)
        if not (os.path.exists(bp) and os.path.exists(rp)):
            print("skip", family)
            continue
        img = Image.new("RGB", (w, h), PAPER)
        d = ImageDraw.Draw(img)
        big = ImageFont.truetype(bp, 84 * S)
        mid = ImageFont.truetype(bp, 30 * S)
        body = ImageFont.truetype(rp, 18 * S)
        label = ImageFont.truetype(os.path.join(FONTS, "Inter-Bold.ttf"), 13 * S)
        small = ImageFont.truetype(os.path.join(FONTS, "Inter-Regular.ttf"), 13 * S)
        if var:
            try:
                big.set_variation_by_name(var[0]); mid.set_variation_by_name(var[0]); body.set_variation_by_name(var[1])
            except Exception:
                pass
        d.rounded_rectangle((0, 0, w - 1, h - 1), 24 * S, fill=PAPER)
        d.text((48 * S, 34 * S), key.upper(), font=label, fill=BLUE)
        d.text((48 * S + d.textlength(key.upper() + "   ", font=label), 34 * S), f"{family} · {note}", font=small, fill=MUTED)
        d.text((44 * S, 62 * S), "Aa Gg 1234", font=big, fill=INK)
        d.text((48 * S, 180 * S), "Tabs that tidy themselves.", font=mid, fill=INK)
        d.text((48 * S, 228 * S), "The quick brown fox jumps over the lazy dog — 0123456789 ?!&@", font=body, fill="#3B3F4C")
        img = img.resize((W, 300), Image.LANCZOS) if False else img
        img.save(os.path.join(OUT, f"type-{key}.png"), optimize=True)
        print("wrote", f"type-{key}.png")


for f in (hero, core, brand, space_picker, scales, easel, window, specimens):
    f()
