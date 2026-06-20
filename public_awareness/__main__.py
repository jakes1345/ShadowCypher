"""Run: PYTHONPATH=. python3 -m public_awareness [--export PATH] [--list]"""

from __future__ import annotations

import argparse
import sys

from public_awareness.engine import ThreatBriefingEngine


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Public threat awareness briefings (standalone)"
    )
    parser.add_argument(
        "--export",
        metavar="PATH",
        help="Export family playbook + all briefings to markdown",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print threat titles and exit",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Open GTK window (default when no other flags)",
    )
    args = parser.parse_args(argv)

    if args.list:
        for t in ThreatBriefingEngine.list_threats():
            print(f"[{t.severity}] {t.title} ({t.id})")
        return 0

    if args.export:
        print(ThreatBriefingEngine.export_markdown(args.export))
        return 0

    from public_awareness.app import main as gui_main

    return gui_main()


if __name__ == "__main__":
    sys.exit(_cli())
