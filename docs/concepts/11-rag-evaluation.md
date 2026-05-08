# 11 — RAG Evaluation with Ragas

## What it is

Ragas is a framework for evaluating RAG pipelines. It computes four metrics that each measure a different failure mode. The key insight is that RAG has two components that can fail independently — the retriever and the generator — and you need separate metrics for each.

## Why it matters for this project

We have zero-hallucination tolerance. "The system answers correctly" is not a testable assertion without a metric. Ragas gives us four concrete numbers. One of them (Faithfulness) is a CI gate — the build fails if it drops below 0.95. This is the signal that the system is trustworthy enough to run in production.

## The four metrics

### Faithfulness ≥ 0.95 (CI deploy-blocker)

**What it measures:** Does every claim in the answer trace back to the retrieved context?

This detects LLM hallucination. If the model makes a claim that isn't supported by any retrieved chunk, Faithfulness drops. In a legal/fiscal system, an unsupported claim could be incorrect tax advice.

Formula: `faithfulness = (claims supported by context) / (total claims in answer)`

Our structured output schema (the `CitedClaim` Pydantic model) already forces claims to have citations. Ragas Faithfulness checks whether those citations actually support the claim.

### Context Precision ≥ 0.85 (warning, human review)

**What it measures:** Of the chunks we retrieved, how many were actually relevant to the answer?

This detects retriever noise. If we retrieved 8 chunks but only 2 were relevant to the correct answer, Context Precision is 0.25. Low precision means we're sending irrelevant context to the LLM — wasting tokens, increasing hallucination risk, and degrading answer quality.

### Context Recall ≥ 0.80 (warning, human review)

**What it measures:** Did we retrieve all the chunks needed to correctly answer the question?

This detects retriever misses. If the correct answer requires knowing both artikel 3.16a lid 1 AND lid 2, but we only retrieved lid 1, Context Recall is 0.5. Low recall means the LLM can't give a complete answer because we didn't give it the right documents.

### Answer Relevancy ≥ 0.85 (warning, human review)

**What it measures:** Does the answer actually address the question asked?

This detects topic drift — the model generated something faithful to the context but didn't answer what was asked. Less common but still a failure mode.

## The golden dataset

50-100 question/answer pairs, hand-curated from the demo corpus, with correct citations.

Stored at `data/golden/golden_set.jsonl`. Each entry:
```json
{
  "question": "Wat is de aftrekbaarheid van een werkruimte aan huis voor een IB-ondernemer?",
  "ground_truth": "Op grond van artikel 3.16a lid 1 Wet IB 2001...",
  "ground_truth_chunk_ids": ["wet_ib_2001_art_3_16a_lid_1", "wet_ib_2001_art_3_16a_lid_2"],
  "user_role": "helpdesk"
}
```

The golden dataset is the regression baseline. New embedding models and new LLM versions are evaluated against it before production rollout.

## CI integration

Faithfulness is the only deploy-blocker. If it drops below 0.95, the GitHub Actions workflow fails. The other three trigger a warning annotation on the PR requiring human review before merge.

This is deliberate: Faithfulness is the hallucination metric. A faithful answer with lower precision (some irrelevant chunks retrieved) might still be correct. A non-faithful answer is wrong by definition.

## Concrete example

Query: "Mag een zzp'er de volledige autokosten aftrekken?"

System retrieves: chunk A (artikel 3.16a), chunk B (artikel 3.17 zakelijke kilometers), chunk C (artikel 3.14 gemengde kosten).

System generates: "Ja, een zzp'er kan de volledige autokosten aftrekken mits..."

Ragas evaluation:
- Faithfulness: 0.4 (claim about "volledige aftrek" is not supported — artikel 3.16a limits it)
- Context Precision: 0.67 (chunk C was noise)
- Context Recall: 0.9 (retrieved the right artikels)
- Answer Relevancy: 0.95 (answered the question)

Faithfulness < 0.95 → **CI build fails.** The model hallucinated a favorable but incorrect interpretation.

## How it appears in our code

TODO — see `src/evaluation/ragas_runner.py` and `data/golden/` once Phase 5 is implemented.

## Self-check questions

1. Faithfulness is 0.4 but Context Recall is 0.9. What does this tell me about where the failure occurred — retriever or generator?
2. Context Precision is 0.3 but Faithfulness is 0.96. The build passes CI. Should I be concerned? What does this tell me?
3. Why is Faithfulness the only CI deploy-blocker rather than all four metrics?
