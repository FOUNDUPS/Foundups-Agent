---
name: antifafm_linkedin_post
description: Generate LinkedIn posts for antifaFM live streams on GeoZai page
version: 0.1.0_prototype
author: 0102
created: 2026-03-05
agents: [qwen]
primary_agent: qwen
intent_type: GENERATION
promotion_state: prototype
pattern_fidelity_threshold: 0.90
target_linkedin_page: 104834798 (GeoZai)
category: workflow
evals: []
---
# antifaFM LinkedIn Post Generator

**Purpose**: Generate engaging LinkedIn posts for antifaFM live streams that align with the FFCPLN anti-fascist music brand.

**Target**: GeoZai LinkedIn page (104834798) - shared with Move2Japan political content

---

## Context: antifaFM Brand

**antifaFM** = 24/7 anti-fascist music radio stream on YouTube

**Alignment with FFCPLN**:
- Same political audience as Move2Japan shorts
- 160+ pro-democracy, anti-authoritarian songs
- 2026: Critical year for US democracy
- Targets: Democracy, labor rights, reproductive freedom, climate action, immigrant rights

**Shared LinkedIn Page**: GeoZai (104834798)
- Move2Japan political shorts content
- antifaFM live stream announcements
- Unified anti-fascist messaging

---

## Post Templates

### Template 1: Stream Announcement (Standard)

```
🔴 LIVE NOW: antifaFM - 24/7 Music for Fighting Fascism

The resistance has a soundtrack. 160+ songs for democracy.

🎵 Tune in: {stream_url}

#FFCPLN #Democracy2026 #Resistance #AntiFascist #Music

👆 2026 is the year. Join us.
```

### Template 2: Urgency Hook

```
🚨 antifaFM is LIVE - The Playlist They Fear

160 songs MAGA doesn't want you to hear.
24/7 anti-fascist radio. No commercials. No compromise.

🔴 {stream_url}

#FFCPLN #Democracy #Antifascist #TrumpFiles

250 years of freedom at stake. Music matters.
```

### Template 3: Community Hook

```
✊ antifaFM Live Stream - Democracy's Soundtrack

Fighting for:
🗳️ Democracy over authoritarianism
💪 Labor rights over exploitation
🏥 Reproductive freedom
🌍 Climate action
🛡️ Immigrant rights vs ICE cruelty

🎵 Listen now: {stream_url}

#FFCPLN #Resistance #Democracy2026 #Music
```

### Template 4: Direct Action

```
🔥 antifaFM: 24/7 Anti-Fascist Radio - LIVE

160+ songs. One mission: Defend democracy.

2026 is not the year to be silent.
This is the year to turn it UP.

🔴 Join the resistance: {stream_url}

#FFCPLN #AntiFascist #Democracy #Music #Resistance
```

---

## Dynamic Elements

### {stream_url}
- Format: `https://www.youtube.com/watch?v={video_id}`
- Always include full URL for LinkedIn click tracking

### {title}
- Usually: "antifaFM Live Stream" or custom title from OBS
- Can incorporate if meaningful, otherwise use template defaults

---

## Output Format

```json
{
  "post_content": "🔴 LIVE NOW: antifaFM - 24/7 Music for Fighting Fascism...",
  "template_used": "stream_announcement",
  "stream_url": "https://www.youtube.com/watch?v=xxxxx",
  "hashtags": ["#FFCPLN", "#Democracy2026", "#Resistance", "#AntiFascist", "#Music"],
  "confidence": 0.95,
  "patterns": {
    "ffcpln_aligned": true,
    "url_included": true,
    "hashtags_present": true,
    "under_3000_chars": true
  }
}
```

---

## Integration Points

### Posting Orchestrator
- `RefactoredPostingOrchestrator.handle_stream_detected()`
- Channel: antifaFM → LinkedIn: 104834798 (GeoZai)

### Dynamic Metadata
- `DynamicMetadataDaemon` provides stream title from news
- Can be incorporated into post if relevant

---

## Validation Checklist

- [ ] Post contains stream URL?
- [ ] Post under 3000 characters (LinkedIn limit)?
- [ ] Contains #FFCPLN hashtag?
- [ ] Contains call-to-action?
- [ ] Aligns with anti-fascist messaging?

---

## Notes

- GeoZai LinkedIn audience overlaps with Move2Japan political shorts
- antifaFM and FFCPLN share the same 160+ song catalog
- Post should drive clicks to YouTube stream
- Avoid corporate/sanitized language - this is resistance content
