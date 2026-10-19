#!/usr/bin/env python3
"""Cheap repository hygiene check used by CI.

Fails if source assets, renders or large binaries accidentally land in git.
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX = 50 * 1024 * 1024
bad_dirs = {"pdoom-video", "out", "__pycache__", ".git", ".venv", "node_modules"}
allowed_big = set()
bad = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in bad_dirs]
    for f in filenames:
        p = os.path.join(dirpath, f)
        rel = os.path.relpath(p, ROOT).replace("\\", "/")
        if rel.endswith((".blend", ".blend1", ".pyc")):
            bad.append("generated file: " + rel)
        if os.path.getsize(p) > MAX and rel not in allowed_big:
            bad.append("large file: " + rel)
for req in ["LICENSE", "NOTICE.md", "README.md"]:
    if not os.path.exists(os.path.join(ROOT, req)):
        bad.append("missing " + req)
if bad:
    print("\n".join(bad))
    sys.exit(1)
print("repo hygiene OK")
