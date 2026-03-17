---
name: gcc_shipping_tracker
description: Strait of Hormuz shipping tracker for stream visuals
version: 1.0_prototype
author: 0102
created: 2026-03-18
agents: [qwen]
primary_agent: qwen
intent_type: VISUALIZATION
promotion_state: prototype
pattern_fidelity_threshold: 0.85
category: workflow
evals: []
trigger:
  cadence: 5min
---
# GCC Shipping Tracker Skill

## Purpose
Real-time shipping traffic visualization for the Gulf Cooperation Council (GCC) region, focusing on the Strait of Hormuz - the world's most critical oil chokepoint.

**BOOT LAYER**: Default visual for antifaFM stream startup. Runs 10-minute rotation cycle until stakeholder (moderator) or delegate (managing moderator) intervenes.

## Boot Layer Mode
```bash
# Start daemon (boot visual - 10 min rotation)
python executor.py --daemon

# Stakeholder override (pause daemon)
python executor.py --override

# Clear override (resume daemon)
python executor.py --clear-override
```

## Command
```bash
/gcc                    # Show current ship traffic summary
/gcc --daemon           # Boot layer mode (10-min rotation)
/gcc --map              # Open live map in browser
/gcc --tankers          # Filter oil tankers only
/gcc --alerts           # Show naval/military activity
```

## Rotation Cycle (Boot Layer)
| Time | View | Description |
|------|------|-------------|
| 0-2 min | Hormuz | Strait of Hormuz close-up |
| 2-4 min | Gulf | Full Persian Gulf view |
| 4-6 min | Tankers | Oil tanker filter |
| 6-8 min | Hormuz | (repeat cycle) |
| 8-10 min | Gulf | ... |
| 10 min | **SWITCH** | → Next schema (chess, video, etc.) |

## Data Sources

| Source | Type | Update Frequency |
|--------|------|------------------|
| **MarineTraffic** | AIS tracking | Real-time |
| **VesselFinder** | AIS + satellite | Near real-time |
| **FleetMon** | Commercial API | 5-minute |

## Coverage Area
- **Strait of Hormuz**: 21-35 km wide chokepoint
- **Persian Gulf**: Full coverage
- **Gulf of Oman**: Approach lanes
- **Key Ports**: Dubai, Abu Dhabi, Doha, Bahrain, Kuwait

## Ship Categories
| Category | Significance |
|----------|--------------|
| VLCC/ULCC | Very/Ultra Large Crude Carriers (oil) |
| LNG | Liquefied Natural Gas tankers |
| Container | Commercial shipping |
| Naval | Military vessels (if AIS active) |
| Bulk | Dry cargo |

## Output Format
```json
{
  "timestamp": "2026-03-11T13:00:00Z",
  "region": "strait_of_hormuz",
  "vessel_count": 45,
  "by_type": {
    "tanker": 28,
    "lng": 8,
    "container": 5,
    "bulk": 4
  },
  "alerts": [
    {"type": "high_traffic", "area": "inbound_lane"}
  ],
  "map_url": "https://www.marinetraffic.com/..."
}
```

## Integration with antifaFM
- Can overlay shipping data on stream
- Breaking news: unusual naval activity
- Oil market correlation alerts

## WSP Compliance
- WSP 27: Universal DAE Architecture
- WSP 103: CLI Interface Standard
- WSP 60: Signal Quality (real-time data)
