"""Typed absolute tolerances and dimensionless solver settings."""
from dataclasses import dataclass
from .quantities import Length, Force, Moment, finite


@dataclass(frozen=True, slots=True)
class NumericalPolicy:
    geometric_tol: Length
    force_balance_tol: Force
    moment_tol: Moment
    relative_tol: float
    angle_count: int = 72
    max_iterations: int = 100

    def __post_init__(self):
        for key, cls in (("geometric_tol", Length),
                         ("force_balance_tol", Force),
                         ("moment_tol", Moment)):
            val = getattr(self, key)
            if type(val) is not cls:
                raise TypeError(f"{key} requires {cls.__name__}")
            if val._value <= 0:
                raise ValueError(f"{key} must be positive")
        v = finite(self.relative_tol, "relative_tol")
        if v <= 0:
            raise ValueError("relative_tol must be > 0")
        if type(self.angle_count) is not int or self.angle_count < 8 or self.angle_count % 4:
            raise ValueError("angle_count must be >=8 and a multiple of 4")
        if type(self.max_iterations) is not int or self.max_iterations <= 0:
            raise ValueError("max_iterations must be positive integer")
