"""C-09 dimensional absolute and relative numerical-policy contract."""
from __future__ import annotations
from dataclasses import dataclass
from .quantities import Length, Force, Moment, finite_real


@dataclass(frozen=True, slots=True)
class NumericalPolicy:
    geometric_tol: Length
    axis_tol: float
    force_balance_tol: Force
    moment_tol: Moment
    relative_tol: float
    angle_count: int = 72
    max_iterations: int = 100

    def __post_init__(self) -> None:
        for name, kind in (("geometric_tol", Length), ("force_balance_tol", Force),
                           ("moment_tol", Moment)):
            item = getattr(self, name)
            if type(item) is not kind:
                raise TypeError(f"{name} requires {kind.__name__}")
            if item._canonical <= 0:
                raise ValueError(f"{name} must be > 0")
        for name, positive in (("axis_tol", True), ("relative_tol", False)):
            value = finite_real(getattr(self, name), field=name)
            if value <= 0 if positive else value < 0:
                raise ValueError(f"{name} out of range")
        if type(self.angle_count) is not int or self.angle_count < 8 or self.angle_count%4:
            raise ValueError("angle_count must be integer >=8 divisible by four")
        if type(self.max_iterations) is not int or self.max_iterations <= 0:
            raise ValueError("max_iterations must be positive integer")


def within(value_a: float, value_b: float, abs_tol: float, rel_tol: float) -> bool:
    from math import isfinite
    a, b = finite_real(value_a), finite_real(value_b)
    atol, rtol = finite_real(abs_tol), finite_real(rel_tol)
    if atol < 0 or rtol < 0:
        raise ValueError("tolerances must be nonnegative")
    return abs(a-b) <= atol + rtol * max(abs(a),abs(b))
