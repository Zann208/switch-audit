# switch-audit

A small Python tool that audits Cisco switch **VLANs, 802.1Q trunks and EtherChannel** and reports misconfigurations. It collects `show` output with [Netmiko](https://github.com/ktbyers/netmiko), parses it (ntc-templates plus a custom trunk parser), and runs checks within each switch and across switches.

It also runs **offline** on saved output, so you can use it with Packet Tracer, GNS3 or EVE-NG captures without any hardware.

## Checks

| Check | Severity | What it catches |
|---|---|---|
| `trunk-vlan-missing` | error | Trunk allows a VLAN that does not exist on the switch |
| `native-vlan-mismatch` | error | Same trunk or port-channel has different native VLANs on each switch |
| `etherchannel-member` / `etherchannel-down` | error | Bundle member not in `P` state, or bundle not in use |
| `trunk-allows-all` | warning | Trunk carries VLANs 1-4094 instead of a pruned list |
| `native-vlan-1` | warning | Trunk uses the default native VLAN |
| `vlan-inconsistent` / `vlan-name-mismatch` | warning | VLAN missing or named differently across switches |
| `vlan-no-ports` | info | VLAN has no access ports assigned |

## Usage

```bash
pip install -r requirements.txt

# Offline: folder of saved output (samples/<switch>/<command>.txt)
python -m switch_audit --offline samples

# Live: credentials come from the environment, never from files
cp inventory.example.yaml inventory.yaml
export SWITCH_USER=admin SWITCH_PASS=... SWITCH_ENABLE=...
python -m switch_audit --inventory inventory.yaml --save-raw raw
```

The exit code is `1` if any errors are found, so it can run in CI.

Commands collected: `show vlan brief`, `show interfaces trunk`, `show etherchannel summary`.

## Tests

```bash
pytest
```

The sample files in `samples/` contain deliberate faults (missing VLAN on a trunk, native VLAN mismatch, a down EtherChannel member) and the tests assert each one is caught.

## Try it on a lab

`lab/` has two switch configs that reproduce the sample faults, plus steps for capturing real output from Packet Tracer, GNS3 or EVE-NG. See [lab/README.md](lab/README.md).

## Notes

- Targets Cisco IOS output (`cisco_ios`).
- The live collection path uses Netmiko's standard SSH flow.
