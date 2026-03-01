"""
Process allocation module for CO2 reduction applications.

Includes:
- Direct Air Capture (DAC) model
- High-Temperature Steam Electrolysis (HTSE) model
- Methanol synthesis model
- Constrained allocation optimizer
- CO2 accounting
"""

from .allocation import (
    DACConfig,
    DACModel,
    HTSEConfig,
    HTSEModel,
    MethanolConfig,
    MethanolModel,
    AllocationConfig,
    AllocationResult,
    CO2AccountingResult,
    ProcessAllocator,
)
