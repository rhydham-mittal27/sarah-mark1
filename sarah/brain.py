"""Sarah Mark 1 - the assembled brain.

          +-----------------------------  Curriculum / curiosity  (what to practise next)
          |
 task --> |  Memory (lessons)  --filter-->  World model (imagination: safest k)  -->  LLM (llama3.2:1b)  --> action
          |  Skill library --hint-----------------------------------------------^
          v
 outcome --> Reflection (which property failed?) --> Memory.add_lesson / consolidate  (+ skills + world model updates)

Every module is optional (see config.py); the language model is only a *tie-breaker among the options the other modules leave open*."""
import random
import re

from . import prompts
from .config import BrainConfig
from .curriculum import Curriculum
from .memory import Memory
from .reflection import Reflector
from .skills import SkillLibrary
from .world import Composite, Nursery
from .worldmodel import WorldModel


class Brain:
    def __init__(self, cfg: BrainConfig, llm, seed: int = 0):
        self.cfg, self.llm = cfg, llm
        self.rng = random.Random(seed + 12345)
        self.memory = Memory()
        self.skills = SkillLibrary()
        self.wm = WorldModel()
        self.reflector = Reflector(llm, use_llm=cfg.reflection)
        self.curriculum = Curriculum(cfg.curiosity, seed)
        self.stats = dict(decisions=0, llm_decisions=0, invalid=0, skill_suggested=0, skill_followed=0, skill_followed_ok=0, filtered_actions=0, n_learn=0, sleeps=0, forgotten=0)
        self.tracer = None          # optional callback(kind, data) - the X-ray viewer hooks in here; no effect when None

    def _t(self, kind, **data):
        if self.tracer:
            self.tracer(kind, data)

    # ------------------------------------------------------------------ curriculum interface
    def next_activity(self):
        return self.curriculum.choose()

    def record_outcome(self, activity, success):
        self.curriculum.record(activity, success)

    # ------------------------------------------------------------------ decide
    def decide(self, task):
        cfg = self.cfg
        options = list(task.actions)
        all_actions = list(options)
        removed = []
        self.stats["decisions"] += 1
        if cfg.memory and cfg.lesson_filter:
            forb = self.memory.forbidden(task.domain, task.props)
            keep = [a for a in options if a not in forb]
            if keep:
                self.stats["filtered_actions"] += len(options) - len(keep)
                removed = [(a, f"avoid {a.replace('_', ' ')} when {p}") for a in options if a in forb for p in task.props if (task.domain, a, p) in self.memory.lessons][:6]
                options = keep
        after_filter = list(options)
        risk = None
        if cfg.worldmodel:
            options = self.wm.shortlist(task.domain, task.props, options, cfg.shortlist_k, rng=self.rng)
            risk = [(a, self.wm.predict(task.domain, task.props, a)) for a in options]
        lessons = [l.text for l in self.memory.retrieve(task.domain, task.props, cfg.n_lessons_in_prompt)] if cfg.memory else None
        sugg = None
        if cfg.skills:
            sugg, _ = self.skills.suggest(task.domain, task.props, options)
            if sugg:
                self.stats["skill_suggested"] += 1
        info = dict(options=options, suggested=sugg)
        ev = dict(domain=task.domain, props=list(task.props), all=all_actions, removed=removed, after_filter=after_filter, options=list(options),
                  risk=risk, lessons=lessons, skill=sugg, prompt=None, reply=None, via_llm=False, invalid=False)
        if len(options) == 1:
            ev["choice"] = options[0]
            self._t("decide", **ev)
            return options[0], info
        prompt = prompts.action_prompt(Nursery.describe(task), options, lessons, sugg.replace("_", " ") if sugg else None, risk)
        choice, raw = self.llm.choose(prompt, options, seed=self.rng.randrange(10 ** 6))
        self.stats["llm_decisions"] += 1
        ev.update(prompt=prompt, reply=raw, via_llm=True)
        if choice is None:
            self.stats["invalid"] += 1
            ev["invalid"] = True
            choice = self.rng.choice(options)
        if sugg and choice == sugg:
            self.stats["skill_followed"] += 1
            info["followed_skill"] = True
        ev["choice"] = choice
        self._t("decide", **ev)
        return choice, info

    # ------------------------------------------------------------------ learn
    def learn_atomic(self, task, action, success, feedback, followed_skill=False):
        cfg = self.cfg
        self.stats["n_learn"] += 1
        culprit = None
        if cfg.memory:
            self.memory.add_episode(task.domain, task.props, action, success, feedback)
        if not success and cfg.reflection:
            refl = self.reflector.reflect(task, action, feedback, self.memory, cfg.deduction)
            culprit = refl.prop
            self._t("reflect", domain=task.domain, action=action, prop=culprit, source=refl.source, feedback=feedback)
            if culprit and cfg.memory:
                self.memory.add_lesson(task.domain, action, culprit)
                les = self.memory.lessons[(task.domain, action, culprit)]
                self._t("lesson", domain=task.domain, action=action, prop=culprit, support=les.support, text=les.text)
        if cfg.memory:
            self.memory.update_with_outcome(task.domain, task.props, action, success)
        if cfg.skills:
            self.skills.record(task.domain, task.props, action, success, culprit)
            if success:
                self._t("skill", domain=task.domain, props=list(task.props), action=action)
        if cfg.worldmodel:
            self.wm.update(task.domain, task.props, action, success, culprit)
            self._t("wm", domain=task.domain, props=list(task.props), action=action, success=success, culprit=culprit)
        if followed_skill and success:
            self.stats["skill_followed_ok"] += 1
        if cfg.memory and cfg.consolidation and self.stats["n_learn"] % cfg.consolidate_every == 0:
            self.stats["sleeps"] += 1
            n = self.memory.consolidate()
            self.stats["forgotten"] += n
            self._t("sleep", forgotten=list(self.memory.last_dropped), lessons=len(self.memory.lessons))

    def learn_composite(self, comp: Composite, actions, success, feedback):
        if success:
            for t, a in zip(comp.parts, actions):
                self.learn_atomic(t, a, True, "It worked.")
            return
        m = re.search(r"step (\d)", feedback)
        if m and self.cfg.memory:
            i = int(m.group(1)) - 1
            self.learn_atomic(comp.parts[i], actions[i], False, feedback)
        elif self.cfg.memory:
            self.memory.add_episode("compose", [p for t in comp.parts for p in t.props], "+".join(actions), False, feedback)

    # ------------------------------------------------------------------ one attempt
    def attempt(self, nursery: Nursery, task, learn=True):
        if isinstance(task, Composite):
            res = [self.decide(t) for t in task.parts]
            acts = [r[0] for r in res]
            ok, fb, cul = nursery.step_composite(task, acts)
            self._t("outcome", domain="compose", props=[list(t.props) for t in task.parts], action="+".join(acts), success=ok, feedback=fb)
            if learn:
                self.learn_composite(task, acts, ok, fb)
            return dict(domain="compose", task=task, actions=acts, success=ok, feedback=fb, culprits=cul)
        a, info = self.decide(task)
        ok, fb, cul = nursery.step(task, a)
        self._t("outcome", domain=task.domain, props=list(task.props), action=a, success=ok, feedback=fb)
        if learn:
            self.learn_atomic(task, a, ok, fb, followed_skill=info.get("followed_skill", False))
        return dict(domain=task.domain, task=task, actions=[a], success=ok, feedback=fb, culprits=cul)

    # ------------------------------------------------------------------ introspection
    def lesson_precision(self):
        if not self.memory.lessons:
            return None
        good = sum(Nursery.true_rule(l.domain, l.prop, l.action) for l in self.memory.lessons.values())
        return good / len(self.memory.lessons)

    def report(self):
        s = dict(self.stats)
        s.update(lessons=len(self.memory.lessons), lesson_precision=self.lesson_precision(), skills=self.skills.size(), episodes=len(self.memory.episodes),
                 reflect_hint=self.reflector.n_hint, reflect_llm=self.reflector.n_llm, reflect_none=self.reflector.n_none, reflect_deduce=self.reflector.n_deduce,
                 stages_unlocked=len(self.curriculum.unlocked))
        return s
