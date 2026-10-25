"""Merge all worker result JSONs (downloaded artifacts) into one markdown report per step.   python scripts/report.py <artifacts_dir> <out.md>"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from sarah.bench import summarise  # noqa: E402

root, out = sys.argv[1], sys.argv[2]
by_step = {}
for f in sorted(glob.glob(os.path.join(root, "**", "*.json"), recursive=True)):
    try:
        rs = json.load(open(f))
    except Exception:
        continue
    step = os.path.basename(os.path.dirname(f)).split("__")[0] if "__" in os.path.basename(os.path.dirname(f)) else "all"
    for r in rs if isinstance(rs, list) else []:
        by_step.setdefault(step, []).append(r)
lines = ["# Sarah Mark 1: real llama3.2:1b benchmark (GitHub Actions)\n"]
for step, rs in sorted(by_step.items()):
    lines += [f"## {step}  ({len(rs)} runs)\n", summarise(rs), ""]
open(out, "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines))
