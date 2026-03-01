# HTGR Stage-2 sCO2 Plant Model

This repository contains the HTGR-only Stage-2 modelling workflow for:
- HTGR thermal source + sCO2 cycle
- process allocation (DAC/HTSE)
- CO2 Figure of Merit generation
- scenario-tagged canonical outputs for team synchronization

## Start Here (AI + Parallel Sessions)

Primary onboarding entry point:
- `AI_ONBOARDING.md`

Operational coordination docs:
- `SESSION_HANDBOOK.md`
- `TASKS_TBC.md`
- `PARALLEL_SESSION_LEDGER.md`
- `PLANNING_PROTOCOL.md`
- `PR_TRACKER.md`

## Scope Locks

Current locked defaults:
1. HTGR-only scope
2. Headline CO2 boundary: `operational_only`
3. Baseline case: `S0_BASE_30MW_OPONLY` (`30 MWth`)
4. `36 MWth` is sensitivity only

## Canonical Outputs

Generated artifacts live in:
- `outputs/canonical_pack/`

Key files:
- `outputs/canonical_pack/canonical_pack_index.json`
- `outputs/canonical_pack/scenarios/*.json`
- `outputs/canonical_pack/fom_summary_with_uncertainty.csv`
- `outputs/canonical_pack/assumptions_register.csv`
- `outputs/canonical_pack/teammate_number_reconciliation.csv`
- `outputs/canonical_pack/teammate_delta_table.csv`
- `outputs/canonical_pack/feasibility_failure_report.json` (written only when `require_feasible=True` gate fails)
- `outputs/diagnostics/headline_feasibility_trace.json`

## Final Report Pack

Report drafting and traceability artifacts live in:
- `reports/final/UCL_Group3_Final_Report_Draft_v2.md`
- `reports/final/UCL_Group3_Final_Report_Draft_v2.docx`
- `reports/final/qa/numbers_lock_table.csv`
- `reports/final/qa/claim_to_evidence_table.csv`
- `reports/final/qa/report_sync_check.json`

The report headline basis is locked to:
- scenario: `S0_BASE_30MW_OPONLY`
- boundary: `operational_only`

## Running the Pipeline

From repo root:

```bash
source venv/bin/activate
python run_tests.py
```

### Full Mode (Authoritative)

Full mode is the default and is the authoritative run:
- Runs Dostal validation, headline plant solve, CO2 analysis, and canonical pack generation.
- Enforces canonical feasibility gate (`require_feasible=True`).
- Exits non-zero if any required gate fails.

### Smoke Mode (Quick Check)

Use a reduced UQ sample count for faster local checks:

```bash
source venv/bin/activate
STAGE2_UQ_SAMPLES=30 python -u run_tests.py
```

Smoke mode is convenience-only; full mode remains the source of record.

### Fail-Fast Semantics

- If the headline fixed-boundary solve is infeasible, the pipeline stops before Test 3 and canonical generation.
- In fail-fast mode, diagnostics and baseline feasibility artifacts are still written.
- CO2/canonical downstream outputs are skipped unless override is explicitly enabled.

Override for diagnostics-only continuation:

```bash
source venv/bin/activate
ALLOW_INFEASIBLE_DIAGNOSTIC=1 python -u run_tests.py
```

When override is enabled, the run continues for diagnostics, but canonical feasibility gating is still enforced in canonical generation.

To generate canonical scenario pack only:

```bash
source venv/bin/activate
python - <<'PY'
from run_tests import generate_stage2_canonical_pack
generate_stage2_canonical_pack(require_feasible=True)
PY
```
