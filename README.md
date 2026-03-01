# HTGR Stage-2 sCO2 Plant Model

This repository contains the HTGR-only Stage-2 modelling workflow for:
- HTGR thermal source + sCO2 cycle
- process allocation (DAC/HTSE)
- CO2 Figure of Merit generation
- scenario-tagged canonical outputs for team synchronization

## Start Here (AI + Parallel Sessions)

Primary onboarding entry point:
- `AI_ONBOARDING.md`

Single canonical project context:
- `docs/canonical/CANONICAL_PROJECT_CONTEXT.md`

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

## Document Hygiene

Legacy context and draft references are archived under:
- `docs/archive/`

Only `docs/canonical/CANONICAL_PROJECT_CONTEXT.md` should be treated as the active context reference.

Key files:
- `outputs/canonical_pack/canonical_pack_index.json`
- `outputs/canonical_pack/scenarios/*.json`
- `outputs/canonical_pack/fom_summary_with_uncertainty.csv`
- `outputs/canonical_pack/assumptions_register.csv`
- `outputs/canonical_pack/teammate_number_reconciliation.csv`
- `outputs/canonical_pack/teammate_delta_table.csv`

## Running the Pipeline

From repo root:

```bash
source venv/bin/activate
python run_tests.py
```

To generate canonical scenario pack only:

```bash
source venv/bin/activate
python - <<'PY'
from run_tests import generate_stage2_canonical_pack
generate_stage2_canonical_pack()
PY
```
