# Sarah Mark 1 — a modular software "child brain" around a tiny local LLM

A prototype of the architecture suggested by the 50-paper study in `../papers`, `../simulations`, `../latex`.
The language model (default **llama3.2:1b via Ollama**) is deliberately weak: Mark 1 tests whether *the surrounding modules*
(memory, reflection, skills, imagination, curiosity) let a weak model learn like a child inside a small developmental world.

```
 task ──►  Memory (lessons)  ──filter──►  World model (imagination: safest k)  ──►  LLM  ──► action
           Skill library ──hint───────────────────────────────────────────────────▲
 outcome ──► Reflection (which property failed?) ──► lessons / skills / world-model updates ──► "sleep" (consolidation)
 Curriculum + curiosity (learning progress) decides *what to practise next* and unlocks the next stage
```

| module | file | role |
|---|---|---|
| world | `sarah/world.py` | the **Nursery**: 4 stages (grasp, carry, stack, tool) + composite two-step tasks, hidden rules, feedback text, train/exam split of property combinations |
| llm | `sarah/llm.py` | Ollama client + tolerant action parser + `StubLLM` for tests |
| prompts | `sarah/prompts.py` | every prompt template |
| memory | `sarah/memory.py` | episodes, lessons with evidence counts, TF-IDF retrieval, consolidation ("sleep") |
| reflection | `sarah/reflection.py` | after a failure: which property caused it (feedback hint, else ask the LLM) |
| skills | `sarah/skills.py` | what worked for which property; generalises to unseen combinations |
| world model | `sarah/worldmodel.py` | counts-based P(success\|action, properties); shortlists the safest actions |
| curriculum | `sarah/curriculum.py` | stage unlocking + task chooser (`lp` learning-progress / `random` / `sequential`) |
| brain | `sarah/brain.py` | **assembly** of the modules, each switchable via `config.py` |
| bench | `sarah/bench.py` | **Sarah-Bench v0**: free play → frozen exam on held-out combinations; ablation suite |

## Run
```
python -m unittest discover -s tests -v                     # 12 module tests, no LLM needed
python run.py --stub --seeds 3 --play 100 --exam 12          # pipeline check with a random stand-in model
python run.py --configs bare,lessons_filter,full --seeds 3 --play 100 --exam 12      # real llama3.2:1b (needs `ollama serve`)
python run.py --model qwen3:4b ...                           # stronger reference model
```
Results are written to `results/bench_*.json` (+ `.md` summary table).

## Benchmark (Sarah-Bench v0)
* **play success / learning curve** — success during free play
* **exam accuracy on unseen property combinations** (transfer), per stage, plus **composite** tasks (skill reuse + credit assignment)
* **repeated-mistake rate**, **LLM calls**, **invalid-reply rate**, **lesson precision** (vs. ground truth), skills, stages unlocked
Ablation configs: `bare`, `lessons_in_prompt`, `lessons_filter`, `worldmodel_only`, `full_random_tasks`, `full`.

## Honest status
Prototype 1. The nursery is a tiny symbolic world; hidden rules are simple property→forbidden-action tables; reflection receives
explicit hints 75 % of the time. It tests the *architecture*, not general intelligence. See `results/` for the latest numbers.
