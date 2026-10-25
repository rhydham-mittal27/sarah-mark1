# Sarah Mark 1: real llama3.2:1b benchmark (GitHub Actions)

## step4_textworld  (12 runs)

| mode | train score | HELD-OUT score | held-out win rate | repeated commands | invalid replies | LLM calls |
|---|---|---|---|---|---|---|
| bare | 0.20±0.07 | 0.18±0.08 | 0.00±0.00 | 0.73 | 0.00 | 400 |
| filter | 0.45±0.05 | 0.61±0.00 | 0.00±0.00 | 0.15 | 0.00 | 295 |
| full | 0.66±0.01 | 0.70±0.03 | 0.00±0.00 | 0.04 | 0.00 | 303 |
| prompt_mem | 0.02±0.00 | 0.03±0.02 | 0.00±0.00 | 0.93 | 0.00 | 400 |
