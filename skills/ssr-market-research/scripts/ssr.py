#!/usr/bin/env python3
"""Semantic Similarity Rating (SSR) engine.

Maps free-text survey/concept-test responses to Likert distributions via embedding
similarity to anchor statements, then aggregates to survey-level intent estimates.

Implements the method from:
  Maier et al. (2025), "LLMs Reproduce Human Purchase Intent via Semantic Similarity
  Elicitation of Likert Ratings", arXiv:2510.08338.

Per-response mapping (paper eq.): for a response t and an anchor set with reference
statements {sigma_r}, with similarities gamma(sigma_r, t) = cosine(v_sigma_r, v_t):
    p'(r) ∝ gamma(sigma_r, t) - min_l gamma(sigma_l, t)
normalize so sum_r p'(r) = 1. Optional temperature: p(r) ∝ p'(r)^(1/T). Average the PMF
across all anchor sets. Aggregate across respondents by averaging PMFs.

Usage:
    python3 ssr.py --responses responses.json --anchors anchors.json --out results.json
        [--temperature 1.0] [--backend local|openai] [--model NAME]

Input files:
    responses.json : [{"persona_id","segment","concept","response_text"}, ...]
    anchors.json   : {"scale":[1,2,3,4,5], "labels":{...},
                      "sets":[{"1":"...",...,"5":"..."}, ... up to 6 ]}
"""
import argparse
import json
import os
import sys
import numpy as np


def load_dotenv(*paths):
    """Minimal .env loader: set vars from the first existing file, without overwriting
    anything already in the environment. No external dependency."""
    for p in paths:
        if not p or not os.path.isfile(p):
            continue
        for line in open(p):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)
        break


# ---------------------------------------------------------------- embeddings
def make_embedder(backend, model):
    """Return a function: list[str] -> np.ndarray (n, d)."""
    if backend == "openai":
        from openai import OpenAI  # lazy import
        client = OpenAI()
        mdl = model or "text-embedding-3-small"

        def embed(texts):
            # batch in chunks to stay within request limits
            out = []
            for i in range(0, len(texts), 256):
                chunk = texts[i : i + 256]
                resp = client.embeddings.create(model=mdl, input=chunk)
                out.extend([d.embedding for d in resp.data])
            return np.asarray(out, dtype=np.float64)

        return embed

    # default: local static embeddings, no torch / no API key
    from model2vec import StaticModel
    sm = StaticModel.from_pretrained(model or "minishlab/potion-base-8M")

    def embed(texts):
        return np.asarray(sm.encode(list(texts)), dtype=np.float64)

    return embed


def cosine(a_rows, b_rows):
    """Cosine similarity matrix between rows of a (n,d) and b (m,d) -> (n,m)."""
    an = a_rows / (np.linalg.norm(a_rows, axis=1, keepdims=True) + 1e-12)
    bn = b_rows / (np.linalg.norm(b_rows, axis=1, keepdims=True) + 1e-12)
    return an @ bn.T


# ---------------------------------------------------------------- ssr core
def response_pmf(sim_per_set, temperature):
    """sim_per_set: list of 1-D arrays (one per anchor set), each length P (Likert points).
    Returns averaged PMF over the P points."""
    pmfs = []
    for sims in sim_per_set:
        adj = sims - sims.min()                 # subtract minimum-similarity reference
        s = adj.sum()
        p = adj / s if s > 0 else np.full_like(adj, 1.0 / len(adj))
        if temperature != 1.0:
            p = p ** (1.0 / temperature)
            p = p / p.sum()
        pmfs.append(p)
    return np.mean(pmfs, axis=0)


def summarize(pmf, scale):
    scale = np.asarray(scale, dtype=np.float64)
    mean = float((pmf * scale).sum())
    var = float((pmf * (scale - mean) ** 2).sum())
    top2 = float(pmf[-2:].sum())            # strong intent (top two Likert points)
    bottom = float(pmf[0])                  # hard "no"
    return {
        "mean": round(mean, 3),
        "std": round(var ** 0.5, 3),
        "top2box": round(top2, 3),
        "bottombox": round(bottom, 3),
        "pmf": [round(x, 4) for x in pmf.tolist()],
    }


def aggregate(pmfs, scale):
    arr = np.vstack(pmfs)
    mean_pmf = arr.mean(axis=0)
    out = summarize(mean_pmf, scale)
    out["n"] = len(pmfs)
    return out


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Score free-text responses with SSR.")
    ap.add_argument("--responses", required=True)
    ap.add_argument("--anchors", required=True)
    ap.add_argument("--out", default="results.json")
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--backend", choices=["local", "openai"], default="openai")
    ap.add_argument("--model", default=None)
    args = ap.parse_args()

    # pick up OPENAI_API_KEY (etc.) from a local .env if not already in the environment
    load_dotenv(".env", os.path.expanduser("~/.env"))

    # openai is the default backend; fall back to local embeddings if no key is available
    if args.backend == "openai" and not os.environ.get("OPENAI_API_KEY"):
        print("No OPENAI_API_KEY found — falling back to local embeddings "
              "(pass --backend local to silence).", file=sys.stderr)
        args.backend = "local"

    responses = json.load(open(args.responses))
    anchors = json.load(open(args.anchors))
    scale = anchors["scale"]
    points = [str(s) for s in scale]
    sets = anchors["sets"]

    # ---- embed anchors (each set: P statements in scale order) and responses
    embed = make_embedder(args.backend, args.model)
    anchor_texts = [aset[p] for aset in sets for p in points]
    resp_texts = [r["response_text"] for r in responses]

    print(f"Embedding {len(anchor_texts)} anchors + {len(resp_texts)} responses "
          f"({args.backend})...", file=sys.stderr)
    anchor_vecs = embed(anchor_texts)
    resp_vecs = embed(resp_texts)

    P = len(points)
    set_vecs = [anchor_vecs[i * P:(i + 1) * P] for i in range(len(sets))]
    # sims[set][response] = (P,) cosine vector
    sims_by_set = [cosine(resp_vecs, sv) for sv in set_vecs]  # each (R, P)

    # ---- per-response PMF
    per_response = []
    for ri, r in enumerate(responses):
        sim_per_set = [sims_by_set[si][ri] for si in range(len(sets))]
        pmf = response_pmf(sim_per_set, args.temperature)
        rec = dict(r)
        rec["ssr"] = summarize(pmf, scale)
        rec["_pmf"] = pmf
        per_response.append(rec)

    # ---- aggregate by concept and by concept x segment
    by_concept = {}
    by_concept_segment = {}
    for rec in per_response:
        by_concept.setdefault(rec["concept"], []).append(rec["_pmf"])
        key = (rec["concept"], rec.get("segment", "all"))
        by_concept_segment.setdefault(key, []).append(rec["_pmf"])

    concept_results = {c: aggregate(p, scale) for c, p in by_concept.items()}
    segment_results = {}
    for (c, seg), p in by_concept_segment.items():
        segment_results.setdefault(c, {})[seg] = aggregate(p, scale)

    results = {
        "scale": scale,
        "labels": anchors.get("labels", {}),
        "n_responses": len(responses),
        "n_anchor_sets": len(sets),
        "temperature": args.temperature,
        "by_concept": concept_results,
        "by_concept_segment": segment_results,
        "per_response": [
            {k: v for k, v in rec.items() if k != "_pmf"} for rec in per_response
        ],
    }
    json.dump(results, open(args.out, "w"), indent=2)

    # ---- ranked table to stdout
    ranked = sorted(concept_results.items(), key=lambda kv: kv[1]["top2box"], reverse=True)
    print(f"\n=== SSR results  (scale {scale[0]}–{scale[-1]}, n={len(responses)}, "
          f"{len(sets)} anchor sets) ===\n")
    print(f"{'rank':<5}{'concept':<40}{'mean':>6}{'top2box':>9}{'bottom':>8}{'n':>4}")
    print("-" * 72)
    for i, (c, s) in enumerate(ranked, 1):
        label = c if len(c) <= 38 else c[:35] + "..."
        print(f"{i:<5}{label:<40}{s['mean']:>6.2f}{s['top2box']*100:>8.0f}%"
              f"{s['bottombox']*100:>7.0f}%{s['n']:>4}")
    print(f"\nFull breakdown (incl. per-segment) written to {args.out}")


if __name__ == "__main__":
    main()
