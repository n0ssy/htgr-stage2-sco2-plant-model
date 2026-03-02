# Latest PDF vs Canonical Final Values Cross-Reference

## Canonical source-of-truth location
All finalised numbers are in:
`/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/outputs/canonical_pack/`

Use these files in order of priority:
1. `report_number_map.csv` for report-facing numbers (Sections 1, 6, 8).
2. `scenarios/S2_30MW_FUELDISP.json` for complete headline plant/process state.
3. `fom_summary_with_uncertainty.csv` for scenario matrix values.
4. `uncertainty_summary.json` for headline UQ stats.
5. `validation_matrix.csv` and `audit_gate_results.json` for V&V/gate claims.
6. `assumptions_register.csv` for assumptions and justifications.

## Quick stale-value check against latest PDF
Latest PDF reviewed:
`/Users/stefioannidis/Downloads/UCL HTGR Group 3 Report Draft Revised.pdf`

| Report item | Latest PDF value | Canonical final value | Canonical source |
|---|---:|---:|---|
| Headline scenario ID | S2_30MW_FUELDISP | S2_30MW_FUELDISP | `canonical_pack_index.json` |
| Headline accounting boundary | fuel_displacement | fuel_displacement | `canonical_pack_index.json` |
| Headline net power | 9.939 MWe | 9.628 MWe | `report_number_map.csv` (S2 net electric output) |
| Headline thermal efficiency | 33.90% | 32.85% | `scenarios/S2_30MW_FUELDISP.json` |
| Headline net efficiency | 33.13% | 32.09% | `scenarios/S2_30MW_FUELDISP.json` |
| Headline net CO2 reduction | 9,898 tCO2/yr | 30,364.1 tCO2/yr | `scenarios/S2_30MW_FUELDISP.json` |
| Headline primary FoM | 329.9 tCO2/MWth/yr | 1012.1 tCO2/MWth/yr | `report_number_map.csv` |
| Headline DAC capture | 44,468 tCO2/yr | 15,192.4 tCO2/yr | `scenarios/S2_30MW_FUELDISP.json` |
| Headline H2 production | 627.3 t/yr | 1,924.4 t/yr | `scenarios/S2_30MW_FUELDISP.json` |
| Headline methanol production | 3245.3 t/yr | 9,955.4 t/yr | `report_number_map.csv` |
| Plant energy closure | 0.435% | 0.377% | `scenarios/S2_30MW_FUELDISP.json` |
| CO2 mass flow | 165.9 kg/s | 162.5 kg/s | `scenarios/S2_30MW_FUELDISP.json` |
| Turbine inlet temperature | 517.7 C | 520.0 C | `scenarios/S2_30MW_FUELDISP.json` |
| HTR pinch margin | +1.66 K | +0.98 K | `scenarios/S2_30MW_FUELDISP.json` |
| IHX pinch margin | +13.00 K | +13.37 K | `scenarios/S2_30MW_FUELDISP.json` |
| LTR pinch margin | +2.82 K | +3.02 K | `scenarios/S2_30MW_FUELDISP.json` |
| Helium return margin | +10.74 K | +0.92 K | `scenarios/S2_30MW_FUELDISP.json` |
| UQ sample count | 120 | 40 | `uncertainty_summary.json` |
| UQ mean FoM | 331.6 | 1004.9 | `uncertainty_summary.json` |
| UQ P10/P50/P90 | 302.7 / 331.5 / 360.8 | 892.2 / 1007.9 / 1220.1 | `uncertainty_summary.json` |
| UQ 95% interval | 288.6 to 377.9 | 690.2 to 1238.5 | `uncertainty_summary.json` |
| S0 FoM in scenario table | 1482.3 | 3014.8 | `fom_summary_with_uncertainty.csv` |
| S1 FoM in scenario table | 1471.9 | 3025.6 | `fom_summary_with_uncertainty.csv` |
| S2 FoM in scenario table | 329.9 | 1012.1 | `fom_summary_with_uncertainty.csv` |
| S3 FoM in scenario table | 334.7 | 1004.3 | `fom_summary_with_uncertainty.csv` |
| S1/S3 net power in scenario table | 12.101 MWe | 11.464 MWe | `fom_summary_with_uncertainty.csv` |

## Final report-ready files to pull from
1. Report mapping: `report_number_map.csv`
2. Headline state: `scenarios/S2_30MW_FUELDISP.json`
3. Scenario matrix: `fom_summary_with_uncertainty.csv`
4. UQ: `uncertainty_summary.json`
5. Validation: `validation_matrix.csv`
6. Gates: `audit_gate_results.json`
7. Assumptions: `assumptions_register.csv`

## Notes for review workflow
1. If a number in the PDF differs from these canonical files, treat PDF as stale.
2. Do not use any untagged number (missing scenario/boundary/source).
3. Headline claims must always map to `S2_30MW_FUELDISP`.
