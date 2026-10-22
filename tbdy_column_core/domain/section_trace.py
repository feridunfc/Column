"""Source-local RC section input snapshot, for deterministic audit only.

SHA-256 identifies identical **declared** section data; it is not a trusted
signature, a guarantee of authentic evidence, a certified calculation, or a
full problem/result fingerprint. No structural physics is performed here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json

from .identity import RevisionRef, RuleRef
from .section_models import RCSection


TRACE_SCHEMA = "column.section.declared-input.v1.3-b5"


def _revision(ref: RevisionRef) -> dict[str, str]:
    return {
        "namespace": ref.namespace,
        "identifier": ref.identifier,
        "revision": ref.revision,
    }


def section_input_payload(section: RCSection) -> dict:
    """Normalize actual declared local section geometry, material and cage.

    Bar identifiers and steel references are included, as are every supplied
    steel law, whether or not the law is used by a particular bar. The
    source-local section is independent of global frame/policy/request.
    """
    if type(section) is not RCSection:
        raise TypeError("typed RCSection required")
    profile=section.profile
    material=section.material
    layout=section.longitudinal
    return {
        "schema":TRACE_SCHEMA,
        "section_ref":_revision(section.ref),
        "geometry":{
            "b_mm":profile.b.as_mm,
            "h_mm":profile.h.as_mm,
        },
        "material":{
            "revision":_revision(material.revision),
            "rule":{
                "code_id":material.rule.code_id,
                "edition":material.rule.edition,
                "rule_id":material.rule.rule_id,
            },
            "concrete":{
                "revision":_revision(material.concrete.ref),
                "fck_mpa":material.concrete.fck.as_mpa,
                "fcd_mpa":material.fcd.as_mpa,
                "k1":material.k1,
                "epsilon_cu":material.epsilon_cu,
            },
            "steel_laws":[{
                "steel_ref":law.steel_ref,
                "revision":_revision(law.law_revision),
                "fyd_mpa":law.fyd.as_mpa,
                "es_mpa":law.es.as_mpa,
            } for law in sorted(material.steel_laws,key=lambda law:law.steel_ref)],
        },
        "longitudinal":{
            "revision":_revision(layout.revision),
            "clear_cover_mm":layout.clear_cover.as_mm,
            "tie_diameter_mm":layout.tie_diameter.as_mm,
            "bars":[{
                "bar_id":bar.bar_id,
                "x2_mm":bar.x2.as_mm,
                "x3_mm":bar.x3.as_mm,
                "diameter_mm":bar.diameter.as_mm,
                "steel_ref":bar.steel_ref,
            } for bar in sorted(layout.bars,key=lambda bar:bar.bar_id)],
        },
    }


def encode_section_input(section: RCSection) -> str:
    return json.dumps(
        section_input_payload(section),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",",":"),
        allow_nan=False,
    )


@dataclass(frozen=True,slots=True)
class SectionInputTrace:
    """Immutable exact canonical serialization captured with a numeric result."""
    # Canonical JSON owns value-equality, independent of original bar ordering.
    # The validated original typed input remains available for diagnostics.
    section: RCSection = field(compare=False, repr=False)
    canonical_json: str
    sha256: str

    def __post_init__(self)->None:
        if type(self.section) is not RCSection:
            raise TypeError("SectionInputTrace requires RCSection")
        if type(self.canonical_json) is not str or type(self.sha256) is not str:
            raise TypeError("canonical JSON and digest must be strings")
        if self.canonical_json != encode_section_input(self.section):
            raise ValueError("section input trace serialization does not match section")
        expected=hashlib.sha256(self.canonical_json.encode("utf-8")).hexdigest()
        if self.sha256 != expected:
            raise ValueError("section input trace digest does not match source")

    @classmethod
    def capture(cls,section: RCSection)->"SectionInputTrace":
        value=encode_section_input(section)
        return cls(section,value,hashlib.sha256(value.encode("utf-8")).hexdigest())
