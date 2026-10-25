"""A live Sarah session for the X-ray viewer: runs the real Brain step by step, collects trace events, and serves state snapshots.
Default LLM mode is the instant stand-in ('stub') so that a benchmark running on Ollama is not disturbed."""
import collections
import dataclasses
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sarah.brain import Brain                                  # noqa: E402
from sarah.config import CONFIGS                               # noqa: E402
from sarah.llm import OllamaLLM, StubLLM                       # noqa: E402
from sarah.world import DOMAINS, STAGE_ORDER, Nursery, Task    # noqa: E402


class Session:
    def __init__(self):
        self.lock = threading.RLock()
        self.running = False
        self.speed = 3.0
        self.reset(0, "full", "stub", "llama3.2:1b")
        threading.Thread(target=self._loop, daemon=True).start()

    # ------------------------------------------------------------------ lifecycle
    def reset(self, seed, cfg_name, llm_mode, model):
        with self.lock:
            self.seed, self.llm_mode, self.model = seed, llm_mode, model
            self.nursery = Nursery(seed)
            self.llm = OllamaLLM(model) if llm_mode == "ollama" else StubLLM()
            self.brain = Brain(CONFIGS[cfg_name], self.llm, seed)
            self.brain.tracer = self._trace
            self.events = collections.deque(maxlen=4000)
            self.eid = 0
            self.tick = 0
            self.outcomes = []
            self.shares = collections.Counter()
            self.cur_task = None
            self.last_error = None

    def _trace(self, kind, data):
        if kind == "decide":                                    # attach ground truth for the viewer's 'reveal hidden rules' overlay (the brain never sees it)
            t = Task(data["domain"], tuple(data["props"]))
            data["truth_forbidden"] = [a for a in t.actions if Nursery.forbidders(t, a)]
        self.emit(kind, **data)

    def emit(self, kind, **data):
        with self.lock:
            self.eid += 1
            self.events.append(dict(id=self.eid, tick=self.tick, kind=kind, data=data))

    # ------------------------------------------------------------------ one task attempt
    def step(self):
        b = self.brain
        act = b.next_activity()
        lp = {a: round(b.curriculum._lp(a), 3) for a in b.curriculum.activities()}
        self.emit("choose", activity=act, lp=lp, unlocked=list(b.curriculum.unlocked), policy=b.curriculum.policy)
        task = self.nursery.sample_composite(b.curriculum.unlocked, "train") if act == "compose" else self.nursery.sample(act, "train")
        self.cur_task = act
        res = b.attempt(self.nursery, task, learn=True)
        before = len(b.curriculum.unlocked)
        b.record_outcome(act, res["success"])
        if len(b.curriculum.unlocked) > before:
            self.emit("unlock", stage=b.curriculum.unlocked[-1])
        self.tick += 1
        self.shares[act] += 1
        self.outcomes.append(int(res["success"]))
        self.emit("done", activity=act, success=res["success"])

    def _loop(self):
        while True:
            if self.running:
                t0 = time.time()
                try:
                    self.step()
                except Exception as e:                           # keep the viewer alive and show the error
                    self.last_error = repr(e)
                    self.emit("error", message=repr(e))
                    self.running = False
                time.sleep(max(0.0, 1.0 / self.speed - (time.time() - t0)))
            else:
                time.sleep(0.05)

    # ------------------------------------------------------------------ controls
    def control(self, c):
        a = c.get("action")
        if a == "run":
            self.running = True
        elif a == "pause":
            self.running = False
        elif a == "step":
            if not self.running:
                try:
                    self.step()
                except Exception as e:
                    self.emit("error", message=repr(e))
        elif a == "speed":
            self.speed = max(0.2, min(40.0, float(c["value"])))
        elif a == "reset":
            self.running = False
            self.reset(int(c.get("seed", 0)), c.get("config", "full"), c.get("llm_mode", "stub"), c.get("model", "llama3.2:1b"))
        elif a == "toggle":
            with self.lock:
                self.brain.cfg = dataclasses.replace(self.brain.cfg, **{c["module"]: c["value"]})
                if c["module"] == "curiosity":
                    self.brain.curriculum.policy = c["value"]
                if c["module"] == "reflection":
                    self.brain.reflector.use_llm = c["value"]
                self.emit("toggle", module=c["module"], value=c["value"])
        return {"ok": True}

    # ------------------------------------------------------------------ views
    def events_since(self, since):
        with self.lock:
            ev = [e for e in self.events if e["id"] > since]
        return dict(events=ev[-400:], last=self.eid)

    def snapshot(self):
        b = self.brain
        with self.lock:
            lessons = [dict(text=l.text, domain=l.domain, action=l.action, prop=l.prop, support=l.support, contra=l.contra, conf=round(l.confidence, 2),
                            true=Nursery.true_rule(l.domain, l.prop, l.action)) for l in list(b.memory.lessons.values())]
            wm = {}
            for d, spec in DOMAINS.items():
                acts, props = spec["actions"], list(spec["forbid"])
                mat = [[(None if b.wm.n.get((d, p, a), 0) == 0 else round((b.wm.s.get((d, p, a), 0) + b.wm.prior) / (b.wm.n[(d, p, a)] + 1.0), 2)) for p in props] for a in acts]
                cnt = [[int(b.wm.n.get((d, p, a), 0)) for p in props] for a in acts]
                truth = [[Nursery.true_rule(d, p, a) for p in props] for a in acts]
                wm[d] = dict(actions=acts, props=props, pred=mat, n=cnt, truth=truth)
            skills = sorted(((k[0], list(k[1]), k[2], v) for k, v in b.skills.exact.items()), key=lambda x: -x[3])[:14]
            cur = b.curriculum
            rates = {a: (round(sum(h[-10:]) / len(h[-10:]), 2) if h else None) for a, h in cur.hist.items()}
            curr = dict(unlocked=list(cur.unlocked), activities=cur.activities(), rates=rates, lp={a: round(cur._lp(a), 3) for a in cur.activities()},
                        shares=dict(self.shares), policy=cur.policy, counts={a: len(h) for a, h in cur.hist.items()})
            rep = b.report()
            return dict(tick=self.tick, running=self.running, speed=self.speed, llm_mode=self.llm_mode, model=self.model, seed=self.seed,
                        cfg=dataclasses.asdict(b.cfg), lessons=lessons, wm=wm, skills=skills, curriculum=curr, stats=rep, llm_calls=self.llm.calls,
                        curve=self.outcomes[-300:], stage_order=STAGE_ORDER, error=self.last_error, configs=list(CONFIGS))
