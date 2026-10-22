"""Public v1.3 B1 section-only entry point."""
from __future__ import annotations
from ..domain.section_requests import SectionCapacityProblem,SectionCapacityResult
from ..engineering.section_solver import SectionSolver


def calculate_section(problem: SectionCapacityProblem)->SectionCapacityResult:
    """Given an immutable RCSection + one explicit request, compute once.

    This is NOT check_column or design_column.
    """
    return SectionSolver().calculate(problem)
