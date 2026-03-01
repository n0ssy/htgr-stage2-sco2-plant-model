# PR Tracker (Local Branch)

Branch: `codex/htgr-stage2-sync`

## Commit Modules
1. `d29464a` - `chore: bootstrap htgr model repository snapshot`
2. `3309cef` - `feat: add scenario-tagged canonical sync pipeline and report gates`
3. `8bdded9` - `docs: add parallel session handoff ledger and planning protocol`
4. `9db0244` - `docs: consolidate canonical context and archive legacy references`
5. `fb7eb52` - `fix: support archived teammate PDFs in reconciliation parser`

## Suggested PR Split
1. **PR-A Bootstrap**
   - Commit: `d29464a`
   - Purpose: initialize repo baseline for auditability.
2. **PR-B Stage-2 Sync Pipeline**
   - Commit: `3309cef`
   - Purpose: scenario-tagged outputs, reconciliation tables, report-gate metadata.
3. **PR-C Parallel Session Ops Docs**
   - Commit: `8bdded9`
   - Purpose: handoff standards, task queue, planning workflow.
4. **PR-D Canonical Context Cleanup**
   - Commit: `9db0244`
   - Purpose: single canonical context doc, archive clutter, keep parser compatibility.
5. **PR-E Reconciliation Parser Compatibility**
   - Commit: `fb7eb52`
   - Purpose: keep teammate extraction working after teammate resource archival.

## If/When Remote Is Added
```bash
git remote add origin <your-repo-url>
git push -u origin codex/htgr-stage2-sync
```

Then open PRs in order (A -> B -> C), or squash B+C if you prefer one implementation PR and one docs PR.
