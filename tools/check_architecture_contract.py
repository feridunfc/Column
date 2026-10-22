"""Check the pinned architecture release; this is not an engineering approval."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sys


RELEASE_ID = "COLUMN-OOP-1.3-20261022"
CONSTITUTION_VERSION = "1.3.0"
CONSTITUTION_PATH = "docs/architecture/COLUMN_CONSTITUTION.md"
WORKER_PATH = "docs/tasks/COLUMN_WORKER_AB.md"
SUPERVISOR_PATH = "docs/tasks/COLUMN_SUPERVISOR.md"
EXPECTED_DIGESTS = {
    CONSTITUTION_PATH: "38b63b66896e273112e1a075b3acb8d2727475760512b8532299bebab5993c00",
    WORKER_PATH: "167caa6dd9a2a0ea1ab912cc4a034e76dca47a60f90a3ec28c596fae13cc833f",
    SUPERVISOR_PATH: "4a3b6ebf222c6ec01869121218cc354af1ef50d3f800900be269bed0275bc393",
}


def _field(text: str, name: str) -> str | None:
    match = re.search(rf"^{re.escape(name)}:[ \t]*([^\r\n]+)", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def check_contract(root: Path) -> tuple[str, ...]:
    """Return blocking identity/metadata errors without mutating any file."""
    errors: list[str] = []
    texts: dict[str, str] = {}
    for relative, expected in EXPECTED_DIGESTS.items():
        try:
            raw = (root / relative).read_bytes()
            text = raw.decode("utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{relative}: unavailable ({type(exc).__name__})")
            continue
        texts[relative] = text
        actual = hashlib.sha256(raw).hexdigest()
        if actual != expected:
            errors.append(f"{relative}: SHA-256 mismatch; expected {expected}, got {actual}")
        if _field(text, "release_id") != RELEASE_ID:
            errors.append(f"{relative}: release_id mismatch")
        if _field(text, "constitution_version") != CONSTITUTION_VERSION:
            errors.append(f"{relative}: constitution_version mismatch")

    constitution = texts.get(CONSTITUTION_PATH)
    if constitution is not None:
        clauses = re.findall(r"^### (C-\d{2}) —", constitution, re.MULTILINE)
        if clauses != [f"C-{number:02}" for number in range(1, 33)]:
            errors.append(f"{CONSTITUTION_PATH}: clause identifiers differ from C-01 through C-32")
    for relative in (WORKER_PATH, SUPERVISOR_PATH):
        text = texts.get(relative)
        if text is None:
            continue
        if _field(text, "constitution_path") != CONSTITUTION_PATH:
            errors.append(f"{relative}: constitution_path mismatch")
        if _field(text, "constitution_sha256") != EXPECTED_DIGESTS[CONSTITUTION_PATH]:
            errors.append(f"{relative}: constitution pin mismatch")
    supervisor = texts.get(SUPERVISOR_PATH)
    if supervisor is not None:
        if _field(supervisor, "worker_path") != WORKER_PATH:
            errors.append(f"{SUPERVISOR_PATH}: worker_path mismatch")
        if _field(supervisor, "worker_sha256") != EXPECTED_DIGESTS[WORKER_PATH]:
            errors.append(f"{SUPERVISOR_PATH}: worker pin mismatch")
    try:
        instructions = (root / "AGENTS.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"AGENTS.md: unavailable ({type(exc).__name__})")
    else:
        if "## READ_BEFORE_WORK" not in instructions:
            errors.append("AGENTS.md: mandatory read-before-work entry point missing")
        if _field(instructions, "release_id") != RELEASE_ID:
            errors.append("AGENTS.md: release_id mismatch")
        if _field(instructions, "constitution_version") != CONSTITUTION_VERSION:
            errors.append("AGENTS.md: constitution_version mismatch")
        if _field(instructions, "constitution_sha256") != EXPECTED_DIGESTS[CONSTITUTION_PATH]:
            errors.append("AGENTS.md: constitution pin mismatch")
        for relative in EXPECTED_DIGESTS:
            if relative not in instructions:
                errors.append(f"AGENTS.md: missing canonical link {relative}")
    return tuple(errors)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = check_contract(root)
    if errors:
        print("ARCHITECTURE_CONTRACT_MISMATCH — stop affected work", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"ARCHITECTURE_CONTRACT_OK {RELEASE_ID}")
    print("Document identity only; full reading and Supervisor review remain required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
