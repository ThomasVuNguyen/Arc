#!/usr/bin/env bash
# extract-app.sh: archive and take apart an installed copy of Arc.app.
#
# Everything is written under vault/ (gitignored). Nothing here leaves your
# machine. The output is The Browser Company's copyrighted material, kept for
# personal preservation and study. Do not commit or redistribute it.
#
#   vault/app/Arc-<version>.app    byte-for-byte copy of the signed app
#   vault/extracted/meta           Info.plists, entitlements, linked libraries
#   vault/extracted/swift          reconstructed Swift/ObjC interfaces per binary
#   vault/extracted/strings        printable strings from the binaries
#   vault/extracted/bundles/<B>    every resource bundle, with Assets.car unpacked
#   vault/extracted/l10n/<lang>    all localizations converted to JSON
#   vault/extracted/chromium       paks unpacked, Arc mojom headers, DevTools
#
# Requirements: Xcode command line tools (swiftc, assetutil, plutil),
# python3 with `brotli`, and `ipsw` (brew install blacktop/tap/ipsw).
#
# usage: scripts/extract-app.sh [/Applications/Arc.app]
set -euo pipefail

APP="${1:-/Applications/Arc.app}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VAULT="$ROOT/vault"
OUT="$VAULT/extracted"
TOOLS="$ROOT/scripts/tools"
C="$APP/Contents"
CORE="$C/Frameworks/ArcCore.framework/Versions/A"

[[ -d "$C" ]] || { echo "Arc.app not found at $APP" >&2; exit 1; }
command -v ipsw >/dev/null || { echo "missing ipsw: brew install blacktop/tap/ipsw" >&2; exit 1; }

VERSION=$(plutil -extract CFBundleShortVersionString raw "$C/Info.plist")
BUILD=$(plutil -extract CFBundleVersion raw "$C/Info.plist")
echo "Arc $VERSION ($BUILD)"

mkdir -p "$VAULT" && chmod 700 "$VAULT"
mkdir -p "$VAULT/app" "$VAULT/build" "$OUT"/{meta,swift,strings,bundles,l10n,chromium}

# 1. Pristine copy of the app (keeps code signature and xattrs) ---------------
DEST="$VAULT/app/Arc-$VERSION-$BUILD.app"
if [[ ! -d "$DEST" ]]; then
  echo "- copying app bundle"
  ditto "$APP" "$DEST"
fi

# 2. Metadata ------------------------------------------------------------------
echo "- metadata"
plutil -convert json -o "$OUT/meta/Info.json" "$C/Info.plist"
plutil -convert json -o "$OUT/meta/ArcCore-Info.json" "$CORE/Resources/Info.plist"
codesign -d --entitlements - --xml "$APP" 2>/dev/null | plutil -convert json -o "$OUT/meta/entitlements.json" - || true
codesign -dvvv "$APP" > "$OUT/meta/codesign.txt" 2>&1 || true
security cms -D -i "$C/embedded.provisionprofile" > "$OUT/meta/provisionprofile.plist" 2>/dev/null || true
for b in "$C/MacOS/Arc" "$CORE/ArcCore" "$CORE/Libraries/libaperitif.dylib"; do
  n=$(basename "$b")
  otool -L "$b" > "$OUT/meta/linked-$n.txt"
  lipo -info "$b" >> "$OUT/meta/architectures.txt"
done
ls "$C/Frameworks" > "$OUT/meta/frameworks.txt"
ls "$CORE/Helpers" > "$OUT/meta/helpers.txt"
cp "$C/Resources/Arc.sdef" "$OUT/meta/"
cp "$C/Resources/README.md" "$OUT/meta/applescript-README.md"

# 3. Reconstructed interfaces --------------------------------------------------
echo "- swift / objc interfaces"
ipsw swift-dump "$C/MacOS/Arc" --arch arm64 --demangle > "$OUT/swift/Arc.swift" 2>/dev/null || true
ipsw class-dump "$C/MacOS/Arc" --arch arm64 > "$OUT/swift/Arc.objc.h" 2>/dev/null || true
for fw in Lottie Sparkle; do
  bin=$(find "$C/Frameworks/$fw.framework/Versions" -maxdepth 2 -type f -name "$fw" | head -1)
  [[ -n "$bin" ]] && ipsw swift-dump "$bin" --arch arm64 --demangle > "$OUT/swift/$fw.swift" 2>/dev/null || true
done
ipsw class-dump "$CORE/ArcCore" --arch arm64 > "$OUT/swift/ArcCore.objc.h" 2>/dev/null || true
nm -U -arch arm64 "$C/MacOS/Arc" | xcrun swift-demangle > "$OUT/swift/Arc.symbols.txt" || true
nm -gU -arch arm64 "$CORE/ArcCore" > "$OUT/swift/ArcCore.exports.txt" || true
nm -gU -arch arm64 "$CORE/Libraries/libaperitif.dylib" > "$OUT/swift/libaperitif.exports.txt" || true

# 4. Strings ------------------------------------------------------------------
echo "- binary strings"
strings -a -n 6 -arch arm64 "$C/MacOS/Arc" > "$OUT/strings/Arc.txt"
strings -a -n 6 -arch arm64 "$CORE/Libraries/libaperitif.dylib" > "$OUT/strings/libaperitif.txt"
grep -Eo 'https?://[A-Za-z0-9._~:/?#@!$&()*+,;=%-]+' "$OUT/strings/Arc.txt" | sort -u > "$OUT/strings/Arc.urls.txt" || true
grep -Eo 'arc://[A-Za-z0-9._/-]+' "$OUT/strings/Arc.txt" | sort -u > "$OUT/strings/Arc.arc-urls.txt" || true

# 5. Resource bundles + asset catalogs -----------------------------------------
echo "- resource bundles"
CAR="$VAULT/build/car_extract"
[[ -x "$CAR" && "$CAR" -nt "$TOOLS/car_extract.swift" ]] || swiftc -O "$TOOLS/car_extract.swift" -o "$CAR"

extract_bundle () {   # $1 = bundle path (app or .bundle), $2 = resources dir, $3 = out dir
  local bundle="$1" res="$2" dst="$3"
  mkdir -p "$dst"
  # Copy raw resources (Lottie JSON, fonts, sounds, video, html/js/css, svg, ...)
  rsync -a --exclude '*.lproj' --exclude 'Assets.car' --exclude '_CodeSignature' \
        --exclude '*.bundle' --exclude '*.xcprivacy' "$res/" "$dst/raw/" 2>/dev/null || true
  if [[ -f "$res/Assets.car" ]]; then
    assetutil --info "$res/Assets.car" > "$dst/assets-info.json" 2>/dev/null
    "$CAR" "$bundle" "$dst/assets-info.json" "$dst/assets" > "$dst/assets-summary.txt" 2>&1 || true
  fi
  # Base / English strings, converted to JSON
  for lp in "$res/Base.lproj" "$res/en.lproj"; do
    [[ -d "$lp" ]] || continue
    for s in "$lp"/*.strings "$lp"/*.stringsdict; do
      [[ -f "$s" ]] || continue
      mkdir -p "$dst/strings"
      plutil -convert json -o "$dst/strings/$(basename "$s").json" "$s" 2>/dev/null || true
    done
  done
}

extract_bundle "$APP" "$C/Resources" "$OUT/bundles/_App"
for b in "$C"/Resources/*.bundle; do
  name=$(basename "$b" .bundle)
  res="$b/Contents/Resources"; [[ -d "$res" ]] || res="$b"
  extract_bundle "$b" "$res" "$OUT/bundles/$name"
done
extract_bundle "$C/PlugIns/DockTilePlugIn.plugin" "$C/PlugIns/DockTilePlugIn.plugin/Contents/Resources" "$OUT/bundles/_DockTilePlugIn"
cp "$C/Resources/AppIcon.icns" "$OUT/bundles/_App/AppIcon.icns"
iconutil -c iconset "$C/Resources/AppIcon.icns" -o "$OUT/bundles/_App/AppIcon.iconset" 2>/dev/null || true

# 6. Localizations (every language, every bundle) -------------------------------
echo "- localizations"
find "$C/Resources" -name '*.lproj' -type d | while read -r lp; do
  lang=$(basename "$lp" .lproj)
  if [[ "$lp" =~ /Resources/([^/]+)\.bundle/ ]]; then owner="${BASH_REMATCH[1]}"; else owner="_App"; fi
  for s in "$lp"/*.strings "$lp"/*.stringsdict; do
    [[ -f "$s" ]] || continue
    mkdir -p "$OUT/l10n/$lang"
    plutil -convert json -o "$OUT/l10n/$lang/$owner.$(basename "$s").json" "$s" 2>/dev/null || true
  done
done

# 7. Chromium layer -------------------------------------------------------------
echo "- chromium resources"
for p in resources chrome_100_percent chrome_200_percent; do
  python3 -I "$TOOLS/pak_extract.py" "$CORE/Resources/$p.pak" "$OUT/chromium/pak-$p"
done
rsync -a "$CORE/Resources/arc/" "$OUT/chromium/arc-mojom/"
rsync -a "$CORE/Resources/DevTools/" "$OUT/chromium/DevTools/" 2>/dev/null || true
for h in "$CORE"/Helpers/*.app; do
  plutil -convert json -o "$OUT/chromium/helper-$(basename "$h" .app | tr ' ()' '_--').json" "$h/Contents/Info.plist"
done
plutil -convert json -o "$OUT/chromium/en.lproj-locale.json" "$CORE/Resources/en.lproj/locale.pak" 2>/dev/null || true

du -sh "$DEST" "$OUT" | sed 's#'"$ROOT"'/##'
echo "done -> $OUT"
