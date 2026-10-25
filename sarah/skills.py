"""Skill library: remembers which action worked for which property, and composes evidence across properties for unseen combinations."""
from collections import defaultdict


class SkillLibrary:
    def __init__(self):
        self.succ = defaultdict(int)         # (domain, prop, action) -> successes
        self.fail = defaultdict(int)
        self.exact = defaultdict(int)        # (domain, props, action) -> successes (whole-object skills)
        self.n_added = 0

    def record(self, domain, props, action, success, culprit=None):
        key = tuple(sorted(props))
        if success:
            self.exact[(domain, key, action)] += 1
            for p in props:
                self.succ[(domain, p, action)] += 1
            self.n_added += 1
        else:
            for p in ([culprit] if culprit else props):
                self.fail[(domain, p, action)] += 1

    def score(self, domain, props, action):
        """Evidence that `action` works: exact whole-object successes count most; otherwise the weakest per-property evidence."""
        key = tuple(sorted(props))
        ex = self.exact.get((domain, key, action), 0)
        per = [self.succ.get((domain, p, action), 0) - 2 * self.fail.get((domain, p, action), 0) for p in props]
        return ex * 2.0 + min(per)

    def suggest(self, domain, props, actions, min_score=1.0):
        sc = {a: self.score(domain, props, a) for a in actions}
        best = max(sc.values())
        if best < min_score:
            return None, sc
        return max(sc, key=sc.get), sc

    def size(self):
        return len(self.exact)
