"""Sarah-Bench v0: free play (learning curve) -> frozen exam on held-out property combinations -> metrics, over ablated brains.

Metrics (per run):  play_success, learning curve, exam accuracy per domain, composite exam accuracy (skill reuse + credit assignment),
repeated-mistake rate (failing again with the same action/property pair), LLM calls, invalid-reply rate, lessons + their precision
against ground truth, skills, stages unlocked, activity shares (curiosity health)."""
import json
import statistics as st
import time

from .brain import Brain
from .config import CONFIGS
from .world import Nursery, STAGE_ORDER


def _mistake_keys(res):
    keys = set()
    if res["domain"] == "compose":
        for t, a, cul in zip(res["task"].parts, res["actions"], res["culprits"]):
            keys |= {(t.domain, a, p) for p in cul}
    else:
        t, a = res["task"], res["actions"][0]
        keys |= {(t.domain, a, p) for p in res["culprits"]}
    return keys


def run_one(cfg, seed, n_play, n_exam, llm_factory, log=None, env=None, progress=None):
    t0 = time.time()
    nursery, llm = Nursery(seed, **(env or {})), llm_factory()
    brain = Brain(cfg, llm, seed)
    mistakes, repeated, failures, play, shares = set(), 0, 0, [], {}
    for t in range(n_play):
        act = brain.next_activity()
        shares[act] = shares.get(act, 0) + 1
        task = nursery.sample_composite(brain.curriculum.unlocked, "train") if act == "compose" else nursery.sample(act, "train")
        res = brain.attempt(nursery, task, learn=True)
        brain.record_outcome(act, res["success"])
        if not res["success"]:
            failures += 1
            keys = _mistake_keys(res)
            if keys & mistakes:
                repeated += 1
            mistakes |= keys
        play.append(int(res["success"]))
        if progress:
            progress(dict(phase="play", done=t + 1, total=n_play, recent=round(sum(play[-20:]) / len(play[-20:]), 3), success_total=sum(play), calls=llm.calls, lessons=len(brain.memory.lessons), stages=len(brain.curriculum.unlocked), curve=play[:]))
        if log and (t + 1) % 25 == 0:
            log(f"    {cfg.name} seed{seed} play {t + 1}/{n_play}  recent success {sum(play[-25:]) / 25:.2f}  stages {len(brain.curriculum.unlocked)}")
    nursery.clean = True                                  # exam = true rules, no noise
    exam = {}
    for i, d in enumerate(STAGE_ORDER):
        if progress:
            progress(dict(phase="exam", done=n_play, total=n_play, exam_domain=d, exam_step=i, exam_steps=len(STAGE_ORDER) + 1, calls=llm.calls, curve=play[:]))
        exam[d] = sum(brain.attempt(nursery, nursery.sample(d, "exam"), learn=False)["success"] for _ in range(n_exam)) / n_exam
    exam_comp = sum(brain.attempt(nursery, nursery.sample_composite(STAGE_ORDER, "exam"), learn=False)["success"] for _ in range(n_exam)) / n_exam
    rep = brain.report()
    bins = [sum(play[i:i + 20]) / len(play[i:i + 20]) for i in range(0, len(play), 20)]
    return dict(config=cfg.name, seed=seed, play_success=sum(play) / len(play), curve=bins, exam=exam,
                exam_mean=sum(exam.values()) / len(exam), exam_compose=exam_comp,
                repeated_mistake_rate=repeated / max(1, failures), failures=failures, llm_calls=llm.calls,
                invalid_rate=rep["invalid"] / max(1, rep["llm_decisions"]), lessons=rep["lessons"], lesson_precision=rep["lesson_precision"],
                skills=rep["skills"], stages=rep["stages_unlocked"], shares={k: v / n_play for k, v in shares.items()},
                reflect=dict(deduce=rep["reflect_deduce"], hint=rep["reflect_hint"], llm=rep["reflect_llm"], none=rep["reflect_none"]), forgotten=rep["forgotten"],
                filtered=rep["filtered_actions"], seconds=round(time.time() - t0, 1))


def run_suite(config_names, seeds, n_play, n_exam, llm_factory, out_path=None, log=print, env=None, progress=None):
    results = []
    for name in config_names:
        for s in seeds:
            r = run_one(CONFIGS[name], s, n_play, n_exam, llm_factory, log=log, env=env, progress=progress)
            results.append(r)
            log(f"[{name:18s} seed {s}] play {r['play_success']:.2f} | exam {r['exam_mean']:.2f} compose {r['exam_compose']:.2f} | repeat-mistakes {r['repeated_mistake_rate']:.2f} | "
                f"LLM calls {r['llm_calls']} | lessons {r['lessons']} (precision {r['lesson_precision']}) | stages {r['stages']} | {r['seconds']}s")
            if out_path:
                json.dump(results, open(out_path, "w"), indent=1)
    return results


def summarise(results):
    rows = {}
    for r in results:
        rows.setdefault(r["config"], []).append(r)
    m = lambda xs: (st.mean(xs), st.pstdev(xs) if len(xs) > 1 else 0.0)
    lines = ["| config | play success | exam (unseen combos) | exam composite | repeated mistakes | LLM calls | lessons (precision) | stages |", "|---|---|---|---|---|---|---|---|"]
    for name, rs in rows.items():
        ps, ex, co, rp = m([r["play_success"] for r in rs]), m([r["exam_mean"] for r in rs]), m([r["exam_compose"] for r in rs]), m([r["repeated_mistake_rate"] for r in rs])
        prec = [r["lesson_precision"] for r in rs if r["lesson_precision"] is not None]
        lines.append(f"| {name} | {ps[0]:.2f}±{ps[1]:.2f} | {ex[0]:.2f}±{ex[1]:.2f} | {co[0]:.2f}±{co[1]:.2f} | {rp[0]:.2f} | {st.mean(r['llm_calls'] for r in rs):.0f} | "
                     f"{st.mean(r['lessons'] for r in rs):.0f} ({st.mean(prec):.2f}) | {st.mean(r['stages'] for r in rs):.1f} |" if prec else
                     f"| {name} | {ps[0]:.2f}±{ps[1]:.2f} | {ex[0]:.2f}±{ex[1]:.2f} | {co[0]:.2f}±{co[1]:.2f} | {rp[0]:.2f} | {st.mean(r['llm_calls'] for r in rs):.0f} | - | {st.mean(r['stages'] for r in rs):.1f} |")
    return "\n".join(lines)
