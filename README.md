<p align="center"><img src="docs/readme/hero.png" alt="Arc Brand Book: colors worth copying, icons worth keeping, type worth setting and motion worth watching, recovered from the last build of a browser that felt like a place." width="100%"></p>

<p align="center">
<a href="#motion">Motion</a> &nbsp;·&nbsp; <a href="#icons">Icons</a> &nbsp;·&nbsp; <a href="#color">Color</a> &nbsp;·&nbsp; <a href="#spaces">Spaces</a> &nbsp;·&nbsp; <a href="#type">Type</a> &nbsp;·&nbsp; <a href="#glyphs">Glyphs</a> &nbsp;·&nbsp; <a href="#how-arc-works">How Arc works</a> &nbsp;·&nbsp; <a href="#keep-your-arc">Keep your Arc</a>
</p>

<br>

Arc for macOS is sunsetting (its own farewell banner says **December 22, 2026**). This repo keeps what made it special: the design, reverse-engineered from the last build (1.174.0, Chromium 158), plus a field guide to how it was built and scripts to save your own Arc before it goes.

<a id="motion"></a>
<p align="center"><img src="docs/readme/header-motion.png" alt="Arc Motion" width="100%"></p>

<p align="center">
<img src="docs/readme/rings.webp" width="32%" alt="Kinetic type rings: Arc phrases rotating on concentric circles">
<img src="docs/readme/halftone.webp" width="32%" alt="Halftone study: Arc wordmark in peach-to-blue dots">
<img src="docs/readme/particles.webp" width="32%" alt="Particle fields on Arc Blue">
<img src="docs/readme/lottiegrid.webp" width="32%" alt="Arc's Library Lottie icons on brand colors">
<img src="docs/readme/tidytabs.webp" width="32%" alt="Tidy Tabs: sidebar rows re-sorting with a spring">
<img src="docs/readme/cmdbar.webp" width="32%" alt="Command Bar typing and suggestions">
<img src="docs/readme/logo.webp" width="32%" alt="The Arc logo, drawn">
<img src="docs/readme/heart.webp" width="32%" alt="Arc updated banner heart">
<img src="docs/readme/spacearc.webp" width="32%" alt="Arc Space gradient drifting">
</p>

<sub>The drawn logo, the Library icons and the update heart are Arc's own Lottie files. The rings, halftone, particles, Tidy Tabs and Command Bar are new studies made for this book.</sub>

<a id="icons"></a>
<p align="center"><img src="docs/readme/header-icons.png" alt="Arc Icons" width="100%"></p>

<p align="center"><img src="docs/readme/iconwall.png" alt="All ten Arc app icons: Original, Canary, Candy, Colorful, Neon, Hologram, Fluted Glass, Schoolbook, Early Birds, Dev" width="100%"></p>

<a id="color"></a>
<p align="center"><img src="docs/readme/header-color.png" alt="Arc Color" width="100%"></p>

<p align="center">
<img src="docs/readme/gradient.png" width="32%" alt="The gradient #FF9396 to #0048FF">
<img src="docs/readme/arcblue.png" width="32%" alt="Arc Blue #3139FB">
<img src="docs/readme/ink.png" width="32%" alt="Ink #0E0F10">
<img src="docs/readme/brand.png" width="32%" alt="Brand colors">
<img src="docs/readme/extended.png" width="32%" alt="Extended brand colors">
<img src="docs/readme/scales.png" width="32%" alt="ARCUI gray and indigo scales, light and dark">
</p>

<sub>All 519 named colors, light and dark, are in <a href="docs/design-tokens.json">docs/design-tokens.json</a>.</sub>

<a id="spaces"></a>
<p align="center"><img src="docs/readme/header-spaces.png" alt="Arc Spaces" width="100%"></p>

<p align="center">
<img src="docs/readme/picker.png" width="32%" alt="Space color picker: Brand, Pastel, Drab and Greyscale presets">
<img src="docs/readme/space-moss.webp" width="32%" alt="Moss Space gradient">
<img src="docs/readme/space-night.webp" width="32%" alt="Night Space gradient">
</p>

<sub>A Space color seeds a 4-tone palette and a 12-role light/dark palette, drawn as a grained gradient by Metal shaders. Details in <a href="docs/design-system.md#2-space-theming">design-system.md</a>.</sub>

<a id="type"></a>
<p align="center"><img src="docs/readme/header-type.png" alt="Arc Type" width="100%"></p>

<p align="center">
<img src="docs/readme/type-eb-garamond.png" width="32%" alt="EB Garamond, Easel fancy">
<img src="docs/readme/type-inter.png" width="32%" alt="Inter, Easel hip">
<img src="docs/readme/type-space-mono.png" width="32%" alt="Space Mono, Easel mono">
</p>

<sub>18 families ship inside Arc, from Space Mono and EB Garamond to ABC Favorit, GT Ultra, Marlin Soft and Klim's Pitch and Söhne.</sub>

<a id="glyphs"></a>
<p align="center"><img src="docs/readme/header-glyphs.png" alt="Arc Glyphs" width="100%"></p>

<p align="center">
<img src="docs/readme/glyphs1.webp" width="32%" alt="Template glyphs tinted in brand colors">
<img src="docs/readme/glyphs2.webp" width="32%" alt="Glyphs on Arc Blue">
<img src="docs/readme/vibrant.webp" width="32%" alt="Easel Vibrant palette">
</p>

<br>

## How Arc works

| | |
|---|---|
| [**Architecture**](docs/architecture.md) | A Swift/AppKit/SwiftUI app that *is* the Chromium browser process (ArcCore.framework). About 235 first-party modules, The Composable Architecture, the Swift↔Chromium bridge, ADK, persistence, AI layering, signing |
| [**Features**](docs/features.md) | Spaces, sidebar, auto-archive, Split View, Little Arc, Peek, Command Bar, Air Traffic Control, Boosts, Easels, Notes, Live Folders, Arc Max, AppleScript, and how each is built |
| [**Data model**](docs/data-model.md) | Every `Storable*.json` file, the sidebar item graph, Codable quirks, window themes, profiles, and sync (CloudKit to end-to-end-encrypted Firestore) |
| [**Design system**](docs/design-system.md) | 519 color tokens, Space theming, typography, icons, springs and Lottie, sound, ARCUI components ([tokens JSON](docs/design-tokens.json)) |
| [**Services & flags**](docs/services-and-flags.md) | Backend hosts, integrations, all 243 feature flags, telemetry, and what breaks when the servers shut down |

<a id="keep-your-arc"></a>

## Keep your Arc

```bash
brew install blacktop/tap/ipsw          # Swift/ObjC interface dumper
python3 -m pip install brotli           # Chromium .pak resources

scripts/backup-user-data.sh             # back up YOUR Arc data (quit Arc first)
scripts/extract-app.sh                  # archive + unpack /Applications/Arc.app
python3 scripts/tools/brand_book.py vault && open vault/brand-book.html
```

- **`backup-user-data.sh`** copies your Arc profile and exports `bookmarks.html` (favorites, Spaces, pinned tabs, folders, archived tabs and tabs recovered from Arc's rolling snapshots), importable into Chrome, Dia, Zen, Firefox, Safari or Brave. You also get history as CSV and your extensions with Web Store links.
- **`extract-app.sh`** keeps a pristine copy of the app and unpacks its interfaces, strings, asset catalogs, fonts, animations, sounds, videos, localizations and Chromium resources.
- **`brand_book.py`** builds the full interactive brand book these images come from: every color, icon, typeface, glyph, animation, sound and video. `scripts/tools/readme_capture.cjs` re-exports the images on this page.

Everything those scripts produce goes to **`vault/`, which is gitignored**. Your data never leaves your machine.

**Before Arc goes away:**

1. Quit Arc and run `scripts/backup-user-data.sh`.
2. Export **passwords** in Arc (Settings → Passwords) and import the CSV elsewhere. The backup keeps them encrypted with your Keychain.
3. **Boosts, Easels and Notes live in Arc's cloud.** Use Arc's own exports (Export All Easels, Notes to zip) and copy any Boost code you love.
4. Keep `vault/app/Arc-1.174.0-91305.app`, the last build.

<sub>Arc and its icons, animations and artwork belong to The Browser Company; they appear here as a tribute and for preservation. Raw binaries, fonts and animation files are not redistributed, and every key or token found in the app is written as <code>&lt;redacted&gt;</code>. No personal data is included.</sub>

<p align="center"><br><sub>Arc, 2022–2026. Kept with love.</sub></p>
