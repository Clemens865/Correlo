#!/usr/bin/env python3
"""
Wiggum Loop — validate ALL possible correlations across all 146 APIs.

Strategy:
  1. Fetch all datasets once with smart params (cache to disk)
  2. Run alignment + Pearson correlation for all N*(N-1)/2 pairs in-memory
  3. Report: failures, low-data, and interesting correlations
"""

import json
import math
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = "http://localhost:8080"
CACHE_DIR = Path(__file__).parent / ".wiggum_cache"
CACHE_DIR.mkdir(exist_ok=True)

MIN_DAYS = {
    "yearly": 7300, "monthly": 1825, "weekly": 730,
    "daily": 365, "10-day": 365, "quarterly": 1825,
}


def load_catalog():
    data = json.loads(urllib.request.urlopen(f"{BASE}/api/catalog").read())
    return {a["id"]: a for a in data["apis"]}


def smart_days(api, for_yearly_partner=False):
    """Compute optimal fetch days for an API."""
    days = max(365, MIN_DAYS.get(api["granularity"], 365))
    if for_yearly_partner:
        days = max(days, api.get("max_history_days", 7300))
    else:
        days = max(days, MIN_DAYS.get("yearly", 7300))
    return min(days, api.get("max_history_days", days))


def fetch_dataset(api):
    """Fetch a dataset with maximum useful history."""
    aid = api["id"]
    cache_file = CACHE_DIR / f"{aid}.json"

    # Use disk cache if fresh (< 1 hour)
    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < 3600:
            return json.loads(cache_file.read_text())

    days = smart_days(api, for_yearly_partner=True)
    country = "AT" if api["location_type"] == "country" else "WLD"
    lat, lon = (45.64, 13.78) if "marine" in aid else (48.21, 16.37)

    params = {"id": aid, "lat": lat, "lon": lon, "country": country, "days": days}
    req = urllib.request.Request(
        f"{BASE}/api/fetch",
        data=json.dumps(params).encode(),
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=120)
    data = json.loads(resp.read())

    # Cache to disk
    cache_file.write_text(json.dumps(data))
    return data


def detect_gran(labels):
    if not labels:
        return "unknown"
    s = labels[0]
    if re.match(r"^\d{4}$", s):
        return "yearly"
    if re.match(r"^\d{4}-\d{2}$", s):
        return "monthly"
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return "daily"
    return "unknown"


def aggregate(labels, values, target):
    """Aggregate labels/values to target granularity using means."""
    buckets = {}
    for l, v in zip(labels, values):
        if v is None:
            continue
        key = l[:4] if target == "yearly" else l[:7]
        buckets.setdefault(key, []).append(v)
    keys = sorted(buckets)
    vals = [sum(buckets[k]) / len(buckets[k]) for k in keys]
    return keys, vals


def pearson(x, y):
    """Compute Pearson correlation coefficient."""
    n = len(x)
    if n < 3:
        return None
    mx = sum(x) / n
    my = sum(y) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    if sx == 0 or sy == 0:
        return 0.0
    return cov / (sx * sy)


def align_and_correlate(d1, d2):
    """Align two datasets (cross-granularity) and compute correlation."""
    l1, v1 = d1["labels"][:], d1["values"][:]
    l2, v2 = d2["labels"][:], d2["values"][:]
    g1, g2 = detect_gran(l1), detect_gran(l2)

    gran_order = {"daily": 0, "monthly": 1, "yearly": 2}

    if g1 != g2 and g1 in gran_order and g2 in gran_order:
        target = g1 if gran_order[g1] > gran_order[g2] else g2
        if g1 != target:
            l1, v1 = aggregate(l1, v1, target)
        if g2 != target:
            l2, v2 = aggregate(l2, v2, target)

    # Find common labels
    set2 = set(l2)
    common = [l for l in l1 if l in set2]
    n = len(common)
    if n < 3:
        return {
            "n": n,
            "pearson": None,
            "range1": f"{l1[0]}..{l1[-1]}" if l1 else "empty",
            "range2": f"{l2[0]}..{l2[-1]}" if l2 else "empty",
            "g1": g1, "g2": g2,
        }

    idx1 = {l: i for i, l in enumerate(l1)}
    idx2 = {l: i for i, l in enumerate(l2)}
    x = [v1[idx1[l]] for l in common]
    y = [v2[idx2[l]] for l in common]

    r = pearson(x, y)
    return {"n": n, "pearson": r, "g1": g1, "g2": g2}


def main():
    print("=" * 70)
    print("WIGGUM LOOP — Full Correlation Validation")
    print("=" * 70)

    # Step 1: Load catalog
    apis = load_catalog()
    total = len(apis)
    total_pairs = total * (total - 1) // 2
    print(f"\n{total} APIs → {total_pairs:,} unique pairs to test\n")

    # Step 2: Fetch all datasets (with caching)
    print("PHASE 1: Fetching all datasets...")
    datasets = {}
    fetch_failures = []
    for i, (aid, api) in enumerate(apis.items()):
        try:
            d = fetch_dataset(api)
            if d.get("count", 0) > 0 and not d.get("error"):
                datasets[aid] = d
                g = detect_gran(d["labels"])
                sys.stdout.write(f"\r  [{i+1:3d}/{total}] {len(datasets)} fetched, {len(fetch_failures)} failed")
                sys.stdout.flush()
            else:
                fetch_failures.append((aid, d.get("error", "no data")))
                sys.stdout.write(f"\r  [{i+1:3d}/{total}] {len(datasets)} fetched, {len(fetch_failures)} failed")
                sys.stdout.flush()
            time.sleep(0.2)  # Rate limit courtesy
        except Exception as e:
            fetch_failures.append((aid, str(e)[:60]))
            sys.stdout.write(f"\r  [{i+1:3d}/{total}] {len(datasets)} fetched, {len(fetch_failures)} failed")
            sys.stdout.flush()

    print(f"\n  Done: {len(datasets)} datasets fetched, {len(fetch_failures)} failed")
    if fetch_failures:
        print(f"\n  Fetch failures:")
        for aid, err in fetch_failures:
            print(f"    ✗ {aid}: {err}")

    # Step 3: Run ALL pairs
    available = sorted(datasets.keys())
    actual_pairs = len(available) * (len(available) - 1) // 2
    print(f"\nPHASE 2: Computing {actual_pairs:,} correlations...")

    ok = []          # ≥ 5 common points
    low_data = []    # 3-4 common points
    no_overlap = []  # < 3 common points
    strong = []      # |r| > 0.7

    pair_num = 0
    t_start = time.time()
    for i in range(len(available)):
        for j in range(i + 1, len(available)):
            pair_num += 1
            id1, id2 = available[i], available[j]
            d1, d2 = datasets[id1], datasets[id2]

            result = align_and_correlate(d1, d2)

            if result["pearson"] is None:
                no_overlap.append((id1, id2, result))
            elif result["n"] < 5:
                low_data.append((id1, id2, result))
            else:
                ok.append((id1, id2, result))
                if abs(result["pearson"]) > 0.7:
                    strong.append((id1, id2, result))

            if pair_num % 1000 == 0 or pair_num == actual_pairs:
                elapsed = time.time() - t_start
                rate = pair_num / elapsed if elapsed > 0 else 0
                sys.stdout.write(
                    f"\r  [{pair_num:6,}/{actual_pairs:,}] "
                    f"{len(ok):,} ok, {len(low_data)} low, {len(no_overlap)} fail "
                    f"({rate:.0f} pairs/sec)"
                )
                sys.stdout.flush()

    elapsed = time.time() - t_start
    print(f"\n  Done in {elapsed:.1f}s")

    # Step 4: Report
    print(f"\n{'='*70}")
    print(f"RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"  Total datasets fetched:  {len(datasets)}")
    print(f"  Total pairs tested:      {actual_pairs:,}")
    print(f"  Successful (≥5 pts):     {len(ok):,} ({len(ok)/actual_pairs*100:.1f}%)")
    print(f"  Low data (3-4 pts):      {len(low_data)} ({len(low_data)/actual_pairs*100:.1f}%)")
    print(f"  No overlap (<3 pts):     {len(no_overlap)} ({len(no_overlap)/actual_pairs*100:.1f}%)")
    print(f"  Strong (|r|>0.7):        {len(strong)}")

    # Incompatible pairs breakdown
    if no_overlap:
        print(f"\n--- NO OVERLAP ({len(no_overlap)} pairs) ---")
        # Group by reason
        reasons = {}
        for id1, id2, res in no_overlap:
            g1 = detect_gran(datasets[id1]["labels"])
            g2 = detect_gran(datasets[id2]["labels"])
            r1 = res.get("range1", "?")
            r2 = res.get("range2", "?")
            # Categorize
            key = f"{apis[id1]['granularity']}({apis[id1]['max_history_days']}d) vs {apis[id2]['granularity']}({apis[id2]['max_history_days']}d)"
            reasons.setdefault(key, []).append((id1, id2))
        for reason, pairs in sorted(reasons.items(), key=lambda x: -len(x[1])):
            print(f"  [{len(pairs):3d}] {reason}")
            if len(pairs) <= 5:
                for id1, id2 in pairs:
                    print(f"        {apis[id1]['name']} vs {apis[id2]['name']}")

    # Top 30 strongest correlations
    if strong:
        strong.sort(key=lambda x: abs(x[2]["pearson"]), reverse=True)
        print(f"\n--- TOP 30 STRONGEST CORRELATIONS ---")
        for id1, id2, res in strong[:30]:
            r = res["pearson"]
            n = res["n"]
            direction = "+" if r > 0 else "-"
            name1 = apis[id1]["name"]
            name2 = apis[id2]["name"]
            print(f"  r={r:+.4f} ({n:4d} pts) {name1} vs {name2}")

    # Top 20 most surprising (high r between unrelated categories)
    print(f"\n--- SURPRISING CORRELATIONS (different categories, |r|>0.8) ---")
    surprising = []
    for id1, id2, res in strong:
        cat1 = apis[id1]["category"].split("/")[0]
        cat2 = apis[id2]["category"].split("/")[0]
        if cat1 != cat2 and abs(res["pearson"]) > 0.8:
            surprising.append((id1, id2, res))
    surprising.sort(key=lambda x: abs(x[2]["pearson"]), reverse=True)
    for id1, id2, res in surprising[:20]:
        r = res["pearson"]
        n = res["n"]
        print(f"  r={r:+.4f} ({n:4d} pts) {apis[id1]['name']} [{apis[id1]['category']}] vs {apis[id2]['name']} [{apis[id2]['category']}]")

    # Save full results
    output = {
        "total_apis": len(datasets),
        "total_pairs": actual_pairs,
        "ok": len(ok),
        "low_data": len(low_data),
        "no_overlap": len(no_overlap),
        "strong_count": len(strong),
        "fetch_failures": fetch_failures,
        "no_overlap_pairs": [(id1, id2, res.get("range1",""), res.get("range2","")) for id1, id2, res in no_overlap],
        "top_correlations": [
            {"a": id1, "b": id2, "r": res["pearson"], "n": res["n"],
             "nameA": apis[id1]["name"], "nameB": apis[id2]["name"]}
            for id1, id2, res in strong[:100]
        ],
    }
    out_path = Path(__file__).parent / "wiggum_results.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\nFull results saved to {out_path}")


if __name__ == "__main__":
    main()
