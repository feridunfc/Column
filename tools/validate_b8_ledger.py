"""B8 ledger format gate. Metadata consistency is NOT Supervisor engineering audit."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"evidence"/"ab_closure_ledger.json"
C_STATES={"SATISFIED","PRESERVED_DEFERRED","VIOLATION","UNVERIFIED"}
AB_STATES={"CI_EVIDENCE_PRESENT","UNVERIFIED","VIOLATION"}

def validate_ledger(path: Path=LEDGER) -> dict:
    doc=json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("schema")!="column.ab.closure-ledger.v1":
        raise ValueError("LEDGER_SCHEMA_UNRECOGNIZED")
    if doc.get("release_gate")!="HOLD":
        raise ValueError("LEDGER_CANNOT_SELF_APPROVE_RELEASE")
    if doc.get("supervisor_disposition")!="NOT_REVIEWED_INDEPENDENTLY":
        raise ValueError("LEDGER_CANNOT_SELF_CLAIM_SUPERVISOR_APPROVAL")
    if doc.get("c02_process_status")!="OPEN_UNRATIFIED":
        raise ValueError("C02_UNRATIFIED_STATUS_MUST_BE_PRESERVED")
    claims=doc.get("claims",{})
    if not claims or any(type(x) is not bool or x for x in claims.values()):
        raise ValueError("ENGINEERING_APPROVAL_CLAIMS_MUST_REMAIN_FALSE")
    for key,prefix,count,states in (
        ("constitution_rows","C",32,C_STATES),
        ("acceptance_rows","AB",18,AB_STATES),
    ):
        rows=doc.get(key,[])
        expected={f"{prefix}-{i:02d}" for i in range(1,count+1)}
        ids=[row.get("id") for row in rows]
        if len(ids)!=count or len(set(ids))!=count or set(ids)!=expected:
            raise ValueError(key+":COVERAGE_INCOMPLETE_OR_DUPLICATE")
        for row in rows:
            if row.get("worker_assessment") not in states:
                raise ValueError(row["id"]+":UNKNOWN_DISPOSITION")
            paths=row.get("evidence_paths")
            if not isinstance(paths,list) or not paths:
                raise ValueError(row["id"]+":MISSING_EVIDENCE_LINK")
            for evidence in paths:
                if not isinstance(evidence,str) or not evidence:
                    raise ValueError(row["id"]+":INVALID_EVIDENCE_PATH")
                fp=(ROOT/evidence).resolve()
                if not fp.is_relative_to(ROOT.resolve()) or not fp.exists():
                    raise ValueError(row["id"]+":EVIDENCE_PATH_NOT_FOUND:"+evidence)
    finding_ids=[item.get("id") for item in doc.get("open_findings",[])]
    if len(finding_ids)!=len(set(finding_ids)) or not finding_ids:
        raise ValueError("OPEN_FINDINGS_REQUIRED")
    return doc


if __name__=="__main__":
    doc=validate_ledger()
    print("B8_EVIDENCE_LEDGER_FORMAT_OK; RELEASE_HOLD; NOT SUPERVISOR ACCEPTANCE")
