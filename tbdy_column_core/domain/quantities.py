"""C-08: canonical mm, N, Nmm and MPa scalar value objects.

No implicit float conversion; arithmetic is restricted by physical dimension.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt, radians, degrees
from typing import Self


def finite_real(value: int | float, *, field: str = "scalar") -> float:
    if isinstance(value, bool) or type(value) not in (int, float):
        raise TypeError(f"{field} requires int|float, never bool or a quantity")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{field} overflow") from exc
    if not isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class Quantity:
    _canonical: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "_canonical",
                           finite_real(self._canonical, field=type(self).__name__))

    def __float__(self):
        raise TypeError("explicit unit property required")

    def __add__(self, other: object) -> Self:
        if type(self) is not type(other):
            return NotImplemented
        return type(self)(self._canonical + other._canonical)

    def __sub__(self, other: object) -> Self:
        if type(self) is not type(other):
            return NotImplemented
        return type(self)(self._canonical - other._canonical)

    def __neg__(self) -> Self:
        return type(self)(-self._canonical)

    def __mul__(self, other: object):
        if type(other) in (int, float):
            return type(self)(self._canonical * finite_real(other))
        return NotImplemented

    def __rmul__(self, other: object):
        # Do not recursively re-dispatch unrelated Quantity subclasses.
        # Python 3.13 may try the reflected method again before raising.
        if type(other) in (int, float):
            return self * other
        return NotImplemented

    def __truediv__(self, other: object):
        if type(other) in (int, float):
            denominator = finite_real(other)
            if denominator == 0.0:
                raise ZeroDivisionError("scalar is zero")
            return type(self)(self._canonical / denominator)
        return NotImplemented


@dataclass(frozen=True, slots=True)
class Length(Quantity):
    @classmethod
    def mm(cls, x): return cls(finite_real(x))
    @classmethod
    def cm(cls, x): return cls(finite_real(x)*10)
    @classmethod
    def m(cls, x): return cls(finite_real(x)*1000)
    @property
    def as_mm(self): return self._canonical
    @property
    def as_cm(self): return self._canonical/10
    @property
    def as_m(self): return self._canonical/1000

    def __mul__(self, other):
        if type(other) is Length:
            return Area.mm2(self._canonical*other._canonical)
        if type(other) is Force:
            return Moment.nmm(self._canonical*other.as_n)
        return super().__mul__(other)


@dataclass(frozen=True, slots=True)
class Area(Quantity):
    @classmethod
    def mm2(cls, x): return cls(finite_real(x))
    @classmethod
    def cm2(cls, x): return cls(finite_real(x)*100)
    @property
    def as_mm2(self): return self._canonical
    @property
    def as_cm2(self): return self._canonical/100

    def __mul__(self, other):
        if type(other) is Stress:
            return Force.n(self._canonical*other.as_mpa)
        return super().__mul__(other)


@dataclass(frozen=True, slots=True)
class LengthSquared(Quantity):
    @classmethod
    def mm2(cls, x): return cls(finite_real(x))
    @classmethod
    def cm2(cls, x): return cls(finite_real(x)*100)
    @property
    def as_mm2(self): return self._canonical

    def sqrt(self) -> Length:
        if self._canonical < 0:
            raise ValueError("negative squared length")
        return Length.mm(sqrt(self._canonical))


@dataclass(frozen=True, slots=True)
class Inertia(Quantity):
    @classmethod
    def mm4(cls, x): return cls(finite_real(x))
    @classmethod
    def cm4(cls, x): return cls(finite_real(x)*10_000)
    @classmethod
    def m4(cls, x): return cls(finite_real(x)*1_000_000_000_000)
    @property
    def as_mm4(self): return self._canonical
    @property
    def as_cm4(self): return self._canonical/10_000

    def __truediv__(self, other):
        if type(other) is Area:
            if other.as_mm2 == 0:
                raise ZeroDivisionError("area is zero")
            return LengthSquared.mm2(self._canonical/other.as_mm2)
        return super().__truediv__(other)


@dataclass(frozen=True, slots=True)
class Force(Quantity):
    @classmethod
    def n(cls, x): return cls(finite_real(x))
    @classmethod
    def kn(cls, x): return cls(finite_real(x)*1000)
    @property
    def as_n(self): return self._canonical
    @property
    def as_kn(self): return self._canonical/1000

    def __mul__(self, other):
        if type(other) is Length:
            return Moment.nmm(self._canonical*other.as_mm)
        return super().__mul__(other)


@dataclass(frozen=True, slots=True)
class Moment(Quantity):
    @classmethod
    def nmm(cls, x): return cls(finite_real(x))
    @classmethod
    def kn_cm(cls, x): return cls(finite_real(x)*10_000)
    @classmethod
    def kn_m(cls, x): return cls(finite_real(x)*1_000_000)
    @property
    def as_nmm(self): return self._canonical
    @property
    def as_kn_cm(self): return self._canonical/10_000
    @property
    def as_kn_m(self): return self._canonical/1_000_000


@dataclass(frozen=True, slots=True)
class Stress(Quantity):
    @classmethod
    def mpa(cls, x): return cls(finite_real(x))
    @property
    def as_mpa(self): return self._canonical

    def __mul__(self, other):
        if type(other) is Area:
            return Force.n(self._canonical*other.as_mm2)
        return super().__mul__(other)


@dataclass(frozen=True, slots=True)
class ElasticModulus(Quantity):
    @classmethod
    def mpa(cls, x): return cls(finite_real(x))
    @property
    def as_mpa(self): return self._canonical


@dataclass(frozen=True, slots=True)
class Angle(Quantity):
    @classmethod
    def deg(cls, x): return cls(radians(finite_real(x)))
    @classmethod
    def rad(cls, x): return cls(finite_real(x))
    @property
    def as_deg(self): return degrees(self._canonical)
    @property
    def as_rad(self): return self._canonical
