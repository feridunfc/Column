"""C-17/C-18: immutable geometric RC section and explicit design material laws."""
from __future__ import annotations
from dataclasses import dataclass
from math import pi, hypot
from .quantities import Length, Area, Inertia, Stress, ElasticModulus
from .identity import RevisionRef, RuleRef, required


@dataclass(frozen=True, slots=True)
class RectangularSection:
    b: Length             # dimension local 2
    h: Length             # dimension local 3

    def __post_init__(self):
        if any(type(x) is not Length for x in (self.b,self.h)):
            raise TypeError("b,h must be Length")
        if self.b.as_mm <= 0 or self.h.as_mm <= 0:
            raise ValueError("dimensions must be positive")

    @property
    def area(self)->Area:
        return self.b*self.h

    @property
    def i22(self)->Inertia:
        return Inertia.mm4(self.b.as_mm*self.h.as_mm**3/12)

    @property
    def i33(self)->Inertia:
        return Inertia.mm4(self.h.as_mm*self.b.as_mm**3/12)


@dataclass(frozen=True, slots=True)
class ConcreteMaterial:
    ref: RevisionRef
    fck: Stress
    def __post_init__(self):
        if type(self.ref) is not RevisionRef or type(self.fck) is not Stress:
            raise TypeError("concrete requires revision and Stress")
        if self.fck.as_mpa <= 0:
            raise ValueError("concrete strength must be positive")


@dataclass(frozen=True, slots=True)
class RebarSteel:
    ref: RevisionRef
    fyk: Stress
    def __post_init__(self):
        if type(self.ref) is not RevisionRef or type(self.fyk) is not Stress:
            raise TypeError("steel needs revision and Stress")
        if self.fyk.as_mpa <= 0:
            raise ValueError("steel strength must be positive")


@dataclass(frozen=True, slots=True)
class DesignSteelLaw:
    steel_ref: str
    fyd: Stress
    es: ElasticModulus
    law_revision: RevisionRef
    def __post_init__(self):
        required(self.steel_ref,"steel_ref")
        if type(self.fyd) is not Stress or type(self.es) is not ElasticModulus or type(self.law_revision) is not RevisionRef:
            raise TypeError("steel law requires typed strengths and revision")
        if self.fyd.as_mpa <= 0 or self.es.as_mpa <= 0:
            raise ValueError("steel law must be positive")


@dataclass(frozen=True, slots=True)
class DesignMaterial:
    concrete: ConcreteMaterial
    fcd: Stress
    k1: float
    epsilon_cu: float
    steel_laws: tuple[DesignSteelLaw,...]
    rule: RuleRef
    revision: RevisionRef
    def __post_init__(self):
        from .quantities import finite_real
        if type(self.concrete) is not ConcreteMaterial or type(self.fcd) is not Stress:
            raise TypeError("explicit concrete law required")
        if self.fcd.as_mpa <= 0 or not 0 < finite_real(self.k1) <= 1:
            raise ValueError("invalid concrete design block")
        if not 0 < finite_real(self.epsilon_cu) <= 0.02:
            raise ValueError("invalid concrete ultimate strain")
        if type(self.steel_laws) is not tuple or not self.steel_laws or any(
            type(x) is not DesignSteelLaw for x in self.steel_laws):
            raise ValueError("explicit immutable steel law population required")
        if len({x.steel_ref for x in self.steel_laws}) != len(self.steel_laws):
            raise ValueError("duplicate steel law reference")
        if type(self.rule) is not RuleRef or type(self.revision) is not RevisionRef:
            raise TypeError("material rule and revision required")

    def resolve_steel_laws(self, bar_refs: set[str]):
        matching=tuple(x for x in self.steel_laws if x.steel_ref in bar_refs)
        if len(matching)!=len(bar_refs):
            return None
        return matching


@dataclass(frozen=True, slots=True)
class BarPoint:
    bar_id: str
    x2: Length
    x3: Length
    diameter: Length
    steel_ref: str
    def __post_init__(self):
        required(self.bar_id,"bar_id")
        required(self.steel_ref,"steel_ref")
        if any(type(x) is not Length for x in (self.x2,self.x3,self.diameter)):
            raise TypeError("bar position and diameter require Length")
        if self.diameter.as_mm<=0:
            raise ValueError("diameter must be positive")
    @property
    def area(self)->Area:
        return Area.mm2(pi*self.diameter.as_mm**2/4)


@dataclass(frozen=True, slots=True)
class LongitudinalLayout:
    # Coordinates in section local 2/3. No duplicated profile.
    clear_cover: Length
    tie_diameter: Length
    bars: tuple[BarPoint,...]
    revision: RevisionRef
    def __post_init__(self):
        if type(self.clear_cover) is not Length or type(self.tie_diameter) is not Length:
            raise TypeError("cover and tie must be Length")
        if self.clear_cover.as_mm < 0 or self.tie_diameter.as_mm <= 0:
            raise ValueError("invalid cover/tie")
        if type(self.revision) is not RevisionRef:
            raise TypeError("layout revision required")
        if type(self.bars) is not tuple or not self.bars or any(
            type(b) is not BarPoint for b in self.bars):
            raise ValueError("tuple of actual bars required")
        if len({b.bar_id for b in self.bars}) != len(self.bars):
            raise ValueError("duplicate bar id")
        for i,b in enumerate(self.bars):
            for other in self.bars[i+1:]:
                d=hypot(b.x2.as_mm-other.x2.as_mm,b.x3.as_mm-other.x3.as_mm)
                if d+1e-9 < .5*(b.diameter.as_mm+other.diameter.as_mm):
                    raise ValueError("longitudinal bars overlap")

    @property
    def total_area(self):
        return Area.mm2(sum(b.area.as_mm2 for b in self.bars))

    def validate_cover(self, shape: RectangularSection)->None:
        if type(shape) is not RectangularSection:
            raise TypeError("RectangularSection required")
        for b in self.bars:
            setback=self.clear_cover.as_mm+self.tie_diameter.as_mm+b.diameter.as_mm/2
            if abs(b.x2.as_mm)+setback > shape.b.as_mm/2+1e-9 or (
                abs(b.x3.as_mm)+setback > shape.h.as_mm/2+1e-9):
                raise ValueError("bar centre violates geometric cover")


@dataclass(frozen=True, slots=True)
class RCSection:
    ref: RevisionRef
    profile: RectangularSection
    material: DesignMaterial
    longitudinal: LongitudinalLayout
    def __post_init__(self):
        if type(self.ref) is not RevisionRef or type(self.profile) is not RectangularSection:
            raise TypeError("section requires revision and rectangular profile")
        if type(self.material) is not DesignMaterial or type(self.longitudinal) is not LongitudinalLayout:
            raise TypeError("section requires explicit material and layout")
        self.longitudinal.validate_cover(self.profile)
