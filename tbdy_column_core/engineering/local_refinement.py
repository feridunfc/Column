"""Optional demand-ray angular refinement of a *sampled* PMM hull.

Adds actually solved neutral-axis states only near the current ray/hull
contact. No interpolation is passed off as a solved state; no assumption
of certified continuous angular accuracy or global axial-root uniqueness.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from math import hypot, isfinite
from types import SimpleNamespace
from ..domain.quantities import Angle
from ..domain.section_requests import SectionCapacityProblem, RadialCapacityAtAxialForce, SectionStatus
from ..domain.tolerances import within
from .section_solver import SectionSolver
from .section_adapter import SectionKernelAdapter
from .radial_admissibility import check_radial_reference,verify_radial_boundary
from ..physics.section_capacity import ColumnSectionCapacityError


class LocalRefinementStatus(StrEnum):
    OBSERVED_LOCAL_STABLE="OBSERVED_LOCAL_STABLE"
    OBSERVED_LOCAL_NOT_STABLE="OBSERVED_LOCAL_NOT_STABLE"
    NUMERIC_UNRESOLVED="NUMERIC_UNRESOLVED"


@dataclass(frozen=True,slots=True)
class LocalRadialRefinement:
    base_angle_count: int
    added_angles_deg: tuple[float,...]
    capacity_history_nmm: tuple[float,...]
    differences_nmm: tuple[float,...]
    budget_nmm: float
    status: LocalRefinementStatus
    issues: tuple[str,...]
    interpretation: str = (
        "Observed local ray-contact refinement only, NOT a rigorous bound "
        "on continuous-angle envelope error, globally unique axial root or code compliance"
    )


@dataclass(frozen=True,slots=True)
class _Point:
    theta: float
    m2_nmm: float
    m3_nmm: float


def _segment_gap(point,a,b):
    dx=b[0]-a[0]
    dy=b[1]-a[1]
    den=dx*dx+dy*dy
    if den<=0:
        return float("inf")
    t=max(0.,min(1.,((point[0]-a[0])*dx+(point[1]-a[1])*dy)/den))
    return hypot(point[0]-a[0]-t*dx,point[1]-a[1]-t*dy)


def assess_local_radial_refinement(
    problem:SectionCapacityProblem,*,max_added_angles:int=12,
    minimum_stable_steps:int=2
)->LocalRadialRefinement:
    if type(problem) is not SectionCapacityProblem or type(problem.request) is not RadialCapacityAtAxialForce:
        raise TypeError("typed radial problem required")
    if type(max_added_angles) is not int or not 1<=max_added_angles<=64:
        raise ValueError("max_added_angles must be integer 1..64")
    if type(minimum_stable_steps) is not int or not 2<=minimum_stable_steps<=max_added_angles:
        raise ValueError("minimum_stable_steps must be at least two")
    policy=problem.numerical_policy
    baseline=SectionSolver().calculate(problem)
    budget=policy.moment_tol.as_nmm+policy.relative_tol*(
        baseline.radial_capacity.as_nmm if baseline.radial_capacity is not None else 0
    )
    if baseline.status!=SectionStatus.COMPLETE_RADIAL:
        return LocalRadialRefinement(policy.angle_count,(),(),(),budget,
            LocalRefinementStatus.NUMERIC_UNRESOLVED,tuple(baseline.issues)+("BASELINE_UNRESOLVED",))
    adapter=SectionKernelAdapter(problem.section,problem.frame_model_contract)
    material=adapter.prepare_material()
    bars=adapter.bars()
    points=[_Point(s.normal_angle.as_deg,s.m2.as_nmm,s.m3.as_nmm)
            for s in baseline.states]
    history=[baseline.radial_capacity.as_nmm]
    added=[]
    deltas=[]
    issues=[]
    request=problem.request
    for _ in range(max_added_angles):
        hull=check_radial_reference(points,policy)
        if hull.audit.status.value!="VALIDATED":
            issues.append("SAMPLED_ORIGIN_NOT_INTERIOR")
            break
        radial=adapter.radial(points,request.target_compression,
                              request.direction_m2,request.direction_m3,360/policy.angle_count)
        if not verify_radial_boundary(radial,request.direction_m2,
                                      request.direction_m3,policy,hull):
            issues.append("RAY_BOUNDARY_INCONSISTENT")
            break
        boundary=(radial.boundary_m2_nmm,radial.boundary_m3_nmm)
        vertices=hull.vertices
        if len(vertices)<3:
            issues.append("DEGENERATE_HULL")
            break
        edges=[(a,vertices[(i+1)%len(vertices)])
                for i,a in enumerate(vertices)]
        a,b=min(edges,key=lambda pair:_segment_gap(boundary,*pair))
        if _segment_gap(boundary,a,b)>policy.moment_tol.as_nmm:
            issues.append("BOUNDARY_EDGE_NOT_RESOLVED")
            break
        def theta_at(v):
            matches=[p.theta for p in points
                     if (p.m2_nmm,p.m3_nmm)==v]
            if not matches:
                raise ValueError("hull vertex not associated with solved state")
            return matches[0]
        ta,tb=theta_at(a),theta_at(b)
        angular_distance=(tb-ta+180)%360-180
        if abs(angular_distance)<1e-9:
            issues.append("ZERO_NEUTRAL_AXIS_INTERVAL")
            break
        midpoint=(ta+angular_distance/2)%360
        if any(abs((p.theta-midpoint+180)%360-180)<1e-8 for p in points):
            issues.append("DUPLICATE_NEUTRAL_AXIS_ANGLE")
            break
        angle=Angle.deg(midpoint)
        try:
            audit=adapter.sample_axial_brackets(
                angle,request.target_compression,material,bars,
                force_atol_n=policy.force_balance_tol.as_n)
            if not audit.accepted_single_bracket:
                issues.append("LOCAL_ROOT_AMBIGUOUS:"+audit.issue_code)
                break
            solved=adapter.solve_one(angle,request.target_compression,policy,material,bars)
            if solved is None or not audit.contains_solution(solved.neutral_axis_depth_c_mm):
                issues.append("LOCAL_ROOT_NOT_QUALIFIED")
                break
            if not within(solved.n_compression_n,request.target_compression.as_n,
                          policy.force_balance_tol.as_n,policy.relative_tol):
                issues.append("LOCAL_ROOT_RESIDUAL_OVER_POLICY")
                break
            if not all(isfinite(v) for v in (solved.m2_nmm,solved.m3_nmm)):
                issues.append("NONFINITE_LOCAL_MOMENT")
                break
        except (ColumnSectionCapacityError,ValueError,ArithmeticError) as exc:
            issues.append("LOCAL_ROOT_UNRESOLVED:"+type(exc).__name__)
            break
        points.append(_Point(midpoint,solved.m2_nmm,solved.m3_nmm))
        added.append(midpoint)
        newhull=check_radial_reference(points,policy)
        next_radial=adapter.radial(points,request.target_compression,
                                  request.direction_m2,request.direction_m3,360/policy.angle_count)
        if not verify_radial_boundary(next_radial,request.direction_m2,
                    request.direction_m3,policy,newhull):
            issues.append("REFINED_BOUNDARY_UNRESOLVED")
            break
        capacity=next_radial.capacity_nmm
        delta=abs(capacity-history[-1])
        deltas.append(delta)
        history.append(capacity)
        budget=policy.moment_tol.as_nmm+policy.relative_tol*max(abs(capacity),abs(history[-2]))
        if len(deltas)>=minimum_stable_steps and all(d<=budget for d in deltas[-minimum_stable_steps:]):
            return LocalRadialRefinement(policy.angle_count,tuple(added),tuple(history),
                tuple(deltas),budget,LocalRefinementStatus.OBSERVED_LOCAL_STABLE,
                tuple(issues))
    status=(LocalRefinementStatus.NUMERIC_UNRESOLVED if issues
            else LocalRefinementStatus.OBSERVED_LOCAL_NOT_STABLE)
    return LocalRadialRefinement(policy.angle_count,tuple(added),tuple(history),
                                tuple(deltas),budget,status,tuple(issues))
