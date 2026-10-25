"""Reflection module: after a failure, decide *which property* caused it (the lesson's subject).
If the feedback text names a property, trust it; otherwise ask the language model (a weak model guesses poorly -
the memory's consolidation step later repairs the wrong lessons)."""
import re
from dataclasses import dataclass

from . import prompts


@dataclass
class Reflection:
    prop: object          # str or None
    source: str           # 'hint' | 'llm' | 'none'
    raw: str = ""


class Reflector:
    def __init__(self, llm, use_llm=True):
        self.llm, self.use_llm = llm, use_llm
        self.n_llm = self.n_hint = self.n_none = self.n_deduce = 0

    def reflect(self, task, action, feedback, memory=None, deduce=False) -> Reflection:
        props = list(task.props)
        hinted = [p for p in props if re.search(r"\b" + p + r"\b", feedback)]
        if hinted:
            self.n_hint += 1
            return Reflection(hinted[0], "hint")
        if deduce and memory is not None:
            cand = [p for p in props if not any(e["success"] and e["domain"] == task.domain and e["action"] == action and p in e["props"] for e in memory.episodes)]
            if len(cand) == 1:
                self.n_deduce += 1
                return Reflection(cand[0], "deduce")
        if self.use_llm:
            choice, raw = self.llm.choose(prompts.reflection_prompt(action, props, feedback), props)
            if choice:
                self.n_llm += 1
                return Reflection(choice, "llm", raw)
        self.n_none += 1
        return Reflection(None, "none")
