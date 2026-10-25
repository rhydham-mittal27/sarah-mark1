# Sarah Mark 1: real llama3.2:1b benchmark (GitHub Actions)

## step1_baseline  (4 runs)

| config | play success | exam (unseen combos) | exam composite | repeated mistakes | LLM calls | lessons (precision) | stages |
|---|---|---|---|---|---|---|---|
| bare | 0.62±0.00 | 0.62±0.00 | 0.50±0.00 | 0.00 | 20 | - | 1.0 |
| full | 0.62±0.00 | 0.38±0.00 | 0.00±0.00 | 0.00 | 21 | 3 (1.00) | 1.0 |
| lessons_filter | 0.62±0.00 | 0.62±0.00 | 0.00±0.00 | 0.00 | 21 | 3 (1.00) | 1.0 |
| lessons_in_prompt | 0.62±0.00 | 0.38±0.00 | 0.50±0.00 | 0.00 | 21 | 3 (1.00) | 1.0 |
