import os, sys, unittest, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sarah.llm import StubLLM
from sarah.tw import TWAgent, run_mode


class S:
    def __init__(self, room, cmds, score=0, fb="", won=False):
        self.description, self.admissible_commands, self.score, self.feedback, self.won = f"-= {room} =-\nstuff", cmds, score, fb, won
        self.objective, self.max_score = "get the apple", 2


class FakeEnv:
    def reset(self):
        self.score = 0
        return S("Kitchen", ["examine table", "go north", "take apple", "look", "inventory"], 0)

    def step(self, c):
        if c == "take apple" and self.score == 0:
            self.score = 2
        return S("Kitchen", ["examine table", "go north", "take apple", "look"], self.score, "ok", self.score == 2), 0, self.score == 2


class FakeGames:
    def make(self, seed):
        return FakeEnv()


class T(unittest.TestCase):
    def test_modes_run_and_learn(self):
        for mode in ("bare", "prompt_mem", "filter", "full"):
            r = run_mode(mode, 0, FakeGames(), StubLLM(random.Random(1)), n_train=3, n_eval=3, max_steps=6, log=lambda *a: None)
            self.assertIn("eval_score", r)
        ag = TWAgent("full", StubLLM(), 0)
        ag.play(FakeEnv(), 6, learn=True)
        self.assertGreater(ag.hits["take"], 0)

    def test_filter_drops_tried_commands(self):
        ag = TWAgent("filter", StubLLM(), 0)
        st = FakeEnv().reset()
        cmd, _ = ag.decide(st, [], {"examine table", "go north"})
        self.assertEqual(cmd, "take apple")


if __name__ == "__main__":
    unittest.main()
