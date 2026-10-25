"""World model: a counts-based outcome predictor P(success | action, properties).  Used to 'imagine' before acting:
rank actions by predicted success and offer the LLM only the safest few.  Unknown (action, property) pairs get a neutral prior."""
from collections import defaultdict


class WorldModel:
    def __init__(self, prior=0.5):
        self.s = defaultdict(float)
        self.n = defaultdict(float)
        self.prior = prior

    def update(self, domain, props, action, success, culprit=None):
        if success:
            for p in props:
                self.s[(domain, p, action)] += 1
                self.n[(domain, p, action)] += 1
        else:
            for p in ([culprit] if culprit else props):                 # credit assignment: blame the named culprit if known
                self.n[(domain, p, action)] += 1

    def predict(self, domain, props, action):
        """predicted success = weakest property (an action fails if ANY property forbids it); Beta-style smoothing"""
        return min((self.s[(domain, p, action)] + self.prior) / (self.n[(domain, p, action)] + 1.0) for p in props)

    def shortlist(self, domain, props, actions, k=3, rng=None):
        """the k actions with the highest predicted success (ties broken randomly so that early, ignorant choices are not biased)"""
        noise = (lambda: rng.random() * 1e-6) if rng else (lambda: 0.0)
        ranked = sorted(actions, key=lambda a: -(self.predict(domain, props, a) + noise()))
        return ranked[:k]

    def imagined_rollout(self, domain, props, actions):
        return [(a, self.predict(domain, props, a)) for a in actions]
