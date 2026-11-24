# How to start building v5: from scratch, or from a copy of v4?

> **Recommendation: start from a copy of v4, as a new private repository that keeps v4's git history. Then prune and replace the pipeline.** Do not start from scratch, and do not build v5 inside the v4 repository.

## The three options

| | A. From scratch | B. Keep building in the v4 repo | **C. New repo from a copy of v4 (recommended)** |
|---|---|---|---|
| What you keep | Nothing; only ideas and ports | Everything | Everything you choose to keep, with history |
| Work before v5's first new feature | Rebuild the Kit (65 entries, 26 apparatus parts, about 35 cited science models), the verifier (L6 suite of about 224 planted defects), about 1,400 Python tests and 700 Kit tests, 30 environments with proved citations, Bahasa Melayu, the web shell | None | A pruning pass and a green baseline |
| Risk to the trust engine | High: every check must be re-earned, and v4's rule says never build the second of anything before the first is green | Low | Low |
| Risk to v4 and the final | None | **High**: v4 is public (since 7 Nov) and frozen for 14 Nov, and its `codefest` mirror merges from `main` | None: v4 is untouched |
| Clean history and docs | Clean | v5's rewrite mixed into v4's record | v4's history kept, v5 starts its own changelog and decisions |
| When it makes sense | When the old code is the problem. It is not: the Kit and verifier are v5's foundation | For small continuous changes, not a redesign | A redesign that keeps the foundation |

**Why not from scratch.** v5 changes how an environment is written and shown: the pipeline (`api/pipeline/`), the prompts, part of the web UI. It keeps what makes Synapse trustworthy: the Kit, the verifier, the gate, the sandbox, the citations and the ledger. Rebuilding those would cost more than all of v5's new work, and it would throw away the measured detection rate that the pitch depends on.

**Why not inside v4.** v4 is the product judges see on 14 November and the public record of the competition entries. A half-built v5 pipeline must never reach it.

## Steps

Do these after the owner answers Q1. Copying earlier is safe (v4 is not changed), but **no v5 work merges back into v4**.

**0. In v4, first.** Commit the uncommitted research note and changelog lines from 1 to 9 November, so the copy includes them. That needs the owner's go: it is a commit to a public repository.

**1. Make the copy.** A local clone copies only committed files, so `.env`, `node_modules`, `.venv` and the local databases stay behind.

```
cd C:/Users/User/Documents/Coding/Hackathon/Genui
git clone --origin v4 Synapse-V4 _v5code
```

**2. Bring these design documents in, and put the code where this folder is.**

```
mkdir _v5code/refdocs/v5
# finale-plan.md holds event context: it goes to the event folder, never into the product repo
mv Synapse-v5/finale-plan.md "UTP Codefest Hackathon/finale-plan-v5.md"
cp -r Synapse-v5/* _v5code/refdocs/v5/
# check the copy, then:
rm -r Synapse-v5
mv _v5code Synapse-v5
```

**3. Give it its own remote.** The owner creates a **private** GitHub repository `Synapse-v5`. Then:

```
cd Synapse-v5
git remote add origin https://github.com/Azimlearning/Synapse-v5.git
git tag v5-start
git push -u origin main --tags
```

Keep the `v4` remote for reading only. A fix needed in both goes to v4 first and is merged into v5, never the other way round.

**4. Keep it out of the GenUI repository.** Add `Synapse-v5/` to `Genui/.gitignore`, as `Synapse-V4/` is (Genui `PUBLISHING.md`).

**5. Local setup, as v4.**

```
uv sync
pnpm install
pnpm --filter @synapse/kit build
pnpm codegen:check
uv run playwright install chromium
```

The owner copies `.env` by hand (it is blocked to Claude's tools). Keep `CORPUS_DIR` pointing outside the repository.

**6. Baseline (V5-0).** Run v4's full suite once, unchanged, and record it in `STATUS.md`: pytest, Kit and web tests, L6, hostile, smoke, environments build. v5 starts from a known green state. Get CI green on GitHub (v4's last four runs failed or were cancelled).

**7. Prune.** Remove, in one commit, what v5 drops (`what-changes-from-v4.md`):

- The planner-then-Free orchestration paths and `LANE_PREFERENCE`. Keep the plan checks' rules for the Build Script validator.
- Prompt files no longer used. Keep only the latest of each and the new v5 packs.
- Event-specific files and guides (`deploy_hackastone.md`, `CODEFEST` context). Business folders stay ignored.
- Local clutter (old `environments.*.db` copies).

Re-run the suite: the kept parts must still pass.

**8. Replace the brief.** Move `refdocs/v5/CLAUDE.md` to the root and mark v4's PRD as the inherited baseline. Start `refdocs/changelog/CHANGELOG.md` and `DECISIONS.md` for v5 with V5-D01 onward.

**9. Version the Kit.** The first behaviour change bumps the Kit to 0.2.0 (hard constraint 6). Stored environments are marked stale and rebuilt.

**Provenance (v4 rule 5).** Git history preserves where every file came from, so files kept from v4 need no header comment. Add a `PROVENANCE.md` that names the v4 commit at `v5-start`. Files ported from other projects keep their headers.

## What lives where afterwards

| Folder | Holds |
|---|---|
| `Genui/Synapse-V4` | v4, frozen; public repo and the CodeFest mirror |
| `Genui/Synapse-v5` | v5 code and these documents under `refdocs/v5/`; private repo |
| `Genui/research` | The owner's GenUI research (unchanged) |
