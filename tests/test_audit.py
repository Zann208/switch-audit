from pathlib import Path

from switch_audit.checks import run_all
from switch_audit.cli import build_devices
from switch_audit.collect import collect_offline
from switch_audit.parse import expand_vlans, parse_trunks

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def findings():
    return run_all(build_devices(collect_offline(SAMPLES)))


def has(check, device=None, text=None):
    return any(
        f.check == check
        and (device is None or device in f.device.split(","))
        and (text is None or text in f.message)
        for f in findings()
    )


def test_expand_vlans():
    assert expand_vlans("1,10,20-22") == {1, 10, 20, 21, 22}
    assert expand_vlans("none") == set()
    assert len(expand_vlans("1-4094")) == 4094


def test_trunk_parser():
    t = parse_trunks((SAMPLES / "SW1/show_interfaces_trunk.txt").read_text())
    assert t["Po1"]["native"] == 99
    assert t["Po1"]["allowed"] == {10, 20, 30, 40, 99}
    assert t["Gi0/1"]["status"] == "trunking"


def test_missing_vlan_on_trunk():
    assert has("trunk-vlan-missing", "SW1", "40")


def test_etherchannel_member_down():
    assert has("etherchannel-member", "SW1", "Fa0/24")
    assert not has("etherchannel-member", "SW2")


def test_native_vlan_mismatch():
    assert has("native-vlan-mismatch", text="Po1")


def test_vlan_inconsistent_across_switches():
    assert has("vlan-inconsistent", "SW2", "VLAN 30")


def test_open_trunk_and_native_1():
    assert has("trunk-allows-all", "SW1")
    assert has("native-vlan-1", "SW2")
