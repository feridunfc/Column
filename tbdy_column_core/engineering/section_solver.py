"""B1: three explicit supplied-rebar section calculations.

No member demand selection, code PASS, shear, second order or PMM utilization
decision. All generated states are tied to the same physical bar layout.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from ..domain.section_requests import (
    SectionCapacityProblem, SectionCapacityResult, SectionStatus, SectionState,
    AtStrainState, EnvelopeAtAxialForce, RadialCapacityAtAxialForce,
    AngularCoverage,
)
from ..domain.quantities import Force, Moment, Length, Angle
from ..domain.coordinates import frame_basis_max_residual
from ..domain.tolerances import within
from ..physics.section_capacity import ColumnSectionCapacityError
from .section_adapter import SectionKernelAdapter,UnsupportedSectionMaterial
from .input_identity import section_input_fingerprint

KERNEL_REF="Column/legacy/column-pre-clean-20261022:physics/section_capacity.py@b2ac0114a5913e3088df6913de7537d7e0792b44"


class SectionSolver:
    @staticmethod
    def _state(s, target: Force | None, audit=None):
        return SectionState(
            Angle.deg(s.neutral_axis_angle_deg),
            Length.mm(s.neutral_axis_depth_c_mm),
            Force.n(s.n_compression_n),
            Moment.nmm(s.m2_nmm),
            Moment.nmm(s.m3_nmm),
            None if target is None else Force.n(s.n_compression_n-target.as_n),
            None if audit is None else audit.sign_brackets,
            None if audit is None else audit.sample_count,
            None if audit is None else Force.n(audit.smallest_abs_residual_n),
        )

    def calculate(self, problem: SectionCapacityProblem) -> SectionCapacityResult:
        if type(problem) is not SectionCapacityProblem:
            raise TypeError("SectionCapacityProblem required")
        section=problem.section
        request=problem.request
        policy=problem.numerical_policy
        identity=section_input_fingerprint(problem,kernel_ref=KERNEL_REF)
        issues=[]
        states=[]
        cap=boundary2=boundary3=None
        step=None
        resolved_indices=None
        quality="NOT_RUN"
        status=SectionStatus.NUMERIC_UNRESOLVED
        # This supplied frame labels local 1/2/3 values, not a request to
        # reinterpret global actions. In this pilot only already-local
        # section inputs are supported. Check declared frame precision
        # against the *requested* policy instead of silently ignoring it.
        from ..domain.coordinates import AxialSignConvention
        if problem.frame_model_contract.axial_sign!=AxialSignConvention.F1_COMPRESSION_POSITIVE:
            raise ValueError("UNSUPPORTED_AXIAL_SIGN_CONVENTION")
        basis_error=frame_basis_max_residual(problem.frame_model_contract.frame)
        if basis_error>policy.axis_tol:
            raise ValueError("FRAME_EXCEEDS_REQUESTED_AXIS_TOLERANCE")
        adapter=SectionKernelAdapter(section,problem.frame_model_contract)
        try:
            material=adapter.prepare_material()
        except UnsupportedSectionMaterial as exc:
            issues.append(str(exc))
            status=SectionStatus.UNSUPPORTED_MATERIAL
            material=None
        bars=adapter.bars()
        if material is not None:
            if type(request) is AtStrainState:
                quality="DIRECT_STRAIN_COMPATIBILITY"
                try:
                    s=adapter.evaluate(request.neutral_axis_normal,
                                       request.neutral_axis_depth.as_mm,material,bars)
                    states.append(self._state(s,None,None))
                    status=SectionStatus.NUMERIC_STATE
                except ColumnSectionCapacityError as exc:
                    issues.append("DIRECT_STATE_UNRESOLVED:"+str(exc))
            else:
                target=request.target_compression
                # Undefined input must not run an expensive fixed-N envelope.
                # It is an input-direction issue independent of root quality.
                zero_direction=(
                    type(request) is RadialCapacityAtAxialForce and
                    request.direction_m2.as_nmm==0 and
                    request.direction_m3.as_nmm==0
                )
                if zero_direction:
                    issues.append("UNDEFINED_MOMENT_DIRECTION")
                    return self._result(
                        section,request,policy,SectionStatus.UNDEFINED_MOMENT_DIRECTION,
                        states,issues,cap,boundary2,boundary3,None,
                        problem.input_refs,"NOT_APPLICABLE_ZERO_DIRECTION",None,
                        problem.frame_model_contract,basis_error,identity
                    )
                angle_count=policy.angle_count
                step=Angle.deg(360/angle_count)
                quality="DUAL_GRID_SINGLE_SAMPLED_BRACKET_NOT_GLOBAL_ROOT_PROOF"
                kernel_states=[]
                resolved_indices=[]
                for j in range(angle_count):
                    angle=Angle.deg(j*360/angle_count)
                    try:
                        audit=adapter.sample_axial_brackets(
                            angle,target,material,bars,
                            force_atol_n=policy.force_balance_tol.as_n
                        )
                        if not audit.accepted_single_bracket:
                            issues.append(f"ANGLE_{j}:"+audit.issue_code+
                                          f":COUNT_{audit.sign_brackets}"+
                                          f":MIN_RESIDUAL_N_{audit.smallest_abs_residual_n:.8g}")
                            continue
                        solution=adapter.solve_one(angle,target,policy,material,bars)
                        if solution is None:
                            issues.append(f"ANGLE_{j}:NO_QUALIFIED_NUMERIC_ROOT")
                            continue
                        resid=abs(solution.n_compression_n-target.as_n)
                        if not within(solution.n_compression_n,target.as_n,
                            policy.force_balance_tol.as_n,policy.relative_tol):
                            issues.append(f"ANGLE_{j}:AXIAL_RESIDUAL_OVER_POLICY")
                            continue
                        if not all(isfinite(x) for x in
                            (solution.n_compression_n,solution.m2_nmm,solution.m3_nmm)):
                            issues.append(f"ANGLE_{j}:NONFINITE_SOLUTION")
                            continue
                        states.append(self._state(solution,target,audit))
                        kernel_states.append(solution)
                        resolved_indices.append(j)
                    except (ColumnSectionCapacityError,ArithmeticError,ValueError) as exc:
                        issues.append(f"ANGLE_{j}:NUMERIC_UNRESOLVED:{type(exc).__name__}")
                complete=len(kernel_states)==angle_count
                if not complete:
                    status=SectionStatus.PARTIAL_ENVELOPE if kernel_states else SectionStatus.NUMERIC_UNRESOLVED
                elif type(request) is EnvelopeAtAxialForce:
                    status=SectionStatus.COMPLETE_ENVELOPE
                else:
                    radial=adapter.radial(kernel_states,target,
                                          request.direction_m2,request.direction_m3,
                                          step.as_deg)
                    if radial.status!="PROVEN" or not all(isfinite(v) for v in (
                        radial.capacity_nmm,radial.boundary_m2_nmm,radial.boundary_m3_nmm)):
                        issues.append("RADIAL_UNRESOLVED:"+radial.status)
                        status=SectionStatus.NUMERIC_UNRESOLVED
                    else:
                        cap=Moment.nmm(radial.capacity_nmm)
                        boundary2=Moment.nmm(radial.boundary_m2_nmm)
                        boundary3=Moment.nmm(radial.boundary_m3_nmm)
                        status=SectionStatus.COMPLETE_RADIAL

        return self._result(
            section,request,policy,status,states,issues,cap,boundary2,boundary3,
            step,problem.input_refs,quality,resolved_indices,
            problem.frame_model_contract,basis_error,identity
        )

    @staticmethod
    def _result(section,request,policy,status,states,issues,
                cap,boundary2,boundary3,step,input_refs,quality,resolved_indices,
                frame_contract,basis_error,input_fingerprint):
        coverage=None
        if resolved_indices is not None:
            count=policy.angle_count
            observed=frozenset(resolved_indices)
            coverage=AngularCoverage(
                count,tuple(sorted(observed)),
                tuple(i for i in range(count) if i not in observed)
            )
        return SectionCapacityResult(
            section_ref=section.ref,
            request_kind=type(request).__name__,
            status=status,states=tuple(states),
            radial_capacity=cap,
            radial_boundary_m2=boundary2,
            radial_boundary_m3=boundary3,
            issues=tuple(issues),
            requested_policy=policy,applied_policy=policy,
            angle_step=step,
            input_refs=input_refs,
            material_revision=section.material.revision,
            law_ref=f"{section.material.rule.code_id}/{section.material.rule.edition}/{section.material.rule.rule_id}",
            kernel_ref=KERNEL_REF,
            source_geometry=(
                ("b",section.profile.b.as_mm,"mm"),
                ("h",section.profile.h.as_mm,"mm"),
                ("bar_count",float(len(section.longitudinal.bars)),"count"),
                ("As",section.longitudinal.total_area.as_mm2,"mm2"),
            ),
            root_quality=quality,
            input_fingerprint=input_fingerprint,
            frame_model_contract=frame_contract,
            frame_basis_max_residual=basis_error,
            angular_coverage=coverage,
        )
