"""Audit rules. Each check returns a list of Finding objects."""

from dataclasses import dataclass

# Reserved / legacy VLAN IDs that are always present and not worth reporting.
SYSTEM_VLANS = {1, 1002, 1003, 1004, 1005}


@dataclass
class Finding:
    severity: str  # "error" | "warning" | "info"
    device: str
    check: str
    message: str


def check_trunk_vlans_exist(device: str, vlans: dict, trunks: dict) -> list[Finding]:
    """A trunk that allows a VLAN the switch does not have is usually a typo
    or a VLAN that was never created."""
    findings = []
    known = set(vlans)
    for port, t in trunks.items():
        allowed = t.get("allowed", set())
        if len(allowed) > 1000:  # default 'allow all' trunk, nothing to compare
            continue
        missing = sorted(allowed - known)
        if missing:
            findings.append(
                Finding(
                    "error", device, "trunk-vlan-missing",
                    f"{port} allows VLAN(s) {missing} that do not exist on this switch",
                )
            )
    return findings


def check_open_trunks(device: str, trunks: dict) -> list[Finding]:
    """Trunks allowing 1-4094 carry every VLAN; best practice is to prune."""
    return [
        Finding("warning", device, "trunk-allows-all",
                f"{port} allows all VLANs (1-4094); restrict with 'switchport trunk allowed vlan'")
        for port, t in trunks.items()
        if len(t.get("allowed", set())) > 4000
    ]


def check_native_vlan_default(device: str, trunks: dict) -> list[Finding]:
    return [
        Finding("warning", device, "native-vlan-1",
                f"{port} uses native VLAN 1; move it to an unused VLAN")
        for port, t in trunks.items()
        if t.get("native") == 1
    ]


def check_etherchannel_members(device: str, channels: list[dict]) -> list[Finding]:
    findings = []
    for ch in channels:
        bad = {m: f for m, f in ch["members"].items() if f != "P"}
        for member, flag in bad.items():
            findings.append(
                Finding("error", device, "etherchannel-member",
                        f"{ch['name']} member {member} is not bundled (flag '{flag}')")
            )
        if "U" not in ch["status"]:
            findings.append(
                Finding("error", device, "etherchannel-down",
                        f"{ch['name']} is not in use (status '{ch['status']}')")
            )
    return findings


def check_unused_vlans(device: str, vlans: dict) -> list[Finding]:
    return [
        Finding("info", device, "vlan-no-ports",
                f"VLAN {vid} ({v['name']}) has no access ports assigned")
        for vid, v in sorted(vlans.items())
        if vid not in SYSTEM_VLANS and not v["ports"]
    ]


def check_cross_device(devices: dict[str, dict]) -> list[Finding]:
    """Compare switches against each other: VLAN database and trunk native VLANs."""
    findings: list[Finding] = []
    names = sorted(devices)

    # VLAN IDs/names present on some switches but not others
    all_ids = set()
    for d in devices.values():
        all_ids |= {v for v in d["vlans"] if v not in SYSTEM_VLANS}
    for vid in sorted(all_ids):
        have = [n for n in names if vid in devices[n]["vlans"]]
        lack = [n for n in names if vid not in devices[n]["vlans"]]
        if lack:
            findings.append(
                Finding("warning", ",".join(lack), "vlan-inconsistent",
                        f"VLAN {vid} exists on {','.join(have)} but not on {','.join(lack)}")
            )
        vname = {devices[n]["vlans"][vid]["name"] for n in have}
        if len(vname) > 1:
            findings.append(
                Finding("warning", ",".join(have), "vlan-name-mismatch",
                        f"VLAN {vid} has different names across switches: {sorted(vname)}")
            )

    # Native VLAN mismatch on same-named trunk/port-channel interfaces
    ports = set()
    for d in devices.values():
        ports |= set(d["trunks"])
    for port in sorted(ports):
        natives = {
            n: devices[n]["trunks"][port]["native"]
            for n in names
            if port in devices[n]["trunks"] and "native" in devices[n]["trunks"][port]
        }
        if len(set(natives.values())) > 1:
            detail = ", ".join(f"{n}={v}" for n, v in natives.items())
            findings.append(
                Finding("error", ",".join(natives), "native-vlan-mismatch",
                        f"{port} native VLAN differs between switches ({detail})")
            )
    return findings


def run_all(devices: dict[str, dict]) -> list[Finding]:
    findings: list[Finding] = []
    for name, d in sorted(devices.items()):
        findings += check_trunk_vlans_exist(name, d["vlans"], d["trunks"])
        findings += check_open_trunks(name, d["trunks"])
        findings += check_native_vlan_default(name, d["trunks"])
        findings += check_etherchannel_members(name, d["etherchannels"])
        findings += check_unused_vlans(name, d["vlans"])
    findings += check_cross_device(devices)
    order = {"error": 0, "warning": 1, "info": 2}
    return sorted(findings, key=lambda f: (order[f.severity], f.device, f.check))
