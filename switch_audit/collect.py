"""Get raw `show` output, either from live switches (Netmiko) or from saved files."""

import os
from pathlib import Path

COMMANDS = {
    "show_vlan_brief": "show vlan brief",
    "show_interfaces_trunk": "show interfaces trunk",
    "show_etherchannel_summary": "show etherchannel summary",
}


def collect_offline(folder: str) -> dict[str, dict[str, str]]:
    """Read <folder>/<switch>/<command>.txt files."""
    out: dict[str, dict[str, str]] = {}
    for sw in sorted(Path(folder).iterdir()):
        if sw.is_dir():
            out[sw.name] = {
                key: (sw / f"{key}.txt").read_text() for key in COMMANDS
                if (sw / f"{key}.txt").exists()
            }
    return out


def collect_live(inventory: list[dict], save_to: str | None = None) -> dict[str, dict[str, str]]:
    """Connect to each switch over SSH and run the audit commands.

    Credentials come from the environment (SWITCH_USER / SWITCH_PASS /
    SWITCH_ENABLE) so they never end up in the inventory file or in git.
    """
    from netmiko import ConnectHandler  # imported lazily so offline mode needs no SSH

    user = os.environ["SWITCH_USER"]
    password = os.environ["SWITCH_PASS"]
    enable = os.environ.get("SWITCH_ENABLE", password)

    out: dict[str, dict[str, str]] = {}
    for dev in inventory:
        conn = ConnectHandler(
            device_type=dev.get("device_type", "cisco_ios"),
            host=dev["host"],
            username=user,
            password=password,
            secret=enable,
        )
        conn.enable()
        out[dev["name"]] = {key: conn.send_command(cmd) for key, cmd in COMMANDS.items()}
        conn.disconnect()

        if save_to:  # keep raw output so a live run can be replayed offline
            folder = Path(save_to) / dev["name"]
            folder.mkdir(parents=True, exist_ok=True)
            for key, text in out[dev["name"]].items():
                (folder / f"{key}.txt").write_text(text)
    return out
