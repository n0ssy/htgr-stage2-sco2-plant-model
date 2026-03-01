# Supporting Document: Technical Reference for Q&A

This document contains backup information for answering follow-up questions after the presentation.

---

## 1. Major Assumptions Summary Table

| # | Assumption | Value | Literature Source | Qualitative Impact |
|---|------------|-------|-------------------|-------------------|
| 1 | Turbine isentropic efficiency | 90% | Dostal (2004) MIT Thesis | ±1% efficiency → ±0.5% cycle efficiency |
| 2 | Main compressor efficiency | 89% | Dostal (2004) MIT Thesis | ±1% efficiency → ±0.3% cycle efficiency |
| 3 | Recompressor efficiency | 89% | Dostal (2004) MIT Thesis | ±1% efficiency → ±0.2% cycle efficiency |
| 4 | Minimum pinch temperature (recuperators) | 10 K | Industry standard for PCHEs | Lower pinch = more recovery but larger HX |
| 5 | Minimum pinch temperature (cooler) | 5 K | Air-side heat transfer limited | Sets minimum T1 above ambient |
| 6 | CO2 property data | Span-Wagner EOS via CoolProp | IAPWS/NIST standard (1996) | Foundational — all calculations depend on this |
| 7 | Helium outlet temperature | 850°C | HTTR (Japan) operating data | Sets max turbine inlet temperature |
| 8 | Helium return temperature | 395°C | HTTR design specification | Must match reactor requirements |
| 9 | Helium pressure | 4 MPa | HTTR design specification | Affects He mass flow rate |
| 10 | Reactor thermal power | 30 MW | HTTR test reactor scale | Scales linearly — affects absolute values only |
| 11 | Ambient temperature | 40°C | Hot climate design point | Conservative; hotter = worse efficiency |
| 12 | High-side pressure | 25 MPa | Mid-range of feasible (20-30 MPa) | Could be optimised in future work |
| 13 | Low-side pressure | 8 MPa | Above critical + margin | Must stay supercritical |
| 14 | Recompression fraction | 0.35 | Near-optimal from literature | ±0.05 → ±0.5% cycle efficiency |
| 15 | IHX pressure drop (He side) | 50 kPa | ~1.25% of He pressure, typical | Higher drop = lower efficiency |
| 16 | IHX pressure drop (CO2 side) | 100 kPa | ~0.5% of CO2 pressure, typical | Higher drop = lower efficiency |
| 17 | Recuperator pressure drops | 50 kPa each side | Typical for compact PCHEs | Each +10 kPa costs ~0.05% efficiency |
| 18 | Fan efficiency | 70% | Industry typical for large fans | Affects parasitic power |
| 19 | Motor efficiency | 95% | Industry typical for VFD motors | Affects parasitic power |
| 20 | Number of HX segments | 10 | Convergence testing | More = slower but more accurate |

---

## 2. Key Results Summary

### Dostal Validation Case (Cycle Only)
| Parameter | Dostal (2004) | Our Model | Status |
|-----------|---------------|-----------|--------|
| Compressor inlet T1 | 32°C | 32°C | Match |
| Turbine inlet T5 | 550°C | 550°C | Match |
| High pressure | 20 MPa | 20 MPa | Match |
| Low pressure | 7.7 MPa | 7.7 MPa | Match |
| Thermal efficiency | ~45% | 44.7% | <1% error |

### Coupled Plant at 40°C Ambient
| Parameter | Value |
|-----------|-------|
| Compressor inlet T1 | 50°C |
| Turbine inlet T5 | 520°C |
| Gross cycle power | 9.7 MW |
| Fan power (parasitic) | 1.4 MW |
| Auxiliary power | 0.1 MW |
| Net power output | 8.2 MW |
| Thermal efficiency (gross) | 32.5% |
| Net efficiency (after parasitics) | 27.4% |
| CO2 mass flow | 161 kg/s |
| Air mass flow (cooler) | 1,001 kg/s |
| Heat rejected | 20.2 MW |

---

## 3. The 11 Embedded Constraints

| ID | Constraint | Description | Limit |
|----|------------|-------------|-------|
| T01 | Supercritical temperature margin | T1 > T_critical + margin | +3 K above 31.1°C |
| T02 | Supercritical pressure margin | P_low > P_critical + margin | +0.3 MPa above 7.38 MPa |
| T03 | Turbine inlet temperature limit | T5 ≤ T_max | 800°C (material limit) |
| T04 | Helium return temperature | T_He_return ≥ required | 395°C for reactor |
| P01 | IHX pinch | ΔT ≥ minimum at all segments | 10 K |
| P02 | HTR pinch | ΔT ≥ minimum at all segments | 10 K |
| P03 | LTR pinch | ΔT ≥ minimum at all segments | 10 K |
| P04 | Cooler pinch | ΔT ≥ minimum at all segments | 5 K |
| E01 | Positive gross work | W_turbine > W_compressors | Must produce power |
| E02 | Positive net work | W_net > 0 after parasitics | Must have usable output |
| E03 | Energy closure | \|Q_in - W_out - Q_reject\| < 0.1% | Conservation of energy |

---

## 4. Phenomena Included vs. Excluded

### Included in Model
- Real-gas property variations (critical for accuracy near critical point)
- Pressure drops in all heat exchangers
- Segmented heat exchanger analysis (10 segments each)
- Per-segment pinch checking
- Physical fan power calculation
- Recompression cycle with flow split
- Counterflow heat exchanger configuration

### Excluded from Model (with justification)
| Excluded | Justification |
|----------|---------------|
| Transient behaviour | Phase 1 is steady-state design point |
| Part-load performance | Design point first; off-design later |
| Detailed HX geometry | Segmented approach captures key physics without geometry |
| Mechanical bearing losses | <1% of shaft power; captured in efficiency values |
| Generator efficiency | 98-99%; would just scale output |
| Piping heat losses | Insulated; <1% loss |
| Seal leakage | Well-designed seals; negligible |
| Reactor neutronics | Out of scope; we model power extraction, not reactor physics |
| Two-phase regions | Supercritical margins ensure we stay single-phase |

---

## 5. Potential Questions and Answers

### Q: Why 10 segments specifically?
**A:** We tested 5, 10, and 20 segments. 10 segments gives results within 0.1% of 20 segments while running faster. For the Dostal validation, we use 20 segments for higher accuracy. 10 is the balance between accuracy and computation time.

### Q: Why is your coupled plant efficiency (32%) lower than Dostal (45%)?
**A:** Different operating conditions. Dostal's validation case uses ideal conditions: 32°C compressor inlet, 550°C turbine inlet. Our coupled plant at 40°C ambient can only achieve ~50°C compressor inlet (limited by cooler approach temperature) and ~520°C turbine inlet (limited by IHX approach). The smaller temperature difference between heat source and heat sink means lower Carnot-limited efficiency.

### Q: What is the Span-Wagner equation?
**A:** A Helmholtz free energy equation of state for CO2, containing 42 terms fitted to experimental data. It's accurate to 0.03% in density and better than 1% in heat capacity across the supercritical region. It was adopted as the NIST/IAPWS reference standard in 1996 and is implemented in CoolProp.

### Q: How do you handle two-phase regions?
**A:** We don't need to — the supercritical constraints (T01 and T02) ensure that T > 34°C and P > 7.68 MPa at all points in the cycle, keeping CO2 in the supercritical single-phase regime throughout.

### Q: Why use a recompression cycle instead of a simple Brayton cycle?
**A:** The LTR has mismatched heat capacity rates between the hot and cold sides due to CO2 property variations near the critical point. If we sent all flow through both sides, we'd get a pinch violation. By splitting the flow (35% to recompressor, 65% to main compressor), we balance the heat capacities and recover more heat. This improves efficiency by 3-5 percentage points.

### Q: What would happen if ambient temperature increased to 50°C?
**A:** The cooler would struggle to reject heat with only a 5K approach. Compressor inlet temperature would rise to ~55°C minimum. Efficiency would drop by approximately 2-3 percentage points, and fan power would increase as more air flow is needed.

### Q: Why not use water cooling?
**A:** The project brief specifies water-independent heat rejection. Dry cooling with air allows deployment in arid locations without water infrastructure. The trade-off is higher parasitic power (fans vs. pumps) and lower efficiency at high ambient temperatures.

### Q: How sensitive is the model to turbomachinery efficiency?
**A:** Very sensitive. A 1% drop in turbine efficiency (90% → 89%) reduces cycle efficiency by approximately 0.5 percentage points. Compressor efficiency is slightly less sensitive. This is why we use well-established values from Dostal's thesis.

### Q: Can your model handle different reactor powers?
**A:** Yes. The thermodynamic cycle scales — if you double the reactor power to 60 MW, you approximately double the CO2 mass flow and power output. The efficiencies and temperatures remain similar. The current 30 MW is based on HTTR; commercial plants would be 100-600 MW.

### Q: Why is the IHX pressure drop on the CO2 side (100 kPa) higher than on the He side (50 kPa)?
**A:** CO2 at 20 MPa is much denser than helium at 4 MPa, so for similar velocities it generates more pressure drop. The values are typical for printed-circuit heat exchangers and represent approximately 0.5% and 1.25% of their respective operating pressures.

### Q: What is your primary figure of merit for the HTGR team?
**A:** Net CO2 reduced per year per MWth. This accounts for:
- CO2 avoided by displacing grid electricity
- CO2 captured via DAC (using waste heat and electricity)
- CO2 embodied in products (methanol synthesis)

Our model calculates the optimal allocation of electricity and heat to maximise this figure.

---

## 6. Glossary of Key Terms

| Term | Definition |
|------|------------|
| **sCO2** | Supercritical carbon dioxide — CO2 above its critical point (31.1°C, 7.38 MPa) |
| **Brayton cycle** | A thermodynamic cycle with compression, heating, expansion, and cooling |
| **Recompression** | A cycle variant where flow is split to balance heat capacity rates |
| **Recuperator** | A heat exchanger that recovers waste heat to preheat the working fluid |
| **HTR** | High-Temperature Recuperator — between turbine outlet and IHX inlet |
| **LTR** | Low-Temperature Recuperator — between HTR outlet and cooler/compressor |
| **IHX** | Intermediate Heat Exchanger — transfers heat from helium to CO2 |
| **Pinch point** | Location where hot and cold streams are closest in temperature |
| **PCHE** | Printed-Circuit Heat Exchanger — compact design with etched channels |
| **Isentropic efficiency** | Ratio of actual work to ideal (reversible) work |
| **Parasitic load** | Power consumed by plant auxiliary equipment (fans, pumps, controls) |
| **HTTR** | High Temperature Test Reactor — Japanese 30 MW test reactor |
| **CoolProp** | Open-source thermodynamic property library |
| **Span-Wagner** | Reference equation of state for CO2 properties |
| **Effectiveness** | Ratio of actual heat transfer to maximum possible |
| **NTU** | Number of Transfer Units — dimensionless HX performance parameter |

---

## 7. File Locations for Reference

| File | Purpose |
|------|---------|
| `assumptions.yaml` | Complete documented assumptions with sources |
| `results_baseline.json` | Numerical results from coupled plant solve |
| `feasibility_report.txt` | Constraint satisfaction report |
| `co2_reduction_results.json` | CO2 reduction analysis outputs |
| `validation/dostal_validation.py` | Dostal benchmark test code |
| `cycle/coupled_solver.py` | Main plant solver |
| `hx/segmented_hx.py` | Segmented heat exchanger engine |
| `components/dry_cooler.py` | Physical fan power model |
| `properties/fluids.py` | CoolProp wrapper |

---

## 8. Quick Reference: State Points in the Cycle

```
State 1:  Main compressor inlet (coldest point)      ~32-50°C,  7.7-8 MPa
State 2:  Main compressor outlet                     ~65-145°C, 20-25 MPa
State 2a: LTR cold outlet (MC path only)             ~190-310°C
State 3:  Merge point (2a + 9 combined)              ~200-315°C
State 4:  HTR cold outlet / IHX CO2 inlet            ~370-400°C
State 5:  Turbine inlet / IHX CO2 outlet (hottest)   ~520-550°C, 20-25 MPa
State 6:  Turbine outlet                             ~390-400°C, 7.7-8 MPa
State 6a: HTR hot outlet                             ~300-330°C
State 7:  LTR hot outlet / split point               ~190°C
State 9:  Recompressor outlet                        ~200-320°C
```

The lower values are for Dostal validation (ideal conditions); the higher values are for the coupled plant at 40°C ambient.

---

*Document prepared for UCL HTGR Team - Rolls Royce Fission Energy Project Phase 1 Presentation*
