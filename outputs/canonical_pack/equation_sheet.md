# Equation Sheet (Scenario-Tagged)

## Allocation Constraints
- Electricity: `W_HTSE + W_DAC + W_grid <= W_allocatable`
- Heat: `Q_DAC + Q_HTSE <= Q_waste_available`
- HTSE heat: `Q_HTSE = W_HTSE * (HTSE_heat_intensity / HTSE_elec_intensity)` when enforced.

## CO2 Accounting
- Operational-only mode: `CO2_net = CO2_DAC + CO2_grid`
- Fuel-displacement mode: `CO2_net = CO2_displaced_fossil + CO2_grid - CO2_embodied - (CO2_reemitted_synthetic if neutrality disabled)`

## Unit Conversions
- `kgCO2/TJ = gCO2/kWh * 277.7777778`
- `gCO2/kWh = kgCO2/TJ / 277.7777778`
