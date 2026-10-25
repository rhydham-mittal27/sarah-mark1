"""Build the Actions job matrix.  python scripts/plan.py "1,2,3" 3   ->  prints JSON {"include":[...]} on one line."""
import json
import sys

STEPS = {
    "1": dict(label="step1_baseline", hint=0.75, noise=0.0, wrong=0.0, configs=["bare", "lessons_in_prompt", "lessons_filter", "full"]),
    "2": dict(label="step2_nohint", hint=0.0, noise=0.0, wrong=0.0, configs=["bare", "lessons_filter", "lessons_filter_ded", "full", "full_ded"]),
    "3": dict(label="step3_noisy", hint=0.5, noise=0.1, wrong=0.2, configs=["bare", "lessons_filter", "lessons_filter_ded", "full", "full_ded"]),
}

steps = [s.strip() for s in sys.argv[1].split(",") if s.strip()]
seeds = int(sys.argv[2])
inc = []
for s in steps:
    st = STEPS[s]
    for c in st["configs"]:
        for seed in range(seeds):
            inc.append(dict(step=st["label"], config=c, seed=seed, hint=st["hint"], noise=st["noise"], wrong=st["wrong"], name=f"{st['label']}__{c}__s{seed}"))
print(json.dumps({"include": inc}))
