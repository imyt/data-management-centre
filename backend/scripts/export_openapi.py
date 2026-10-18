"""Write the OpenAPI spec to contracts/openapi.json (or the path given).

    uv run python scripts/export_openapi.py [PATH] [--check]

--check exits 1 when the file differs from the app, without writing.
"""

import argparse
import sys
from pathlib import Path

from app.openapi import render_openapi

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "contracts" / "openapi.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    spec = render_openapi()
    if args.check:
        current = args.path.read_text(encoding="utf-8") if args.path.exists() else ""
        if current != spec:
            message = f"{args.path} is out of date. Run `npm run api:sync` in frontend/."
            print(message, file=sys.stderr)
            return 1
        return 0
    args.path.parent.mkdir(parents=True, exist_ok=True)
    args.path.write_text(spec, encoding="utf-8", newline="\n")
    print(f"Wrote {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
