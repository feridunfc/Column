"""Provided-cage section capacity pilot: no search, shear or column-code PASS."""
from __future__ import annotations
from dataclasses import dataclass
from json import dumps
from math import isfinite
from ..domain.quantities import Force, Moment, Length, finite
from ..domain.tolerances import NumericalPolicy
from ..domain.outcomes import CalculationStep
from ..domain.section_models import RCSection
from .section_adapter import SectionKernelAdapter


@dataclass(frozen=True, slots=True)
class SectionCapacityProblem:
    section: RCSection
    neutral_axis_angle_deg: float
    neutral_axis_depth: Length
    policy: NumericalPolicy
    # Optional fixed-axial-force PMM section envelope/ray, NOT a column check.
    target_axial: Force | None = None
    radial_demand_m2: Moment | None = None
    radial_demand_m3: Moment | None = None

    def __post_init__(self):
        if type(self.section) is not RCSection or type(self.policy) is not NumericalPolicy:
            raise TypeError("SectionCapacityProblem needs RCSection and NumericalPolicy")
        if type(self.neutral_axis_depth) is not Length or self.neutral_axis_depth.as_mm <= 0:
            raise ValueError("positive neutral-axis depth required")
        finite(self.neutral_axis_angle_deg, "neutral-axis angle")
        if self.target_axial is not None and type(self.target_axial) is not Force:
            raise TypeError("target_axial requires Force")
        moments = (self.radial_demand_m2, self.radial_demand_m3)
        if any(x is not None for x in moments):
            if self.target_axial is None or any(type(x) is not Moment for x in moments):
                raise ValueError("PMM radial demand requires axial and both signed moments")
        if self.policy.max_iterations != 100:
            # Retained fixed-axial kernel currently hardcodes 100 iterations;
            # do not silently ignore a caller's numerical-policy instruction.
            raise ValueError("kernel max_iterations is fixed at 100 in this pilot")


@dataclass(frozen=True, slots=True)
class SectionCapacityResult:
    section_id: str
    status: str
    state_n: Force
    state_m2: Moment
    state_m3: Moment
    neutral_axis_angle_deg: float
    neutral_axis_depth: Length
    bar_count: int
    total_bar_area_mm2: float
    axial_residual: Force | None
    converged: bool
    angle_step_deg: float | None
    radial_capacity: Moment | None
    radial_status: str | None
    calculation_steps: tuple[CalculationStep, ...]
    full_column_design_pass: bool = False


class SectionSolver:
    def calculate(self, problem: SectionCapacityProblem) -> SectionCapacityResult:
        adapter = SectionKernelAdapter(problem.section)
        result = adapter.fixed_state(problem.neutral_axis_angle_deg,
                                     problem.neutral_axis_depth)
        cap_radial = None
        radial_status = None
        angle_step = None
        residual = None
        converged = True
        status = "NUMERIC_SECTION_STATE_NOT_COLUMN_DESIGN"
        if problem.target_axial is not None:
            envelope = adapter.envelope(
                problem.target_axial, problem.policy.angle_count,
                problem.policy.force_balance_tol,
            )
            angle_step = envelope.angle_step_deg
            if envelope.states:
                residual = Force.n(max(
                    abs(x.n_compression_n - problem.target_axial.as_n)
                    for x in envelope.states
                ))
            converged = (envelope.status == "PROVEN" and
                         residual is not None and
                         residual.as_n <= problem.policy.force_balance_tol.as_n)
            if not converged:
                status = "SECTION_ENVELOPE_NUMERIC_UNRESOLVED"
            if problem.radial_demand_m2 is not None and converged:
                radial = adapter.radial_capacity(
                    envelope, problem.radial_demand_m2, problem.radial_demand_m3,
                )
                radial_status = radial.status
                if radial.status == "PROVEN" and isfinite(radial.capacity_nmm):
                    cap_radial = Moment.nmm(radial.capacity_nmm)
                else:
                    converged = False
                    status = "SECTION_RADIAL_NUMERIC_UNRESOLVED"

        trace = (CalculationStep(
            rule_ref=problem.section.design_material.rule_ref,
            input_values=(
                ("b",problem.section.profile.b.as_mm,"mm"),
                ("h",problem.section.profile.h.as_mm,"mm"),
                ("angle",problem.neutral_axis_angle_deg,"deg"),
                ("neutral_axis_depth",problem.neutral_axis_depth.as_mm,"mm"),
                ("bar_count",float(len(problem.section.longitudinal.bars)),"count"),
            ),
            output_values=(
                ("N",result.n_compression_n,"N"),
                ("M2",result.m2_nmm,"Nmm"),
                ("M3",result.m3_nmm,"Nmm"),
            ),
            solver_quality=status,
        ),)
        return SectionCapacityResult(
            section_id=problem.section.section_id,
            status=status,
            state_n=Force.n(result.n_compression_n),
            state_m2=Moment.nmm(result.m2_nmm),
            state_m3=Moment.nmm(result.m3_nmm),
            neutral_axis_angle_deg=result.neutral_axis_angle_deg,
            neutral_axis_depth=Length.mm(result.neutral_axis_depth_c_mm),
            bar_count=len(problem.section.longitudinal.bars),
            total_bar_area_mm2=problem.section.longitudinal.total_area.as_mm2,
            axial_residual=residual,
            converged=converged,
            angle_step_deg=angle_step,
            radial_capacity=cap_radial,
            radial_status=radial_status,
            calculation_steps=trace,
        )


def calculate_section(problem: SectionCapacityProblem) -> SectionCapacityResult:
    return SectionSolver().calculate(problem)


def section_capacity_report_json(result: SectionCapacityResult) -> str:
    """Deterministic passive result projection; does not recompute physics."""
    if type(result) is not SectionCapacityResult:
        raise TypeError("expected SectionCapacityResult")
    d = {
        "schema":"column.section_capacity.v1",
        "section_id":result.section_id, "status":result.status,
        "state_N_n":result.state_n.as_n,
        "state_M2_nmm":result.state_m2.as_nmm,
        "state_M3_nmm":result.state_m3.as_nmm,
        "neutral_axis_angle_deg":result.neutral_axis_angle_deg,
        "neutral_axis_depth_mm":result.neutral_axis_depth.as_mm,
        "bar_count":result.bar_count,
        "longitudinal_as_mm2":result.total_bar_area_mm2,
        "axial_residual_n":None if result.axial_residual is None else result.axial_residual.as_n,
        "converged":result.converged, "angle_step_deg":result.angle_step_deg,
        "radial_capacity_nmm":None if result.radial_capacity is None else result.radial_capacity.as_nmm,
        "radial_status":result.radial_status,
        "full_column_design_pass":False,
        "trace":[{
            "rule_ref":s.rule_ref,
            "inputs":list(s.input_values),
            "outputs":list(s.output_values),
            "solver_quality":s.solver_quality,
        } for s in result.calculation_steps],
    }
    return dumps(d,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(",",":"))
