"""Canonical *content* fingerprint for an explicit supplied-cage section request.

The SHA-256 digest binds declared engineering inputs and the pinned physics
identifier, but does not authenticate an external source, demonstrate that a
calculation was performed, or confer TS500/TBDY compliance. No IO or clock.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite
from ..domain.section_requests import (
    SectionCapacityProblem,AtStrainState,EnvelopeAtAxialForce,
    RadialCapacityAtAxialForce,CalculationInputFingerprint,
)


def _f(value: float) -> str:
    """Canonical finite IEEE-754 value in canonical units, normalize -0."""
    number=float(value)
    if not isfinite(number):
        raise ValueError("nonfinite numerical calculation identity input")
    return (0.0 if number == 0 else number).hex()


def _revision(ref):
    return [ref.namespace,ref.identifier,ref.revision]


def _source(ref):
    return {
        "evidence_id":ref.evidence_id,
        "producer":ref.source.producer,
        "source_identifier":ref.source.source_identifier,
        "record_identifier":ref.source.record_identifier,
        "declared_units":ref.source.declared_units,
        "acquisition_ref":ref.source.acquisition_ref,
        "input_revision":_revision(ref.input_revision),
    }


def section_input_fingerprint(problem: SectionCapacityProblem, *,
                              kernel_ref: str) -> CalculationInputFingerprint:
    """Digest every declared calculation-determining input, without computing N/M.

    All physical quantities use canonical N, mm, Nmm, MPa or radians.
    Stable sort canonicalizes the unordered population of actual bars, steel
    laws and evidence refs without erasing any elements.
    """
    if type(problem) is not SectionCapacityProblem:
        raise TypeError("SectionCapacityProblem required")
    if type(kernel_ref) is not str or not kernel_ref.strip():
        raise ValueError("pinned kernel_ref required")
    section=problem.section
    material=section.material
    cage=section.longitudinal
    policy=problem.numerical_policy
    contract=problem.frame_model_contract
    frame=contract.frame
    request=problem.request
    if type(request) is AtStrainState:
        req={"kind":"AtStrainState",
             "angle_rad":_f(request.neutral_axis_normal.as_rad),
             "neutral_axis_depth_mm":_f(request.neutral_axis_depth.as_mm)}
    elif type(request) is EnvelopeAtAxialForce:
        req={"kind":"EnvelopeAtAxialForce",
             "target_compression_n":_f(request.target_compression.as_n)}
    elif type(request) is RadialCapacityAtAxialForce:
        req={"kind":"RadialCapacityAtAxialForce",
             "target_compression_n":_f(request.target_compression.as_n),
             "direction_m2_nmm":_f(request.direction_m2.as_nmm),
             "direction_m3_nmm":_f(request.direction_m3.as_nmm)}
    else:
        raise TypeError("unsupported calculation request type")

    body={
        "schema":CalculationInputFingerprint.SCHEMA,
        "kernel":kernel_ref,
        "section":{
            "ref":_revision(section.ref),
            "b_mm":_f(section.profile.b.as_mm),
            "h_mm":_f(section.profile.h.as_mm),
            "material":{
                "revision":_revision(material.revision),
                "concrete":{
                    "revision":_revision(material.concrete.ref),
                    "fck_mpa":_f(material.concrete.fck.as_mpa)},
                "fcd_mpa":_f(material.fcd.as_mpa),
                "k1":_f(material.k1),
                "epsilon_cu":_f(material.epsilon_cu),
                "rule":[material.rule.code_id,material.rule.edition,
                        material.rule.rule_id],
                "steel_laws":sorted([
                    {"steel_ref":law.steel_ref,
                     "fyd_mpa":_f(law.fyd.as_mpa),
                     "es_mpa":_f(law.es.as_mpa),
                     "revision":_revision(law.law_revision)}
                    for law in material.steel_laws],
                    key=lambda row:json.dumps(row,sort_keys=True))
            },
            "longitudinal":{
                "revision":_revision(cage.revision),
                "clear_cover_mm":_f(cage.clear_cover.as_mm),
                "tie_diameter_mm":_f(cage.tie_diameter.as_mm),
                "bars":sorted([
                    {"id":bar.bar_id,
                     "x2_mm":_f(bar.x2.as_mm),
                     "x3_mm":_f(bar.x3.as_mm),
                     "diameter_mm":_f(bar.diameter.as_mm),
                     "steel_ref":bar.steel_ref} for bar in cage.bars],
                    key=lambda row:row["id"])
            }
        },
        "request":req,
        "numerical_policy":{
            "geometric_tol_mm":_f(policy.geometric_tol.as_mm),
            "axis_tol":_f(policy.axis_tol),
            "force_balance_tol_n":_f(policy.force_balance_tol.as_n),
            "moment_tol_nmm":_f(policy.moment_tol.as_nmm),
            "relative_tol":_f(policy.relative_tol),
            "angle_count":policy.angle_count,
            "max_iterations":policy.max_iterations
        },
        "frame":{
            "reference":contract.reference,
            "axial_sign":contract.axial_sign.value,
            "origin_mm":[_f(v) for v in frame.origin.mm],
            "e1":[_f(v) for v in frame.e1],
            "e2":[_f(v) for v in frame.e2],
            "e3":[_f(v) for v in frame.e3],
            "frame_axis_tolerance":_f(frame.axis_tolerance)
        },
        "evidence":sorted(
            [_source(ref) for ref in problem.input_refs],
            key=lambda row:json.dumps(row,sort_keys=True,ensure_ascii=False)
        ),
    }
    encoded=json.dumps(body,sort_keys=True,separators=(",",":"),
                       ensure_ascii=False,allow_nan=False).encode("utf-8")
    return CalculationInputFingerprint(
        CalculationInputFingerprint.SCHEMA,sha256(encoded).hexdigest())
