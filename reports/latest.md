# Sarah Mark 1: real llama3.2:1b benchmark (GitHub Actions)

## step4_textworld  (15 runs)

| mode | train score | HELD-OUT score | held-out win rate | repeated commands | invalid replies | LLM calls |
|---|---|---|---|---|---|---|
| bare | 0.20±0.07 | 0.18±0.08 | 0.00±0.00 | 0.73 | 0.00 | 400 |
| filter | 0.48±0.03 | 0.61±0.00 | 0.00±0.00 | 0.14 | 0.00 | 295 |
| full | 0.68±0.02 | 0.70±0.01 | 0.00±0.00 | 0.06 | 0.00 | 306 |
| norepeat | 0.32±0.04 | 0.36±0.03 | 0.00±0.00 | 0.46 | 0.00 | 358 |
| prompt_mem | 0.01±0.01 | 0.02±0.02 | 0.00±0.00 | 0.93 | 0.00 | 400 |
