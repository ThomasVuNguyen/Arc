#!/usr/bin/env bash
# backup-user-data.sh: back up YOUR Arc data before Arc goes away.
#
# Writes to vault/user-data/ (gitignored, chmod 700). This is private data:
# browsing history, cookies, saved logins, open tabs, account state.
# Never commit it, never share it.
#
#   vault/user-data/Application Support/Arc   Arc's own state + Chromium profiles
#   vault/user-data/Preferences               Arc's NSUserDefaults plists
#   vault/user-data/export/bookmarks.html     sidebar as importable bookmarks
#   vault/user-data/export/sidebar.{json,md}  readable sidebar tree
#   vault/user-data/export/profiles/<P>/      per-profile Chromium bookmarks,
#                                             history CSV, extension list
#
# Saved passwords and cookies stay encrypted with the "Arc Safe Storage" key in
# your login Keychain, so this backup alone can't decrypt them. To move
# passwords, use Arc > Settings > Passwords > Export (or chrome://password-manager
# inside Arc) and import the CSV into your next browser.
#
# usage: scripts/backup-user-data.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$HOME/Library/Application Support/Arc"
DST="$ROOT/vault/user-data"
EXP="$DST/export"

if pgrep -xq Arc; then
  echo "Quit Arc first (its databases are locked/inconsistent while it runs)." >&2
  exit 1
fi
[[ -d "$SRC" ]] || { echo "No Arc data at $SRC" >&2; exit 1; }

mkdir -p "$ROOT/vault" && chmod 700 "$ROOT/vault"
mkdir -p "$DST/Application Support" "$DST/Preferences" "$EXP"
chmod 700 "$DST"

echo "- copying Arc data (skipping regenerable caches)"
rsync -a --delete \
  --exclude 'Cache/' --exclude 'Code Cache/' --exclude 'GPUCache/' --exclude 'DawnGraphiteCache/' \
  --exclude 'DawnWebGPUCache/' --exclude 'GrShaderCache/' --exclude 'ShaderCache/' \
  --exclude 'GraphiteDawnCache/' --exclude 'component_crx_cache/' --exclude 'Safe Browsing/' \
  --exclude 'CertificateRevocation/' --exclude 'OptimizationHints/' --exclude 'WidevineCdm/' \
  --exclude 'OnDeviceHeadSuggestModel/' --exclude 'optimization_guide_*' --exclude 'Singleton*' \
  "$SRC" "$DST/Application Support/"

for p in "$HOME"/Library/Preferences/company.thebrowser.Browser*.plist; do
  [[ -f "$p" ]] && plutil -convert xml1 -o "$DST/Preferences/$(basename "$p")" "$p"
done

echo "- exporting sidebar"
python3 -I "$ROOT/scripts/tools/export_sidebar.py" "$SRC" "$EXP"

echo "- exporting Chromium profiles"
UD="$SRC/User Data"
for prof in "$UD"/Default "$UD"/Profile*; do
  [[ -d "$prof" ]] || continue
  name=$(basename "$prof")
  out="$EXP/profiles/$name"
  mkdir -p "$out"
  [[ -f "$prof/Bookmarks" ]] && cp "$prof/Bookmarks" "$out/Bookmarks.json"
  if [[ -f "$prof/History" ]]; then
    cp "$prof/History" "$out/.History.sqlite"   # copy: never open the live DB
    sqlite3 -header -csv "$out/.History.sqlite" \
      "SELECT datetime(last_visit_time/1000000-11644473600,'unixepoch') AS last_visit, visit_count, title, url
         FROM urls ORDER BY last_visit_time DESC;" > "$out/history.csv"
    rm -f "$out/.History.sqlite"
  fi
  if [[ -d "$prof/Extensions" ]]; then
    for m in "$prof"/Extensions/*/*/manifest.json; do
      [[ -f "$m" ]] || continue
      id=$(basename "$(dirname "$(dirname "$m")")")
      python3 -I -c 'import json,sys; m=json.load(open(sys.argv[1])); print(sys.argv[2]+"\t"+str(m.get("name"))+"\t"+str(m.get("version"))+"\thttps://chromewebstore.google.com/detail/"+sys.argv[2])' "$m" "$id"
    done | sort -u > "$out/extensions.tsv"
  fi
  echo "  $name: $(wc -l < "$out/history.csv" 2>/dev/null || echo 0) history rows, $(wc -l < "$out/extensions.tsv" 2>/dev/null || echo 0) extensions"
done

du -sh "$DST" | sed 's#'"$ROOT"'/##'
echo "done -> $DST"
