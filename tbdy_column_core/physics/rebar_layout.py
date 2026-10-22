"""Only the geometrical ColumnBarPoint dependency of the frozen section kernel.

Source signature from legacy/column-pre-clean-20261022:
physics/rebar_layout.py::ColumnBarPoint. Does not include any candidate generator,
code-dependent spacing policy or search.
"""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ColumnBarPoint:
    index: int
    x2_mm: float
    x3_mm: float
    diameter_mm: float
    area_mm2: float
