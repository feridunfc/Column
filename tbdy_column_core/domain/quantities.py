"""Typed engineering quantities; canonical scalars: N, mm, Nmm, MPa.

Operations cannot combine dimensions implicitly. No UI/IO dependencies.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite, sqrt


def finite(value: float, label: str = "value") -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise TypeError(f"{label} requires numeric scalar (not bool)")
    v = float(value)
    if not isfinite(v):
        raise ValueError(f"{label} must be finite")
    return v


@dataclass(frozen=True, slots=True)
class _Quantity:
    _value: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "_value", finite(self._value, type(self).__name__))

    def __add__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return type(self)(self._value + other._value)

    def __sub__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return type(self)(self._value - other._value)

    def __neg__(self):
        return type(self)(-self._value)

    def __abs__(self):
        return type(self)(abs(self._value))

    def __mul__(self, other):
        if isinstance(other, (int, float)) and not isinstance(other, bool):
            return type(self)(self._value * finite(other))
        return NotImplemented

    def __rmul__(self, other):
        return self * other

    def __truediv__(self, other):
        if isinstance(other, (int, float)) and not isinstance(other, bool):
            v = finite(other)
            if v == 0:
                raise ZeroDivisionError()
            return type(self)(self._value / v)
        return NotImplemented


@dataclass(frozen=True, slots=True)
class Length(_Quantity):
    @classmethod
    def mm(cls, x): return cls(finite(x))
    @classmethod
    def cm(cls, x): return cls(finite(x) * 10)
    @classmethod
    def m(cls, x): return cls(finite(x) * 1000)
    @property
    def as_mm(self): return self._value
    @property
    def as_cm(self): return self._value / 10
    @property
    def as_m(self): return self._value / 1000

    def __mul__(self, other):
        if isinstance(other, Length):
            return Area.mm2(self._value * other._value)
        if isinstance(other, Force):
            return Moment.nmm(self._value * other._value)
        return super(Length, self).__mul__(other)


@dataclass(frozen=True, slots=True)
class Area(_Quantity):
    @classmethod
    def mm2(cls, x): return cls(finite(x))
    @classmethod
    def cm2(cls, x): return cls(finite(x) * 100)
    @property
    def as_mm2(self): return self._value
    @property
    def as_cm2(self): return self._value / 100

    def __mul__(self, other):
        if isinstance(other, Stress):
            return Force.n(self._value * other._value)
        return super(Area, self).__mul__(other)


@dataclass(frozen=True, slots=True)
class LengthSquared(_Quantity):
    @classmethod
    def mm2(cls, x): return cls(finite(x))
    @classmethod
    def cm2(cls, x): return cls(finite(x) * 100)
    @property
    def as_mm2(self): return self._value
    def sqrt(self):
        if self._value < 0:
            raise ValueError("negative length squared")
        return Length.mm(sqrt(self._value))


@dataclass(frozen=True, slots=True)
class Inertia(_Quantity):
    @classmethod
    def mm4(cls, x): return cls(finite(x))
    @classmethod
    def cm4(cls, x): return cls(finite(x) * 10_000)
    @classmethod
    def m4(cls, x): return cls(finite(x) * 1_000_000_000_000)
    @property
    def as_mm4(self): return self._value
    @property
    def as_cm4(self): return self._value / 10_000
    def __truediv__(self, other):
        if isinstance(other, Area):
            if other.as_mm2 == 0:
                raise ZeroDivisionError()
            return LengthSquared.mm2(self._value / other.as_mm2)
        return super(Inertia, self).__truediv__(other)


@dataclass(frozen=True, slots=True)
class Force(_Quantity):
    @classmethod
    def n(cls, x): return cls(finite(x))
    @classmethod
    def kn(cls, x): return cls(finite(x) * 1000)
    @property
    def as_n(self): return self._value
    @property
    def as_kn(self): return self._value / 1000
    def __mul__(self, other):
        if isinstance(other, Length):
            return Moment.nmm(self._value * other.as_mm)
        return super(Force, self).__mul__(other)


@dataclass(frozen=True, slots=True)
class Moment(_Quantity):
    @classmethod
    def nmm(cls, x): return cls(finite(x))
    @classmethod
    def kn_cm(cls, x): return cls(finite(x) * 10_000)
    @classmethod
    def kn_m(cls, x): return cls(finite(x) * 1_000_000)
    @property
    def as_nmm(self): return self._value
    @property
    def as_kn_cm(self): return self._value / 10_000
    @property
    def as_kn_m(self): return self._value / 1_000_000


@dataclass(frozen=True, slots=True)
class Stress(_Quantity):
    @classmethod
    def mpa(cls, x): return cls(finite(x))
    @property
    def as_mpa(self): return self._value
    def __mul__(self, other):
        if isinstance(other, Area):
            return Force.n(self._value * other.as_mm2)
        return super(Stress, self).__mul__(other)


@dataclass(frozen=True, slots=True)
class ElasticModulus(_Quantity):
    @classmethod
    def mpa(cls, x): return cls(finite(x))
    @property
    def as_mpa(self): return self._value
