#!/usr/bin/env python3
"""Export Arc's sidebar (spaces, favorites, pinned tabs, folders, archive) to
formats other browsers and tools understand.

Reads the Storable*.json files in Arc's data directory and writes:

  bookmarks.html   Netscape bookmark file. Imports into Chrome, Dia, Zen,
                   Firefox, Safari, Brave, Edge, Orion, ...
  sidebar.json     clean, readable tree: spaces > sections > folders > tabs
  sidebar.md       the same tree as a Markdown outline

Arc stores everything as Swift Codable JSON. Two encoding quirks to know:
  * enum cases with payloads are {"caseName": {"_0": payload}}
  * dictionaries and some ordered collections are flat [key, value, key, value]

usage: export_sidebar.py <arc-data-dir> <out-dir>
       (arc-data-dir defaults to ~/Library/Application Support/Arc)
"""
import glob
import html
import json
import os
import sys
from datetime import datetime, timezone

APPLE_EPOCH = 978307200  # 2001-01-01, Foundation's reference date


def pairs(flat):
    """[k1, v1, k2, v2] -> [(k1, v1), (k2, v2)]"""
    return list(zip(flat[0::2], flat[1::2]))


def case(enum_obj):
    """{"tab": {...}} -> ("tab", {...})"""
    if isinstance(enum_obj, dict) and len(enum_obj) == 1:
        k = next(iter(enum_obj))
        return k, enum_obj[k]
    return None, enum_obj


def ts(apple_seconds):
    if apple_seconds is None:
        return None
    return int(apple_seconds + APPLE_EPOCH)


def iso(unix):
    return datetime.fromtimestamp(unix, timezone.utc).isoformat() if unix else None


class Sidebar:
    def __init__(self, storable):
        containers = storable["sidebar"]["containers"]
        main = next(c for c in containers if isinstance(c, dict) and "items" in c)
        self.items = {}
        for v in main.get("items", []):
            if isinstance(v, dict) and "id" in v:
                self.items[v["id"]] = v
        self.spaces = [s for s in main.get("spaces", []) if isinstance(s, dict)]
        self.top_apps = pairs(main.get("topAppsContainerIDs", []))

    def node(self, item_id, seen=None):
        """Convert one sidebar item (and its children) to a plain dict."""
        seen = seen or set()
        if item_id in seen or item_id not in self.items:
            return None
        seen.add(item_id)
        it = self.items[item_id]
        kind, data = case(it.get("data", {}))
        children = [n for n in (self.node(c, seen) for c in it.get("childrenIds", [])) if n]
        out = {"type": kind, "created": iso(ts(it.get("createdAt")))}

        if kind == "tab":
            out["title"] = it.get("title") or data.get("savedTitle") or data.get("savedURL")
            out["url"] = data.get("savedURL")
            if it.get("title") and data.get("savedTitle") and it["title"] != data["savedTitle"]:
                out["pageTitle"] = data["savedTitle"]
        elif kind in ("list", "tabGroup", "splitView", "itemContainer"):
            out["title"] = it.get("title") or {"splitView": "Split View", "tabGroup": "Tab Group"}.get(kind, "Folder")
            out["children"] = children
        elif kind in ("easel", "arcDocument", "sharedObject"):
            out["title"] = it.get("title") or (data or {}).get("title") or kind
            out["note"] = f"Arc {kind}: content lives in Arc's cloud / local store, not a URL"
            if children:
                out["children"] = children
        else:
            out["title"] = it.get("title") or kind
            if children:
                out["children"] = children
        return out

    def container_children(self, container_id):
        n = self.node(container_id)
        return (n or {}).get("children", [])

    def tree(self):
        spaces = []
        for sp in self.spaces:
            sections = {}
            for label, cid in pairs(sp.get("containerIDs", [])):
                name = label if isinstance(label, str) else case(label)[0]
                sections[name] = self.container_children(cid)
            spaces.append({
                "id": sp.get("id"),
                "title": sp.get("title") or "Untitled Space",
                "pinned": sections.get("pinned", []),
                "today": sections.get("unpinned", []),
            })
        favorites = []
        for label, cid in self.top_apps:
            k, payload = case(label)
            name = "Favorites" if k == "default" else "Favorites (other profile)"
            favorites.append({"title": name, "children": self.container_children(cid)})
        return {"favorites": favorites, "spaces": spaces}


def walk_urls(nodes):
    for n in nodes:
        if n.get("url"):
            yield n["url"]
        yield from walk_urls(n.get("children", []))


def archive(data_dir):
    path = os.path.join(data_dir, "StorableArchiveItems.json")
    if not os.path.exists(path):
        return []
    out = []
    for entry in json.load(open(path)).get("items", []):
        if not isinstance(entry, dict):
            continue
        it = entry.get("sidebarItem", {})
        kind, data = case(it.get("data", {}))
        if kind == "tab" and data.get("savedURL"):
            out.append({"type": "tab", "title": it.get("title") or data.get("savedTitle") or data["savedURL"],
                        "url": data["savedURL"], "archived": iso(ts(entry.get("archivedAt"))),
                        "reason": entry.get("reason")})
    out.sort(key=lambda x: x.get("archived") or "", reverse=True)
    return out


def from_snapshots(data_dir, known):
    """Tabs that appear in Arc's rolling StorableSidebar.<date>.json backups
    but are no longer in the live sidebar."""
    found = {}
    for f in sorted(glob.glob(os.path.join(data_dir, "StorableSidebar.*.json"))):
        try:
            sb = Sidebar(json.load(open(f)))
        except Exception:
            continue
        for it in sb.items.values():
            kind, data = case(it.get("data", {}))
            url = (data or {}).get("savedURL") if kind == "tab" else None
            if url and url not in known and url not in found:
                found[url] = {"type": "tab", "title": it.get("title") or data.get("savedTitle") or url, "url": url,
                              "lastSeenIn": os.path.basename(f)}
    return list(found.values())


# --- writers -----------------------------------------------------------------
def netscape(tree, archived, recovered):
    lines = ["<!DOCTYPE NETSCAPE-Bookmark-file-1>",
             '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
             "<TITLE>Arc Sidebar</TITLE>", "<H1>Arc Sidebar</H1>", "<DL><p>"]

    def folder(title, children, depth):
        pad = "    " * depth
        lines.append(f"{pad}<DT><H3>{html.escape(title)}</H3>")
        lines.append(f"{pad}<DL><p>")
        for c in children:
            emit(c, depth + 1)
        lines.append(f"{pad}</DL><p>")

    def emit(n, depth):
        pad = "    " * depth
        if n.get("url"):
            lines.append(f'{pad}<DT><A HREF="{html.escape(n["url"], quote=True)}">{html.escape(n.get("title") or n["url"])}</A>')
        elif n.get("children"):
            folder(n.get("title") or "Folder", n["children"], depth)

    root = []
    for fav in tree["favorites"]:
        if fav["children"]:
            root.append({"title": fav["title"], "children": fav["children"]})
    for sp in tree["spaces"]:
        kids = []
        if sp["pinned"]:
            kids.append({"title": "Pinned", "children": sp["pinned"]})
        if sp["today"]:
            kids.append({"title": "Today (unpinned)", "children": sp["today"]})
        root.append({"title": f"Space: {sp['title']}", "children": kids or []})
    if archived:
        root.append({"title": "Archived tabs", "children": archived})
    if recovered:
        root.append({"title": "Recovered from older snapshots", "children": recovered})
    folder("Arc", root, 1)
    lines.append("</DL><p>")
    return "\n".join(lines) + "\n"


def markdown(tree, archived, recovered):
    out = ["# Arc sidebar export", ""]

    def emit(nodes, depth=0):
        for n in nodes:
            pad = "  " * depth
            if n.get("url"):
                out.append(f"{pad}- [{n.get('title') or n['url']}]({n['url']})")
            else:
                out.append(f"{pad}- **{n.get('title')}**" + (f" _({n['note']})_" if n.get("note") else ""))
                emit(n.get("children", []), depth + 1)

    for fav in tree["favorites"]:
        out += [f"## {fav['title']}", ""]
        emit(fav["children"])
        out.append("")
    for sp in tree["spaces"]:
        out += [f"## Space: {sp['title']}", "", "### Pinned", ""]
        emit(sp["pinned"])
        out += ["", "### Today", ""]
        emit(sp["today"])
        out.append("")
    if archived:
        out += ["## Archived tabs", ""]
        emit(archived)
        out.append("")
    if recovered:
        out += ["## Recovered from older snapshots", ""]
        emit(recovered)
    return "\n".join(out) + "\n"


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Library/Application Support/Arc")
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "arc-export"
    os.makedirs(out_dir, exist_ok=True)

    tree = Sidebar(json.load(open(os.path.join(data_dir, "StorableSidebar.json")))).tree()
    live = set(walk_urls(tree["favorites"])) | {u for s in tree["spaces"] for u in walk_urls(s["pinned"] + s["today"])}
    arch = archive(data_dir)
    recovered = from_snapshots(data_dir, live | {a["url"] for a in arch})

    with open(os.path.join(out_dir, "sidebar.json"), "w") as f:
        json.dump({**tree, "archived": arch, "recoveredFromSnapshots": recovered}, f, indent=2, ensure_ascii=False)
    with open(os.path.join(out_dir, "bookmarks.html"), "w") as f:
        f.write(netscape(tree, arch, recovered))
    with open(os.path.join(out_dir, "sidebar.md"), "w") as f:
        f.write(markdown(tree, arch, recovered))

    n_live = len(live)
    print(f"spaces={len(tree['spaces'])} live_urls={n_live} archived={len(arch)} recovered={len(recovered)} -> {out_dir}")


if __name__ == "__main__":
    main()
