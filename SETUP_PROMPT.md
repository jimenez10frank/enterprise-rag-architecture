# SETUP_PROMPT.md — Project Kickoff

> Use this prompt the very first time you open Claude Code in the empty repo. Copy everything between the `---` markers. Paste it as your first message in Claude Code.

---

I am starting a project called `legal-rag-nl`. It is a production RAG system
for Dutch legal and fiscal documents. The repo currently contains a set of MD
files at the root: `CLAUDE.md`, `TRAPS.md`, `STACK.md`, `ROADMAP.md`,
`PROGRESS.md`, `PROJECT_STRUCTURE.md`, `WORKFLOW.md`. There is no code yet.

**Step 1 — Read.** Read all 8 MD files at the repo root in this order before anything else:

1. `ASSESSMENT.md`
2. `CLAUDE.md`
3. `TRAPS.md`
4. `STACK.md`
5. `ROADMAP.md`
6. `PROGRESS.md`
7. `PROJECT_STRUCTURE.md`
8. `WORKFLOW.md`

**Step 2 — Summarize.** After reading, in your response, give me:

- A 4-sentence summary of what this project is and what we're building.
- The current phase and sub-phase from `PROGRESS.md`.
- The next concrete step.
- Any contradictions, ambiguities, or missing information you noticed across the docs.
- 1-3 clarifying questions if anything is unclear.

**Step 3 — Wait.** Do NOT write any code in this first response. Do not create any files. Do not run any commands. Just read, summarize, and ask questions. I will tell you when to proceed.

**Constraints (read these too):**

- Every architectural choice has been pre-committed in `STACK.md`. Do not deviate without asking.
- Every "trap" in `TRAPS.md` is a non-negotiable system requirement. Re-read them before any module they apply to.
- I am a TypeScript developer doing my first serious Python project. Explain WHY in code comments, not just WHAT.
- I want to deeply understand what we build. After every sub-phase, you will quiz me with 3 comprehension questions before we move on.
- Definition of done for any sub-phase: code works + tests pass + comprehension quiz passed + `PROGRESS.md` updated + commit made.

When you are ready, respond with the summary, your review of any issues, and your questions. I will then either answer questions or tell you to proceed to sub-phase 0.1.

---

## After I approve the kickoff

**For each subsequent sub-phase, use this template:**

---

We are starting sub-phase **[X.Y]** from `ROADMAP.md`.

**Goal:** [paste the sub-phase description from ROADMAP.md].

**Read first:**

- `docs/concepts/[NN-topic.md]` (if relevant)
- `docs/decisions/[NNN-...md]` (if relevant)
- `TRAPS.md` TRAP **[N]** (if applicable)

**Constraints (do NOT violate):**

- [list any TRAPS.md items that apply]
- [list any STACK.md commitments that apply]

**Definition of done:**

1. Code exists and works.
2. Tests pass.
3. You ask me 3 comprehension questions and I answer correctly.
4. `PROGRESS.md` updated.
5. Commit made.

**Please:**

1. Confirm you've read the relevant context.
2. Outline your implementation plan in 3-5 bullets.
3. Wait for my OK before writing any code.

---

## At the end of every session

**Use this prompt:**

---

We're ending this session. Please:

1. Update `PROGRESS.md`:
   - Move completed sub-phases from "Doing now" to "Done".
   - Move next sub-phases from "Next" to "Doing now".
   - Update "Last session summary" with what we did today.
   - Add anything to "Open questions" that needs my input next time.
   - Update the velocity log if a phase completed.

2. If we made architectural decisions, ensure they have ADRs in `docs/decisions/`.

3. Stage and commit all changes with descriptive messages (one commit per sub-phase if possible). Push to origin.

4. Tell me explicitly what the next session should start with.

---

## Things to paste verbatim when the agent drifts

**When it starts coding before reading:**

> Stop. Re-read `CLAUDE.md`. The session-start ritual requires you to read all 8 MD files and summarize before any code. Restart from there.

**When it suggests something not in `STACK.md`:**

> That's a deviation from `STACK.md`. Surface the choice — what are we losing, what are we gaining, is this a permanent stack change or a one-off? I will decide; do not silently substitute.

**When it uses shortcut language ("let me just," "for simplicity," "good enough"):**

> That phrase is a shortcut signal. Re-evaluate against `TRAPS.md` and `ROADMAP.md`. Are you skipping a required step?

**When it skips the comprehension questions:**

> You haven't quizzed me yet. The sub-phase is not done until I've answered 3 questions. Ask them now.

**When it forgets prior context:**

> Read `PROGRESS.md` and `docs/decisions/` before continuing. The state is in those files.
