"""Run Sarah-Bench.   examples:
    python run.py --stub --configs bare,full --seeds 2 --play 60 --exam 10          # no LLM, instant (pipeline check)
    python run.py --configs bare,lessons_filter,full --seeds 2 --play 80 --exam 10   # real llama3.2:1b through Ollama
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sarah.bench import run_suite, summarise          # noqa: E402
from sarah.config import CONFIGS                       # noqa: E402
from sarah.llm import OllamaLLM, StubLLM               # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--configs", default=",".join(CONFIGS))
ap.add_argument("--seeds", type=int, default=2)
ap.add_argument("--play", type=int, default=80)
ap.add_argument("--exam", type=int, default=10)
ap.add_argument("--model", default="llama3.2:1b")
ap.add_argument("--stub", action="store_true", help="use a random stand-in instead of the LLM")
ap.add_argument("--hint", type=float, default=0.75, help="P(failure feedback names the culprit property)")
ap.add_argument("--noise", type=float, default=0.0, help="P(an outcome is flipped)")
ap.add_argument("--wrong-hint", type=float, default=0.0, help="P(a hint blames an innocent property)")
ap.add_argument("--tag", default="")
ap.add_argument("--seed-start", type=int, default=0, help="first seed (a worker runs one seed: --seeds 1 --seed-start N)")
ap.add_argument("--progress", default="", help="write live progress JSON to this path (used by the Actions monitor)")
ap.add_argument("--out", default="", help="write result JSON here instead of results/bench_*.json")
a = ap.parse_args()

factory = (lambda: StubLLM()) if a.stub else (lambda: OllamaLLM(a.model))
tag = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ("_stub" if a.stub else "_" + a.model.replace(":", "-")) + (("_" + a.tag) if a.tag else "")
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", f"bench_{tag}.json")
if a.out:
    out = a.out
prog = None
if a.progress:
    def prog(d):
        tmp = a.progress + ".tmp"
        json.dump(d, open(tmp, "w")); os.replace(tmp, a.progress)
res = run_suite(a.configs.split(","), list(range(a.seed_start, a.seed_start + a.seeds)), a.play, a.exam, factory, out_path=out, env=dict(hint_prob=a.hint, noise=a.noise, wrong_hint=a.wrong_hint), progress=prog)
if prog:
    r0 = dict(res[0])
    prog(dict(phase="done", done=1, total=1, result=r0, curve=[]))
table = summarise(res)
print("\n" + table)
open(out.replace(".json", ".md"), "w", encoding="utf-8").write(table + "\n")
print(f"\nsaved {out}")
