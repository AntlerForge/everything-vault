---
title: "Home network"
domains: [it-setup]
type: reference
sensitivity: normal
created: 2026-01-18
last_updated: 2026-03-22
last_verified: 2026-05-07
confidence: high
source: manual
tags: [network, wifi, home]
---

<!-- EXAMPLE: This article demonstrates a reference article kept generic — describes shape and purpose, not real device IDs. -->

# Home network

A small flat, modest needs, one home worker plus the usual phones and
streaming devices.

## Topology

```
ISP modem  →  Router  →  Switch  →  AP (mesh node 1)
                              └─→  AP (mesh node 2)
```

- Single ISP fibre line.
- Router does DHCP and the firewall.
- One unmanaged switch in the cupboard for wired devices.
- Two mesh wifi access points: one in the living room, one near the
  bedroom.

## Wired devices

- Desktop / dev workstation.
- NAS (Time Machine + family photos backup).
- Home assistant box.
- Printer.

## Wireless devices

- Two laptops, two phones, smart speakers, a TV, miscellaneous IoT.

## Segmentation

- Default network for trusted devices.
- IoT/Guest network for everything that doesn't need access to the NAS or
  the dev workstation.

## Things to remember

- Router firmware updates: check quarterly.
- The router and APs are on a small UPS; the modem is not — short power
  cuts won't take the WiFi out, longer ones will.
- No real MAC addresses, IPs, or device identifiers are recorded in this
  vault.
