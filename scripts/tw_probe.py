"""Probe: can we generate and play a TextWorld game on the runner?  Prints the API surface the adapter needs."""
import os, sys, tempfile
import textworld
from textworld import GameOptions
from textworld.challenges import simple
print("textworld", textworld.__version__)
d = tempfile.mkdtemp()
for seed in (1, 2):
    opts = GameOptions(); opts.seeds = seed; opts.path = os.path.join(d, f"g{seed}.z8")
    g = simple.make({"rewards": "dense", "goal": "brief", "test": False}, opts)
    print("made", g, getattr(g, "max_score", None))
    path = textworld.generator.compile_game(g, opts); print("compiled", path)
    if seed == 1: p1 = path
infos = textworld.EnvInfos(admissible_commands=True, objective=True, description=True, inventory=True, score=True, max_score=True, won=True, lost=True)
env = textworld.start(p1, infos)
st = env.reset()
print("OBJ:", st.objective); print("DESC:", st.description[:200]); print("CMDS:", st.admissible_commands[:12], "max", st.max_score)
for c in st.admissible_commands[:3]:
    st2, r, done = env.step(c); print(repr(c), "->", r, done, st2.score, repr(st2.feedback[:80]))
