#!/usr/bin/env python3
"""Merge scored candidates into a per-job ranking, dedup by candidate_key.

Usage:
    python3 merge_ranking.py <job_slug> <scored_candidates.json> [--job-label LABEL]

Rules:
- Dedup by candidate_key; the new record overrides the old.
- Preserve first_seen_run_id from the earliest appearance; update last_run_id.
- Skipped candidates are kept (never silently dropped).
- Sort by total_score desc (missing score sinks to the bottom).

Data dir: ~/.boss-recommend-mcp/boss-chat/greeting-rank/<job_slug>/
Override base dir with env BOSS_GREETING_RANK_DIR (used for tests).
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone


def data_dir(job_slug):
    base = os.environ.get(
        "BOSS_GREETING_RANK_DIR",
        os.path.join(os.path.expanduser("~"), ".boss-recommend-mcp",
                     "boss-chat", "greeting-rank"),
    )
    return os.path.join(base, job_slug)


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def as_candidate_list(payload):
    if isinstance(payload, list):
        return payload, None
    if isinstance(payload, dict):
        return payload.get("candidates") or [], payload.get("run_id")
    return [], None


def display_name(rec, job_label):
    name = rec.get("name") or rec.get("display") or "(未知)"
    if job_label and " · " not in str(rec.get("display", "")):
        return f"{name} · {job_label}"
    return rec.get("display") or name


def sort_key(rec):
    score = rec.get("total_score")
    return score if isinstance(score, (int, float)) else float("-inf")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job_slug")
    ap.add_argument("scored_json")
    ap.add_argument("--job-label", default=None)
    args = ap.parse_args()

    ddir = data_dir(args.job_slug)
    os.makedirs(ddir, exist_ok=True)
    ranking_path = os.path.join(ddir, "ranking.json")
    seen_path = os.path.join(ddir, "seen.json")

    ranking = load_json(ranking_path, {"job_slug": args.job_slug, "candidates": []})
    seen = load_json(seen_path, {"job_slug": args.job_slug,
                                 "seen_candidate_keys": [], "runs": []})

    job_label = args.job_label or ranking.get("job_label")

    existing = {c["candidate_key"]: c for c in ranking.get("candidates", [])
                if c.get("candidate_key")}

    new_payload = load_json(args.scored_json, [])
    new_list, payload_run_id = as_candidate_list(new_payload)

    added, updated = 0, 0
    run_ids = set(seen.get("runs", []))

    for rec in new_list:
        key = rec.get("candidate_key")
        if not key:
            continue
        run_id = rec.get("run_id") or payload_run_id
        if run_id:
            run_ids.add(run_id)

        prev = existing.get(key)
        merged = dict(rec)
        merged["display"] = display_name(rec, job_label)
        if prev:
            merged["first_seen_run_id"] = prev.get("first_seen_run_id") or run_id
            updated += 1
        else:
            merged["first_seen_run_id"] = run_id
            added += 1
        merged["last_run_id"] = run_id
        existing[key] = merged

    candidates = sorted(existing.values(), key=sort_key, reverse=True)

    ranking_out = {
        "job_slug": args.job_slug,
        "job_label": job_label,
        "updated_at": now_iso(),
        "candidate_total": len(candidates),
        "candidates": candidates,
    }
    seen_out = {
        "job_slug": args.job_slug,
        "seen_candidate_keys": sorted(existing.keys()),
        "runs": sorted(run_ids),
    }

    with open(ranking_path, "w", encoding="utf-8") as f:
        json.dump(ranking_out, f, ensure_ascii=False, indent=2)
    with open(seen_path, "w", encoding="utf-8") as f:
        json.dump(seen_out, f, ensure_ascii=False, indent=2)

    skipped = sum(1 for c in candidates if c.get("skipped"))
    summary = {
        "ranking_path": ranking_path,
        "added": added,
        "updated": updated,
        "total": len(candidates),
        "skipped_in_ranking": skipped,
        "top": [
            {"display": c.get("display"), "total_score": c.get("total_score"),
             "skipped": c.get("skipped")}
            for c in candidates[:10]
        ],
    }
    json.dump(summary, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
