"""Brain configuration: every module can be switched on/off, which is what the ablation benchmark uses."""
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class BrainConfig:
    name: str = "full"
    memory: bool = True            # episodic store + lessons (retrieved into the prompt)
    reflection: bool = True        # write a lesson after a failure
    lesson_filter: bool = True     # hard-remove actions contradicted by confident lessons before the LLM chooses
    skills: bool = True            # skill library: remember what worked for which properties
    worldmodel: bool = True        # counts-based outcome predictor -> shortlist of the safest actions ("imagination")
    consolidation: bool = True     # periodic "sleep": merge lessons, drop contradicted ones
    deduction: bool = False        # blame-by-elimination: a property that already succeeded with this action is exonerated (works without hints)
    curiosity: str = "lp"          # task chooser: 'lp' (learning progress) | 'random' | 'sequential'
    shortlist_k: int = 3
    n_lessons_in_prompt: int = 4
    consolidate_every: int = 15
    temperature: float = 0.3


CONFIGS = {
    # bare 1B model: no memory of any kind, random task choice
    "bare": BrainConfig("bare", memory=False, reflection=False, lesson_filter=False, skills=False, worldmodel=False, consolidation=False, curiosity="random"),
    # lessons only appear in the prompt (the model may or may not obey them)
    "lessons_in_prompt": BrainConfig("lessons_in_prompt", lesson_filter=False, skills=False, worldmodel=False, curiosity="random"),
    # lessons are enforced architecturally (filter), the LLM picks among the remaining actions
    "lessons_filter": BrainConfig("lessons_filter", skills=False, worldmodel=False, curiosity="random"),
    # counts-based world model only
    "worldmodel_only": BrainConfig("worldmodel_only", memory=False, reflection=False, lesson_filter=False, skills=False, consolidation=False, curiosity="random"),
    # everything except the curiosity-driven curriculum
    "full_random_tasks": BrainConfig("full_random_tasks", curiosity="random"),
    # everything
    "full": BrainConfig("full"),
}

# step 2/3 variants: same brains plus deduction (what a child does when nobody tells them what went wrong)
CONFIGS["lessons_filter_ded"] = BrainConfig("lessons_filter_ded", skills=False, worldmodel=False, curiosity="random", deduction=True)
CONFIGS["full_ded"] = BrainConfig("full_ded", deduction=True)


def variant(cfg: BrainConfig, **kw) -> BrainConfig:
    return replace(cfg, **kw)
