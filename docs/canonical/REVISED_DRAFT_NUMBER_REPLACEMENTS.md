# Revised Draft Number Replacements (Minimal-Edit Companion)

Use this file when preserving teammate prose and only correcting stale values.

## Headline policy replacement
1. Replace headline policy text from `S0_BASE_30MW_OPONLY operational_only` to `S2_30MW_FUELDISP fuel_displacement`.
2. Add statement: project-level avoided-emissions FoM, not audited inventory claim.

## Core value replacements
| Location | Old value | New value | Source |
|---|---:|---:|---|
| Section 1 headline net power | 9.939 MWe | 9.628 MWe | `report_number_map.csv` |
| Section 1 thermal efficiency | 33.90% | 32.85% | `scenarios/S2_30MW_FUELDISP.json` |
| Section 1 net efficiency | 33.13% | 32.09% | `scenarios/S2_30MW_FUELDISP.json` |
| Section 1 net CO2 reduction | 44,468 tCO2/year | 30,364.1 tCO2/year | `report_number_map.csv` + scenario json |
| Section 1 primary FoM | 1482.3 tCO2/MWth/year | 1012.1 tCO2/MWth/year | `report_number_map.csv` |
| Section 6.1 plant closure | 0.435% | 0.377% | `scenarios/S2_30MW_FUELDISP.json` |
| Section 6.1 CO2 mass flow | 165.9 kg/s | 162.5 kg/s | `scenarios/S2_30MW_FUELDISP.json` |
| Section 6.1 turbine inlet T | 517.7 C | 520.0 C | `scenarios/S2_30MW_FUELDISP.json` |
| Section 6.1 HTR pinch margin | +1.66 K | +0.98 K | `scenarios/S2_30MW_FUELDISP.json` |
| Section 6.1 IHX pinch margin | +13.00 K | +13.37 K | `scenarios/S2_30MW_FUELDISP.json` |
| Section 6.1 LTR pinch margin | +2.82 K | +3.02 K | `scenarios/S2_30MW_FUELDISP.json` |
| Section 6.1 He return margin | +10.74 K | +0.92 K | `scenarios/S2_30MW_FUELDISP.json` |
| Section 6.2 DAC capture | 44,468 tCO2/year | 15,192.4 tCO2/year | `scenarios/S2_30MW_FUELDISP.json` |
| Section 6.2 hydrogen production | 627.3 t/year | 1,924.4 t/year | `report_number_map.csv` |
| Section 6.2 methanol production | 3,245.3 t/year | 9,955.4 t/year | `report_number_map.csv` |
| UQ sample count | 120 | 40 | `uncertainty_summary.json` |
| UQ mean FoM | 1474.0 | 1004.9 | `uncertainty_summary.json` |
| UQ p10/p50/p90 | 1345.2 / 1473.2 / 1615.1 | 892.2 / 1007.9 / 1220.1 | `uncertainty_summary.json` |
| UQ 95% interval | 1273.7 to 1676.3 | 690.2 to 1238.5 | `uncertainty_summary.json` |
| Section 6.3 S0 FoM | 1482.3 | 3014.8 | `fom_summary_with_uncertainty.csv` |
| Section 6.3 S1 FoM | 1471.9 | 3025.6 | `fom_summary_with_uncertainty.csv` |
| Section 6.3 S2 FoM | 329.9 | 1012.1 | `fom_summary_with_uncertainty.csv` |
| Section 6.3 S3 FoM | 334.7 | 1004.3 | `fom_summary_with_uncertainty.csv` |
| Section 6.3 S1/S3 net power | 12.101 MWe | 11.464 MWe | `fom_summary_with_uncertainty.csv` |

## Methodology wording replacements
1. Replace "operational_only (headline)" with "fuel_displacement (headline)".
2. Replace "fuel_displacement (sensitivity)" with "operational_only (sensitivity boundary)" where needed.
3. Replace any universal `0.1%` closure statement with Stage-2 gate: `0.5%` relative tolerance (`0.005`) and reported achieved residual in headline run.

## Quick consistency checks
1. If any table labels `S0` as headline, update to `S2`.
2. If any statement says fuel-displacement is secondary-only, update to headline policy.
3. If any figure lacks scenario tag, add `scenario_id` and boundary mode in caption.
