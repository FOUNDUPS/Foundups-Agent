---
name: news_maps
category: workflow
description: Consolidated conflict/shipping map rotation with ticker scraping
entrypoint: executor.py
version: 1.0.0
last_updated: 2026-03-25
status: active
evals: []
retirement_date: null
---

# News Maps Skill

Merged GCC shipping tracker + LiveUAMap conflict maps into unified schema for antifaFM stream.

## Purpose

Provides visual rotation of:
- Iran conflict map (iran.liveuamap.com)
- Israel-Palestine conflict map (israelpalestine.liveuamap.com)
- Strait of Hormuz shipping (vesselfinder.com)
- Persian Gulf shipping (vesselfinder.com)
- Israel rocket alerts (rocketalert.live)

Uses screenshot capture to avoid WAF blocking (5 min refresh cycle).

## CLI Interface

```bash
# Start rotation daemon
python executor.py --daemon

# Capture single source
python executor.py --capture iran

# Fetch ticker headlines
python executor.py --ticker

# List all sources
python executor.py --list
```

## Anti-Blocking Pattern

- Screenshots captured every 5 minutes (not live embeds)
- Human-like delays between requests (1-4s random)
- Uses undetected-chromedriver for stealth
- Ticker selectors scraped cautiously with caching

## Sources

| ID | Name | Type | Ticker |
|----|------|------|--------|
| iran | Iran Conflict Map | map | Yes |
| palestine | Israel-Palestine Map | map | Yes |
| hormuz | Strait of Hormuz Shipping | shipping | No |
| gulf | Persian Gulf Shipping | shipping | No |
| rockets | Israel Rocket Alerts | alerts | Yes |

## Integration

Used by `boot_layer_rotator` when the "news" schema is active.
Screenshots saved to `cache/screenshots/` as `{source_id}_latest.png`.
Ticker events cached in `cache/ticker/` as JSON.

## WSP References

- WSP 27: Universal DAE Architecture
- WSP 80: DAE Pattern Memory
