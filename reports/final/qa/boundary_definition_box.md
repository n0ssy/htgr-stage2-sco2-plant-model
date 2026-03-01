# Boundary Definition Box

## Headline Boundary (Main Text)
`fuel_displacement`

\[
CO2_{net} = CO2_{displaced\_fossil} + CO2_{grid} - CO2_{embodied} - CO2_{reemitted\_synthetic}\,(\text{if neutrality disabled})
\]

For the locked headline case, `W_to_grid = 0` and neutrality is enabled, so net reduction reduces to displaced-fossil minus embodied terms.

## Sensitivity Boundary (Secondary Only)
`operational_only`

\[
CO2_{net} = CO2_{DAC} + CO2_{grid}
\]

This boundary is reported in Section 6.3 sensitivity tables and is not used as the primary headline FoM basis.
