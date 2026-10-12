#!/usr/bin/env python3
"""Validate cio/scorecard.json: weights, arithmetic, gates, verdict mapping, layer rules.

  python3 scripts/validate_scorecard.py RUN_DIR/cio/scorecard.json
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print(__doc__)
        return 2
    res = rl.validate_scorecard(Path(args[0]))
    print(res.render())
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
