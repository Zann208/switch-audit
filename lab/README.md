# Reproducing the sample faults on a real lab

`SW1.cfg` and `SW2.cfg` build a two-switch lab that produces the faults the tests expect. Use them to capture real output and replace the hand-written files in `samples/`.

## Topology

Two Cisco IOS switches (Catalyst 2960 in Packet Tracer, or an IOSvL2 node in GNS3/EVE-NG), connected by:

- `Gi0/1` to `Gi0/1` (plain trunk)
- `Fa0/23-24` to `Fa0/23-24` (LACP EtherChannel `Po1`)

Two parallel links make a loop, so expect spanning tree to block one path. That does not affect the audit.

## Steps

1. Paste each `.cfg` into its switch CLI in privileged mode (`enable`, then `configure terminal`).
2. On each switch, run the three commands and copy the output:
   - `show vlan brief`
   - `show interfaces trunk`
   - `show etherchannel summary`
3. Save the output as `show_vlan_brief.txt`, `show_interfaces_trunk.txt` and `show_etherchannel_summary.txt` under `captures/SW1/` and `captures/SW2/`.
4. Run `python -m switch_audit --offline captures`.

If a command prints `% Invalid input`, your IOS version lacks it; note which command and platform so the parser can be adjusted.
