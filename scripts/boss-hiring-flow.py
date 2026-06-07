#!/usr/bin/env python3
"""boss-hiring incremental flow: bootstrap all → later only unscored → merge global ranking.

Usage:
  boss-hiring-flow.py plan <job_slug>
  boss-hiring-flow.py sync-seen <job_slug>
  boss-hiring-flow.py extract-run <run_id> [--job-slug SLUG] [-o FILE]
  boss-hiring-flow.py filter-unscored <job_slug> <candidates.json> [-o FILE]
  boss-hiring-flow.py show-ranking <job_slug> [--top N]
  boss-hiring-flow.py post-run <job_slug> <run_id> [--job-label LABEL]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from boss_hiring_state import (  # noqa: E402
    is_v7_scored,
    job_dir,
    load_json,
    load_ranking,
    plan_run,
    scored_key_set,
    sync_seen,
)


def run_extract(report_json: Path, run_id: str) -> dict:
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "extract_candidates.py"),
        str(report_json),
        "--run-id",
        run_id,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)
    return json.loads(proc.stdout)


def resolve_report_json(run_id: str) -> Path:
    run_path = Path.home() / ".boss-recommend-mcp/boss-chat/runs" / f"{run_id}.json"
    if not run_path.exists():
        raise SystemExit(f"run not found: {run_path}")
    run = json.loads(run_path.read_text(encoding="utf-8"))
    report = (run.get("result") or {}).get("report_json")
    if not report:
        artifacts = run.get("artifacts") or {}
        report = artifacts.get("report_json")
    if not report:
        raise SystemExit(f"no report_json in run {run_id}")
    return Path(report)


def filter_unscored(job_slug: str, payload: dict) -> dict:
    scored = scored_key_set(job_slug)
    all_cands = payload.get("candidates") or []
    unscored = [c for c in all_cands if c.get("candidate_key") not in scored]
    return {
        "job_slug": job_slug,
        "run_id": payload.get("run_id"),
        "scored_keys_count": len(scored),
        "input_count": len(all_cands),
        "unscored_count": len(unscored),
        "candidates": unscored,
    }


def cmd_plan(args: argparse.Namespace) -> None:
    print(json.dumps(plan_run(args.job_slug), ensure_ascii=False, indent=2))


def cmd_sync_seen(args: argparse.Namespace) -> None:
    print(json.dumps(sync_seen(args.job_slug), ensure_ascii=False, indent=2))


def cmd_extract_run(args: argparse.Namespace) -> None:
    report = resolve_report_json(args.run_id)
    payload = run_extract(report, args.run_id)
    if args.job_slug:
        payload = filter_unscored(args.job_slug, payload)
    out = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"wrote {args.output} ({payload.get('unscored_count', payload.get('candidate_count'))} candidates)")
    else:
        print(out, end="")


def cmd_filter_unscored(args: argparse.Namespace) -> None:
    payload = json.loads(Path(args.candidates_json).read_text(encoding="utf-8"))
    filtered = filter_unscored(args.job_slug, payload)
    out = json.dumps(filtered, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
    else:
        print(out, end="")


def cmd_show_ranking(args: argparse.Namespace) -> None:
    ranking = load_ranking(args.job_slug)
    cands = ranking.get("candidates") or []
    scored = [c for c in cands if is_v7_scored(c)]
    unscored = [c for c in cands if c.get("candidate_key") and not is_v7_scored(c)]
    top = sorted(scored, key=lambda c: c.get("total_score") or -1, reverse=True)[: args.top]

    print(f"# {args.job_slug} 全量榜 · 已 v7 打分 {len(scored)} / 榜内共 {len(cands)}")
    if unscored:
        print(f"（另有 {len(unscored)} 人仅有 MCP 记录、待 v7 打分）\n")
    for i, c in enumerate(top, 1):
        skip = " [skip]" if c.get("skipped") else ""
        print(f"{i:2}. {c.get('display') or c.get('name')} — {c.get('total_score')}{skip}")
    if args.json:
        print(json.dumps({"scored": len(scored), "total": len(cands), "top": top}, ensure_ascii=False, indent=2))


def cmd_post_run(args: argparse.Namespace) -> None:
    report = resolve_report_json(args.run_id)
    extracted = run_extract(report, args.run_id)
    filtered = filter_unscored(args.job_slug, extracted)

    work = job_dir(args.job_slug)
    work.mkdir(parents=True, exist_ok=True)
    raw_path = work / f"extract-{args.run_id}.json"
    unscored_path = work / f"unscored-{args.run_id}.json"
    raw_path.write_text(json.dumps(extracted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unscored_path.write_text(json.dumps(filtered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "run_id": args.run_id,
        "report_json": str(report),
        "extract_path": str(raw_path),
        "unscored_path": str(unscored_path),
        "extracted": extracted.get("candidate_count"),
        "to_v7_score": filtered.get("unscored_count"),
        "already_scored_skip": extracted.get("candidate_count", 0) - filtered.get("unscored_count", 0),
        "next_steps": [
            f"只对 {unscored_path} 里 {filtered['unscored_count']} 人按 rubric.json 打 v7 分",
            "写入 scored_candidates.json（每人必须有 scored_at + dimension_scores + total_score）",
            f"python3 {SCRIPT_DIR}/merge_ranking.py {args.job_slug} scored_candidates.json"
            + (f' --job-label "{args.job_label}"' if args.job_label else ""),
            f"python3 {SCRIPT_DIR}/boss-hiring-flow.py show-ranking {args.job_slug}",
        ],
    }
    sync_seen(args.job_slug)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(description="boss-hiring incremental flow")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="Bootstrap vs incremental plan")
    p.add_argument("job_slug")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("sync-seen", help="Rebuild seen.json from ranking")
    p.add_argument("job_slug")
    p.set_defaults(func=cmd_sync_seen)

    p = sub.add_parser("extract-run", help="Extract report; optional filter unscored")
    p.add_argument("run_id")
    p.add_argument("--job-slug")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_extract_run)

    p = sub.add_parser("filter-unscored", help="Filter extract JSON to unscored only")
    p.add_argument("job_slug")
    p.add_argument("candidates_json")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_filter_unscored)

    p = sub.add_parser("show-ranking", help="Print global ranking top N (v7 scored)")
    p.add_argument("job_slug")
    p.add_argument("--top", type=int, default=15)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_show_ranking)

    p = sub.add_parser("post-run", help="After boss-chat: extract + list unscored + paths")
    p.add_argument("job_slug")
    p.add_argument("run_id")
    p.add_argument("--job-label")
    p.set_defaults(func=cmd_post_run)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
