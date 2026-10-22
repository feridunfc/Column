"""Conservative sampled fixed-N moment-hull preflight; no TS500 rules.

The source-pinned kernel constructs a convex hull and intersects a ray.
That intersection is meaningful as a radial *from the origin* only when
(0,0) is strictly inside the sampled hull. Angular-gap containment
implements this precondition without modifying/copying legacy hull math.

It is a necessary numerical/model guard, NOT a proof of physical
capacity, continuous-angle completeness or global axial-root uniqueness.
"""
from __future__ import annotations
from math import atan2, hypot, pi, isfinite
from collections.abc import Sequence

from ..domain.quantities import Angle, Moment, finite_real
from ..domain.section_requests import RadialHullEvidence, RadialHullStatus


def audit_radial_moment_hull(
    states: Sequence[object], *,
    moment_abs_tolerance: Moment,
    relative_tolerance: float,
) -> RadialHullEvidence:
    if type(moment_abs_tolerance) is not Moment:
        raise TypeError("moment_abs_tolerance requires Moment")
    if moment_abs_tolerance.as_nmm <= 0:
        raise ValueError("moment_abs_tolerance must be positive")
    rel=finite_real(relative_tolerance)
    if rel < 0:
        raise ValueError("relative_tolerance must be nonnegative")
    points=tuple((finite_real(x.m2_nmm),finite_real(x.m3_nmm)) for x in states)
    if not points:
        return RadialHullEvidence(RadialHullStatus.DEGENERATE_SAMPLED_HULL,
                                  0,0,None,None,None)
    magnitudes=[hypot(m2,m3) for m2,m3 in points]
    if not all(isfinite(m) for m in magnitudes):
        raise ValueError("nonfinite radial point magnitude")
    scale=max(magnitudes)
    threshold=moment_abs_tolerance.as_nmm+rel*scale
    directions=sorted(
        (atan2(m3,m2)%(2*pi))
        for (m2,m3),m in zip(points,magnitudes) if m>threshold
    )
    good=len(directions)
    discarded=len(points)-good
    if good<3:
        return RadialHullEvidence(RadialHullStatus.DEGENERATE_SAMPLED_HULL,
                                  good,discarded,None,None,None)
    gaps=[directions[i+1]-directions[i] for i in range(good-1)]
    gaps.append(2*pi+directions[0]-directions[-1])
    widest=max(gaps)
    # Points contained in an open semicircle cannot enclose the origin.
    # A gap of exactly pi is a hull-boundary (not strictly interior) case.
    # A 1e-12-rad floating guard rejects near-boundary classifications.
    margin=pi-widest
    status=(RadialHullStatus.ORIGIN_STRICT_INTERIOR_SAMPLED
            if margin>1e-12 else
            RadialHullStatus.ORIGIN_NOT_INTERIOR_SAMPLED)
    return RadialHullEvidence(
        status,good,discarded,Angle.rad(widest),Angle.rad(margin),
        None
    )


def radial_boundary_alignment_residual(
    *, demand_m2: Moment, demand_m3: Moment,
    radius: float, boundary_m2: float, boundary_m3: float,
) -> Moment:
    """Difference between the kernel boundary and the positive demand ray.

    Uses *returned* radius/boundary only. It does not construct an
    alternative interaction envelope, capacity or acceptance factor.
    """
    if any(type(m) is not Moment for m in (demand_m2,demand_m3)):
        raise TypeError("signed Moment direction required")
    d=hypot(demand_m2.as_nmm,demand_m3.as_nmm)
    values=(radius,boundary_m2,boundary_m3)
    if d==0 or not all(isfinite(x) for x in values) or radius<=0:
        raise ValueError("invalid radial capacity or demand direction")
    expected=(radius*demand_m2.as_nmm/d,radius*demand_m3.as_nmm/d)
    return Moment.nmm(hypot(boundary_m2-expected[0],
                            boundary_m3-expected[1]))
