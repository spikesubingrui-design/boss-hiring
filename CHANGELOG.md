# Changelog

## [1.0.0] - 2026-06-01

### Added

- Open-source **boss-greeting-rank** agent skill (MIT)
- Workflow: rubric interview → read-only boss-chat scan → extract → merge ranking
- Python tools: `extract_candidates.py`, `merge_ranking.py`
- Install script for OpenClaw (`~/.openclaw/skills`) and Cursor (`~/.cursor/skills`)
- Docs: OpenClaw / Cursor install guides
- Runtime notes for `@reconcrap/boss-recommend-mcp` ≥ 2.0.57 (greeting text persistence)
- Patch reference: `runtime/patches/2.0.57/conversation-greeting.js`

### Safety

- Read-only defaults: no auto greeting, no resume request
- Skip candidates kept in ranking with reasons; stuck recovery playbook
