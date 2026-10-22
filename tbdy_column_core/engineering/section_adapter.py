"""Narrow bridge to the pinned strain-compatibility kernel, no rebar search.

Physics files are byte-preserved; neither this adapter nor the section domain
imports code-dependent rebar-layout candidate-generation functions.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import hypot, isfinite
from ..domain.section_models import RCSection
from ..domain.section_requests import FrameModelContract
from ..domain.quantities import Force, Angle
from ..physics.rebar_layout import ColumnBarPoint
from ..physics.section_capacity import (
    ColumnSectionMaterial, ColumnSectionCapacityError,
    evaluate_rectangular_column_capacity_state,
    solve_capacity_state_for_axial_force,
    ColumnInteractionEnvelope,
    radial_moment_capacity,
)


class UnsupportedSectionMaterial(ValueError):
    pass


@dataclass(frozen=True,slots=True)
class SectionKernelAdapter:
    section: RCSection
    frame: FrameModelContract

    def __post_init__(self):
        if type(self.section) is not RCSection or type(self.frame) is not FrameModelContract:
            raise TypeError("typed section and frame contract required")
        if self.frame.reference != "SECTION_GEOMETRIC_CENTROID":
            raise ValueError("pilot supports geometric-centroid section reference only")

    def prepare_material(self) -> ColumnSectionMaterial:
        d=self.section.material
        refs={bar.steel_ref for bar in self.section.longitudinal.bars}
        laws=d.resolve_steel_laws(refs)
        if laws is None:
            raise UnsupportedSectionMaterial("UNKNOWN_BAR_STEEL_REFERENCE")
        model={(x.fyd.as_mpa,x.es.as_mpa,x.law_revision) for x in laws}
        if len(model)!=1:
            raise UnsupportedSectionMaterial("MIXED_BAR_STEEL_CONSTITUTIVE_LAWS")
        l=laws[0]
        try:
            return ColumnSectionMaterial(
                fck_mpa=d.concrete.fck.as_mpa,
                fcd_mpa=d.fcd.as_mpa,
                fyd_mpa=l.fyd.as_mpa,
                k1=d.k1, es_mpa=l.es.as_mpa, epsilon_cu=d.epsilon_cu,
            )
        except ColumnSectionCapacityError as ex:
            raise UnsupportedSectionMaterial(str(ex)) from ex

    def bars(self) -> tuple[ColumnBarPoint,...]:
        # Canonical order: reordering physical bars cannot change FP summation.
        return tuple(
            ColumnBarPoint(i,b.x2.as_mm,b.x3.as_mm,b.diameter.as_mm,b.area.as_mm2)
            for i,b in enumerate(sorted(self.section.longitudinal.bars,
                                         key=lambda b:b.bar_id))
        )

    def evaluate(self, angle: Angle, c_mm: float, material, bars):
        return evaluate_rectangular_column_capacity_state(
            width_mm=self.section.profile.b.as_mm, depth_mm=self.section.profile.h.as_mm,
            bars=bars,material=material,
            neutral_axis_angle_deg=angle.as_deg,
            neutral_axis_depth_c_mm=c_mm,
        )

    def sample_axial_brackets(self, angle: Angle, target: Force,
                              material, bars, *, force_atol_n: float) -> tuple[int,bool]:
        """Conservative sampled sign-bracket census, NOT a global root proof.

        The production kernel takes the first crossing. Multiple detected
        crossings are rejected. A tangential or unresolved crossing remains
        uncertain; 'sampled=1' is labelled SAMPLED_SINGLE_BRACKET.
        """
        d=hypot(self.section.profile.b.as_mm,self.section.profile.h.as_mm)
        c_min=max(d*1e-6,1e-6)
        c_max=d*1e4
        ratio=(c_max/c_min)**(1/179)
        c=c_min
        prev=None
        changes=0
        near_zero=False
        for _ in range(180):
            st=self.evaluate(angle,c,material,bars)
            residue=st.n_compression_n-target.as_n
            if not isfinite(residue):
                raise ColumnSectionCapacityError("nonfinite axial sample")
            if abs(residue)<=force_atol_n:
                near_zero=True
            if prev is not None and prev*residue<0:
                changes+=1
            prev=residue
            c*=ratio
        return changes,near_zero

    def solve_one(self, angle: Angle, target: Force, policy,material,bars):
        return solve_capacity_state_for_axial_force(
            width_mm=self.section.profile.b.as_mm,
            depth_mm=self.section.profile.h.as_mm,
            bars=bars,material=material,
            neutral_axis_angle_deg=angle.as_deg,
            target_n_compression_n=target.as_n,
            axial_tolerance_n=policy.force_balance_tol.as_n,
            max_iterations=policy.max_iterations,
        )

    def radial(self, states, target: Force, m2, m3, step_deg: float):
        envelope=ColumnInteractionEnvelope(
            target_n_compression_n=target.as_n,
            states=tuple(states),
            status="PROVEN",
            angle_step_deg=step_deg,
        )
        return radial_moment_capacity(envelope,demand_m2_nmm=m2.as_nmm,
                                      demand_m3_nmm=m3.as_nmm)
