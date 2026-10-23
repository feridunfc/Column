"""B6: three-level observed radial convergence, not a numerical certificate.

Distinct Force and Moment budgets. The 72/144/288 probe is explicitly
opt-in; fast ordinary calculations remain unchanged. Every resolution goes
through the public section solver and its source-bound TS500 kernel.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from enum import StrEnum
from math import isfinite

from ..domain.quantities import Moment
from ..domain.section_requests import SectionCapacityProblem,RadialCapacityAtAxialForce,SectionStatus
from .section_solver import SectionSolver


class TripleRefinementStatus(StrEnum):
    OBSERVED_STABLE_AT_BOTH_STEPS="OBSERVED_STABLE_AT_BOTH_STEPS"
    OBSERVED_NOT_STABLE="OBSERVED_NOT_STABLE"
    NUMERIC_UNRESOLVED="NUMERIC_UNRESOLVED"


@dataclass(frozen=True, slots=True)
class TripleAngularRefinement:
    counts: tuple[int,int,int]
    capacity_nmm: tuple[float|None,float|None,float|None]
    differences_nmm: tuple[float|None,float|None]
    moment_budgets_nmm: tuple[float|None,float|None]
    statuses: tuple[SectionStatus,SectionStatus,SectionStatus]
    verdict: TripleRefinementStatus
    issues: tuple[str,...]
    interpretation: str = (
        "Observed successive sampled radial differences, not a rigorous bound "
        "on continuous envelope error, global root uniqueness or code compliance"
    )


def assess_three_level_radial_refinement(
    problem: SectionCapacityProblem, *,
    counts: tuple[int,int,int]=(72,144,288)
)->TripleAngularRefinement:
    if type(problem) is not SectionCapacityProblem or type(problem.request) is not RadialCapacityAtAxialForce:
        raise TypeError("typed radial SectionCapacityProblem required")
    if type(counts) is not tuple or len(counts)!=3 or any(
        type(n) is not int or n<8 or n%4 for n in counts
    ) or not (counts[0]<counts[1]<counts[2]):
        raise ValueError("increasing three counts divisible by four required")
    policy=problem.numerical_policy
    results=[]
    for count in counts:
        variant=replace(problem,numerical_policy=replace(policy,angle_count=count))
        results.append(SectionSolver().calculate(variant))
    issues=tuple(f"ANGLE_COUNT_{n}:{issue}" for n,result in zip(counts,results)
                 for issue in result.issues)
    statuses=tuple(result.status for result in results)
    capacities=tuple(
        result.radial_capacity.as_nmm if result.radial_capacity is not None else None
        for result in results
    )
    delta=[]
    budget=[]
    for low,high in zip(capacities,capacities[1:]):
        if low is None or high is None or not(isfinite(low) and isfinite(high)):
            delta.append(None)
            budget.append(None)
        else:
            delta.append(abs(high-low))
            budget.append(policy.moment_tol.as_nmm +
                          policy.relative_tol*max(abs(low),abs(high)))
    if any(s!=SectionStatus.COMPLETE_RADIAL for s in statuses):
        verdict=TripleRefinementStatus.NUMERIC_UNRESOLVED
    elif all(d is not None and d<=b for d,b in zip(delta,budget)):
        verdict=TripleRefinementStatus.OBSERVED_STABLE_AT_BOTH_STEPS
    else:
        verdict=TripleRefinementStatus.OBSERVED_NOT_STABLE
    return TripleAngularRefinement(
        counts,capacities,tuple(delta),tuple(budget),statuses,verdict,issues
    )
