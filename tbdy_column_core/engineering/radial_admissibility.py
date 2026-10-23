"""B5: independent geometric admissibility checks before interpreting radial PMM.

The pinned physics kernel's ray/convex-hull function is not altered. This
check only verifies that a ray from (M2,M3)=(0,0) is meaningful for the
sampled interaction polygon. When zero is outside the sampled hull, the
legacy kernel can report an ENTRY intersection as if it were capacity.
Reject that interpretation; never claim physical axial-capacity failure.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import hypot, isfinite
from typing import Sequence
from ..domain.section_requests import RadialReferenceAudit, RadialReferenceStatus
from ..domain.quantities import Moment
from ..domain.tolerances import NumericalPolicy, within


def _cross(a,b,c)->float:
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def _hull(points: Sequence[tuple[float,float]])->tuple[tuple[float,float],...]:
    points=sorted(set(points))
    if len(points)<3:
        return tuple(points)
    lower=[]
    for p in points:
        while len(lower)>1 and _cross(lower[-2],lower[-1],p)<=0:
            lower.pop()
        lower.append(p)
    upper=[]
    for p in reversed(points):
        while len(upper)>1 and _cross(upper[-2],upper[-1],p)<=0:
            upper.pop()
        upper.append(p)
    return tuple(lower[:-1]+upper[:-1])


def _closest_segment_distance(p,a,b)->float:
    dx=b[0]-a[0]
    dy=b[1]-a[1]
    length2=dx*dx+dy*dy
    if not isfinite(length2) or length2<=0:
        return float("inf")
    t=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length2
    t=max(0.,min(1.,t))
    return hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)


@dataclass(frozen=True,slots=True)
class RadialHullCheck:
    audit: RadialReferenceAudit
    vertices: tuple[tuple[float,float],...]


def check_radial_reference(states,policy: NumericalPolicy)->RadialHullCheck:
    """Check only finite, non-degenerate convex hull and strict origin inside.

    Clearance is signed perpendicular distance in Nmm from the origin
    to the nearest supporting hull line. If within the supplied absolute
    Moment tolerance of a hull edge, the reference is unresolved.
    """
    if type(policy) is not NumericalPolicy:
        raise TypeError("NumericalPolicy required")
    samples=tuple((v.m2_nmm,v.m3_nmm) for v in states)
    tolerance=policy.moment_tol.as_nmm
    if len(samples)<3 or not all(isfinite(x) and isfinite(y) for x,y in samples):
        status=(RadialReferenceStatus.NONFINITE_SAMPLED_HULL
                if len(samples)>=3 else RadialReferenceStatus.DEGENERATE_SAMPLED_HULL)
        return RadialHullCheck(RadialReferenceAudit(status,len(samples),None,policy.moment_tol),())
    hull=_hull(samples)
    if len(hull)<3:
        return RadialHullCheck(RadialReferenceAudit(
            RadialReferenceStatus.DEGENERATE_SAMPLED_HULL,len(hull),None,policy.moment_tol),hull)
    signed=[]
    for a,b in zip(hull,hull[1:]+hull[:1]):
        edge_length=hypot(b[0]-a[0],b[1]-a[1])
        if not isfinite(edge_length) or edge_length<=0:
            return RadialHullCheck(RadialReferenceAudit(
                RadialReferenceStatus.DEGENERATE_SAMPLED_HULL,len(hull),None,policy.moment_tol),hull)
        # Hull ordering is CCW, positive cross for interior origin.
        signed.append(_cross(a,b,(0.,0.))/edge_length)
    if not all(isfinite(x) for x in signed):
        return RadialHullCheck(RadialReferenceAudit(
            RadialReferenceStatus.NONFINITE_SAMPLED_HULL,len(hull),None,policy.moment_tol),hull)
    minimum=min(signed)
    status=(RadialReferenceStatus.VALIDATED
            if minimum>tolerance else RadialReferenceStatus.ORIGIN_NOT_STRICT_INTERIOR)
    return RadialHullCheck(RadialReferenceAudit(
        status,len(hull),Moment.nmm(minimum),policy.moment_tol),hull)


def verify_radial_boundary(radial, demand_m2: Moment,demand_m3: Moment,
                           policy: NumericalPolicy,hull: RadialHullCheck)->bool:
    """Independent numerical geometry consistency, NOT a design decision."""
    if hull.audit.status!=RadialReferenceStatus.VALIDATED:
        return False
    if radial.status!="PROVEN":
        return False
    values=(radial.capacity_nmm,radial.boundary_m2_nmm,radial.boundary_m3_nmm)
    if not all(isfinite(x) for x in values):
        return False
    capacity,m2,m3=values
    if capacity<=policy.moment_tol.as_nmm:
        return False
    demand=hypot(demand_m2.as_nmm,demand_m3.as_nmm)
    if demand<=0 or not isfinite(demand):
        return False
    expected_m2=capacity*demand_m2.as_nmm/demand
    expected_m3=capacity*demand_m3.as_nmm/demand
    if not all((
        within(hypot(m2,m3),capacity,policy.moment_tol.as_nmm,policy.relative_tol),
        within(m2,expected_m2,policy.moment_tol.as_nmm,policy.relative_tol),
        within(m3,expected_m3,policy.moment_tol.as_nmm,policy.relative_tol),
    )):
        return False
    boundary_gap=min(_closest_segment_distance((m2,m3),a,b)
                     for a,b in zip(hull.vertices,hull.vertices[1:]+hull.vertices[:1]))
    if not isfinite(boundary_gap):
        return False
    return boundary_gap<=policy.moment_tol.as_nmm+policy.relative_tol*capacity
