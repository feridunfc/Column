"""Explicit rectangular RC section supplied by caller; no rebar search policy."""
from __future__ import annotations
from dataclasses import dataclass
from math import pi, hypot
from .quantities import Length, Area, Inertia, Stress, ElasticModulus, finite


@dataclass(frozen=True, slots=True)
class RectangularSection:
    b: Length  # local 2 dimension
    h: Length  # local 3 dimension
    def __post_init__(self):
        if type(self.b) is not Length or type(self.h) is not Length:
            raise TypeError("section dimensions require Length")
        if self.b.as_mm <= 0 or self.h.as_mm <= 0:
            raise ValueError("section dimensions must be positive")
    @property
    def area(self) -> Area: return self.b * self.h
    @property
    def i22(self) -> Inertia:
        return Inertia.mm4(self.b.as_mm * self.h.as_mm**3 / 12.0)
    @property
    def i33(self) -> Inertia:
        return Inertia.mm4(self.h.as_mm * self.b.as_mm**3 / 12.0)


@dataclass(frozen=True, slots=True)
class ConcreteMaterial:
    fck: Stress
    def __post_init__(self):
        if type(self.fck) is not Stress or self.fck.as_mpa <= 0:
            raise ValueError("concrete requires positive fck Stress")


@dataclass(frozen=True, slots=True)
class RebarSteel:
    fyk: Stress
    es: ElasticModulus
    def __post_init__(self):
        if type(self.fyk) is not Stress or type(self.es) is not ElasticModulus:
            raise TypeError("steel requires typed fyk and Es")
        if self.fyk.as_mpa <= 0 or self.es.as_mpa <= 0:
            raise ValueError("steel properties must be positive")


@dataclass(frozen=True, slots=True)
class DesignMaterial:
    concrete: ConcreteMaterial
    longitudinal_steel: RebarSteel
    fcd: Stress
    fyd: Stress
    epsilon_cu: float
    k1: float
    rule_ref: str

    def __post_init__(self):
        if type(self.concrete) is not ConcreteMaterial or type(self.longitudinal_steel) is not RebarSteel:
            raise TypeError("typed characteristic materials are required")
        if type(self.fcd) is not Stress or type(self.fyd) is not Stress:
            raise TypeError("design strengths require Stress")
        if self.fcd.as_mpa <= 0 or self.fyd.as_mpa <= 0:
            raise ValueError("design strengths must be positive")
        if not 0 < finite(self.epsilon_cu) <= 0.02:
            raise ValueError("unsupported concrete ultimate strain")
        if not 0 < finite(self.k1) <= 1:
            raise ValueError("unsupported rectangular block factor")
        if not isinstance(self.rule_ref, str) or not self.rule_ref.strip():
            raise ValueError("rule_ref is required")


@dataclass(frozen=True, slots=True)
class BarPoint:
    bar_id: str
    x2: Length
    x3: Length
    diameter: Length
    steel_ref: str
    def __post_init__(self):
        if not self.bar_id or not self.steel_ref:
            raise ValueError("bar identity/steel required")
        if any(type(v) is not Length for v in (self.x2,self.x3,self.diameter)):
            raise TypeError("bar coordinates and diameter require Length")
        if self.diameter.as_mm <= 0:
            raise ValueError("bar diameter must be positive")
    @property
    def area(self):
        return Area.mm2(pi * self.diameter.as_mm**2 / 4.0)


@dataclass(frozen=True, slots=True)
class LongitudinalLayout:
    section: RectangularSection
    clear_cover: Length
    tie_diameter: Length
    bars: tuple[BarPoint, ...]

    def __post_init__(self):
        if type(self.section) is not RectangularSection:
            raise TypeError("layout requires RectangularSection")
        if any(type(v) is not Length for v in (self.clear_cover, self.tie_diameter)):
            raise TypeError("cover and tie diameter require Length")
        if self.clear_cover.as_mm < 0 or self.tie_diameter.as_mm <= 0:
            raise ValueError("invalid cover/tie")
        if not isinstance(self.bars, tuple) or not self.bars:
            raise ValueError("explicit nonempty tuple of bars is required")
        if len({b.bar_id for b in self.bars}) != len(self.bars):
            raise ValueError("duplicate bar id")
        w = self.section.b.as_mm / 2
        h = self.section.h.as_mm / 2
        for bar in self.bars:
            if type(bar) is not BarPoint:
                raise TypeError("bars require BarPoint")
            limit = self.clear_cover.as_mm + self.tie_diameter.as_mm + bar.diameter.as_mm/2
            if abs(bar.x2.as_mm)+limit > w+1e-9 or abs(bar.x3.as_mm)+limit > h+1e-9:
                raise ValueError("bar violates clear cover/tie or lies outside section")
        for i, b in enumerate(self.bars):
            for other in self.bars[i+1:]:
                center_dist = hypot(b.x2.as_mm-other.x2.as_mm,b.x3.as_mm-other.x3.as_mm)
                if center_dist+1e-9 < (b.diameter.as_mm+other.diameter.as_mm)/2:
                    raise ValueError("overlapping longitudinal bars")
    @property
    def total_area(self):
        return Area.mm2(sum(b.area.as_mm2 for b in self.bars))


@dataclass(frozen=True, slots=True)
class RCSection:
    section_id: str
    profile: RectangularSection
    design_material: DesignMaterial
    longitudinal: LongitudinalLayout
    def __post_init__(self):
        if not isinstance(self.section_id,str) or not self.section_id.strip():
            raise ValueError("section_id is required")
        if self.profile != self.longitudinal.section:
            raise ValueError("layout section must match RC section")
        if type(self.design_material) is not DesignMaterial:
            raise TypeError("typed DesignMaterial required")
        if any(b.steel_ref != "LONGITUDINAL" for b in self.longitudinal.bars):
            raise ValueError("pilot supports only bars of supplied longitudinal steel")
