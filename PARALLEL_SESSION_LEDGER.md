# Parallel Session Ledger

Use this file to claim, coordinate, and hand off parallel AI sessions.

## Session Claim Rules
1. Add a new row before editing.
2. Claim only non-overlapping tasks/files.
3. Keep `Files Claimed` explicit to avoid merge conflict.
4. Update row at every major milestone.

## Active Sessions
| Session ID | Started (UTC) | Task IDs | Phase | Files Claimed | Status | Last Commit | Notes |
|---|---|---|---|---|---|---|---|
| SESSION-CURRENT | 2026-03-01T13:00Z | T001,T002,T003,T004,T005,T006,T007 | implementation/validation | `process/allocation.py`, `run_tests.py`, `SESSION_HANDBOOK.md`, `TASKS_TBC.md`, `PARALLEL_SESSION_LEDGER.md` | active | pending | Building sync pipeline + documentation system |

## Session Template (Copy For New Session)
| Session ID | Started (UTC) | Task IDs | Phase | Files Claimed | Status | Last Commit | Notes |
|---|---|---|---|---|---|---|---|
| SESSION-XXXX | YYYY-MM-DDThh:mmZ | T### | research/plan/implementation/validation | `path1`, `path2` | active/blocked/done | `<hash>` | blockers, assumptions, next step |

## Handoff Notes
- Always include:
  - what changed,
  - what is still pending,
  - exact files touched,
  - commands used for validation.
