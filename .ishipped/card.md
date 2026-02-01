---
title: "NAVAID API"
summary: "Get coordinates for any US airport, navaid, or waypoint via REST API."
shipped: 2026-01-13
tags: [aviation, api, faa, navigation]
links:
  - label: "Try it"
    url: "https://navaid-api.azurewebsites.net"
    primary: true
  - label: "GitHub"
    url: "https://github.com/dandriscoll/navaid-api"
    primary: false
---

## What is it?

A lightweight REST API that returns lat/long coordinates for FAA airports, navaids (VORs, NDBs, TACANs), and waypoints. Supports radial/distance calculations to find points along a bearing from any reference — useful for flight planning, aviation tools, and airspace analysis.

## Key Features

- **Radial/distance math** — Calculate coordinates at any bearing and distance from a navaid or airport
- **ICAO fix notation** — Query `SEA270005` to get the point 5nm on the 270° radial from Seattle VORTAC
- **Unified search** — Single `/points/{id}` endpoint searches airports, navaids, and waypoints at once
- **FAA NASR data** — Parses official FAA subscription files with automated download scripts
- **Self-hosted** — Runs anywhere with Python, includes systemd service for production

---

[View on ishipped.io](https://ishipped.io/card/dandriscoll/navaid-api)
