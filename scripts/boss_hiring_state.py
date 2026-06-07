#!/usr/bin/env python3
"""Shared state helpers for boss-hiring incremental scoring."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def greeting_rank_root() -> Path:
    base = os.environ.get(
        "BOSS_GREETING_RANK_DIR",
        os.path.expanduser("~/.boss-recommend-mcp/boss-chat/greeting-rank"),
    )
    return Path(base)


def job_dir(job_slug: str) -> Path:
    return greeting_rank_root() / job_slug


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_v7_scored(record: dict) -> bool:
    """True when this candidate has a completed rubric score (not MCP-only)."""
    if not record.get("scored_at"):
        return False
    dims = record.get("dimension_scores")
    return isinstance(dims, dict) and len(dims) > 0


def load_ranking(job_slug: str) -> dict:
    return load_json(job_dir(job_slug) / "ranking.json", {"job_slug": job_slug, "candidates": []})


def scored_key_set(job_slug: str) -> set[str]:
    ranking = load_ranking(job_slug)
    return {
        c["candidate_key"]
        for c in ranking.get("candidates", [])
        if c.get("candidate_key") and is_v7_scored(c)
    }


def all_ranked_key_set(job_slug: str) -> set[str]:
    ranking = load_ranking(job_slug)
    return {c["candidate_key"] for c in ranking.get("candidates", []) if c.get("candidate_key")}


def sync_seen(job_slug: str) -> dict:
    """Rebuild seen.json from ranking.json."""
    ranking = load_ranking(job_slug)
    scored = sorted(scored_key_set(job_slug))
    all_keys = sorted(all_ranked_key_set(job_slug))
    runs = sorted(
        {
            c.get("last_run_id") or c.get("first_seen_run_id")
            for c in ranking.get("candidates", [])
            if c.get("last_run_id") or c.get("first_seen_run_id")
        }
    )
    seen = {
        "job_slug": job_slug,
        "scored_candidate_keys": scored,
        "seen_candidate_keys": all_keys,
        "runs": runs,
    }
    save_json(job_dir(job_slug) / "seen.json", seen)
    return seen


def plan_run(job_slug: str) -> dict:
    """Decide boss-chat start_from and what to v7-score after the run."""
    rubric_path = job_dir(job_slug) / "rubric.json"
    ranking_path = job_dir(job_slug) / "ranking.json"
    scored = scored_key_set(job_slug)
    first_bootstrap = len(scored) == 0

    return {
        "job_slug": job_slug,
        "rubric_path": str(rubric_path),
        "ranking_path": str(ranking_path),
        "mode": "bootstrap_all" if first_bootstrap else "incremental_unread",
        "boss_chat": {
            "start_from": "all" if first_bootstrap else "unread",
            "target_count": "all",
            "note": "首次无 v7 打分记录 → 全量扫招呼；之后只扫未读新招呼",
        },
        "v7_scoring": {
            "only_unscored": not first_bootstrap,
            "scored_count": len(scored),
            "note": "run 完成后只对 ranking 里无 scored_at 的 candidate_key 做 v7 七维打分",
        },
        "merge": {
            "into_full_ranking": True,
            "note": "merge_ranking 按 candidate_key 合并进历史全员榜，按 total_score 全局排序",
        },
    }
