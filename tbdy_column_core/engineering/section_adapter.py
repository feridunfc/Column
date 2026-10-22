"""Narrow scalar interface to the existing TS500 strain-compatible kernel.

No model/ETABS activity. Does not generate reinforcement or apply code-filter
selection. Only physical signed axial and local moment coordinates are used.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from math import pi
from ..domain.section_models import RCSection
from ..domain.quantities import Force, Moment, Length
from ..physics.rebar_layout import ColumnBarPoint
from ..physics.section_capacity import (
    ColumnSectionMaterial, evaluate_rectangular_column_capacity_state,
    build_interaction_envelope_at_axial_force, radial_moment_capacity,
)


@dataclass(frozen=True, slots=True)
class SectionKernelAdapter:
    section: RCSection
    axis_2_sign: int = 1
    axis_3_sign: int = 1

    def __post_init__(self):
        if type(self.section) is not RCSection:
            raise TypeError("SectionKernelAdapter requires RCSection")
        if type(self.axis_2_sign) is not int or self.axis_2_sign not in (-1,1) or type(self.axis_3_sign) is not int or self.axis_3_sign not in (-1,1):
            raise ValueError("axis sign must be +1/-1")
        # Holding local 1 fixed, changing only one transverse axis makes a
        # left-handed frame. That needs a complete LocalFrame transform instead.
        if self.axis_2_sign != self.axis_3_sign:
            raise ValueError("axis sign transform would reverse handedness")

    def _material(self):
        d=self.section.design_material
        return ColumnSectionMaterial(
            fck_mpa=d.concrete.fck.as_mpa, fcd_mpa=d.fcd.as_mpa,
            fyd_mpa=d.fyd.as_mpa, k1=d.k1,
            es_mpa=d.longitudinal_steel.es.as_mpa,
            epsilon_cu=d.epsilon_cu,
        )

    def _bars(self):
        result=[]
        for i, bar in enumerate(self.section.longitudinal.bars):
            result.append(ColumnBarPoint(
                index=i, x2_mm=self.axis_2_sign*bar.x2.as_mm,
                x3_mm=self.axis_3_sign*bar.x3.as_mm,
                diameter_mm=bar.diameter.as_mm, area_mm2=bar.area.as_mm2,
            ))
        return tuple(result)

    def _angle_kernel(self, angle_deg: float) -> float:
        # Rotating both local transverse axes 180 degrees also rotates the
        # neutral-axis normal. A single reflection was rejected above.
        return (angle_deg + (180.0 if self.axis_2_sign == -1 else 0.0)) % 360.0

    def _state_to_domain(self, state):
        if self.axis_2_sign == 1:
            return state
        return replace(
            state,
            neutral_axis_angle_deg=(state.neutral_axis_angle_deg + 180.0) % 360.0,
            m2_nmm=-state.m2_nmm, m3_nmm=-state.m3_nmm,
            concrete_centroid_x2_mm=-state.concrete_centroid_x2_mm,
            concrete_centroid_x3_mm=-state.concrete_centroid_x3_mm,
        )

    def fixed_state(self, angle_deg: float, c: Length):
        state = evaluate_rectangular_column_capacity_state(
            width_mm=self.section.profile.b.as_mm,
            depth_mm=self.section.profile.h.as_mm,
            bars=self._bars(), material=self._material(),
            neutral_axis_angle_deg=self._angle_kernel(angle_deg),
            neutral_axis_depth_c_mm=c.as_mm,
        )
        return self._state_to_domain(state)

    def envelope(self, n: Force, angle_count: int, axial_tolerance: Force):
        envelope = build_interaction_envelope_at_axial_force(
            width_mm=self.section.profile.b.as_mm,
            depth_mm=self.section.profile.h.as_mm,
            bars=self._bars(), material=self._material(),
            target_n_compression_n=n.as_n, angle_count=angle_count,
            axial_tolerance_n=axial_tolerance.as_n,
        )
        return replace(envelope, states=tuple(self._state_to_domain(x)
                                               for x in envelope.states))

    def radial_capacity(self, envelope, m2: Moment, m3: Moment):
        # Existing kernel expects local M2/M3 relative to section centroid.
        return radial_moment_capacity(envelope, demand_m2_nmm=m2.as_nmm,
                                      demand_m3_nmm=m3.as_nmm)

    @staticmethod
    def shift_moment_reference(
        n: Force, m2: Moment, m3: Moment, *,
        offset_old_to_new_2: Length, offset_old_to_new_3: Length,
    ) -> tuple[Moment, Moment]:
        # M_new = M_old - r(old_to_new) x F; F=(N,0,0) in local axes.
        # (r x F)_2 = +r3*N, (r x F)_3 = -r2*N.
        return (Moment.nmm(m2.as_nmm - n.as_n*offset_old_to_new_3.as_mm),
                Moment.nmm(m3.as_nmm + n.as_n*offset_old_to_new_2.as_mm))
