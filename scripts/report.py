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
def tw_table(rs):
    import statistics as st
    rows = {}
    for r in rs:
        rows.setdefault(r["config"], []).append(r)
    f = lambda xs: f"{st.mean(xs):.2f}±{(st.pstdev(xs) if len(xs) > 1 else 0):.2f}"
    out = ["| mode | train score | HELD-OUT score | held-out win rate | repeated commands | invalid replies | LLM calls |", "|---|---|---|---|---|---|---|"]
    for c, x in rows.items():
        out.append(f"| {c} | {f([r['train_score'] for r in x])} | {f([r['eval_score'] for r in x])} | {f([r['eval_win'] for r in x])} | "
                   f"{st.mean(r['repeat_rate'] for r in x):.2f} | {st.mean(r['invalid_rate'] for r in x):.2f} | {st.mean(r['llm_calls'] for r in x):.0f} |")
    return "\n".join(out)


for step, rs in sorted(by_step.items()):
    lines += [f"## {step}  ({len(rs)} runs)\n", tw_table(rs) if "eval_score" in rs[0] else summarise(rs), ""]
open(out, "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines))
