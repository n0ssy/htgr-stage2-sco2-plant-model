"""
sCO2 Plant Simulation Package

A physically-consistent simulation of HTGR + sCO2 recompression Brayton cycle.

Features:
- Enthalpy-based segmented heat exchanger models
- Pressure drops throughout cycle
- Coupled IHX-cycle solve
- Physical dry cooler model (airflow/dP-based fan power)
- Embedded feasibility constraints
"""

__version__ = '1.0.0'
__author__ = 'HTGR Team'

from .cycle.coupled_solver import CoupledPlantSolver, PlantConfig, PlantResult
from .cycle.sco2_cycle import SCO2RecompressionCycle, CycleConfig
