"""Curriculum + curiosity module.  Decides which activity to practise next.
Stages unlock when the previous one is mastered (or after a patience limit).  Among unlocked activities the chooser is:
  'lp'         learning progress (decrease of failure rate between two windows) + an optimism bonus for under-practised activities
  'random'     uniform
  'sequential' fixed order, N tasks per stage
'compose' (two-domain tasks) becomes available once two stages are unlocked."""
import math
import random

from .world import STAGE_ORDER


class Curriculum:
    def __init__(self, policy="lp", seed=0, mastery=0.8, window=10, patience=30, seq_len=25):
        self.policy, self.rng = policy, random.Random(seed)
        self.mastery, self.window, self.patience, self.seq_len = mastery, window, patience, seq_len
        self.unlocked = [STAGE_ORDER[0]]
        self.hist = {k: [] for k in STAGE_ORDER + ["compose"]}
        self.t = 0
        self.unlock_times = {STAGE_ORDER[0]: 0}

    def activities(self):
        return self.unlocked + (["compose"] if len(self.unlocked) >= 2 else [])

    def record(self, activity, success):
        self.hist[activity].append(1 if success else 0)
        self.t += 1
        newest = self.unlocked[-1]
        if activity == newest and len(self.unlocked) < len(STAGE_ORDER):
            h = self.hist[newest]
            rate = sum(h[-self.window:]) / max(1, len(h[-self.window:]))
            if (len(h) >= self.window and rate >= self.mastery) or len(h) >= self.patience:
                nxt = STAGE_ORDER[len(self.unlocked)]
                self.unlocked.append(nxt)
                self.unlock_times[nxt] = self.t

    def _lp(self, activity):
        h = self.hist[activity]
        w = self.window
        if len(h) < 2 * w:
            return 0.35 + 1.0 / (1 + len(h))                 # optimism for under-practised activities
        old, new = h[-2 * w:-w], h[-w:]
        fail_old = 1 - sum(old) / w
        fail_new = 1 - sum(new) / w
        return max(0.0, fail_old - fail_new) + 0.04 + (0.3 * fail_new if fail_new < 0.9 else 0.0)   # learnable-and-not-yet-mastered gets a boost

    def choose(self):
        acts = self.activities()
        if self.policy == "random":
            return self.rng.choice(acts)
        if self.policy == "sequential":
            idx = min(self.t // self.seq_len, len(acts) - 1)
            return acts[idx] if idx < len(STAGE_ORDER) else self.rng.choice(acts)
        lp = [self._lp(a) for a in acts]
        z = [math.exp(6 * v) for v in lp]
        s = sum(z)
        u, acc = self.rng.random() * s, 0.0
        for a, zz in zip(acts, z):
            acc += zz
            if u <= acc:
                return a
        return acts[-1]
