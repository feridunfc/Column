"""C-07/C-13: explicitly revised, immutable and source-specific identities."""
from dataclasses import dataclass


def required(value, name):
    if not isinstance(value,str) or not value.strip():
        raise ValueError(f"{name} must be a nonblank string")


@dataclass(frozen=True, slots=True)
class RevisionRef:
    namespace: str
    identifier: str
    revision: str
    def __post_init__(self):
        for name in ("namespace","identifier","revision"):
            required(getattr(self,name),name)


@dataclass(frozen=True, slots=True)
class SourceRef:
    producer: str
    source_identifier: str
    record_identifier: str
    declared_units: str
    acquisition_ref: str
    def __post_init__(self):
        for name in ("producer","source_identifier","record_identifier",
                     "declared_units","acquisition_ref"):
            required(getattr(self,name),name)


@dataclass(frozen=True, slots=True)
class RuleRef:
    code_id: str
    edition: str
    rule_id: str
    def __post_init__(self):
        for name in ("code_id","edition","rule_id"):
            required(getattr(self,name),name)


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    evidence_id: str
    source: SourceRef
    input_revision: RevisionRef
    def __post_init__(self):
        required(self.evidence_id,"evidence_id")
        if type(self.source) is not SourceRef or type(self.input_revision) is not RevisionRef:
            raise TypeError("EvidenceRef needs SourceRef and RevisionRef")
