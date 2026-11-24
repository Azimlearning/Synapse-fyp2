# Risks

| # | Risk | Likelihood | Impact | Response |
|---|---|---|---|---|
| R1 | Build Script does not shrink the reply as hoped (twists still need lots of custom drawing) | Medium | High: speed targets missed | The V5-2 go/no-go gate measures it on 3 twists before the pipeline is rebuilt. Grow Kit scenes and the parts library (C3) from the gap log |
| R2 | The writer misuses Kit parts (wrong arguments, wrong wiring) more than v4's planner did | Medium | Medium: more retries | Per-line validation with the reason fed back; v4's PLAN rules move into the validator; worked examples per pattern template |
| R3 | A streamed draft shows something the checks then reject, and the student remembers it | Medium | Medium | The forming Environment shows no numbers and nothing operable; a status line shows it is still being checked; text sections pass the cheap checks first; the reader still gates the live environment (V5-D05, accepted without a Draft label) |
| R4 | The virtual clock or a warm browser lowers detection | Low | High | Accepted only if the L6 rate holds; hostile set reruns; fresh context per environment |
| R5 | Formula recomputation gives false confidence ("it was recomputed") | Medium | Medium | Per-part badge says "written by the model, recomputed", and the label stays `model-checked` |
| R6 | Cache serves a wrong environment | Low | High | C1 is exact-key only; paraphrases added only by a person or a measured check; flags evict (v4) |
| R7 | Parts library spreads a subtle error to many environments | Low | High | Parts become offerable only after review; promotion to the Kit needs a registration suite; a flag withdraws the part and every environment using it |
| R8 | Starting from a v4 copy carries cruft | High | Low | One pruning commit in V5-0; the suite must stay green after it |
| R9 | v5 work leaks into v4 or its public mirror | Low | High | Separate private repo; v4 remote read-only; never merge v5 into v4 |
| R10 | Paid runs exceed what the owner expects | Low | Medium | Every run states its cost and waits; ledger cap enforced before sending |
| R11 | Model or API changes (deprecations, fast mode availability) | Medium | Low | Model ids re-checked before each paid run (v4 rule); tier chosen by measurement |
| R12 | Scope grows before the core is green | High | High | Roadmap order; "never build the second of anything until the first is green" |
