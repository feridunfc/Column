"""Read-only, exact-hash S1-G archive audit: never opens ETABS."""
from __future__ import annotations
import argparse
from tbdy_column_core.s1g_archive import audit_archive_zip

def main() -> None:
    parser=argparse.ArgumentParser(
        description="Audit historical Column 235 original source ZIP, without ETABS")
    parser.add_argument("source_zip",help="Original TBDY_COLUMN_EXTERNAL_AUDIT_2026-10-20.zip")
    args=parser.parse_args()
    print(audit_archive_zip(args.source_zip).to_json())

if __name__ == "__main__":
    main()
