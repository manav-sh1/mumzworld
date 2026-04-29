"""Evaluation runner — sends test cases to the API and scores results."""
from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

from eval.test_cases import TEST_CASES, TestCase

API_URL = "http://127.0.0.1:8000/api/recommend"

# Mock catalog for age-range lookups
_CATALOG_PATH = Path(__file__).parent.parent / "backend" / "gift_finder" / "catalog.json"
CATALOG: list[dict] = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
CATALOG_BY_NAME = {p["name"]: p for p in CATALOG}


def score_case(tc: TestCase, data: dict) -> dict:
    """Score a single test-case response. Returns dimension→score dict."""
    scores: dict[str, int | str] = {"id": tc.id}

    # 1. Schema validity — if we got parseable JSON with expected keys
    has_recs = "recommendations" in data
    scores["schema_valid"] = 1 if has_recs else 0

    recs = data.get("recommendations", [])
    out_of_scope = data.get("out_of_scope", False)
    clarification = data.get("clarification_needed")

    # 2. Budget compliance
    if tc.budget_aed is not None and recs:
        scores["budget_ok"] = (
            1
            if all(
                (r.get("price_aed") or 0) <= tc.budget_aed for r in recs
            )
            else 0
        )
    else:
        scores["budget_ok"] = 1  # N/A

    # 3. Age appropriateness
    if tc.age_months is not None and recs:
        ok = True
        for r in recs:
            cat_entry = CATALOG_BY_NAME.get(r.get("name", ""))
            if cat_entry:
                if not (
                    cat_entry["age_months_min"]
                    <= tc.age_months
                    <= cat_entry["age_months_max"]
                ):
                    ok = False
                    break
        scores["age_ok"] = 1 if ok else 0
    else:
        scores["age_ok"] = 1

    # 4. Uncertainty handling
    if tc.expects_refusal:
        scores["uncertainty"] = 1 if (out_of_scope or len(recs) == 0) else 0
    elif tc.expects_clarification:
        # If clarification was returned, pass regardless of rec count
        scores["uncertainty"] = 1 if clarification is not None else 0
    else:
        scores["uncertainty"] = 1

    # 5. Recommendation count range
    # If clarification was expected AND returned, auto-pass count check
    if tc.expects_clarification and clarification is not None:
        scores["count_ok"] = 1
    else:
        count_ok = tc.min_recommendations <= len(recs) <= tc.max_recommendations
        scores["count_ok"] = 1 if count_ok else 0

    # 6. Catalog grounding — all names must be in the catalog
    if recs:
        scores["grounded"] = (
            1
            if all(r.get("name", "") in CATALOG_BY_NAME for r in recs)
            else 0
        )
    else:
        scores["grounded"] = 1

    # Total (automated — max 6)
    scores["auto_total"] = sum(
        scores[k] for k in ("schema_valid", "budget_ok", "age_ok",
                            "uncertainty", "count_ok", "grounded")
    )
    return scores


def run_eval() -> None:
    """Run all test cases and print a score table."""
    print("=" * 78)
    print("  Mumzworld Gift Finder — Evaluation Suite")
    print("=" * 78)
    print()

    client = httpx.Client(timeout=60.0)
    all_scores: list[dict] = []
    raw_outputs: list[dict] = []

    for tc in TEST_CASES:
        print(f"  [{tc.id}] {tc.description}")
        print(f"       Query: {tc.query[:70]}...")
        try:
            res = client.post(API_URL, json={"query": tc.query})
            if res.status_code == 200:
                data = res.json()
            else:
                # Treat HTTP errors as schema failure
                data = {"recommendations": [], "error": res.text[:200]}
                print(f"       ⚠ HTTP {res.status_code}")
        except httpx.RequestError as exc:
            data = {"recommendations": [], "error": str(exc)}
            print(f"       ❌ Connection error: {exc}")

        scores = score_case(tc, data)
        all_scores.append(scores)
        raw_outputs.append({"tc_id": tc.id, "response": data})

        recs = data.get("recommendations", [])
        print(f"       → {len(recs)} recommendations, "
              f"auto_score={scores['auto_total']}/6")
        print()
        time.sleep(1.5)  # rate-limit courtesy

    # Summary table
    print("-" * 78)
    print(f"  {'ID':<6} {'Schema':>7} {'Budget':>7} {'Age':>5} "
          f"{'Uncert':>7} {'Count':>6} {'Ground':>7} {'TOTAL':>7}")
    print("-" * 78)

    grand = 0
    for s in all_scores:
        print(
            f"  {s['id']:<6} {s['schema_valid']:>7} {s['budget_ok']:>7} "
            f"{s['age_ok']:>5} {s['uncertainty']:>7} {s['count_ok']:>6} "
            f"{s['grounded']:>7} {s['auto_total']:>5}/6"
        )
        grand += s["auto_total"]

    max_total = len(all_scores) * 6
    print("-" * 78)
    print(f"  GRAND TOTAL: {grand}/{max_total} "
          f"({grand / max_total * 100:.0f}%)")
    print()

    # Dump raw outputs
    out_path = Path(__file__).parent / "eval_results.json"
    out_path.write_text(
        json.dumps(raw_outputs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  Raw outputs saved to {out_path}")


if __name__ == "__main__":
    run_eval()
