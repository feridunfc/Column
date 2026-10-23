"""C-01/A0: canonical UTF-8/LF document, role, lock and AGENTS verification.

Do not silently update these pinned values. Any revision is a C-02 change.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import re

VERSION = "1.3.1"
RELEASE = "COLUMN-OOP-1.3.1-20261022"
DOCS = (
    "COLUMN_CONSTITUTION.md",
    "COLUMN_WORKER_AB.md",
    "COLUMN_SUPERVISOR.md",
)
SHA256 = (
    "9865cae76655226b36e90d69ecd93836e97e1c8dd5d92acf59ef63e0da0ac519",
    "b3210d4cdc33950f03df8ae95c320c2f0ea5d112f5960465b997154d1122d9be",
    "bda54ca3ca35bd573e3d64fd1d3015603bef3bff881b3e8804f861828daf5873",
)
AGENT_REQUIRED = ("COLUMN_CONSTITUTION.md", "COLUMN_WORKER_AB.md",
                  "COLUMN_SUPERVISOR.md", "G0/G1/G2",
                  "tools/check_architecture_contract.py")


class ArchitectureContractError(ValueError):
    pass


def _field(text: str, name: str, key: str) -> str:
    values = re.findall(
        r"^" + re.escape(key) + r":[ \t]*([^\r\n]+)", text, flags=re.M
    )
    if len(values) != 1 or not values[0].strip():
        raise ArchitectureContractError(f"{name}: missing/duplicate {key}")
    return values[0].strip()


def validate(root: Path) -> dict[str, str]:
    root = Path(root)
    bodies: dict[str, str] = {}
    digests: dict[str, str] = {}
    for name, locked in zip(DOCS, SHA256):
        try:
            data = (root / name).read_bytes()
        except FileNotFoundError as e:
            raise ArchitectureContractError(f"missing canonical document {name}") from e
        data = data.replace(b"\r\n", b"\n")
        if data.startswith(b"\xef\xbb\xbf") or b"\r" in data:
            raise ArchitectureContractError(f"{name}: BOM or unsupported newline")
        try:
            bodies[name] = data.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ArchitectureContractError(f"{name}: not UTF-8") from e
        got = hashlib.sha256(data).hexdigest()
        if got != locked:
            raise ArchitectureContractError(
                f"{name}: SHA-256 mismatch; C-02 revision required"
            )
        digests[name] = got
        for key, expected in (
            ("constitution_version", VERSION), ("release_id", RELEASE),
            ("canonical_path", name),
        ):
            if _field(bodies[name], name, key) != expected:
                raise ArchitectureContractError(f"{name}: {key} mismatch")
    for name in DOCS[1:]:
        if _field(bodies[name], name, "constitution_sha256") != SHA256[0]:
            raise ArchitectureContractError(f"{name}: constitution link mismatch")
    if _field(bodies[DOCS[2]], DOCS[2], "worker_sha256") != SHA256[1]:
        raise ArchitectureContractError("Supervisor: Worker hash link mismatch")
    try:
        agent_bytes = (root / "AGENTS.md").read_bytes()
        if agent_bytes.startswith(b"\xef\xbb\xbf"):
            raise ArchitectureContractError("AGENTS.md: BOM forbidden")
        agent_text = agent_bytes.decode("utf-8")
    except (FileNotFoundError, UnicodeDecodeError) as e:
        raise ArchitectureContractError("AGENTS.md: absent/invalid") from e
    if any(value not in agent_text for value in AGENT_REQUIRED):
        raise ArchitectureContractError("AGENTS.md: full-read or audit hook removed")
    return digests


if __name__ == "__main__":
    try:
        for name, value in validate(Path(__file__).resolve().parents[1]).items():
            print(name, value)
    except ArchitectureContractError as exc:
        raise SystemExit(str(exc)) from exc
    print("ARCHITECTURE_CONTRACT_OK; G0/G1/G2 review still required")
