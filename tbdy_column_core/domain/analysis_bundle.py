"""C-12..C-15: source dimensions and scoped evidence resolution.

The caller MUST supply a provenance resolver/catalog. This is a typed
contract-level qualification of supplied, resolved evidence, NOT proof of
native ETABS analysis validity. No global is_qualified shortcut.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from .identity import EvidenceRef, RuleRef, required


class ResponseSemantics(StrEnum):
    SIGNED_STATIC="SIGNED_STATIC"
    MODAL="MODAL"
    SPECTRAL="SPECTRAL"
    ENVELOPE="ENVELOPE"


class QualificationStatus(StrEnum):
    SCOPE_MATCH="SCOPE_MATCH"
    UNRESOLVED="UNRESOLVED"


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    producer: str
    acquisition_mode: str
    intended_use: str
    response_semantics: ResponseSemantics
    def __post_init__(self):
        for name in ("producer","acquisition_mode","intended_use"):
            required(getattr(self,name),name)
        if type(self.response_semantics) is not ResponseSemantics:
            raise TypeError("response semantics required")


@dataclass(frozen=True, slots=True)
class AnalysisRun:
    run_id: str
    model_revision_id: str
    result_generation_id: str
    basis_revision_id: str
    source: SourceMetadata
    population_keys: tuple[str,...]
    def __post_init__(self):
        for name in ("run_id","model_revision_id","result_generation_id","basis_revision_id"):
            required(getattr(self,name),name)
        if type(self.source) is not SourceMetadata:
            raise TypeError("typed SourceMetadata required")
        if not self.population_keys or len(set(self.population_keys))!=len(self.population_keys):
            raise ValueError("explicit, unique result population required")


@dataclass(frozen=True, slots=True)
class RequiredRole:
    role: str
    method_id: str
    consumer_id: str
    input_revision_id: str
    supported_semantics: tuple[ResponseSemantics,...]
    expected_population: tuple[str,...]
    def __post_init__(self):
        for name in ("role","method_id","consumer_id","input_revision_id"):
            required(getattr(self,name),name)
        if not self.supported_semantics or any(type(s) is not ResponseSemantics
            for s in self.supported_semantics):
            raise ValueError("typed supported response semantics required")
        if not self.expected_population or len(set(self.expected_population))!=len(self.expected_population):
            raise ValueError("explicit expected population required")


@dataclass(frozen=True, slots=True)
class VerifiedScope:
    evidence: EvidenceRef
    role: str
    method_id: str
    consumer_id: str
    input_revision_id: str
    run_id: str
    model_revision_id: str
    result_generation_id: str
    population_keys: tuple[str,...]
    verification_receipt_ref: str
    applicability_rule: RuleRef | None = None

    def __post_init__(self):
        if type(self.evidence) is not EvidenceRef:
            raise TypeError("typed EvidenceRef required")
        for name in ("role","method_id","consumer_id","input_revision_id",
                     "run_id","model_revision_id","result_generation_id",
                     "verification_receipt_ref"):
            required(getattr(self,name),name)
        if self.evidence.input_revision.revision != self.input_revision_id:
            raise ValueError("scope evidence/input revision mismatch")
        if self.applicability_rule is not None and type(self.applicability_rule) is not RuleRef:
            raise TypeError("applicability_rule must be RuleRef")


@dataclass(frozen=True, slots=True)
class VerifiedCompatibility:
    evidence: EvidenceRef
    run_ids: tuple[str,...]
    method_id: str
    consumer_id: str
    input_revision_id: str
    verification_receipt_ref: str
    def __post_init__(self):
        if type(self.evidence) is not EvidenceRef:
            raise TypeError("typed EvidenceRef required")
        if len(set(self.run_ids))<2 or any(not isinstance(x,str) or not x.strip()
                                           for x in self.run_ids):
            raise ValueError("cross-run proof needs distinct run IDs")
        for name in ("method_id","consumer_id","input_revision_id",
                     "verification_receipt_ref"):
            required(getattr(self,name),name)
        if self.evidence.input_revision.revision != self.input_revision_id:
            raise ValueError("compatibility evidence/input revision mismatch")


@dataclass(frozen=True, slots=True)
class EvidenceCatalog:
    """Immutable receipts from an explicitly supplied verification producer.

    The record exists only after an integration verifier provides it; strings
    passed to the qualification request are not inserted as proof.
    """
    scopes: tuple[VerifiedScope,...] = ()
    compatibilities: tuple[VerifiedCompatibility,...] = ()

    def __post_init__(self):
        if type(self.scopes) is not tuple or type(self.compatibilities) is not tuple:
            raise TypeError("immutable tuple evidence catalogs required")
        if any(type(x) is not VerifiedScope for x in self.scopes) or any(
                type(x) is not VerifiedCompatibility for x in self.compatibilities):
            raise TypeError("catalog may contain only typed verified receipts")
        ids=[r.evidence.evidence_id for r in (*self.scopes,*self.compatibilities)]
        if len(ids)!=len(set(ids)):
            raise ValueError("duplicate evidence ID")


@dataclass(frozen=True, slots=True)
class RoleBinding:
    role: str
    run: AnalysisRun
    def __post_init__(self):
        required(self.role,"role")
        if type(self.run) is not AnalysisRun:
            raise TypeError("role needs AnalysisRun")


@dataclass(frozen=True, slots=True)
class QualificationDecision:
    status: QualificationStatus
    issues: tuple[str,...]
    matched_evidence_refs: tuple[str,...]
    @property
    def contract_ready(self):
        return self.status==QualificationStatus.SCOPE_MATCH and not self.issues


@dataclass(frozen=True, slots=True)
class AnalysisBundle:
    bindings: tuple[RoleBinding,...]
    def __post_init__(self):
        if not self.bindings or any(type(x) is not RoleBinding for x in self.bindings):
            raise ValueError("role bindings required")
        roles=[x.role for x in self.bindings]
        if len(roles)!=len(set(roles)):
            raise ValueError("duplicated role")

    def qualify(self, needs: tuple[RequiredRole,...],
                catalog: EvidenceCatalog) -> QualificationDecision:
        if type(catalog) is not EvidenceCatalog or not needs:
            raise TypeError("explicit EvidenceCatalog and needs required")
        by_role={x.role:x.run for x in self.bindings}
        issues:list[str]=[]
        matched:list[str]=[]
        selected:list[AnalysisRun]=[]
        if len({need.role for need in needs}) != len(needs):
            raise ValueError("duplicate required roles")
        for need in needs:
            if type(need) is not RequiredRole:
                raise TypeError("typed required roles only")
            run=by_role.get(need.role)
            if run is None:
                issues.append(f"{need.role}:MISSING_ROLE")
                continue
            selected.append(run)
            if run.source.response_semantics not in need.supported_semantics:
                issues.append(f"{need.role}:UNSUPPORTED_SEMANTICS")
            if not set(need.expected_population).issubset(run.population_keys):
                issues.append(f"{need.role}:INCOMPLETE_POPULATION")
            proofs=[r for r in catalog.scopes if
                    r.role==need.role and r.method_id==need.method_id and
                    r.consumer_id==need.consumer_id and
                    r.input_revision_id==need.input_revision_id and
                    r.run_id==run.run_id and
                    r.model_revision_id==run.model_revision_id and
                    r.result_generation_id==run.result_generation_id and
                    r.evidence.input_revision.revision==need.input_revision_id and
                    r.evidence.source.producer==run.source.producer and
                    set(need.expected_population).issubset(r.population_keys)]
            if len(proofs)!=1:
                issues.append(f"{need.role}:EVIDENCE_UNRESOLVED_OR_AMBIGUOUS")
            else:
                matched.append(proofs[0].evidence.evidence_id)
        run_ids=tuple(sorted({r.run_id for r in selected}))
        if len(run_ids)>1:
            keys={(n.method_id,n.consumer_id,n.input_revision_id) for n in needs}
            if len(keys)!=1:
                issues.append("CROSS_RUN_MULTI_METHOD_UNQUALIFIED")
            else:
                method,consumer,revision=next(iter(keys))
                compatibility=[c for c in catalog.compatibilities
                               if tuple(sorted(c.run_ids))==run_ids and
                               (c.method_id,c.consumer_id,c.input_revision_id)==(
                                   method,consumer,revision) and
                               c.evidence.input_revision.revision==revision]
                if len(compatibility)!=1:
                    issues.append("CROSS_RUN_COMPATIBILITY_UNRESOLVED")
                else:
                    matched.append(compatibility[0].evidence.evidence_id)
        return QualificationDecision(
            QualificationStatus.UNRESOLVED if issues else QualificationStatus.SCOPE_MATCH,
            tuple(issues),tuple(matched)
        )
