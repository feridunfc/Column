"""C-10: right-handed frames, signed physical 6-vector and r×F transfer.

No ETABS local forces are assumed compression positive; axial sign must be
provided explicitly at the kernel boundary.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from math import sqrt
from .quantities import Length, Force, Moment, finite_real


@dataclass(frozen=True, slots=True)
class Point3D:
    x: Length
    y: Length
    z: Length
    def __post_init__(self):
        if any(type(v) is not Length for v in (self.x,self.y,self.z)):
            raise TypeError("Point3D requires typed Length coordinates")
    @property
    def mm(self) -> tuple[float,float,float]:
        return (self.x.as_mm,self.y.as_mm,self.z.as_mm)


def dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],
            a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


@dataclass(frozen=True, slots=True)
class LocalFrame:
    origin: Point3D
    e1: tuple[float,float,float]
    e2: tuple[float,float,float]
    e3: tuple[float,float,float]
    axis_tolerance: float = 1e-10

    def __post_init__(self):
        if type(self.origin) is not Point3D:
            raise TypeError("frame origin must be Point3D")
        tol=finite_real(self.axis_tolerance)
        if tol <= 0 or tol >= 1e-2:
            raise ValueError("axis tolerance must be reasonable positive dimensionless")
        axes=(self.e1,self.e2,self.e3)
        for name,axis in zip(("e1","e2","e3"),axes):
            if type(axis) is not tuple or len(axis)!=3:
                raise TypeError(f"{name} must have three components")
            v=tuple(finite_real(c) for c in axis)
            if abs(dot(v,v)-1)>tol:
                raise ValueError(f"{name} not unit-length")
        for i,j in ((0,1),(0,2),(1,2)):
            if abs(dot(axes[i],axes[j]))>tol:
                raise ValueError("local frame axes not orthogonal")
        if abs(dot(cross(self.e1,self.e2),self.e3)-1)>tol:
            raise ValueError("right-handed frame required")

    def to_global(self, local_components):
        if len(local_components)!=3:
            raise ValueError("need 3 components")
        v=tuple(finite_real(x) for x in local_components)
        return tuple(sum(v[j]*axis[i] for j,axis in enumerate((self.e1,self.e2,self.e3)))
                     for i in range(3))

    def to_local(self, global_components):
        if len(global_components)!=3:
            raise ValueError("need 3 components")
        v=tuple(finite_real(x) for x in global_components)
        return tuple(dot(v,axis) for axis in (self.e1,self.e2,self.e3))


@dataclass(frozen=True, slots=True)
class ActionVector:
    f1: Force
    f2: Force
    f3: Force
    m1: Moment
    m2: Moment
    m3: Moment
    def __post_init__(self):
        if any(type(x) is not Force for x in (self.f1,self.f2,self.f3)) or any(
            type(x) is not Moment for x in (self.m1,self.m2,self.m3)):
            raise TypeError("action requires three Force + three Moment")
    @property
    def f(self): return (self.f1.as_n,self.f2.as_n,self.f3.as_n)
    @property
    def m(self): return (self.m1.as_nmm,self.m2.as_nmm,self.m3.as_nmm)


def transform_action(action: ActionVector, source: LocalFrame,
                     target: LocalFrame) -> ActionVector:
    """M_target = R M_source + r_target×F_target;
    r_target points from target origin to source origin.
    """
    if any(type(x) is not t for x,t in ((action,ActionVector),
                                         (source,LocalFrame),(target,LocalFrame))):
        raise TypeError("requires ActionVector and explicit LocalFrames")
    global_f=source.to_global(action.f)
    global_m=source.to_global(action.m)
    f=target.to_local(global_f)
    m_rot=target.to_local(global_m)
    r_global=tuple(x-y for x,y in zip(source.origin.mm,target.origin.mm))
    r=target.to_local(r_global)
    t=cross(r,f)
    return ActionVector(*(Force.n(v) for v in f),
                        *(Moment.nmm(a+b) for a,b in zip(m_rot,t)))


class AxialSignConvention(StrEnum):
    F1_COMPRESSION_POSITIVE="F1_COMPRESSION_POSITIVE"
    F1_TENSION_POSITIVE="F1_TENSION_POSITIVE"


def kernel_compression_n(action: ActionVector, convention: AxialSignConvention) -> Force:
    if type(convention) is not AxialSignConvention:
        raise TypeError("explicit axial sign mapping required")
    return action.f1 if convention==AxialSignConvention.F1_COMPRESSION_POSITIVE else -action.f1


def frame_basis_max_residual(frame: LocalFrame) -> float:
    """Maximum dimensionless mismatch with a proper orthonormal basis.

    LocalFrame construction checks its own declared tolerance, but a separate
    NumericalPolicy may require more stringent precision. This helper does
    not transform or reinterpret a load/action or its reference position.
    """
    if type(frame) is not LocalFrame:
        raise TypeError("LocalFrame required")
    e1,e2,e3=frame.e1,frame.e2,frame.e3
    return max(
        *(abs(dot(e,e)-1.0) for e in (e1,e2,e3)),
        *(abs(dot(a,b)) for a,b in ((e1,e2),(e1,e3),(e2,e3))),
        abs(dot(cross(e1,e2),e3)-1.0),
    )
