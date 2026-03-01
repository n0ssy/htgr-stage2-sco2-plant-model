# Boundary Definition Box

## Headline Boundary (Main Text)
`operational_only`

\[
CO2_{net} = CO2_{DAC} + CO2_{grid}
\]

For the locked headline case, `W_to_grid = 0`, so operational-only net reduction is DAC-driven under solved allocation constraints.

## Sensitivity Boundary (Secondary Only)
`fuel_displacement`

\[
CO2_{net} = CO2_{displaced\_fossil} + CO2_{grid} - CO2_{embodied} - CO2_{reemitted\_synthetic}\,(\text{if neutrality disabled})
\]

This boundary is reported in Section 6.3 sensitivity tables and is not used as the primary headline FoM basis.
