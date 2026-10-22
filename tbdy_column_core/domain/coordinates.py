"""Right-handed global/local frames and dimensionful positions."""
from dataclasses import dataclass
from math import sqrt
from .quantities import Length, finite


@dataclass(frozen=True, slots=True)
class Point3D:
    x: Length
    y: Length
    z: Length
    def __post_init__(self):
        if any(type(v) is not Length for v in (self.x, self.y, self.z)):
            raise TypeError("Point3D coordinates require Length")


def _dot(a, b): return sum(x*y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


@dataclass(frozen=True, slots=True)
class LocalFrame:
    origin: Point3D
    axis_1: tuple[float, float, float]
    axis_2: tuple[float, float, float]
    axis_3: tuple[float, float, float]

    def __post_init__(self):
        if type(self.origin) is not Point3D:
            raise TypeError("LocalFrame origin must be Point3D")
        axes = (self.axis_1, self.axis_2, self.axis_3)
        for axis in axes:
            if not isinstance(axis, tuple) or len(axis) != 3:
                raise TypeError("axes require 3-component tuples")
            v = tuple(finite(x, "axis component") for x in axis)
            if abs(_dot(v, v) - 1.0) > 1e-10:
                raise ValueError("non-unit axis")
        if any(abs(_dot(axes[i], axes[j])) > 1e-10 for i, j in ((0,1), (0,2), (1,2))):
            raise ValueError("axes must be orthogonal")
        if _dot(_cross(self.axis_1, self.axis_2), self.axis_3) < 1.0-1e-10:
            raise ValueError("LocalFrame must be right-handed")

    def to_global_vector(self, local):
        if len(local) != 3: raise ValueError("three local components required")
        return tuple(sum(finite(local[j]) * self.__getattribute__(f"axis_{j+1}")[i]
                         for j in range(3)) for i in range(3))

    def to_local_vector(self, global_xyz):
        if len(global_xyz) != 3: raise ValueError("three global components required")
        v = tuple(finite(x) for x in global_xyz)
        return tuple(_dot(v, axis) for axis in (self.axis_1, self.axis_2, self.axis_3))
