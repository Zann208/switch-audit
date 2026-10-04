"""Turn raw `show` output into plain Python structures."""

from ntc_templates.parse import parse_output

PLATFORM = "cisco_ios"


def expand_vlans(spec: str) -> set[int]:
    """'1,10,20-22' -> {1, 10, 20, 21, 22}. 'none' -> empty set."""
    spec = spec.strip().lower()
    if not spec or spec == "none":
        return set()
    vlans: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            vlans.update(range(int(lo), int(hi) + 1))
        elif part:
            vlans.add(int(part))
    return vlans


def parse_vlans(raw: str) -> dict[int, dict]:
    rows = parse_output(platform=PLATFORM, command="show vlan", data=raw)
    return {
        int(r["vlan_id"]): {
            "name": r["vlan_name"],
            "status": r["status"],
            "ports": r["interfaces"],
        }
        for r in rows
    }


def parse_etherchannels(raw: str) -> list[dict]:
    rows = parse_output(platform=PLATFORM, command="show etherchannel summary", data=raw)
    channels = []
    for r in rows:
        members = r["member_interface"]
        flags = r["member_interface_status"]
        # ntc-templates returns strings when there is a single member
        if isinstance(members, str):
            members, flags = [members], [flags]
        channels.append(
            {
                "group": int(r["group"]),
                "name": r["bundle_name"],
                "status": r["bundle_status"],
                "protocol": r["bundle_protocol"],
                "members": dict(zip(members, flags)),
            }
        )
    return channels


_SECTION_MARKERS = {
    "Native vlan": "main",
    "Vlans allowed on trunk": "allowed",
    "Vlans allowed and active": "active",
    "Vlans in spanning tree": "forwarding",
}


def parse_trunks(raw: str) -> dict[str, dict]:
    """Parse `show interfaces trunk` (ntc-templates has no template for it)."""
    trunks: dict[str, dict] = {}
    section = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        marker = next((s for m, s in _SECTION_MARKERS.items() if m in line), None)
        if marker:
            section = marker
            continue
        cols = line.split()
        if section is None or len(cols) < 2:
            continue
        port = cols[0]
        entry = trunks.setdefault(port, {})
        if section == "main" and len(cols) >= 5:
            entry.update(
                mode=cols[1], encapsulation=cols[2], status=cols[3], native=int(cols[4])
            )
        elif section != "main":
            entry[section] = expand_vlans(cols[1])
    return trunks
