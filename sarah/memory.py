"""Memory module: episodic store + lessons ("avoid <action> when <property>"), relevance retrieval (TF-IDF), and sleep-style consolidation.

Lessons carry evidence counts: a failure of the avoided action on an object with that property is *support*; a success is *contradiction*.
Consolidation drops lessons that reality has contradicted (this repairs wrong reflections by a weak language model).
"""
import math
import re
from collections import Counter
from dataclasses import dataclass


def tokens(text):
    return re.findall(r"[a-z]+", text.lower().replace("_", " "))


@dataclass
class Lesson:
    domain: str
    action: str
    prop: str
    support: int = 1
    contra: int = 0

    @property
    def text(self):
        return f"{self.domain}: avoid {self.action.replace('_', ' ')} when the object is {self.prop}"

    @property
    def confidence(self):
        return self.support / (self.support + self.contra + 1e-9)


class Memory:
    def __init__(self):
        self.episodes = []
        self.lessons = {}               # (domain, action, prop) -> Lesson
        self.last_dropped = []

    # ------------------------------------------------------------------ writing
    def add_episode(self, domain, props, action, success, feedback):
        self.episodes.append(dict(domain=domain, props=tuple(props), action=action, success=success, feedback=feedback))

    def add_lesson(self, domain, action, prop):
        k = (domain, action, prop)
        if k in self.lessons:
            self.lessons[k].support += 1
        else:
            self.lessons[k] = Lesson(domain, action, prop)

    def update_with_outcome(self, domain, props, action, success):
        """Evidence update for every stored lesson that applied to this attempt."""
        for p in props:
            les = self.lessons.get((domain, action, p))
            if les is None:
                continue
            if success:
                les.contra += 1
            # a failure re-supports the lesson only through add_lesson (reflection names the culprit)

    def consolidate(self, min_conf=0.45, min_evidence=3):
        """'Sleep': forget lessons that reality contradicts."""
        drop = [k for k, l in self.lessons.items() if (l.support + l.contra) >= min_evidence and l.confidence < min_conf]
        self.last_dropped = [self.lessons[k].text for k in drop]
        for k in drop:
            del self.lessons[k]
        return len(drop)

    # ------------------------------------------------------------------ reading
    def forbidden(self, domain, props, min_conf=0.5):
        """Actions that confident lessons say to avoid for this object."""
        return {l.action for (d, _, p), l in self.lessons.items() if d == domain and p in props and l.confidence >= min_conf}

    def retrieve(self, domain, props, k=4):
        """TF-IDF cosine between the query (domain + properties) and each lesson text; same-domain lessons only."""
        cand = [l for l in self.lessons.values() if l.domain == domain]
        if not cand:
            return []
        docs = [Counter(tokens(l.text)) for l in cand]
        df = Counter(t for d in docs for t in d)
        n = len(docs)
        idf = {t: math.log((n + 1) / (c + 0.5)) + 1 for t, c in df.items()}
        q = Counter(tokens(" ".join(props)))
        qv = {t: c * idf.get(t, 1.0) for t, c in q.items()}
        qn = math.sqrt(sum(v * v for v in qv.values())) or 1.0
        scored = []
        for l, d in zip(cand, docs):
            dv = {t: c * idf[t] for t, c in d.items()}
            dn = math.sqrt(sum(v * v for v in dv.values())) or 1.0
            sc = sum(qv[t] * dv.get(t, 0.0) for t in qv) / (qn * dn)
            scored.append((sc * l.confidence, l))
        scored.sort(key=lambda x: -x[0])
        return [l for s, l in scored[:k] if s > 0]

    def stats(self):
        return dict(episodes=len(self.episodes), lessons=len(self.lessons))
