"""A run's origin, response meaning and evidential qualification are independent."""
from dataclasses import dataclass
from enum import StrEnum


class SourceOrigin(StrEnum):
    ETABS="ETABS"
    RECORDED="RECORDED"
    MANUAL="MANUAL"
    SYNTHETIC="SYNTHETIC"


class ResponseSemantics(StrEnum):
    SIGNED_STATIC="SIGNED_STATIC"
    MODAL="MODAL"
    SPECTRAL="SPECTRAL"
    ENVELOPE="ENVELOPE"


class QualificationStatus(StrEnum):
    VERIFIED="VERIFIED"
    INCOMPLETE="INCOMPLETE"
    UNRESOLVED="UNRESOLVED"
    REJECTED="REJECTED"


@dataclass(frozen=True, slots=True)
class AnalysisRun:
    run_id: str
    model_revision_id: str
    result_generation_id: str
    source_origin: SourceOrigin
    response_semantics: ResponseSemantics
    qualification_status: QualificationStatus
    basis_ref: str
    def __post_init__(self):
        if not all(isinstance(x,str) and x.strip() for x in (
            self.run_id, self.model_revision_id, self.result_generation_id, self.basis_ref
        )):
            raise ValueError("AnalysisRun identities and basis must be nonblank")
        for key, enum_type in (("source_origin", SourceOrigin),
                                ("response_semantics", ResponseSemantics),
                                ("qualification_status", QualificationStatus)):
            if not isinstance(getattr(self,key), enum_type):
                raise TypeError(f"{key} requires {enum_type.__name__}")


@dataclass(frozen=True, slots=True)
class AnalysisBundle:
    # Tuple pairs avoid mutable dictionaries. Each role has one source run.
    role_runs: tuple[tuple[str, AnalysisRun], ...]
    compatibility_evidence: tuple[str, ...] = ()
    unresolved_role_constraints: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.role_runs:
            raise ValueError("role_runs required")
        roles = [role for role, _ in self.role_runs]
        if any(not isinstance(r, str) or not r.strip() for r in roles) or len(roles) != len(set(roles)):
            raise ValueError("duplicate or blank analysis role")
        if any(type(run) is not AnalysisRun for _,run in self.role_runs):
            raise TypeError("role run requires AnalysisRun")

    @property
    def is_qualified(self) -> bool:
        runs = tuple(x for _,x in self.role_runs)
        if self.unresolved_role_constraints:
            return False
        if any(x.qualification_status != QualificationStatus.VERIFIED for x in runs):
            return False
        if len({x.run_id for x in runs}) > 1:
            if not self.compatibility_evidence:
                return False
            # A textual declaration is NOT a compatibility proof. The pilot
            # explicitly refuses mixed model revisions and different bases.
            if len({x.model_revision_id for x in runs}) > 1:
                return False
            if len({x.basis_ref for x in runs}) > 1:
                return False
        else:
            if len({x.result_generation_id for x in runs}) != 1:
                return False
        return True
