# Open questions for the owner

| # | Question | Recommendation | Blocks |
|---|---|---|---|
| Q1 | Where does the v5 code live? | A new **private** GitHub repo `Synapse-v5`, cloned from v4 with history, in this folder (V5-D14) | V5-0 |
| Q2 | How much may the V5-2 prototype spend on the paid fallback? | With free models first (V5-D22), the go/no-go can run at $0 with `ALLOW_PAID_FALLBACK=false`. A paid fallback budget is only needed to compare against Claude | V5-2 gate |
| Q3 | ~~Is the forming environment's wording accepted?~~ **Answered 2026-11-14:** yes, with no "Draft" label (a plain status line stays) | | |
| Q4 | Deploy with the full gate, or with a time-boxed waiver and an access code? | A waiver with an access code for demos; the full gate before open public use | V5-9 |
| Q5 | May the textbook corpus be on the server (A-8)? Without it no deployed environment earns `source-verified` | The owner's call; only short cited quotations ever reach a student | V5-9 |
| Q6 | May paraphrases of a question share its cache entry? | Only paraphrases a person adds, until a paraphrase check is measured on labelled pairs | V5-1 (later part) |
| Q7 | The name (A-14) and a licence | Decide before any public deploy | V5-9 |
| Q8 | Are generated environments in Bahasa Melayu in v5's core, or later? | Later (V5-10). Library environments keep their Malay | none |
| Q9 | Who reviews parts before the writer may reuse them? | The owner for now; a teacher when one is found | V5-8 |
| Q10 | How much may pre-building likely twists spend (C4)? | Decide at V5-8 with a measured cost per environment | V5-8 |
| Q11 | Is "the Free lane assistant with templates and components" what `docs/genui-engine.md` section 2 describes (a writer working from pattern templates, stored environments and the Kit plus a reviewed parts library)? | Confirm or correct before V5-2 | V5-2 |
| Q12 | The UTP CodeFest judging criteria for 14 November | Send the rubric if available; it shapes the finale plan | `finale-plan.md` |
| Q13 | Commit the uncommitted v4 documents (the 2026-11-01 research note, changelog lines) to the public v4 repository? | Yes, after a look for anything not fit to publish | V5-0 step 0 |
| Q14 | ~~Will you add an OpenRouter API key to `.env`?~~ **Answered 2026-11-14:** `.env` done (not read by Claude). **Still open:** was $10 of OpenRouter credits bought once? | Yes to both: the key enables the free chain; $10 bought once lifts the free quota from 50 to 1,000 requests a day for good (the credits stay unspent while only free models are used) | V5-2 |
| Q15 | ~~May free providers that may train on prompts serve questions?~~ **Answered 2026-11-14:** yes. Recorded in V5-D22; revisit before any public deploy | | |
