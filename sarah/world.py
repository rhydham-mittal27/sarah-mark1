"""The Nursery: a small developmental text world with hidden rules.

Four domains (stages) of increasing breadth - grasp, carry, stack, tool - plus *composite* tasks that need one correct
action in each of two domains (credit assignment + skill reuse).  Each property of an object secretly forbids some actions;
an action succeeds iff none of the object's properties forbids it.  The agent never sees the rules, only feedback text.
Property pairs are split into TRAIN combinations (free play) and held-out EXAM combinations (transfer test).
"""
import itertools
import random
from dataclasses import dataclass

DOMAINS = {
    "grasp": dict(verb="pick up the object", actions=["top_grasp", "side_grasp", "pinch", "scoop", "push_then_grasp", "tool_assist"],
                  forbid={"wet": ["top_grasp", "pinch"], "slippery": ["side_grasp"], "fragile": ["top_grasp", "push_then_grasp"],
                          "heavy": ["pinch", "scoop"], "flat": ["side_grasp", "scoop"], "round": ["push_then_grasp"]}),
    "carry": dict(verb="carry the object to the table", actions=["hands", "tray", "drag", "roll", "ask_help", "cart"],
                  forbid={"heavy": ["hands", "tray"], "hot": ["hands", "drag"], "fragile": ["drag", "roll"], "large": ["tray", "roll"],
                          "liquid": ["drag", "roll"], "sharp": ["hands", "cart"]}),
    "stack": dict(verb="stack the object on the tower", actions=["on_top", "underneath", "beside", "wedge", "tie", "balance"],
                  forbid={"round": ["on_top", "balance"], "flat": ["beside", "wedge"], "fragile": ["underneath", "tie"],
                          "heavy": ["on_top", "wedge"], "wet": ["tie", "balance"], "tall": ["on_top", "beside"]}),
    "tool": dict(verb="reach the object on the shelf", actions=["stool", "stick", "jump", "shout", "ladder", "push_object"],
                 forbid={"high": ["jump", "shout"], "far": ["stool", "stick"], "heavy": ["push_object", "stick"],
                         "wobbly": ["stool", "ladder"], "narrow": ["ladder", "push_object"], "slippery": ["jump", "stool"]}),
}
STAGE_ORDER = ["grasp", "carry", "stack", "tool"]


def _check():
    for d, spec in DOMAINS.items():
        A = set(spec["actions"])
        for forb in spec["forbid"].values():
            assert set(forb) <= A, d
        for a, b in itertools.combinations(spec["forbid"], 2):
            assert len(A - set(spec["forbid"][a]) - set(spec["forbid"][b])) >= 2, (d, a, b)


_check()


@dataclass(frozen=True)
class Task:
    domain: str
    props: tuple

    @property
    def actions(self):
        return DOMAINS[self.domain]["actions"]


@dataclass(frozen=True)
class Composite:
    parts: tuple          # (Task, Task)

    @property
    def domain(self):
        return "compose"


class Nursery:
    def __init__(self, seed: int = 0, hint_prob: float = 0.75, n_train_combos: int = 10, noise: float = 0.0, wrong_hint: float = 0.0):
        self.rng = random.Random(seed)
        self.hint_prob, self.noise, self.wrong_hint = hint_prob, noise, wrong_hint     # noise: P(outcome flipped); wrong_hint: P(a hint blames an innocent property)
        self.clean = False                                                            # exam mode: no noise, no hints needed
        self.train, self.exam = {}, {}
        for d, spec in DOMAINS.items():
            combos = list(itertools.combinations(sorted(spec["forbid"]), 2))
            random.Random(seed + 1).shuffle(combos)
            self.train[d], self.exam[d] = combos[:n_train_combos], combos[n_train_combos:]

    # ---------------------------------------------------------------- sampling
    def sample(self, domain: str, split: str = "train") -> Task:
        pool = self.train[domain] if split == "train" else self.exam[domain]
        return Task(domain, tuple(self.rng.choice(pool)))

    def sample_composite(self, domains, split: str = "train") -> Composite:
        d1, d2 = self.rng.sample(list(domains), 2)
        return Composite((self.sample(d1, split), self.sample(d2, split)))

    # ---------------------------------------------------------------- rules (ground truth - used only by the environment and by metrics)
    @staticmethod
    def forbidders(task: Task, action: str):
        forb = DOMAINS[task.domain]["forbid"]
        return [p for p in task.props if action in forb[p]]

    def valid_actions(self, task: Task):
        return [a for a in task.actions if not self.forbidders(task, a)]

    @staticmethod
    def true_rule(domain: str, prop: str, action: str) -> bool:
        return action in DOMAINS[domain]["forbid"].get(prop, [])

    @staticmethod
    def describe(task: Task) -> str:
        return f"Task ({task.domain}): {DOMAINS[task.domain]['verb']}. The object is {' and '.join(task.props)}."

    # ---------------------------------------------------------------- dynamics + feedback text
    def _flip(self):
        return (not self.clean) and self.noise > 0 and self.rng.random() < self.noise

    def _blame(self, task, culprits):
        pool = [p for p in task.props if p not in culprits]
        if (not self.clean) and pool and self.rng.random() < self.wrong_hint:
            return self.rng.choice(pool)
        return self.rng.choice(culprits)

    def step(self, task: Task, action: str):
        culprits = self.forbidders(task, action)
        if self._flip():                                    # surprise: the world misbehaves this once
            return (False, "It failed.", []) if not culprits else (True, "It worked.", culprits)
        if not culprits:
            return True, "It worked.", []
        if self.rng.random() < self.hint_prob:
            c = self._blame(task, culprits)
            return False, f"It failed: the {c} property was the problem.", culprits
        return False, "It failed.", culprits

    def step_composite(self, comp: Composite, actions):
        outs = [self.step_quiet(t, a) for t, a in zip(comp.parts, actions)]
        if self._flip():                                    # surprise: one step's outcome is inverted
            i = self.rng.randrange(2)
            outs[i] = (False, []) if outs[i][0] else (True, outs[i][1])
        if all(o[0] for o in outs):
            return True, "It worked.", [[], []]
        bad = [i for i, o in enumerate(outs) if not o[0]]
        culprits = [o[1] for o in outs]
        if self.rng.random() < self.hint_prob:
            i = self.rng.choice(bad)
            c = self._blame(comp.parts[i], culprits[i]) if culprits[i] else None
            if c is None:
                return False, "It failed.", culprits
            return False, f"It failed at step {i + 1}: the {c} property was the problem.", culprits
        return False, "It failed.", culprits

    def step_quiet(self, task: Task, action: str):
        c = self.forbidders(task, action)
        return (not c), c
