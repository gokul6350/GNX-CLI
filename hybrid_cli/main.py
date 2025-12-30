import argparse
import os
import sys
from typing import Optional

from desktop_agent import run as run_desktop
from mobile_agent import run as run_mobile


def main() -> None:
    parser = argparse.ArgumentParser(description="Hybrid CLI agent for desktop or mobile")
    parser.add_argument("goal", type=str, help="Goal text, e.g., 'open calculator'")
    parser.add_argument("--target", choices=["desktop", "mobile"], default="desktop")
    parser.add_argument("--region", help="Desktop capture region x,y,w,h", default=None)
    parser.add_argument("--device-id", help="ADB device id for mobile", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Print only, no actions")
    args = parser.parse_args()

    try:
        if args.target == "desktop":
            region = _parse_region(args.region)
            run_desktop(args.goal, region=region, dry_run=args.dry_run)
        else:
            run_mobile(args.goal, device_id=args.device_id, dry_run=args.dry_run)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def _parse_region(region: Optional[str]):
    if not region:
        return None
    parts = region.split(",")
    if len(parts) != 4:
        raise ValueError("Region must be x,y,w,h")
    x, y, w, h = map(int, parts)
    return {"left": x, "top": y, "width": w, "height": h}


if __name__ == "__main__":
    main()
