import argparse
import sys

import yaml

from .checks import run_all
from .collect import collect_live, collect_offline
from .parse import parse_etherchannels, parse_trunks, parse_vlans


def build_devices(raw: dict[str, dict[str, str]]) -> dict[str, dict]:
    return {
        name: {
            "vlans": parse_vlans(r.get("show_vlan_brief", "")),
            "trunks": parse_trunks(r.get("show_interfaces_trunk", "")),
            "etherchannels": parse_etherchannels(r.get("show_etherchannel_summary", "")),
        }
        for name, r in raw.items()
    }


def render(findings) -> str:
    if not findings:
        return "No findings. All checks passed."
    lines = ["| Severity | Device | Check | Finding |", "|---|---|---|---|"]
    lines += [
        f"| {f.severity} | {f.device} | {f.check} | {f.message} |" for f in findings
    ]
    counts = {s: sum(f.severity == s for f in findings) for s in ("error", "warning", "info")}
    lines.append("")
    lines.append(f"{counts['error']} errors, {counts['warning']} warnings, {counts['info']} info")
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="switch_audit", description="Audit VLANs, trunks and EtherChannel on Cisco switches.")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--offline", metavar="DIR", help="folder of saved show output (DIR/<switch>/<command>.txt)")
    src.add_argument("--inventory", metavar="FILE", help="YAML inventory of live switches")
    p.add_argument("--save-raw", metavar="DIR", help="with --inventory: save raw output for later offline runs")
    args = p.parse_args(argv)

    if args.offline:
        raw = collect_offline(args.offline)
    else:
        with open(args.inventory) as fh:
            inventory = yaml.safe_load(fh)["switches"]
        raw = collect_live(inventory, save_to=args.save_raw)

    findings = run_all(build_devices(raw))
    print(render(findings))
    return 1 if any(f.severity == "error" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
