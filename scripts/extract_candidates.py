#!/usr/bin/env python3
"""Parse a boss-chat report.json into normalized candidate records.

Usage:
    python3 extract_candidates.py <report_json_path> [--run-id RUN_ID]

Output (stdout): JSON array of candidate records the agent then scores against
the saved rubric. This script does NOT score; it only normalizes raw data and
classifies skip reasons so that skipped candidates are never silently dropped.
"""
import argparse
import json
import sys


def _get(d, *path, default=None):
    cur = d
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
        if cur is None:
            return default
    return cur


def _first_text(*values):
    for v in values:
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def classify_skip(result):
    """Return (skipped, category, reason)."""
    screening = result.get("screening") or {}
    status = screening.get("status")
    pre = result.get("pre_action_state") or {}
    detail = result.get("detail") or {}
    cv = detail.get("cv_acquisition") or {}

    if status == "pass":
        return False, None, None

    if pre.get("already_requested_resume") or pre.get("requested_resume"):
        return True, "intentional_already_contacted", "已联系/已发起求简历"

    error_code = cv.get("error_code") or _get(detail, "llm_screening", "error_code")
    if error_code:
        if "timeout" in str(error_code).lower():
            return True, "timeout", str(error_code)
        return True, "cv_unavailable", str(error_code)

    reasons = screening.get("reasons")
    reason_text = None
    if isinstance(reasons, list) and reasons:
        reason_text = "; ".join(str(r) for r in reasons[:3])
    return True, "unknown", reason_text or (status or "skip")


def extract_greeting(result):
    """Best-effort greeting/first-message text. Returns (text, missing, source)."""
    candidate = result.get("candidate") or {}
    preview = result.get("conversation_preview") or {}
    text = _first_text(
        candidate.get("greeting_text"),
        preview.get("greeting_text"),
        candidate.get("greeting"),
        candidate.get("last_message"),
        candidate.get("message"),
        result.get("greeting_text"),
        result.get("greeting"),
        candidate.get("card_preview_text"),
        preview.get("card_preview_text"),
    )
    source = _first_text(
        candidate.get("greeting_text_source"),
        preview.get("greeting_text_source"),
    )
    if text:
        return text, False, source
    return None, True, source


def normalize(result, run_id):
    candidate = result.get("candidate") or {}
    identity = candidate.get("identity") or {}
    screening = result.get("screening") or {}

    skipped, skip_category, skip_reason = classify_skip(result)
    greeting_text, greeting_missing, greeting_source = extract_greeting(result)

    name = identity.get("name")
    if isinstance(name, str) and (not name.strip() or name.strip().isdigit()):
        name = None

    return {
        "candidate_key": result.get("candidate_key"),
        "name": name,
        "identity": {
            "title": identity.get("title"),
            "current_position": identity.get("current_position"),
            "current_company": identity.get("current_company"),
            "school": identity.get("school"),
            "major": identity.get("major"),
            "degree": identity.get("degree"),
            "years_experience": identity.get("years_experience"),
            "age": identity.get("age"),
            "gender": identity.get("gender"),
        },
        "greeting_text": greeting_text,
        "greeting_text_missing": greeting_missing,
        "greeting_text_source": greeting_source,
        "mcp_screening": {
            "status": screening.get("status"),
            "passed": screening.get("passed"),
            "score": screening.get("score"),
            "reasons": screening.get("reasons"),
        },
        "skipped": skipped,
        "skip_category": skip_category,
        "skip_reason": skip_reason,
        "run_id": run_id,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report_json")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()

    with open(args.report_json, "r", encoding="utf-8") as f:
        report = json.load(f)

    run_id = args.run_id or report.get("run_id")
    results = _get(report, "summary", "results", default=[]) or []
    if not isinstance(results, list):
        results = []

    records = [normalize(r, run_id) for r in results if isinstance(r, dict)]
    records = [r for r in records if r.get("candidate_key")]

    abnormal = [r for r in records if r["skip_category"] in
                ("cv_unavailable", "timeout", "detail_budget", "list_truncated")]

    out = {
        "run_id": run_id,
        "report_json": args.report_json,
        "candidate_count": len(records),
        "skipped_count": sum(1 for r in records if r["skipped"]),
        "abnormal_skip_count": len(abnormal),
        "candidates": records,
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
