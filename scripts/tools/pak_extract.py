#!/usr/bin/env python3
"""Unpack a Chromium .pak resource file (format v4 or v5).

Resources are written as <id>.<ext>. The extension is guessed from content,
since the id-to-name map only exists in Chromium's build output. Gzip and
Chromium's brotli wrapper (magic 0x1E 0x9B + 6-byte size) are decompressed.

usage: pak_extract.py <file.pak> <out-dir>
"""
import gzip
import json
import os
import struct
import sys

try:
    import brotli  # pip install brotli
except ImportError:  # pragma: no cover
    brotli = None


def read_pak(path):
    data = open(path, "rb").read()
    version = struct.unpack_from("<I", data, 0)[0]
    if version == 5:
        _enc, count, alias_count = struct.unpack_from("<B3xHH", data, 4)
        header = 12
    elif version == 4:
        count, _enc = struct.unpack_from("<IB", data, 4)
        alias_count, header = 0, 9
    else:
        raise SystemExit(f"{path}: unsupported pak version {version}")

    entries = [struct.unpack_from("<HI", data, header + i * 6) for i in range(count + 1)]
    resources = {}
    for (rid, start), (_, end) in zip(entries, entries[1:]):
        resources[rid] = data[start:end]
    alias_base = header + (count + 1) * 6
    for i in range(alias_count):
        rid, idx = struct.unpack_from("<HH", data, alias_base + i * 4)
        resources[rid] = resources[entries[idx][0]]
    return version, resources


def decode(blob):
    if blob[:2] == b"\x1f\x8b":
        return gzip.decompress(blob), "gzip"
    if blob[:2] == b"\x1e\x9b" and brotli:
        return brotli.decompress(blob[8:]), "brotli"
    return blob, None


def sniff(b):
    head = b[:512].lstrip()
    low = head.lower()
    if b.startswith(b"\x89PNG"):
        return "png"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        return "webp"
    if b[:3] == b"GIF":
        return "gif"
    if b[:2] == b"\xff\xd8":
        return "jpg"
    if b[:4] in (b"wOFF", b"wOF2"):
        return "woff2" if b[:4] == b"wOF2" else "woff"
    if low.startswith(b"<svg") or (low.startswith(b"<?xml") and b"<svg" in low):
        return "svg"
    if low.startswith((b"<!doctype html", b"<html", b"<link", b"<style", b"<meta", b"<!--", b"<template", b"<div", b"<cr-", b"<dom-module")):
        return "html"
    if low.startswith(b"<?xml"):
        return "xml"
    if head[:1] in (b"{", b"[") :
        try:
            json.loads(b)
            return "json"
        except Exception:
            pass
    if b"{" in head and (b":root" in head or b"@media" in head or head.startswith((b"/*", b".", b"#", b"html", b"body", b":host"))):
        if b"function" not in head and b"import " not in head:
            return "css"
    try:
        b.decode("utf-8")
        if any(t in head for t in (b"import ", b"export ", b"function", b"const ", b"'use strict'", b"// Copyright", b"var ", b"let ")):
            return "js"
        return "txt"
    except UnicodeDecodeError:
        return "bin"


def main():
    pak, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    version, res = read_pak(pak)
    index = {}
    for rid, blob in sorted(res.items()):
        body, comp = decode(blob)
        ext = sniff(body)
        name = f"{rid}.{ext}"
        with open(os.path.join(out, name), "wb") as f:
            f.write(body)
        index[rid] = {"file": name, "bytes": len(body), "compression": comp}
    with open(os.path.join(out, "_index.json"), "w") as f:
        json.dump({"pak": os.path.basename(pak), "version": version, "resources": index}, f, indent=1)
    by_ext = {}
    for v in index.values():
        e = v["file"].rsplit(".", 1)[1]
        by_ext[e] = by_ext.get(e, 0) + 1
    print(os.path.basename(pak), len(index), "resources", by_ext)


if __name__ == "__main__":
    main()
