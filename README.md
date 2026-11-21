# Arc

Save everything we can from the Arc browser before it sunsets (Arc's own farewell banner gives **December 22, 2026**).

This repo is a field guide to how Arc for macOS (1.174.0, build 91305, Chromium 158.0.8127.37) is built and how it works, reverse-engineered from the shipping app. It also has scripts to archive the app and back up your own Arc data before it's gone.

## What's here

| Doc | What it covers |
|---|---|
| [docs/architecture.md](docs/architecture.md) | How Arc is built: a Swift/AppKit/SwiftUI app that *is* the Chromium browser process (ArcCore.framework), about 235 first-party modules, The Composable Architecture, `swift-dependencies` clients, the Swift↔Chromium bridge, ADK, persistence, AI layering, third-party stack, signing |
| [docs/features.md](docs/features.md) | How each feature works internally: Spaces, sidebar, auto-archive, Split View, tab groups, Little Arc, Peek, Command Bar, Air Traffic Control, Boosts, Easels, Notes, Live Folders, Arc Max / Browse for Me, PiP, ad blocking, AppleScript, … |
| [docs/data-model.md](docs/data-model.md) | Every `Storable*.json` file Arc writes, the sidebar item graph, Swift Codable encoding quirks, window themes, profiles, and sync (CloudKit to end-to-end-encrypted Firestore) |
| [docs/design-system.md](docs/design-system.md) | Colors (519 light/dark tokens), Space theming and its Metal pipeline, typography, icon inventory, motion (springs and Lottie), sound, ARCUI components |
| [docs/design-tokens.json](docs/design-tokens.json) | Machine-readable color, font and motion tokens |
| [docs/services-and-flags.md](docs/services-and-flags.md) | Backend hosts, integrations, all 243 feature flags, telemetry, internal URLs, and what breaks when the servers shut down |

## Scripts

```bash
brew install blacktop/tap/ipsw          # Swift/ObjC interface dumper
python3 -m pip install brotli           # for Chromium .pak resources

scripts/extract-app.sh                  # archive + take apart /Applications/Arc.app
scripts/backup-user-data.sh             # back up YOUR Arc data (quit Arc first)
```

- **`extract-app.sh`** copies the signed app and extracts reconstructed Swift/ObjC interfaces, binary strings, every asset catalog (images as PNG/PDF, named colors as light/dark JSON), fonts, Lottie animations, sounds, videos, all localizations, Chromium `.pak` resources and Arc's custom mojom interfaces.
- **`backup-user-data.sh`** copies `~/Library/Application Support/Arc` (minus regenerable caches) and Arc's preferences. It then exports:
  - `bookmarks.html`: your favorites, Spaces, pinned tabs, folders, archived tabs, and tabs recovered from Arc's rolling sidebar snapshots. It imports into Chrome, Dia, Zen, Firefox, Safari, Brave and others.
  - `sidebar.json` / `sidebar.md`: the same tree, readable.
  - Per profile: Chromium bookmarks, `history.csv`, and the installed extensions with their Web Store links.
- Tools in `scripts/tools/`: `car_extract.swift` (asset catalogs via public AppKit APIs), `pak_extract.py` (Chromium paks), `export_sidebar.py` (Arc sidebar to bookmarks).

All output goes to **`vault/`, which is gitignored and never committed.**

## What is deliberately *not* in this repo

- **Arc itself:** binaries, icons, fonts, animations, sounds, strings. These are The Browser Company's copyrighted material. The scripts rebuild them locally from your own installed copy, and the docs describe them by name and value only.
- **Personal data:** tabs, history, cookies, accounts, sync state. `vault/user-data/` stays on your machine.
- **Secrets:** every API key, token and DSN found in the binary is written as `<redacted>`.

## Before Arc goes away: checklist

1. Quit Arc and run `scripts/backup-user-data.sh`.
2. **Passwords** stay encrypted with the "Arc Safe Storage" Keychain key, so the backup alone can't move them. Export them in Arc (Settings > Passwords, or `chrome://password-manager`) and import the CSV into your next browser.
3. **Boosts, Easels and Notes live in Arc's cloud** (Firestore and Firebase Storage), not in local files. Use Arc's built-in export options (Export All Easels, Notes export to zip) and copy the code of any Boost you care about.
4. Keep `vault/app/Arc-1.174.0-91305.app`. It's a pristine copy of the last build in case auto-update or removal replaces the installed one.
