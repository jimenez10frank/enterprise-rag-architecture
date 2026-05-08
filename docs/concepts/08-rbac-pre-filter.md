# 08 — RBAC at the Vector Query Stage

## What it is

Role-Based Access Control (RBAC) in this project means that a user can only receive answers based on documents their role is authorized to see. The critical question — the one the assessment tests explicitly — is: at what stage of the RAG pipeline does this filtering happen?

The answer is: **before HNSW search runs**, as a metadata predicate on the Qdrant query. Not after retrieval. Not in the LLM prompt. In the vector database query itself.

## Why it matters — the mathematical argument

This is the most tested concept in the whole project. I need to be able to explain it cold.

**Post-retrieval filtering is a data leak.** Here's why:

HNSW ranks documents by similarity to the query. If classified chunks exist in the corpus, they compete in that ranking. A classified chunk about "FIOD onderzoek belastingfraude" might rank 3rd for a query about "onverklaard vermogen." Even if we filter it out after the fact and never show it to the user, the fact that it competed changed which unclassified chunks made the top-50. The unclassified chunk that would have been rank 4 is now rank 3 because the classified chunk was ranked 3 and removed. Over many probing queries, an attacker can reconstruct the shape of the classified embedding space from the gaps in results.

**LLM-level filtering is worse.** If the classified chunk is in the model's context window, the generation distribution is conditioned on it. Even if the model is instructed not to use it, side-channel analysis of the output can reveal it.

**Pre-filter is the only safe placement.** The metadata predicate runs during HNSW graph traversal. Classified vectors are structurally present in the index but are not visited when the predicate excludes them. The result set is mathematically identical to one produced from a corpus that never contained the classified documents. There is no way for the user's query to "see" classified content.

## The Qdrant implementation

```python
client.search(
    collection_name="docs",
    query_vector=query_embedding,
    query_filter=Filter(
        must=[
            FieldCondition(
                key="allowed_roles",
                match=MatchAny(any=user.roles),
            )
        ]
    ),
    limit=50,
)
```

The `query_filter` runs **before** HNSW search. This is a Qdrant guarantee, not a Python guarantee. The filter must be enforced server-side. Doing it in Python after the response is post-retrieval filtering.

## The three roles in our system

| Role | Can see |
|------|---------|
| `public` | Public legislation, public case law |
| `helpdesk` | Public + internal policy documents |
| `fiod` | Public + internal + classified investigation materials |

Each chunk's `allowed_roles` list in its payload controls this. A `public` user's query never touches a `fiod`-only chunk.

## The semantic cache RBAC connection

The cache must also be keyed on `role_hash`. Without this, a helpdesk user could ask "wat zijn de tekenen van belastingfraude?" hit a cached response generated for a FIOD user, and receive classified information. The cache is effectively another retrieval path — it needs the same RBAC enforcement. (See TRAP 5, docs/concepts/10-semantic-cache.md.)

## How it appears in our code

TODO — see `src/retrieval/dense_retriever.py` and `src/api/query_handler.py` once Phases 3 and 5 are implemented.

## Self-check questions

1. A user with role `helpdesk` queries the system. A chunk with `allowed_roles: ["fiod"]` exists at rank 5 in the HNSW graph. Walk through what happens to that chunk at the vector query stage.
2. Why is "retrieve everything, then filter in Python" not just slow but actively insecure?
3. A new engineer suggests: "Let's add an extra check in the LLM prompt: 'Do not use classified sources.' Why is that insufficient even with our pre-filter already in place?
