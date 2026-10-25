"""Step 4 runner (TextWorld; runs on GitHub Actions - textworld does not support Windows).
python tw_run.py --mode full --seed 0 --train 8 --eval 8 --out out/result.json --progress out/progress.json"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sarah.llm import OllamaLLM          # noqa: E402
from sarah.tw import TWGames, run_mode   # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--mode", required=True)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--train", type=int, default=8)
ap.add_argument("--eval", type=int, default=8)
ap.add_argument("--steps", type=int, default=25)
ap.add_argument("--model", default="llama3.2:1b")
ap.add_argument("--out", default="")
ap.add_argument("--progress", default="")
a = ap.parse_args()

prog = None
if a.progress:
    def prog(d):
        tmp = a.progress + ".tmp"
        json.dump(d, open(tmp, "w")); os.replace(tmp, a.progress)
llm = OllamaLLM(a.model)
res = run_mode(a.mode, a.seed, TWGames(), llm, a.train, a.eval, a.steps, progress=prog)
if a.out:
    json.dump([res], open(a.out, "w"), indent=1)
if prog:
    prog(dict(phase="done", done=1, total=1, result=res, curve=[]))
