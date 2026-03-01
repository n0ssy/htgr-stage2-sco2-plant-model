# Final Report Pack (Locked to Feasible Baseline)

## Generated Drafts
- `UCL_Group3_Final_Report_Draft_v2.md` - updated full report draft with locked headline scenario and boundary.
- `UCL_Group3_Final_Report_Draft_v2.docx` - docx export of the updated draft.

## QA/Traceability Artifacts
- `qa/numbers_lock_table.csv` - single source for report numerics.
- `qa/claim_to_evidence_table.csv` - claim provenance map.
- `qa/boundary_definition_box.md` - main vs sensitivity boundary definitions.
- `qa/validate_report_sync.py` - automated consistency checks.
- `qa/report_sync_check.json` - latest check output.

## Locked Headline Basis
- Scenario: `S2_30MW_FUELDISP`
- Boundary: `fuel_displacement`
- Primary FoM: `329.9 tCO2/MWth/year`
- Net reduction: `9,898 tCO2/year`

## Notes
- 36 MWth content is retained only as historical/sensitivity context.
- Safety transients are explicitly provenance-labeled (literature/external workstream) unless branch-reproducible.

## Quick QA Recheck
From repo root:

```bash
python reports/final/qa/validate_report_sync.py
```
