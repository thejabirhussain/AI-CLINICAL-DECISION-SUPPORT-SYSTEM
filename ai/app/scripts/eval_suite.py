"""Smoke-and-instrumentation suite over 20 clinical information queries.

WHAT THIS MEASURES
    - retrieval hit rate      : did anything clear the similarity cutoff
    - abstention rate         : how often the "no verifiable information" path fires
    - citation presence       : does the answer carry any [Ref N] marker
    - citation resolvability  : does every [Ref N] point at a chunk that was
                                actually retrieved for this query
    - sources returned, similarity scores, confidence label, latency

WHAT THIS DOES NOT MEASURE - and must not be reported as if it did
    - retrieval precision or recall. There are no relevance judgements here;
      measuring precision needs a human to judge query-chunk pairs.
    - answer correctness. Nothing here knows whether a statement is true.
    - citation SUPPORT. A resolvable [Ref N] means the reference points at a
      retrieved chunk. It does NOT mean that chunk entails the sentence citing
      it. Resolvable, supported and correct are three different properties and
      only the first is decidable by this script.
    - hallucination rate. Detecting unsupported claims needs human reading.

    Note also that app.generation.pipeline sanitises the answer before it is
    returned: invalid [Ref N] markers and model-written reference lists are
    stripped. Resolvability measured here is therefore POST-sanitisation and
    will look near-perfect by construction. To measure how often the model
    fabricates references in the first place, instrument the removals inside
    pipeline._drop_invalid_refs rather than counting them here.

CORPUS CAVEAT
    The default knowledge base is MedQuAD: consumer-health question-answer
    pairs scraped from NIH websites, with automatically generated questions.
    It is not a corpus of clinical practice guidelines. These queries are
    written to be answerable from that corpus. Do not describe results from
    this suite as evaluation against clinical guidelines.
"""

import json
import logging
import re
import statistics
import time
from pathlib import Path

import typer

from app.core.config import settings
from app.core.constants import NO_KB_MSG
from app.core.logging import setup_logging
from app.generation.pipeline import RAGPipeline

setup_logging()
logger = logging.getLogger(__name__)

app = typer.Typer()

REF_RE = re.compile(r"\[Refs?\.?\s*(\d+(?:\s*,\s*\d+)*)\]", re.IGNORECASE)

# 20 clinical information queries spanning the question types that actually
# occur in the indexed corpus (information, symptoms, treatment, causes,
# exams and tests, prevention, inheritance, frequency, outlook, complications).
EVAL_QUERIES = [
    {"query": "What is type 2 diabetes mellitus?",
     "qtype": "information", "expect": "definition grounded in a retrieved source"},
    {"query": "What are the symptoms of chronic kidney disease?",
     "qtype": "symptoms", "expect": "symptom list with citation"},
    {"query": "What are the treatments for iron deficiency anemia?",
     "qtype": "treatment", "expect": "treatment options with citation"},
    {"query": "What causes essential hypertension?",
     "qtype": "causes", "expect": "aetiology with citation"},
    {"query": "How is heart failure diagnosed?",
     "qtype": "exams and tests", "expect": "diagnostic workup with citation"},
    {"query": "What are the symptoms of hypothyroidism?",
     "qtype": "symptoms", "expect": "symptom list with citation"},
    {"query": "What are the treatments for atrial fibrillation?",
     "qtype": "treatment", "expect": "management options with citation"},
    {"query": "How can type 2 diabetes be prevented?",
     "qtype": "prevention", "expect": "prevention measures with citation"},
    {"query": "What is (are) chronic obstructive pulmonary disease?",
     "qtype": "information", "expect": "definition with citation"},
    {"query": "What are the symptoms of community acquired pneumonia?",
     "qtype": "symptoms", "expect": "symptom list with citation"},
    {"query": "What are the treatments for gout?",
     "qtype": "treatment", "expect": "acute and preventive treatment with citation"},
    {"query": "What is the outlook for stage 4 chronic kidney disease?",
     "qtype": "outlook", "expect": "prognosis with citation"},
    {"query": "What are the complications of poorly controlled diabetes?",
     "qtype": "complications", "expect": "complication list with citation"},
    {"query": "How is sickle cell disease inherited?",
     "qtype": "inheritance", "expect": "inheritance pattern with citation"},
    {"query": "How many people are affected by cystic fibrosis?",
     "qtype": "frequency", "expect": "prevalence figure with citation"},
    {"query": "What are the symptoms of deep vein thrombosis?",
     "qtype": "symptoms", "expect": "symptom list with citation"},
    {"query": "What are the treatments for osteoporosis?",
     "qtype": "treatment", "expect": "treatment options with citation"},
    {"query": "What is (are) Kawasaki disease?",
     "qtype": "information", "expect": "definition with citation"},
    {"query": "How is asthma diagnosed in adults?",
     "qtype": "exams and tests", "expect": "diagnostic approach with citation"},
    # Deliberately outside the corpus: the system should abstain, not improvise.
    {"query": "What is the recommended vancomycin trough for MRSA bacteraemia "
              "in a patient on continuous renal replacement therapy?",
     "qtype": "out-of-scope", "expect": "ABSTAIN - specialist dosing is not in "
                                        "a consumer-health corpus"},
]


def _cited_refs(text: str) -> list[int]:
    out: list[int] = []
    for m in REF_RE.finditer(text or ""):
        out.extend(int(x) for x in re.findall(r"\d+", m.group(1)))
    return out


@app.command()
def main(
    output_file: str = typer.Option("eval_results.json", help="Where to write per-query results"),
    verbose: bool = typer.Option(False, help="Print each answer"),
):
    """Run the suite and report only what can be honestly computed."""
    logger.info("Starting evaluation suite over %d clinical queries", len(EVAL_QUERIES))
    logger.info("Collection: %s", settings.collection_name)

    pipeline = RAGPipeline()
    results = []

    for i, item in enumerate(EVAL_QUERIES, 1):
        query = item["query"]
        logger.info("[%d/%d] %s", i, len(EVAL_QUERIES), query)
        start = time.time()
        try:
            r = pipeline.answer(query)
            elapsed = time.time() - start
            answer = r.get("answer_text", "")
            sources = r.get("sources", [])
            refs = _cited_refs(answer)
            scores = [s.get("score", 0.0) for s in sources]
            results.append({
                "query": query,
                "qtype": item["qtype"],
                "expected_behavior": item["expect"],
                "answer": answer,
                "abstained": answer.strip() == NO_KB_MSG.strip(),
                "sources_count": len(sources),
                "retrieval_hit": len(sources) > 0,
                "cited_any": bool(refs),
                "cited_refs": refs,
                # post-sanitisation: see the module docstring before reporting this
                "all_refs_resolvable": all(1 <= n <= len(sources) for n in refs) if refs else None,
                "confidence": r.get("confidence"),
                "max_score": max(scores) if scores else None,
                "mean_score": statistics.fmean(scores) if scores else None,
                "latency_seconds": round(elapsed, 3),
                "sources": [{"url": s.get("url", ""), "title": s.get("title", ""),
                             "section": s.get("section"), "score": s.get("score", 0.0)}
                            for s in sources],
            })
            if verbose:
                print(f"\nQ{i}: {query}\n{answer[:400]}\n"
                      f"sources={len(sources)} refs={refs} "
                      f"confidence={r.get('confidence')} {elapsed:.2f}s")
        except Exception as e:
            logger.error("Query %d failed: %s", i, e)
            results.append({"query": query, "qtype": item["qtype"],
                            "error": str(e),
                            "latency_seconds": round(time.time() - start, 3)})

    Path(output_file).write_text(json.dumps(results, indent=2))

    ok = [r for r in results if "error" not in r]
    errs = len(results) - len(ok)
    hits = sum(1 for r in ok if r["retrieval_hit"])
    absts = sum(1 for r in ok if r["abstained"])
    cited = sum(1 for r in ok if r["cited_any"])
    unresolvable = sum(1 for r in ok if r["all_refs_resolvable"] is False)
    lat = [r["latency_seconds"] for r in ok]

    print("\n" + "=" * 68)
    print(f"queries              : {len(results)}  ({errs} errored)")
    print(f"retrieval hit        : {hits}/{len(ok)}")
    print(f"abstained            : {absts}/{len(ok)}")
    print(f"answer cited a source: {cited}/{len(ok)}")
    print(f"unresolvable refs    : {unresolvable}/{len(ok)}  (post-sanitisation)")
    if lat:
        print(f"latency  mean {statistics.fmean(lat):.2f}s   "
              f"median {statistics.median(lat):.2f}s   max {max(lat):.2f}s")
    print("=" * 68)
    print("These are smoke-test and instrumentation figures only.")
    print("They are NOT precision, recall, faithfulness or hallucination rates,")
    print("and must not be reported as such. See the module docstring.")
    print(f"\nPer-query results written to {output_file}")


if __name__ == "__main__":
    app()
