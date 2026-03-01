# Presentation Script: Modelling Framework & Validation

**Core time: approximately 3-4 minutes**
**Extended time: approximately 5-6 minutes**

*Sections marked [EXPAND] can be included if time permits, or skipped if running short.*

---

## Slide 1: Modelling Framework

This slide shows the architecture of our coupled plant simulation. The core challenge we faced is that supercritical CO2 behaves unusually near its critical point — 31 degrees Celsius, 7.4 megapascals. In this region, thermodynamic properties like specific heat can vary by a factor of five over just a few degrees. Traditional heat exchanger models assume constant properties, which fails badly here.

**[EXPAND]** To give you a sense of scale: at 8 megapascals and 35 degrees, the specific heat of CO2 is around 30 kilojoules per kilogram-Kelvin. Move just 20 degrees away, and it drops to about 5. A model that assumes constant properties would be off by a factor of six.

Our solution has four key elements.

First, nested fixed-point iteration. We have an outer loop that converges on three plant-level variables: the compressor inlet temperature T1, the turbine inlet temperature T5, and the CO2 mass flow rate. Inside that, the cycle solver handles the merge point temperature T3, where the recompressor and main compressor flows combine. This nested structure lets us solve the coupled system reliably.

**[EXPAND]** The outer loop typically converges in 30 to 50 iterations. We use relaxation factors to prevent oscillation — updating each variable as a weighted average of old and new values. Convergence is declared when temperatures change by less than 0.1 Kelvin between iterations.

Second, enthalpy-based segmented heat exchangers. We divide each exchanger into 10 segments and track enthalpy — not temperature times specific heat — at each point. This correctly captures property variations near the critical point. Within each exchanger, we use binary search to find the maximum heat transfer that respects the pinch constraint at every segment, not just at the endpoints.

**[EXPAND]** Why enthalpy? Because energy conservation is exact: heat transferred equals mass flow times enthalpy change. If we used temperature times specific heat, we'd need to track how specific heat varies — which is the problem we're trying to avoid. Enthalpy sidesteps this entirely. CoolProp gives us enthalpy directly from pressure and temperature, and temperature back from pressure and enthalpy.

Third, embedded feasibility constraints. The critical constraints — pinch temperatures and supercritical margins — are enforced during the solve. The heat exchanger binary search automatically reduces heat transfer if any segment violates the pinch. The compressor inlet temperature is bounded to stay above the critical point plus a safety margin. Other constraints like energy closure are checked during iteration and the solution is flagged if they're violated.

**[EXPAND]** We enforce 11 constraints in total. Four are pinch temperatures — one for each heat exchanger: the IHX, high-temperature recuperator, low-temperature recuperator, and dry cooler. Three are temperature limits: supercritical margin at compressor inlet, maximum turbine inlet, and helium return temperature. Two are pressure constraints: supercritical margin and bounds on operating pressures. And two are energy constraints: positive net work and energy balance closure.

Fourth, a physical dry cooler model. The fan power is not a fixed percentage of rejected heat — that would be unrealistic. We calculate actual air flow requirements, determine pressure drop through the tube bank using Kays and London correlations, then compute fan power from first principles: volumetric flow times pressure drop, divided by fan and motor efficiencies.

**[EXPAND]** For context: at 40 degrees ambient, we reject about 20 megawatts of heat through the cooler. This requires roughly 1000 kilograms per second of air flow, creating about 1000 pascals of pressure drop through the finned tube bank. The resulting fan power is 1.4 megawatts — that's 7 percent of the heat rejected, or about 15 percent of our gross electrical output. This is a significant parasitic load that a simpler model might underestimate.

All of this sits on CoolProp, which provides real-gas properties for CO2, helium, and air using internationally-accepted equations of state.

**[EXPAND]** CoolProp is an open-source library used in both academia and industry. For CO2, it implements the Span-Wagner equation of state, which has 42 terms fitted to experimental data. This is the same property formulation used by NIST and recommended by the International Association for the Properties of Water and Steam.

---

## Slide 2: Validation & Ingenuity

How do we know the model is correct? We validated against Dostal's 2004 MIT thesis, which is the standard reference for supercritical CO2 recompression cycles.

**[EXPAND]** Dostal's thesis is widely cited because it systematically analysed sCO2 cycles for nuclear applications — the same context as our project. His operating conditions and efficiency predictions have been reproduced by research groups at Sandia National Labs, Argonne, and others. If our model matches Dostal, we can be confident it's calculating the thermodynamics correctly.

The table shows our comparison. We matched Dostal's exact operating conditions: 32 degrees compressor inlet, 550 degrees turbine inlet, 20 megapascals high pressure, 7.7 megapascals low pressure. Using the same component efficiencies — 90 percent turbine, 89 percent compressors — our model predicts 44.7 percent thermal efficiency compared to Dostal's approximately 45 percent. That is less than one percent error.

**[EXPAND]** To be clear about what this validates: the cycle thermodynamics, the recuperator heat transfer calculations, and the turbomachinery work calculations. The small difference — 0.3 percentage points — could come from slightly different property data, numerical tolerances, or how Dostal rounded his published figures. The important point is we're within the uncertainty band of the reference.

Our confidence comes from three sources.

First, literature calibration. We reproduce Dostal's published results within 2 percent using identical conditions. The component efficiencies are not tuned to fit — they are taken directly from his thesis.

**[EXPAND]** This is important: we didn't adjust efficiencies until we matched Dostal. We used his exact values — 90 percent for the turbine, 89 percent for both compressors — and the cycle efficiency fell out of the calculation. This is validation, not curve-fitting.

Second, property data. CoolProp implements the Span-Wagner equation of state for CO2. This was adopted by IAPWS and NIST as the international standard in 1996, and has been validated against experimental data to better than one percent accuracy, even near the critical point.

**[EXPAND]** The Span-Wagner equation was developed specifically because CO2 behaviour near the critical point is so unusual. It's based on a Helmholtz free energy formulation with 42 terms, fitted to thousands of experimental measurements. When we call CoolProp for a property, we're getting the internationally-accepted reference value, not an approximation.

Third, assumption traceability. We have documented over 100 parameters in a YAML file with their sources. Every efficiency, every pressure drop, every constraint bound is recorded and traceable. The results are fully reproducible — anyone can run our code and verify the outputs.

**[EXPAND]** For example, if you want to know why we use 50 kilopascals for the recuperator pressure drop, the YAML file says it's typical for printed-circuit heat exchangers and cites the manufacturer's specifications. If you want to know why 10 Kelvin minimum pinch, it's industry standard for compact heat exchangers. Every number has a justification. This isn't just good practice — it means we can defend any assumption if questioned.

---

## End of Script

---

## Quick Reference Numbers (for Q&A)

| Parameter | Dostal Validation | Coupled Plant (40°C ambient) |
|-----------|-------------------|------------------------------|
| Compressor inlet T₁ | 32°C | 50°C |
| Turbine inlet T₅ | 550°C | 520°C |
| High pressure | 20 MPa | 25 MPa |
| Low pressure | 7.7 MPa | 8 MPa |
| Thermal efficiency | 44.7% | 32.5% |
| Net efficiency | — | 27.4% |
| Fan power | — | 1.4 MW |
| CO₂ mass flow | 250 kg/s | 161 kg/s |
| Heat rejected | — | 20.2 MW |
| Solve time | ~30 seconds | ~2 minutes |

---

## Bridging to Architecture Slide (if needed)

If someone asks how your slides connect to the architecture slide before yours:

> "The architecture slide shows the integrated system design — reactor, power cycle, and applications. My slides focus on how we modelled and validated the power cycle specifically. The cycle model produces the electricity and waste heat that feed into the DAC and HTSE processes shown in Zone 3 of the architecture. We needed to get the cycle model right first, because everything downstream depends on accurate predictions of power output and waste heat temperature."
