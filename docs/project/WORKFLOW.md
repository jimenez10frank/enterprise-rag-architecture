# WORKFLOW.md — Working with Claude Code

> Patterns for getting reliable output from Claude Code on this project. The single biggest mistake on a project like this is letting the AI run wide open. These patterns keep it bounded.

---

## Core principle

**I decide the WHAT and WHY. Claude Code produces the HOW. I verify and learn.**

The repo's MD files exist so the agent has context. The prompt patterns below exist so the agent stays bounded within that context.

---

## Session start ritual

**Every session begins with this prompt:**

```
Read these files in order before doing anything:
1. ASSESSMENT.md
2. CLAUDE.md
3. TRAPS.md
4. STACK.md
5. ROADMAP.md
6. PROGRESS.md
7. PROJECT_STRUCTURE.md
8. WORKFLOW.md (this file)

Then:
- Summarize the current phase and the specific sub-phase from PROGRESS.md.
- State the next concrete step you intend to take.
- List any contradictions or ambiguities you noticed across the docs.
- Ask me 1-3 clarifying questions if anything is unclear.

Do not write any code in this response. Read, summarize, align, then I will tell you to proceed.
```

If the agent skips this and starts coding, stop it. Re-paste the prompt.

---

## Sub-phase prompt template

For each sub-phase from `ROADMAP.md`, use this template:

```
We are starting sub-phase [X.Y] from ROADMAP.md.

The goal is: [paste the sub-phase description].

Relevant context:
- Concept doc: docs/concepts/[NN-topic.md] (read this first)
- Decisions: docs/decisions/[NNN-...md] (if any)
- Trap: TRAPS.md TRAP [N] (if applicable)

Constraints (do NOT violate):
- [list any TRAPS.md items that apply to this sub-phase]
- [list any STACK.md constraints that apply]

Definition of done:
1. The code exists and works.
2. Tests pass (where applicable).
3. You have asked me 3 comprehension questions and I have answered them.
4. PROGRESS.md is updated.

Please:
1. Confirm you've read the relevant context.
2. Outline the implementation plan in 3-5 bullets.
3. Wait for my OK before writing code.
```

The pause-for-OK is the magic ingredient. It's where 80% of bad code gets stopped before it's written.

---

## Mid-implementation prompts

If the agent is actively coding and you notice drift:

**"Stop and re-read TRAPS.md TRAP [N]. Are you about to violate it?"**

**"This is starting to feel generic. What about this code is specific to the legal-document use case?"**

**"Walk me through why you chose [X] over [Y]. If both are valid, surface the choice — don't make it silently."**

---

## End-of-sub-phase ritual

After a sub-phase's code is written and tests pass:

```
Sub-phase [X.Y] code is done. Before we move on:

1. Quiz me on what we just built. Ask 3 questions ranging from basic to deep.
   Don't give answers until I attempt each one.
   Be strict — these questions may come up in any technical discussion.

2. After the quiz:
   - If I got all 3 right: update PROGRESS.md (move X.Y to Done, advance Doing now).
   - If I got any wrong: explain the right answer, point me to the relevant
     docs/concepts/ doc to revise, and we revisit before moving on.

3. After the quiz, draft a commit message for what we did and propose it.
```

This is the most important ritual. It is the one that turns "AI did the work" into "I built this with AI assistance and I understand it."

---

## End-of-session ritual

```
We're ending this session. Please:

1. Update PROGRESS.md:
   - Move completed sub-phases from "Doing now" to "Done".
   - Move next sub-phases from "Next" to "Doing now".
   - Update "Last session summary".
   - Add anything to "Open questions" that needs my input next time.
   - Update the velocity log if a phase completed.

2. If we made architectural decisions, ensure they have ADRs in docs/decisions/.

3. Stage and commit all changes with descriptive messages (one commit per
   sub-phase if possible).

4. Tell me explicitly what the next session should start with.
```

---

## When the agent suggests a deviation from STACK.md

The agent will sometimes suggest alternative libraries or patterns. The reflex is:

```
That's a deviation from STACK.md. Before we adopt it:
- What are we losing if we stick with the committed choice?
- What are we gaining with your suggestion?
- Is this a permanent stack change (update STACK.md and add an ADR)
  or a one-off (don't change STACK.md, just note the local exception)?

I will decide; do not silently substitute.
```

---

## When the agent says "let me just..."

If the agent's response contains "let me just," "for simplicity I'll," "we can skip this for now," or "this is good enough" — STOP. These are shortcut signals. Re-prompt:

```
That phrase is a shortcut signal. Re-evaluate against TRAPS.md and ROADMAP.md.
Is the shortcut you're proposing acceptable, or are you trying to skip a step
that matters for the system requirements?
```

---

## Concept-doc workflow (Phase 1)

Concept docs are NOT written by Claude Code. They are written in my own words. Claude's role is to teach, then quiz, then review.

**Step 1 — In regular Claude.ai chat (not Claude Code):**

```
Explain [topic] to a fullstack developer who knows TypeScript and Postgres
but has never touched ML/RAG production patterns. Use analogies from web dev
where possible. Cover:
- What it is.
- Why it matters specifically for our use case (RAG over Dutch legal
  documents at 20M-chunk scale).
- The key parameters or decisions involved.
- One concrete example with numbers.

Then give me 5 self-check questions of varying difficulty. Don't include
answers — I'll attempt them and ask if I'm stuck.
```

**Step 2 — Write `docs/concepts/NN-topic.md` in your own words.** 200-500 words. If you can't write it without copying Claude's words, you don't understand it yet.

**Step 3 — Paste the doc into Claude Code:**

```
I just wrote docs/concepts/NN-topic.md. Read it and:
- Confirm it's accurate.
- Flag anything missing that we'll need when implementing.
- Don't suggest stylistic changes — these are MY notes in MY voice.
```

---

## Architectural Decision Records (ADRs)

Whenever an architectural choice is made, write an ADR.

**File:** `docs/decisions/NNN-short-title.md`

**Template:**

```markdown
# NNN. [Title]

**Date:** YYYY-MM-DD
**Status:** Accepted

## Context
What problem are we solving? What's the situation that requires a decision?

## Options Considered
1. **Option A:** description, pros, cons.
2. **Option B:** description, pros, cons.
3. **Option C:** description, pros, cons.

## Decision
We chose [option]. Reasoning:
- [Reason 1]
- [Reason 2]

## Consequences
What does this make easy? What does this make hard? What's the rollback path?

## References
- TRAPS.md TRAP [N] (if relevant)
- [external links if any]
```

ADRs are numbered sequentially. Once accepted, they are not edited (write a new one to supersede).

---

## What NOT to ask Claude Code

- "Just figure it out." — Always give explicit constraints.
- "Build the whole thing." — Always work in sub-phases.
- "Is this good?" — Be specific: "does this satisfy [specific requirement]?"
- "Use whatever you think is best." — Architectural choices are mine, with Claude's input.

---

## My debugging discipline

When the agent hits an error during implementation:

1. **Don't paste the error and say "fix it."** Instead, paste the error and ask: *"What do you think this error means? What are the likely causes? Don't fix anything yet."*

2. **Read the agent's diagnosis.** Verify it matches your understanding.

3. **Then say "OK, please fix it."** This forces the agent to articulate before acting, which prevents random shotgun fixes.

---

## When to use regular Claude.ai vs Claude Code

- **Regular Claude.ai chat:** learning concepts, exploring options, drafting prose for design docs and READMEs, brainstorming. No file context needed.
- **Claude Code:** anything that touches files in the repo. Implementation. Tests. Refactoring. Anything where reading existing code is necessary.

Don't use Claude Code for "explain HNSW to me" — that's a regular chat task and burns Code context for no benefit. Don't use regular chat for "modify the chunker" — it has no file access, you'll end up copy-pasting and making mistakes.

---

## The non-negotiable comprehension test

Before any sub-phase is marked done, answer 3 comprehension questions correctly. The fastest way to know whether AI assistance has produced understanding or imitation: try to explain it without the AI. If you can't, the sub-phase is not done — go back to the concept doc, re-learn, then revisit. There is no shortcut here.
