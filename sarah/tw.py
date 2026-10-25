"""Step 4: an EXTERNAL benchmark.  Sarah's learning loop on TextWorld (tw-simple games, dense rewards), same frozen llama3.2:1b.

Protocol (the two-phase style used by continual-learning benchmarks): play K training games (seeds A) with learning on, then freeze and
evaluate on M held-out games (seeds B).  The LLM picks among numbered commands the env says are admissible.

Modes (all use the same LLM; they differ in what the surrounding code does):
  bare        objective + room + last steps -> LLM picks
  prompt_mem  + what earlier games taught (which verbs scored / never scored) written into the prompt
  filter      the same knowledge ENFORCED in code: drop commands already tried in this room and verbs that never scored
  full        filter + value ranking (learned verb success rate with optimism for untried verbs, shortlist of the best k) before the LLM
"""
import os
import random
import re
import tempfile
from collections import defaultdict

MODES = ("bare", "prompt_mem", "filter", "full")
MAX_OPTIONS = 20
NO_VALUE_VERBS = {"examine", "look", "inventory"}


class TWGames:
    """Thin wrapper over textworld so the agent can be unit-tested with a fake."""
    def __init__(self, rewards="dense", goal="brief"):
        import textworld
        from textworld import GameOptions
        from textworld.challenges import simple
        self.tw, self.GameOptions, self.simple, self.rewards, self.goal = textworld, GameOptions, simple, rewards, goal
        self.dir = tempfile.mkdtemp()
        self.infos = textworld.EnvInfos(admissible_commands=True, objective=True, description=True, inventory=True, score=True, max_score=True, won=True, lost=True)

    def make(self, seed):
        opts = self.GameOptions()
        opts.seeds = seed
        opts.path = os.path.join(self.dir, f"g{seed}.z8")
        game = self.simple.make({"rewards": self.rewards, "goal": self.goal, "test": False}, opts)
        path = self.tw.generator.compile_game(game, opts)
        return self.tw.start(path, self.infos)


def verb(cmd):
    return cmd.split()[0]


def room_of(description):
    m = re.search(r"-=\s*(.+?)\s*=-", description or "")
    return m.group(1) if m else "?"


class TWAgent:
    def __init__(self, mode, llm, seed=0, k=5):
        assert mode in MODES
        self.mode, self.llm, self.k = mode, llm, k
        self.rng = random.Random(seed + 777)
        self.tries, self.hits = defaultdict(int), defaultdict(int)      # per verb, across games
        self.stats = dict(steps=0, llm_calls=0, invalid=0, repeats=0, removed=0)

    # ------------------------------------------------------------------ knowledge
    def verb_rate(self, v):
        return (self.hits[v] + 0.5) / (self.tries[v] + 1.0)           # optimistic for untried verbs

    def dead_verbs(self, min_tries=4):
        return {v for v in self.tries if self.tries[v] >= min_tries and self.hits[v] == 0 and v != "go"}

    def good_verbs(self):
        return sorted((v for v in self.tries if self.hits[v] > 0), key=lambda v: -self.verb_rate(v))

    def lessons(self):
        out = []
        g, d = self.good_verbs(), sorted(self.dead_verbs())
        if g:
            out.append("These kinds of actions earned points before: " + ", ".join(g[:5]) + ".")
        if d:
            out.append("These never earned points: " + ", ".join(d) + ".")
        out.append("Do not repeat a command you already tried in the same room.")
        return out

    # ------------------------------------------------------------------ decision
    def decide(self, state, history, tried_here):
        cmds = [c for c in state.admissible_commands if c not in ("look", "inventory")] or list(state.admissible_commands)
        pool, removed = cmds, 0
        if self.mode in ("filter", "full"):
            dead = self.dead_verbs()
            keep = [c for c in pool if c not in tried_here and verb(c) not in dead]
            keep = keep or [c for c in pool if c not in tried_here] or pool
            removed, pool = len(pool) - len(keep), keep
            self.stats["removed"] += removed
        if self.mode == "full":
            def score(c):
                v = verb(c)
                return (max(self.verb_rate(v), 0.3) if v == "go" else self.verb_rate(v)) + self.rng.random() * 0.02
            pool = sorted(pool, key=score, reverse=True)[:self.k]
        elif len(pool) > MAX_OPTIONS:
            pool = self.rng.sample(pool, MAX_OPTIONS)
        if len(pool) == 1:
            return pool[0], None
        prompt = self.prompt(state, pool, history)
        raw = self.llm.generate(prompt, max_tokens=6, seed=self.rng.randrange(10 ** 6))
        self.stats["llm_calls"] += 1
        m = re.search(r"\d+", raw or "")
        i = int(m.group()) - 1 if m else -1
        if not (0 <= i < len(pool)):
            self.stats["invalid"] += 1
            i = self.rng.randrange(len(pool))
        return pool[i], prompt

    def prompt(self, state, pool, history):
        parts = ["You are Sarah, a baby robot playing a text house game.", "Goal: " + (state.objective or "").strip().replace("\n", " ")[:240],
                 "Where I am: " + (state.description or "").strip().replace("\n", " ")[:360]]
        if history:
            parts.append("Recent steps: " + " | ".join(f"{c} -> {f}" for c, f in history[-3:]))
        if self.mode == "prompt_mem":
            parts.append("What I learned before:\n" + "\n".join("- " + t for t in self.lessons()))
        parts.append("Choose the single best next action by number.")
        parts += [f"{i + 1}) {c}" for i, c in enumerate(pool)]
        parts.append("OPTIONS: " + ", ".join(str(i + 1) for i in range(len(pool))))
        parts.append("Answer with just the number.")
        return "\n".join(parts)

    # ------------------------------------------------------------------ one game
    def play(self, env, max_steps=25, learn=True):
        state = env.reset()
        history, tried, last_score = [], defaultdict(set), 0
        for _ in range(max_steps):
            room = room_of(state.description)
            cmd, _ = self.decide(state, history, tried[room])
            if cmd in tried[room]:
                self.stats["repeats"] += 1
            tried[room].add(cmd)
            state2, reward, done = env.step(cmd)
            gain = state2.score - last_score if state2.score is not None else reward
            last_score = state2.score if state2.score is not None else last_score
            self.stats["steps"] += 1
            if learn:
                self.tries[verb(cmd)] += 1
                if gain > 0:
                    self.hits[verb(cmd)] += 1
            history.append((cmd, (state2.feedback or "").strip().replace("\n", " ")[:50]))
            state = state2
            if done:
                break
        return dict(score=last_score, max_score=state.max_score or 1, won=bool(getattr(state, "won", False)), steps=len(history))


def run_mode(mode, seed, games, llm, n_train=8, n_eval=8, max_steps=25, log=print, progress=None):
    import time
    t0 = time.time()
    ag = TWAgent(mode, llm, seed)
    base = 100 * seed
    train, ev = [], []
    total = n_train + n_eval
    for g in range(n_train):
        env = games.make(base + g)
        train.append(ag.play(env, max_steps, learn=True))
        if progress:
            progress(dict(phase="play", done=g + 1, total=total, recent=round(sum(r["score"] / r["max_score"] for r in train[-4:]) / len(train[-4:]), 3), calls=llm.calls, curve=[]))
    for g in range(n_eval):
        env = games.make(10_000 + base + g)
        ev.append(ag.play(env, max_steps, learn=False))
        if progress:
            progress(dict(phase="play", done=n_train + g + 1, total=total, recent=round(sum(r["score"] / r["max_score"] for r in ev[-4:]) / len(ev[-4:]), 3), calls=llm.calls, curve=[]))
    m = lambda rs, f: sum(f(r) for r in rs) / len(rs)
    s = ag.stats
    out = dict(config=mode, seed=seed, train_score=m(train, lambda r: r["score"] / r["max_score"]), eval_score=m(ev, lambda r: r["score"] / r["max_score"]),
               eval_win=m(ev, lambda r: float(r["won"])), repeat_rate=s["repeats"] / max(1, s["steps"]), invalid_rate=s["invalid"] / max(1, s["llm_calls"]),
               llm_calls=llm.calls, removed=s["removed"], lessons=len(ag.good_verbs()), lesson_precision=None, stages=0, good_verbs=ag.good_verbs()[:6], dead_verbs=sorted(ag.dead_verbs()), seconds=round(time.time() - t0, 1))
    out.update(play_success=out["train_score"], exam_mean=out["eval_score"], exam_compose=out["eval_win"], repeated_mistake_rate=out["repeat_rate"])   # keys the live monitor reads
    log(f"[{mode:10s} seed {seed}] train {out['train_score']:.2f} | EVAL score {out['eval_score']:.2f} win {out['eval_win']:.2f} | repeats {out['repeat_rate']:.2f} | invalid {out['invalid_rate']:.2f} | calls {out['llm_calls']} | good {out['good_verbs']} | {out['seconds']}s")
    return out
