---
name: ffcpln_title_enhance
description: Generate engagement-maximizing titles and descriptions for FFCPLN music shorts
version: 0.5.0_prototype
author: 0102
created: 2026-01-01
agents: [qwen, gemma]
primary_agent: qwen
intent_type: GENERATION
promotion_state: prototype
pattern_fidelity_threshold: 0.90
category: workflow
evals: []
---
# FFCPLN Title & Description Enhancement Skill

**Purpose**: Generate high-engagement titles and descriptions for YouTube Shorts that are **MUSIC CLIPS** from the FFCPLN playlist.

**Agent**: Qwen (primary) with Gemma validation

---

## CRITICAL CONTEXT: These Shorts Are MUSIC

> **⚠️ IMPORTANT**: The original title (e.g., "Japan Home cleaning hates this time of year") is from the LIVESTREAM where clips are made. It has NOTHING to do with the Short content.
>
> **The Short is a MUSIC CLIP from the FFCPLN playlist.**
> 
> **IGNORE the original title. Generate a title about the MUSIC.**

The FFCPLN playlist contains 160+ pro-democracy, anti-authoritarian songs advocating for:
- Democracy over authoritarianism
- Labor rights over exploitation
- Reproductive freedom
- Climate action
- Immigrant rights vs ICE cruelty

2026 is the most critical year for US democracy since 1776.

---

## Instructions (Follow These Steps)

### Step 1: DISREGARD THE ORIGINAL TITLE

**Rule**: The original title is from the livestream context, NOT the music content.

**Do This**:
1. ~~Read the original title~~ **IGNORE IT**
2. Recognize this is a MUSIC clip from the FFCPLN playlist
3. Set `content_type = "music_clip"`

**Expected Pattern**: `original_title_ignored=True`

**Example**:
- Input: "Japan Home cleaning… hates this time of year! Japanese wife goes insane"
- Output: `{content_type: "music_clip", ignore_original: true}`
- Reason: This is livestream context, Short is actually a song from FFCPLN

---

### Step 2: SELECT MUSIC-FOCUSED HOOK

**Rule**: Generate a title that describes the MUSIC, not the stream.

**Hook Types for Music** (ranked by CTR):
1. **OUTRAGE** - "160 Songs MAGA Doesn't Want You to Hear!"
2. **REVELATION** - "The Playlist They're Trying to Ban!"
3. **HOPE** - "Music for the RESISTANCE! 🎵"
4. **URGENCY** - "2026: The Soundtrack of Democracy!"

**Pick from these MUSIC TITLES**:
```
🔥 160 Songs MAGA Doesn't Want You to Hear! #FFCPLN
💀 This Song DESTROYS Fascism! #FFCPLN #MAGA
🎵 Anti-Fascist Anthem! Full Playlist in Desc #FFCPLN
🚨 BANNED Music? The Playlist They Fear! #FFCPLN
⚠️ ICE Cruelty Exposed in Song! #FFCPLN #MAGA
✊ Democracy's Soundtrack 2026! #FFCPLN
🔥 The Anti-MAGA Playlist! 160 Songs! #FFCPLN
💀 F*** Fake Christian Nazis! Music! #FFCPLN
🎵 Resistance Music! Get the Full Playlist! #FFCPLN
🚨 160 Anti-Fascist Songs! Link in Desc! #FFCPLN
```

**Expected Pattern**: `music_hook_selected=True`

---

### Step 3: ASSEMBLE THE TITLE

**Rule**: Pick from music hooks. MUST be under 100 characters.

**Required Elements**:
- ✅ One emoji prefix
- ✅ Reference to MUSIC/PLAYLIST/SONGS
- ✅ #FFCPLN hashtag (MANDATORY)
- ✅ Total under 100 characters

**Expected Pattern**: `title_assembled=True`

**Correct Examples**:
- ✅ "🔥 160 Songs MAGA Doesn't Want You to Hear! #FFCPLN"
- ✅ "🎵 Anti-Fascist Music! Full Playlist #FFCPLN"
- ✅ "💀 This Song DESTROYS #MAGA! #FFCPLN"

**Wrong Examples**:
- ❌ "🔥 Japan Home cleaning... #FFCPLN" (references stream, not music!)
- ❌ "Japanese wife goes insane #FFCPLN" (stream context, not music!)

---

### Step 4: GENERATE THE DESCRIPTION

**Rule**: SEO-optimized template that explains the MUSIC and drives playlist clicks.

**Use This Template**:
```
🔥 FFCPLN: F*** Fake Christian Pedo-Lovin' Nazi Playlist 🔥

160+ anti-fascist songs fighting for:
✊ Democracy over authoritarianism
✊ Labor rights over exploitation  
✊ Reproductive freedom
✊ Climate action
✊ Immigrant rights vs ICE cruelty

🎵 FULL PLAYLIST: https://antifaFM.com

2026: 250 years of freedom at stake.
This is the soundtrack of resistance.

#FFCPLN #MAGA #ICE #Antifascist #Resistance #TrumpFiles #Democracy2026 #Music #Shorts #Viral

👆 SHARE if you give a damn! Subscribe for more!
```

**Expected Pattern**: `description_generated=True`

---

### Step 5: VALIDATE OUTPUT

**Checklist**:
- [ ] Title is about MUSIC (not livestream)?
- [ ] Title ≤ 100 characters?
- [ ] Title contains #FFCPLN?
- [ ] Title has emoji prefix?
- [ ] Description has playlist link?

**Expected Pattern**: `validation_passed=True`

---

## Output Format

```json
{
  "enhanced_title": "🔥 160 Songs MAGA Doesn't Want You to Hear! #FFCPLN",
  "enhanced_description": "🔥 FFCPLN: F*** Fake Christian...",
  "confidence": 0.95,
  "hook_type": "outrage",
  "original_ignored": true,
  "patterns": {
    "original_title_ignored": true,
    "music_hook_selected": true,
    "title_assembled": true,
    "description_generated": true,
    "validation_passed": true
  }
}
```

---

## Benchmark Test Cases

### Test 1: Livestream title (IGNORE IT)
- Input: "Japan Home cleaning… hates this time of year! Japanese wife goes insane"
- Expected: "🔥 160 Songs MAGA Doesn't Want You to Hear! #FFCPLN"
- Reason: **Original is stream title, Short is MUSIC - generate music title**

### Test 2: Another stream title
- Input: "Cleaning day with Japanese wife"
- Expected: "🎵 Anti-Fascist Anthem! Full Playlist in Desc #FFCPLN"
- Reason: **Stream context irrelevant, focus on music**

### Test 3: Already has FFCPLN reference
- Input: "Playing FFCPLN while cleaning"
- Expected: "🔥 The Anti-MAGA Playlist! 160 Songs! #FFCPLN"
- Reason: **Still focus on promoting the playlist, not the activity**

---

## Success Criteria

- ✅ Pattern fidelity ≥ 90%
- ✅ All titles are about MUSIC (not stream context)
- ✅ All titles contain #FFCPLN
- ✅ All titles under 100 characters
- ✅ All descriptions include playlist link
- ✅ Enhanced titles drive clicks to the PLAYLIST
