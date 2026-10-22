"""B2: independently observable angular discretization budget (not code PASS).

A coarse/fine difference is *not* a certified error bound on exact section
capacity. Compare it to a separately identified Moment tolerance, never the
Force equilibrium tolerance. Both calculations use the same public B path.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from enum import StrEnum

from ..domain.quantities import Moment
from ..domain.section_requests import (
    RadialCapacityAtAxialForce, SectionCapacityProblem, SectionStatus,
)
from .section_solver import SectionSolver


class AngularRefinementStatus(StrEnum):
    OBSERVED_DELTA_WITHIN_BUDGET = "OBSERVED_DELTA_WITHIN_BUDGET"
    OBSERVED_DELTA_EXCEEDS_BUDGET = "OBSERVED_DELTA_EXCEEDS_BUDGET"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True,slots=True)
class RadialAngularRefinement:
    coarse_angle_count: int
    fine_angle_count: int
    coarse_capacity: Moment | None
    fine_capacity: Moment | None
    observed_delta: Moment | None
    numeric_budget: Moment
    status: AngularRefinementStatus
    issues: tuple[str,...]
    interpretation: str = (
        "Coarse/fine observed delta only; not global root uniqueness, "
        "not a certified exact-capacity error and not TS500 code compliance"
    )


def assess_radial_angular_refinement(
    problem: SectionCapacityProblem,
) -> RadialAngularRefinement:
    if type(problem) is not SectionCapacityProblem or type(problem.request) is not RadialCapacityAtAxialForce:
        raise TypeError("a typed radial SectionCapacityProblem is required")
    coarse=SectionSolver().calculate(problem)
    fine_problem=replace(problem,numerical_policy=replace(
        problem.numerical_policy, angle_count=problem.numerical_policy.angle_count*2))
    fine=SectionSolver().calculate(fine_problem)
    issues=tuple(
        ("COARSE:"+v for v in coarse.issues)
    )+tuple(("FINE:"+v for v in fine.issues))
    base=problem.numerical_policy.moment_tol
    if coarse.status!=SectionStatus.COMPLETE_RADIAL or fine.status!=SectionStatus.COMPLETE_RADIAL:
        return RadialAngularRefinement(
            problem.numerical_policy.angle_count,
            fine_problem.numerical_policy.angle_count,
            coarse.radial_capacity,fine.radial_capacity,
            None,base,AngularRefinementStatus.UNRESOLVED,
            issues+("INCOMPLETE_NUMERICAL_CAPACITY",)
        )
    a=coarse.radial_capacity.as_nmm
    b=fine.radial_capacity.as_nmm
    observed=Moment.nmm(abs(a-b))
    budget=Moment.nmm(base.as_nmm+problem.numerical_policy.relative_tol*max(abs(a),abs(b)))
    status=(AngularRefinementStatus.OBSERVED_DELTA_WITHIN_BUDGET
            if observed.as_nmm<=budget.as_nmm else
            AngularRefinementStatus.OBSERVED_DELTA_EXCEEDS_BUDGET)
    return RadialAngularRefinement(
        problem.numerical_policy.angle_count,
        fine_problem.numerical_policy.angle_count,
        coarse.radial_capacity,fine.radial_capacity,observed,budget,
        status,issues
    )
