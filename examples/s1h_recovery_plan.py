"""Read-only existing-archive evidence route planning (no ETABS)."""
from __future__ import annotations
import argparse
from pathlib import Path
from tools.legacy_audit.s1h_recovery import plan_from_archive_zip

def main() -> None:
    parser=argparse.ArgumentParser(
        description="Classify Column 235 old evidence vs future existing gateway acquisition")
    parser.add_argument("archived_zip", type=Path,
                        help="Original unchanged TBDY_COLUMN_EXTERNAL_AUDIT_2026-10-20.zip")
    parser.add_argument("--output", type=Path,
                        help="Optional local JSON output (no product/source mutation)")
    args=parser.parse_args()
    content=plan_from_archive_zip(args.archived_zip).json()+"\n"
    if args.output is not None:
        args.output.write_text(content,encoding="utf-8")
        print(f"wrote={args.output}")
    else:
        print(content,end="")

if __name__=="__main__":
    main()
