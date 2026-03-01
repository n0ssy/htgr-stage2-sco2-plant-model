# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based thermal power systems simulation for an **HTGR (High-Temperature Gas Reactor) coupled with a supercritical CO2 (sCO2) recompression Brayton cycle**. The simulation uses physically-consistent models with enthalpy-based segmented heat exchangers, pressure drops throughout the cycle, and embedded feasibility constraints.

## Running the Simulation

```bash
# Run all tests and generate output files
python run_tests.py
```

This executes:
1. Dostal-style cycle validation (benchmark against MIT 2004 reference)
2. Full coupled plant solve at T_ambient = 40°C

**Generated outputs:**
- `assumptions.yaml` - Complete list of design parameters
- `results_baseline.json` - Baseline simulation results
- `feasibility_report.txt` - Diagnostic report

## Dependencies

- Python 3.7+
- numpy
- scipy
- CoolProp (thermodynamic properties - critical for real gas CO2/He/Air)
- PyYAML

## Architecture

### Package Structure

```
sco2_plant/
├── properties/fluids.py       # CoolProp wrapper (CO2, Helium, Air)
├── components/
│   ├── turbomachinery.py      # Turbine, MainCompressor, Recompressor
│   ├── ihx.py                 # Intermediate Heat Exchanger (He-CO2)
│   ├── recuperators.py        # HTR & LTR recuperators
│   └── dry_cooler.py          # Physical dry cooler with fan power model
├── hx/segmented_hx.py         # Core segmented counterflow HX solver
├── cycle/
│   ├── sco2_cycle.py          # sCO2 recompression cycle (standalone)
│   └── coupled_solver.py      # Full plant solver (cycle + IHX + cooler)
└── validation/dostal_validation.py  # Reference validation
```

### Solver Strategy

The plant uses **nested fixed-point iteration**:
1. **Outer Loop**: Iterates on (T_5, T_1, P_low, f_recomp) until convergence
2. **Middle Level**: IHX + cycle coupled solve
3. **Inner Level**: Segmented HX solvers (HTR, LTR, IHX, Cooler) with Newton-Raphson per segment

Convergence criteria: ΔT < 0.1 K, energy closure < 0.1%

### Key Entry Points

- `CoupledPlantSolver` in `cycle/coupled_solver.py` - Main plant-level solver
- `SCO2RecompressionCycle` in `cycle/sco2_cycle.py` - Standalone cycle solver
- `solve_counterflow_hx_segmented()` in `hx/segmented_hx.py` - Core HX algorithm

### Cycle State Points

The sCO2 recompression cycle has 9 state points:
- State 1: Main compressor inlet (from cooler)
- State 2: Main compressor outlet
- State 2a: LTR cold outlet
- State 3: Merge point (before HTR)
- State 4: HTR cold outlet (IHX inlet)
- State 5: Turbine inlet (IHX outlet)
- State 6: Turbine outlet
- State 6a: HTR hot outlet
- State 7: LTR hot outlet (split point)
- State 9: Recompressor outlet

## Key Physics

### Why Enthalpy-Based Segmented Models

Near the CO2 critical point (31.1°C, 7.38 MPa), specific heat varies dramatically. Traditional effectiveness methods assuming constant cp are inaccurate. The segmented approach:
- Divides each HX into N segments (typically 10-20)
- Uses CoolProp real-gas properties at each segment
- Checks pinch temperature at every segment (not just endpoints)

### Embedded Feasibility Constraints

Constraints are active during solve, not post-hoc checks:
- **Supercritical margins**: T_1 > T_crit + 3K, P_low > P_crit + 0.3 MPa
- **Pinch constraints**: ΔT ≥ 10 K at every HX segment
- **Temperature limits**: T_5 ≤ 800°C (material limit)
- **Energy closure**: |Q_in - W_out - Q_reject| < 0.1% Q_in

### Dry Cooler Fan Power

Fan power is computed physically (NOT a constant factor):
```
W_fan = (V_dot_air * dP_air) / (eta_fan * eta_motor)
```
Air-side pressure drop uses Kays & London correlation for finned tube banks.

## Reference Documentation

See `source docs/corrected_simulation_architecture.md` for the complete engineering specification including:
- Six corrections vs. original implementation
- Full constraint equations
- Solver pseudocode
- All design assumptions
