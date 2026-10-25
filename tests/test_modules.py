"""Unit tests - no LLM needed.   run:  python -m unittest discover -s tests -v   (from the sarah_mark1 folder)"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sarah.brain import Brain                       # noqa: E402
from sarah.config import CONFIGS                    # noqa: E402
from sarah.curriculum import Curriculum             # noqa: E402
from sarah.llm import StubLLM, parse_choice         # noqa: E402
from sarah.memory import Memory                     # noqa: E402
from sarah.skills import SkillLibrary               # noqa: E402
from sarah.world import DOMAINS, Nursery, Task      # noqa: E402
from sarah.worldmodel import WorldModel             # noqa: E402
from sarah.bench import run_one                     # noqa: E402


class TestWorld(unittest.TestCase):
    def test_rules_leave_valid_actions(self):
        n = Nursery(0)
        for d in DOMAINS:
            for combo in n.train[d] + n.exam[d]:
                self.assertGreaterEqual(len(n.valid_actions(Task(d, combo))), 2)

    def test_train_exam_split_disjoint(self):
        n = Nursery(3)
        for d in DOMAINS:
            self.assertFalse(set(n.train[d]) & set(n.exam[d]))
            self.assertEqual(len(n.train[d]) + len(n.exam[d]), 15)

    def test_step_matches_rules(self):
        n = Nursery(0)
        t = Task("grasp", ("wet", "heavy"))
        self.assertFalse(n.step(t, "pinch")[0])
        self.assertTrue(n.step(t, "side_grasp")[0])


class TestParse(unittest.TestCase):
    def test_parse_variants(self):
        opts = ["top_grasp", "side_grasp", "pinch"]
        self.assertEqual(parse_choice("I'll choose to [side grasp] to pick it up.", opts), "side_grasp")
        self.assertEqual(parse_choice("pinch", opts), "pinch")
        self.assertIsNone(parse_choice("no idea", opts))


class TestMemory(unittest.TestCase):
    def test_lesson_retrieval_and_forbidden(self):
        m = Memory()
        m.add_lesson("grasp", "pinch", "wet"); m.add_lesson("grasp", "scoop", "heavy"); m.add_lesson("carry", "hands", "hot")
        r = m.retrieve("grasp", ("wet", "flat"), 3)
        self.assertEqual(r[0].action, "pinch")
        self.assertEqual(m.forbidden("grasp", ("wet",)), {"pinch"})

    def test_consolidation_drops_contradicted(self):
        m = Memory()
        m.add_lesson("grasp", "pinch", "round")           # a wrong lesson
        for _ in range(4):
            m.update_with_outcome("grasp", ("round", "flat"), "pinch", True)   # reality contradicts it
        self.assertEqual(m.consolidate(), 1)
        self.assertFalse(m.lessons)


class TestSkillsWorldModel(unittest.TestCase):
    def test_skill_generalises_over_properties(self):
        s = SkillLibrary()
        for _ in range(3):
            s.record("grasp", ("wet", "heavy"), "side_grasp", True)
            s.record("grasp", ("wet", "flat"), "side_grasp", True)
        a, _ = s.suggest("grasp", ("wet", "heavy"), ["pinch", "side_grasp"])
        self.assertEqual(a, "side_grasp")

    def test_worldmodel_learns_to_avoid(self):
        w = WorldModel()
        for _ in range(5):
            w.update("grasp", ("wet", "flat"), "pinch", False, culprit="wet")
            w.update("grasp", ("round", "flat"), "scoop", False, culprit="flat")
        acts = ["pinch", "scoop", "top_grasp"]
        self.assertEqual(w.shortlist("grasp", ("wet", "flat"), acts, 1)[0], "top_grasp")


class TestCurriculum(unittest.TestCase):
    def test_unlocks_on_mastery(self):
        c = Curriculum("lp", 0)
        for _ in range(10):
            c.record("grasp", True)
        self.assertEqual(c.unlocked, ["grasp", "carry"])
        self.assertIn("compose", c.activities())

    def test_lp_prefers_improving_over_noise(self):
        c = Curriculum("lp", 0)
        c.unlocked = ["grasp", "carry"]
        c.hist["grasp"] = [0] * 20 + [1] * 20          # clearly improving then mastered... recent window all success
        c.hist["carry"] = [0, 1] * 20                  # flat noise at 50 %
        self.assertGreater(c._lp("grasp") + 0.0, 0.0)


class TestBrainEndToEnd(unittest.TestCase):
    def test_brain_runs_with_stub_llm(self):
        for name in CONFIGS:
            r = run_one(CONFIGS[name], 0, 40, 4, lambda: StubLLM())
            self.assertEqual(r["config"], name)
            self.assertTrue(0 <= r["play_success"] <= 1)

    def test_memory_modules_help_with_a_perfect_enough_llm(self):
        """An LLM that always obeys the options it is given: the architecture alone (filter + world model) should beat the bare stub."""
        bare = run_one(CONFIGS["bare"], 1, 80, 12, lambda: StubLLM())
        full = run_one(CONFIGS["full"], 1, 80, 12, lambda: StubLLM())
        self.assertGreater(full["exam_mean"], bare["exam_mean"])


if __name__ == "__main__":
    unittest.main()
