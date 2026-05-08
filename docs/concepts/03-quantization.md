# 03 — Quantization

## What it is

A 3072-dimension vector stored as 32-bit floats takes 3072 × 4 = 12,288 bytes per vector. Quantization compresses that by reducing precision. Scalar quantization maps each float to an int8 (1 byte), achieving 4× compression. Binary quantization goes further — each dimension becomes a single bit, achieving 32× compression. The tradeoff is a small recall loss because the similarity calculations are now approximate.

## Why it matters for this project

At our demo scale (~50 documents, a few thousand chunks) quantization is irrelevant. But the design doc must address 20M+ vectors:

- 20M vectors × 12,288 bytes = ~234 GB raw float32.
- With scalar int8 quantization: ~58 GB. Fits in memory on a reasonable server.
- With binary quantization: ~7 GB. Relevant for archival/historical document collections.

Memory residency directly affects query latency. If vectors spill to disk, latency spikes. Our config sets `always_ram: True` — the scalar quantized vectors stay in RAM.

## Key parameters

```python
"quantization_config": {
    "scalar": {
        "type": "int8",
        "quantile": 0.99,    # clip top/bottom 1% of values before mapping — reduces outlier distortion
        "always_ram": True    # never spill to disk
    }
}
```

**Rescoring:** After HNSW returns top candidates using int8 distances, Qdrant re-scores the top candidates using the original full-precision vectors. This recovers the ~2-3% recall hit from quantization. We enable this with `rescore=True` and `oversampling=2.0` (retrieve 2× as many candidates for rescoring, then trim back to the requested K).

## Scalar vs Binary — when to use each

| Type | Compression | Recall hit | Use case in our project |
|------|-------------|------------|------------------------|
| Scalar int8 | 4× | ~2-3% | Main corpus (legislation, case law) |
| Binary | 32× | ~5-10% | Archived documents, historical versions pre-2010 |

For the active legal corpus, scalar is the right default. The 2-3% recall hit with rescoring is acceptable. Binary is only worth it for cold storage where latency SLAs are relaxed.

## Concrete example

Vector dimension value before quantization: 0.234567 (float32, 4 bytes).
`quantile=0.99` determines the scale: say the 99th percentile of absolute values is 0.85.
Mapping: `int8 = round(0.234567 / 0.85 × 127)` = `round(35.0)` = 35 (1 byte).

At query time, dot products run in int8 — very fast on modern CPUs (SIMD). Then the top-100 candidates get re-scored with full float32 precision.

## How it appears in our code

TODO — see `src/vectorstore/collection.py` (collection creation with `quantization_config` and `search_params` with `rescore=True, oversampling=2.0`).

## Self-check questions

1. We set `quantile=0.99` instead of `1.0`. What problem does this solve?
2. Why do we still store the original full-precision vectors even when using scalar quantization?
3. If I set `always_ram=False` and the server has only 32 GB RAM for a 58 GB scalar-quantized corpus, what happens to query latency?
