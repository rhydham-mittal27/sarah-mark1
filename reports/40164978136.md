# Sarah Mark 1: real llama3.2:1b benchmark (GitHub Actions)

## step1_baseline  (12 runs)

| config | play success | exam (unseen combos) | exam composite | repeated mistakes | LLM calls | lessons (precision) | stages |
|---|---|---|---|---|---|---|---|
| bare | 0.49±0.10 | 0.44±0.06 | 0.29±0.11 | 0.59 | 165 | - | 2.0 |
| full | 0.69±0.03 | 0.62±0.01 | 0.40±0.09 | 0.10 | 171 | 16 (0.94) | 2.7 |
| lessons_filter | 0.65±0.03 | 0.52±0.04 | 0.27±0.09 | 0.21 | 169 | 18 (0.92) | 3.0 |
| lessons_in_prompt | 0.46±0.02 | 0.28±0.05 | 0.20±0.09 | 0.64 | 168 | 15 (0.88) | 2.3 |

## step2_nohint  (15 runs)

| config | play success | exam (unseen combos) | exam composite | repeated mistakes | LLM calls | lessons (precision) | stages |
|---|---|---|---|---|---|---|---|
| bare | 0.46±0.03 | 0.40±0.01 | 0.09±0.03 | 0.62 | 163 | - | 2.0 |
| full | 0.60±0.04 | 0.58±0.04 | 0.27±0.14 | 0.43 | 184 | 11 (0.55) | 2.0 |
| full_ded | 0.61±0.02 | 0.57±0.03 | 0.18±0.03 | 0.46 | 178 | 11 (0.77) | 2.3 |
| lessons_filter | 0.51±0.01 | 0.41±0.05 | 0.22±0.11 | 0.52 | 183 | 13 (0.63) | 2.3 |
| lessons_filter_ded | 0.54±0.04 | 0.46±0.02 | 0.29±0.06 | 0.49 | 178 | 11 (0.79) | 2.0 |

## step3_noisy  (15 runs)

| config | play success | exam (unseen combos) | exam composite | repeated mistakes | LLM calls | lessons (precision) | stages |
|---|---|---|---|---|---|---|---|
| bare | 0.49±0.05 | 0.43±0.06 | 0.18±0.06 | 0.49 | 164 | - | 2.0 |
| full | 0.51±0.03 | 0.57±0.07 | 0.33±0.11 | 0.37 | 172 | 19 (0.61) | 2.0 |
| full_ded | 0.49±0.04 | 0.58±0.03 | 0.29±0.16 | 0.23 | 167 | 20 (0.65) | 2.0 |
| lessons_filter | 0.52±0.04 | 0.42±0.02 | 0.22±0.03 | 0.20 | 174 | 17 (0.69) | 2.3 |
| lessons_filter_ded | 0.57±0.08 | 0.36±0.05 | 0.20±0.14 | 0.30 | 171 | 16 (0.59) | 2.0 |
