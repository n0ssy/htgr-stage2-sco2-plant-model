# Methods and Limitations (Final Q&A Sheet)

## Headline Policy
1. Headline scenario ID: `S2_30MW_FUELDISP`.
2. Headline concept mode: `fuel_factory`.
3. Headline CO2 boundary: `fuel_displacement`.
4. Headline thermal basis: `30 MWth`.
5. Heat rejection mode for headline: `fixed_boundary`.

## Core Method
1. Solve HTGR+sCO2 plant state with coupled cycle and fixed boundary cooling assumptions.
2. Run constrained process allocation with HTSE/DAC/methanol pathways.
3. Enforce minimum methanol output floor for fuel-factory headline behavior.
4. Compute CO2 FoM under explicit accounting boundary and export scenario-tagged results.
5. Attach strict gate results and uncertainty summary to canonical pack.

## Validation and Gates
1. Dostal cycle benchmark anchor.
2. Secondary cycle anchor point check.
3. Process analytic closure checks (DAC/HTSE/methanol stoichiometry).
4. Accounting-mode consistency check from identical plant state.
5. Strict closure and objective-consistency gates before report export.

## Known Limitations
1. Reactor behavior is boundary-condition driven; no transient core simulation in this cycle.
2. Fuel-displacement headline depends on reference fossil fuel EF and displacement factor assumptions.
3. Heat rejection is represented as boundary assumption in headline mode; coupled cooler remains sensitivity evidence.
