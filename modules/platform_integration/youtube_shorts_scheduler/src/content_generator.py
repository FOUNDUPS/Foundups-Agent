"""
Content Generator for YouTube Shorts Scheduler

Generates clickbait titles and algorithm-friendly descriptions.
FFCPLN (Fake F*** Christian Pedo-Lovin' Nazi) playlist promotion.
"""

import random
from typing import Optional, List, Dict, Any

def validated_video_evidence(index: Dict[str, Any], video_id: str) -> Optional[dict]:
    if not isinstance(index, dict) or not video_id or index.get("video_id") != video_id:
        return None
    if index.get("success") is False or index.get("error") or index.get("errors"):
        return None
    metadata = index.get("metadata")
    if not isinstance(metadata, dict) or metadata.get("retrieval_eligible") is not True:
        return None
    if not index.get("indexed_at"):
        return None
    if index.get("transcript_source") in {"whisper", "faster_whisper", "stt", "whisper_transcript", "youtube_transcript", "youtube", "stacked"}:
        audio = index.get("audio") or {}
        if not isinstance(audio, dict):
            return None
        segments = index.get("youtube_transcript") or index.get("whisper_transcript") or audio.get("segments")
        if not isinstance(segments, list) or not segments:
            return None
        valid = []
        for segment in segments:
            if not isinstance(segment, dict):
                return None
            start, end, text = segment.get("start"), segment.get("end"), segment.get("text")
            if (type(start) not in (int, float) or type(end) not in (int, float)
                    or not 0 <= start < end or not isinstance(text, str) or not text.strip()):
                return None
            valid.append(text.strip())
        return {"text": " ".join(valid), "source": index["transcript_source"],
                "modality": "speech_transcript", "video_id": video_id,
                "indexed_at": index["indexed_at"], "coverage": "provided_segments_only",
                "training_eligible": False}
    if index.get("transcript_source") != "gemini_summary":
        return None
    provenance = metadata.get("provenance") or {}
    if not isinstance(provenance, dict):
        return None
    if provenance.get("provider") == "youtube_studio_ask":
        if (provenance.get("identity_verified") is not True
                or provenance.get("requested_video_id") != video_id
                or provenance.get("response_video_id") != video_id
                or not provenance.get("response_sha256")):
            return None
        source = "youtube_studio_ask_summary"
    elif index.get("indexer") == "gemini" and index.get("model"):
        source = "gemini_video_summary"
    else:
        return None
    audio = index.get("audio") or {}
    visual = index.get("visual") or {}
    if not isinstance(audio, dict) or not isinstance(visual, dict):
        return None
    transcript = audio.get("transcript_summary")
    visual_text = visual.get("description")
    # Do not fall back to title, topics, key_points, category, duration or a stub.
    text = transcript if isinstance(transcript, str) and transcript.strip() else visual_text
    if not isinstance(text, str) or not text.strip():
        return None
    modality = "audio_summary" if isinstance(transcript, str) and transcript.strip() else "visual_summary"
    return {"text": " ".join(text.split()), "source": source, "modality": modality,
            "video_id": video_id, "indexed_at": index["indexed_at"],
            "coverage": "not_established", "training_eligible": False}


# Title templates for FFCPLN music shorts
# FFCPLN = "Fake F*** Christian Pedo-Lovin' Nazi" - describes MAGA, NOT versus MAGA
TITLE_TEMPLATES = [
    "{song_hint} #FFCPLN #MAGA Must Hear!",
    "#FFCPLN Burns #MAGA - SEE DESC!",
    "#MAGA WON'T Like This! #FFCPLN",
    "VIRAL: #FFCPLN Anti-MAGA Anthem! Link in Desc",
    "#FFCPLN Exposes #MAGA - 160 Songs! See Desc!",
    "This Song DESTROYS #MAGA! #FFCPLN",
    "#FFCPLN: The Playlist #MAGA Fears!",
    "#FFCPLN Anti-Fascist Music Exposing #MAGA",
    "#ICE Cruelty Exposed! #FFCPLN Music",
    "160 Songs #MAGA Doesn't Want You to Hear! #FFCPLN",
    "Resist #ICE #ICEout #StopICE #FFCPLN",
    "#FFCPLN #MAGA Exposed! Subscribe!",
]

# Emoji prefixes for variety
EMOJI_PREFIXES = ["🔥", "❌", "💀", "🚨", "⚠️", "👀", "🎵", "🎶"]

# ICE Victims - Real people harmed by Trump's Gestapo (2026-02-21)
# Remember their names in every description
ICE_VICTIMS = [
    "Renee Good",
    "Alex Pretti",
    "Guadalupe Garcia de Rayos",
    "Rosa Maria Hernandez",
    "Romulo Avelica-Gonzalez",
    "Jorge Garcia",
    "Maribel Trujillo-Diaz",
]

# Standard FFCPLN description - ENHANCED 2026-02-21
FFCPLN_DESCRIPTION = """🔥 FFCPLN: Fake F*** Christian Pedo-Lovin' Nazi Playlist 🔥

160+ anti-fascist songs exposing ICE cruelty & MAGA hypocrisy!

🎵 FULL PLAYLIST: https://antifaFM.com
📻 TUNE IN: https://antifaFM.com - Your source for Anti-Trump Gestapo Music!

🚨 Remember the victims: {ice_victims}
#StopICE #ICEout #AbolishICE #ResistICE

#FFCPLN #MAGA #ICE #Antifascist #Resistance #TrumpFiles #Epstein #Music #Shorts #Viral

👆 SHARE if you care! Subscribe for more!"""

# Alternative descriptions - ENHANCED 2026-02-21
ALT_DESCRIPTIONS = [
    """🎵 From the FFCPLN Playlist - 160+ songs fighting fascism!

🔗 Full playlist: https://antifaFM.com
📻 Stream 24/7: https://antifaFM.com

🚨 {ice_victim} deserves justice! #StopICE

#FFCPLN #MAGA #Resistance #Music #Shorts""",

    """💀 This song is part of the FFCPLN collection.

Fake F*** Christian Pedo-Lovin' Nazis - 160 songs exposing the truth!

🎶 https://antifaFM.com | 📻 https://antifaFM.com

Remember {ice_victim}! #AbolishICE

#FFCPLN #AntiMAGA #ICE #Shorts""",

    """🚨 FFCPLN PLAYLIST 🚨

160+ anti-fascist anthems. This is just one.

📻 ANTIFA FM: https://antifaFM.com - 24/7 Anti-Trump Music!
🔗 Full playlist: https://antifaFM.com

Stand with {ice_victim} - #ICEout #StopDeportations

#FFCPLN #MAGA #Resistance #Shorts #Viral""",
]

# =============================================================================
# NON-FFCPLN DESCRIPTION TEMPLATES (2026-02-22)
# FoundUps and UnDaoDu channels have different content types
# =============================================================================

# FoundUps: M2M discoverable Startup/Business/pAVS content
FOUNDUPS_DESCRIPTION = """🚀 Foundups.com - Imagine a World Reimagined by AI

pAVS: Peer-to-Peer Autonomous Venture System
Where AI agents and humans collaborate to build the future.

🔗 Discover more: https://foundups.com
🤖 OpenClaw AI Marketplace: https://foundups.com/openclaw
📺 Subscribe @FoundUps for startup insights!

#FoundUps #pAVS #AI #Startup #OpenClaw #Autonomous #Tech #Innovation #Shorts"""

FOUNDUPS_ALT_DESCRIPTIONS = [
    """🧠 Foundups.com - AI + Human Collaboration

pAVS: Peer-to-Peer Autonomous Venture System
Building the decentralized economy, one venture at a time.

🔗 https://foundups.com
@FoundUps @UnDaoDu

#FoundUps #pAVS #AI #Startup #Autonomous #Shorts""",

    """💡 Foundups.com - The Future is Autonomous

OpenClaw: Where AI agents work alongside humans.
pAVS: Peer-to-Peer Autonomous Venture System.

🔗 https://foundups.com/openclaw
Subscribe @FoundUps

#FoundUps #OpenClaw #AI #pAVS #Innovation #Shorts""",
]

# UnDaoDu: M2M discoverable Mindfulness content linking to foundups.com
UNDAODU_DESCRIPTION = """🧘 Foundups.com - Where Mindfulness Meets Technology

@UnDaoDu explains the path of non-doing (Wu Wei).
Finding balance in a world reimagined by AI.

🔗 Learn more: https://foundups.com
📿 Breathe. Be. Become.

#UnDaoDu #Mindfulness #Foundups #AI #Meditation #Zen #Peace #Shorts"""

UNDAODU_ALT_DESCRIPTIONS = [
    """☯️ Foundups.com - The Dao of AI

@UnDaoDu: Ancient wisdom for the singularity age.
The way that can be spoken is not the eternal way.

🔗 https://foundups.com

#UnDaoDu #Taoism #Foundups #AI #Mindfulness #Shorts""",

    """🌸 Foundups.com - A Moment of Presence

@UnDaoDu guides you through mindful moments.
Where technology and spirituality meet.

🔗 https://foundups.com

#UnDaoDu #Meditation #Foundups #Peace #Mindful #Shorts""",
]

# Template lookup by channel key
DESCRIPTION_TEMPLATES = {
    "ffcpln": (FFCPLN_DESCRIPTION, ALT_DESCRIPTIONS),
    "foundups": (FOUNDUPS_DESCRIPTION, FOUNDUPS_ALT_DESCRIPTIONS),
    "undaodu": (UNDAODU_DESCRIPTION, UNDAODU_ALT_DESCRIPTIONS),
}


def generate_clickbait_title(
    original_title: Optional[str] = None,
    song_hint: Optional[str] = None,
) -> str:
    """
    Generate engaging clickbait title for FFCPLN music shorts.

    Args:
        original_title: Original video title for context
        song_hint: Optional song name/hint to include

    Returns:
        Clickbait title under 100 chars
    """
    # Pick random template
    template = random.choice(TITLE_TEMPLATES)

    # Pick random emoji prefix
    emoji = random.choice(EMOJI_PREFIXES)

    # Fill in song hint if provided
    if song_hint:
        title = template.replace("{song_hint}", song_hint)
    else:
        # Remove song_hint placeholder
        title = template.replace("{song_hint} ", "")

    # Add emoji prefix
    title = f"{emoji} {title}"

    # Add trailing emoji sometimes
    if random.random() > 0.5:
        title = f"{title} {random.choice(EMOJI_PREFIXES)}"

    # Ensure under 100 chars for YouTube
    if len(title) > 100:
        title = title[:97] + "..."

    return title


# =============================================================================
# CONTENT TYPE DETECTION - 3-Tier Agentic Classification
# =============================================================================

# Tier 1 Keywords (instant heuristics, no API)
MUSIC_KEYWORDS = [
    "song", "anthem", "remix", "music", "beat", "track", "melody",
    "symphony", "orchestra", "guitar", "piano", "drum", "bass",
    "hip hop", "rap", "rock", "jazz", "edm", "punk", "metal",
    "lyric", "verse", "chorus", "ffcpln",  # FFCPLN is music playlist
]

SPEECH_KEYWORDS = [
    "interview", "speech", "talk", "podcast", "commentary", "discuss",
    "conversation", "debate", "lecture", "explain", "react", "response",
    "opinion", "review", "analysis", "rant", "vlog",
]

NEWS_KEYWORDS = [
    "breaking", "news", "report", "protest", "arrest", "raid",
    "ice", "immigration", "deportation", "trump", "maga", "cruelty",
    "exposed", "leaked", "investigation", "scandal", "caught",
]

# FFCPLN Suno Song Markers - if transcript contains these, it's a SUNO SONG (music)
# Suno AI generates songs with lyrics from "Fake Fuck Christian Pedo_lovin Nazi" prompt
# CRITICAL: This overrides "substantial transcript = speech" detection
FFCPLN_SONG_MARKERS = [
    "ffcpln",
    "fake fuck christian",
    "pedo_lovin nazi",
    "pedo lovin nazi",
    "christian pedo",
    "fuck christian",
    "fake fuck",
]


def detect_content_type_from_title(title: str) -> str:
    """
    Tier 1: Fast content type detection from title only.

    No API calls, instant classification based on keywords.

    Args:
        title: Video title string

    Returns:
        'music', 'speech', 'news', or 'mixed'
    """
    if not title:
        return "music"  # Default for FFCPLN channels

    title_lower = title.lower()

    # Count keyword matches for each type
    music_score = sum(1 for kw in MUSIC_KEYWORDS if kw in title_lower)
    speech_score = sum(1 for kw in SPEECH_KEYWORDS if kw in title_lower)
    news_score = sum(1 for kw in NEWS_KEYWORDS if kw in title_lower)

    # News content often has speech elements too
    if news_score >= 2 or (news_score >= 1 and any(kw in title_lower for kw in ["breaking", "exposed", "protest", "ice raid"])):
        return "news"

    if speech_score >= 2 or (speech_score >= 1 and music_score == 0):
        return "speech"

    if music_score >= 1:
        return "music"

    # Default based on channel context (FFCPLN is primarily music)
    return "music"


def detect_content_type(index_json: Dict[str, Any], title_hint: Optional[str] = None) -> str:
    """
    Agentic content type detection with 3-tier classification.

    Tier 1: Title heuristics (instant, no API)
    Tier 2: Index metadata analysis (from Gemini deep index)
    Tier 3: Audio transcript analysis (when available)

    Args:
        index_json: Video index artifact (can be stub or full)
        title_hint: Optional title for Tier 1 classification

    Returns:
        Content type: 'music', 'speech', 'news', or 'mixed'
    """
    # Tier 1: Try title-based detection first (fast path)
    title = title_hint or ""
    if isinstance(index_json, dict):
        title = title or index_json.get("title", "")
        # Also check metadata summary for title clues
        metadata = index_json.get("metadata") or {}
        if not title:
            title = (metadata.get("summary") or "")[:100]

    if title:
        title_result = detect_content_type_from_title(title)
        # If confident from title, return early
        title_lower = title.lower()
        music_strong = any(kw in title_lower for kw in ["song", "anthem", "music", "ffcpln"])
        news_strong = any(kw in title_lower for kw in ["breaking", "protest", "ice raid", "exposed"])
        speech_strong = any(kw in title_lower for kw in ["interview", "speech", "lecture"])

        if music_strong or news_strong or speech_strong:
            return title_result

    if not isinstance(index_json, dict):
        return title_result if title else "music"

    # Tier 2: Check index metadata (from deeper indexing)
    metadata = index_json.get("metadata") or {}
    topics = metadata.get("topics") or []

    # Check for explicit content type in topics
    topics_lower = [t.lower() for t in topics if isinstance(t, str)]
    if "news" in topics_lower or "protest" in topics_lower:
        return "news"
    if "interview" in topics_lower or "speech" in topics_lower or "commentary" in topics_lower:
        return "speech"

    speech_topics = {"interview", "commentary", "news", "talk", "podcast", "speech", "discussion"}
    if any(t in speech_topics for t in topics_lower):
        return "speech"

    # Tier 3: Check audio analysis (from Gemini deep index)
    audio = index_json.get("audio") or {}
    transcript = (audio.get("transcript_summary") or "").strip()
    segments = audio.get("segments") or []

    # If transcript exists, analyze content
    if transcript:
        transcript_lower = transcript.lower()

        # CRITICAL: Check for FFCPLN Suno song markers FIRST
        # If transcript IS the song lyrics ("Fake Fuck Christian Pedo_lovin Nazi", "FFCPLN")
        # then it's MUSIC, not speech - Suno AI generated these songs
        if any(marker in transcript_lower for marker in FFCPLN_SONG_MARKERS):
            return "music"

        # Only check for speech/news if substantial transcript (not just song title)
        if len(transcript) > 100 or len(segments) > 5:
            # News indicators in transcript
            news_keywords = ["breaking", "report", "trump", "ice", "immigration", "protest", "arrest", "raid"]
            if any(kw in transcript_lower for kw in news_keywords):
                return "news"

            # If transcript is substantial with clear speech patterns, it's speech
            return "speech"

    # Default: return title-based result or music
    return title_result if title else "music"


def extract_title_hint_from_index(index_json: Dict[str, Any], fallback_title: Optional[str] = None) -> str:
    """
    Extract a compact hint from a video index artifact to inform title generation.

    Occam: deterministic extraction only (no network / no LLM).
    Enhanced to extract actual content from audio/visual analysis.
    """
    if not isinstance(index_json, dict):
        return (fallback_title or "").strip()

    # Priority 1: Audio transcript (if indexed with Gemini)
    audio = index_json.get("audio") or {}
    transcript = (audio.get("transcript_summary") or "").strip()
    if transcript and len(transcript) > 20:
        # Extract first meaningful sentence
        sentences = transcript.split(".")
        for sent in sentences[:3]:
            sent = sent.strip()
            if len(sent) > 15 and not sent.lower().startswith("ffcpln"):
                return sent[:48].strip()

    # Priority 2: Key points from metadata
    metadata = index_json.get("metadata") or {}
    if isinstance(metadata, dict):
        # Check key_points first (most specific)
        key_points = metadata.get("key_points") or []
        if isinstance(key_points, list):
            for kp in key_points[:3]:
                if isinstance(kp, str) and len(kp.strip()) > 10:
                    return kp.strip()[:48]

        summary = metadata.get("summary")
        if isinstance(summary, str) and summary.strip():
            s = summary.strip()
            # Common stub prefix: "FFCPLN music short: <title>"
            for prefix in ("FFCPLN music short:", "FFCPLN music short"):
                if s.lower().startswith(prefix.lower()):
                    s = s[len(prefix):].strip(" :.-")
                    break
            # Skip generic stubs
            if "index stub" not in s.lower():
                return s[:48].strip()

        topics = metadata.get("topics") or []
        if isinstance(topics, list):
            for t in topics:
                if not isinstance(t, str):
                    continue
                candidate = t.strip()
                if not candidate:
                    continue
                if candidate.lower() in {"ffcpln", "music", "shorts"}:
                    continue
                return candidate[:32].strip()

    # Priority 3: Visual description
    visual = index_json.get("visual") or {}
    visual_desc = (visual.get("description") or "").strip()
    if visual_desc and len(visual_desc) > 15:
        return visual_desc[:48].strip()

    classification = index_json.get("classification") or {}
    if isinstance(classification, dict):
        cats = classification.get("discovered_categories") or []
        if isinstance(cats, list):
            for c in cats:
                if not isinstance(c, str):
                    continue
                candidate = c.strip()
                if not candidate:
                    continue
                if candidate.lower() in {"ffcpln", "music", "shorts"}:
                    continue
                return candidate[:32].strip()

    return (fallback_title or "").strip()[:48]


def generate_clickbait_title_from_index(
    *, original_title: str, index_json: Dict[str, Any], video_id: str = "",
) -> str:
    """Use matched analyzer content; preserve the title without evidence.

    Historical function name retained for callers. No random hooks, invented
    topics or title-derived fallback are used in this path.
    """
    evidence = validated_video_evidence(index_json, video_id)
    if evidence is None:
        return original_title
    text = evidence["text"]
    if len(text) <= 100:
        return text
    return text[:97].rsplit(" ", 1)[0].rstrip(".,;:") + "..."


def get_ai_driven_template(
    title: str,
    channel: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Get AI-classified description template using gemma_content_type_classifier skill.

    This replaces static description_template config with dynamic AI classification.

    Args:
        title: Video title
        channel: Channel key (move2japan, undaodu, foundups, antifafm)
        metadata: Optional index artifact with audio/visual analysis

    Returns:
        Template key: "ffcpln", "foundups", or "undaodu"

    WSP Compliance: WSP 95 (SKILLz Wardrobe), WSP 77 (Agent Coordination)
    """
    try:
        from modules.platform_integration.youtube_shorts_scheduler.skillz.gemma_content_type_classifier.executor import classify_content
        result = classify_content(title=title, channel=channel, metadata=metadata)
        return result["description_template"]
    except ImportError:
        # Skill not available, fallback to channel baseline
        import logging
        logging.getLogger(__name__).debug(
            "[CONTENT-GEN] gemma_content_type_classifier skill not available, using channel baseline"
        )
        baselines = {
            "move2japan": "ffcpln",
            "antifafm": "ffcpln",
            "foundups": "foundups",
            "undaodu": "undaodu",
        }
        return baselines.get(channel.lower(), "ffcpln")


def get_standard_description(template: str = "ffcpln") -> str:
    """
    Get standard algorithm-friendly description for channel.

    Args:
        template: "ffcpln", "foundups", "undaodu", or "alt"

    Returns:
        Description string appropriate for channel content type
    """
    # Use DESCRIPTION_TEMPLATES lookup (2026-02-22)
    if template in DESCRIPTION_TEMPLATES:
        main_desc, alt_descs = DESCRIPTION_TEMPLATES[template]
        # 70% main, 30% random alt for variety
        desc = main_desc if random.random() > 0.3 else random.choice(alt_descs)

        # FFCPLN templates need ICE victim names
        if template == "ffcpln":
            victims_sample = random.sample(ICE_VICTIMS, min(3, len(ICE_VICTIMS)))
            victims_str = ", ".join(victims_sample)
            single_victim = random.choice(ICE_VICTIMS)
            if "{ice_victims}" in desc:
                desc = desc.format(ice_victims=victims_str)
            elif "{ice_victim}" in desc:
                desc = desc.format(ice_victim=single_victim)

        return desc

    # Legacy "alt" handling for backward compat
    if template == "alt":
        single_victim = random.choice(ICE_VICTIMS)
        desc = random.choice(ALT_DESCRIPTIONS)
        return desc.format(ice_victim=single_victim)

    # Default fallback to FFCPLN
    victims_sample = random.sample(ICE_VICTIMS, min(3, len(ICE_VICTIMS)))
    victims_str = ", ".join(victims_sample)
    return FFCPLN_DESCRIPTION.format(ice_victims=victims_str)


def generate_description_with_context(
    original_title: Optional[str] = None,
    song_name: Optional[str] = None,
    artist: Optional[str] = None,
    template_type: str = "ffcpln",
) -> str:
    """
    Generate contextual description based on video content and channel template.

    Args:
        original_title: Original video title
        song_name: Song name if known
        artist: Artist name if known
        template_type: "ffcpln", "foundups", or "undaodu"

    Returns:
        Description with context
    """
    # Get template for channel (default to FFCPLN for backward compat)
    if template_type in DESCRIPTION_TEMPLATES:
        main_desc, alt_descs = DESCRIPTION_TEMPLATES[template_type]
        # Use main or random alt
        base = main_desc if random.random() > 0.3 else random.choice(alt_descs)
    else:
        # Fallback to FFCPLN
        base = FFCPLN_DESCRIPTION

    # FFCPLN templates need ICE victim names
    if template_type == "ffcpln":
        victims_sample = random.sample(ICE_VICTIMS, min(3, len(ICE_VICTIMS)))
        victims_str = ", ".join(victims_sample)
        single_victim = random.choice(ICE_VICTIMS)
        if "{ice_victims}" in base:
            base = base.format(ice_victims=victims_str)
        elif "{ice_victim}" in base:
            base = base.format(ice_victim=single_victim)

    # Add song/artist credit if known (FFCPLN music content)
    if (song_name or artist) and template_type == "ffcpln":
        credit = "\n\n🎤 "
        if song_name and artist:
            credit += f'"{song_name}" by {artist}'
        elif song_name:
            credit += f'"{song_name}"'
        elif artist:
            credit += f"by {artist}"

        # Insert before hashtags
        parts = base.split("\n\n#")
        if len(parts) >= 2:
            base = f"{parts[0]}{credit}\n\n#{parts[1]}"

    return base


# Hashtag sets for variety
HASHTAG_SETS = [
    "#FFCPLN #MAGA #ICE #Resistance #Shorts",
    "#FFCPLN #AntiMAGA #Antifascist #Music #Viral",
    "#FFCPLN #TrumpFiles #Epstein #Shorts #FYP",
    "#FFCPLN #MAGA #Immigration #ICE #Shorts",
]

# Trending hashtags for ICE resistance content
TRENDING_ICE_HASHTAGS = [
    "#StopICE #ICEout #ResistICE #AbolishICE",
    "#ICEout #NoHumanIsIllegal #ResistICE #StopDeportations",
    "#AbolishICE #ICERaids #ProtectImmigrants #Sanctuary",
    "#StopICE #ICEout #FamiliesBelongTogether #NoKidsInCages",
    "#ResistICE #ICERaids #StopDeportations #ImmigrantRights",
]

# Content-type specific templates
MUSIC_TITLE_TEMPLATES = [
    "{hint} #FFCPLN #MAGA Music",
    "#FFCPLN Anthem: {hint}",
    "This Song DESTROYS #MAGA! {hint}",
    "{hint} - Anti-Fascist Music #FFCPLN",
]

NEWS_TITLE_TEMPLATES = [
    "BREAKING: {hint} #FFCPLN",
    "#MAGA Won't Show This: {hint}",
    "EXPOSED: {hint} #FFCPLN #ICE",
    "{hint} - Media Blackout! #FFCPLN",
]

SPEECH_TITLE_TEMPLATES = [
    "{hint} #FFCPLN Truth",
    "#MAGA Hates This: {hint}",
    "LISTEN: {hint} #FFCPLN",
    "{hint} - What They Don't Tell You! #FFCPLN",
]


def get_hashtags() -> str:
    """Get random hashtag set."""
    return random.choice(HASHTAG_SETS)


def get_trending_ice_hashtags() -> str:
    """Get trending ICE resistance hashtags."""
    return random.choice(TRENDING_ICE_HASHTAGS)


def get_combined_hashtags(include_trending: bool = True) -> str:
    """Get combined base + trending hashtags."""
    base = random.choice(HASHTAG_SETS)
    if include_trending:
        trending = random.choice(TRENDING_ICE_HASHTAGS)
        return f"{base} {trending}"
    return base


def enhance_title(original_title: str) -> str:
    """
    Enhance existing title for clickability using FFCPLN patterns.
    
    Preserves key content from original while adding engagement hooks.
    
    Args:
        original_title: Original video title
        
    Returns:
        Enhanced clickbait title under 100 chars
    """
    # Pick random emoji
    emoji = random.choice(EMOJI_PREFIXES)
    
    # Extract key words from original (remove existing hashtags)
    clean_title = original_title
    for tag in ["#FFCPLN", "#MAGA", "#trump", "#epstein", "#ICE"]:
        clean_title = clean_title.replace(tag, "").strip()
    
    # Truncate if too long (leave room for hashtags)
    if len(clean_title) > 50:
        clean_title = clean_title[:47] + "..."
    
    # Build enhanced title with hooks
    hooks = [
        f"{emoji} {clean_title} #FFCPLN #MAGA",
        f"{emoji} MUST SEE: {clean_title} #FFCPLN",
        f"{emoji} {clean_title} - 160 Songs! #FFCPLN",
        f"{emoji} VIRAL: {clean_title} #FFCPLN #MAGA",
    ]
    
    enhanced = random.choice(hooks)
    
    # Ensure under 100 chars
    if len(enhanced) > 100:
        enhanced = enhanced[:97] + "..."
    
    return enhanced


def enhance_description(original_desc: str) -> str:
    """
    Enhance existing description for SEO and algorithm optimization.

    Preserves original link if present, adds FFCPLN branding and hashtags.
    ENHANCED 2026-02-21: Added antifaFM.com and ICE victim names.

    Args:
        original_desc: Original video description

    Returns:
        Enhanced description with SEO optimization
    """
    # Select random ICE victims for personalization
    victims_sample = random.sample(ICE_VICTIMS, min(3, len(ICE_VICTIMS)))
    victims_str = ", ".join(victims_sample)

    # Build enhanced description with antifaFM.com
    enhanced = f"""🔥 FFCPLN: Fake F*** Christian Pedo-Lovin' Nazi Playlist 🔥

160+ anti-fascist songs exposing ICE cruelty & MAGA hypocrisy!

🎵 FULL PLAYLIST: https://antifaFM.com
📻 TUNE IN: https://antifaFM.com - Your source for Anti-Trump Gestapo Music!

🚨 Remember the victims: {victims_str}
#StopICE #ICEout #AbolishICE #ResistICE

#FFCPLN #MAGA #ICE #Antifascist #Resistance #TrumpFiles #Epstein #Music #Shorts #Viral

👆 SHARE if you care! Subscribe for more!"""

    return enhanced


# =============================================================================
# ICE NEWS LOOKUP - Dynamic Content Enhancement (2026-02-21)
# =============================================================================

# Recent ICE raid locations for dynamic title generation
ICE_RAID_LOCATIONS = [
    "Chicago", "Los Angeles", "Houston", "Phoenix", "Denver",
    "Atlanta", "New York", "Miami", "San Francisco", "Seattle",
    "Dallas", "Newark", "Boston", "Detroit", "Minneapolis",
]

# ICE news hooks for dynamic titles
ICE_NEWS_HOOKS = [
    "ICE Raids {location}!",
    "BREAKING: ICE in {location}!",
    "{location} Fights Back Against ICE!",
    "Resist ICE in {location}!",
    "{location} Says NO to ICE!",
    "ICE Terror in {location}!",
]


def get_ice_news_title_hook() -> str:
    """
    Generate dynamic ICE news hook for title.

    TODO: Connect to actual news API for real-time ICE raid news.
    For now uses rotating locations to keep content fresh.

    Returns:
        ICE news hook string (e.g., "ICE Raids Chicago!")
    """
    location = random.choice(ICE_RAID_LOCATIONS)
    hook = random.choice(ICE_NEWS_HOOKS)
    return hook.format(location=location)


def generate_ice_aware_title(original_title: str, include_news: bool = True) -> str:
    """
    Generate title with optional current ICE news context.

    Args:
        original_title: Original video title
        include_news: Whether to include ICE news hook (30% chance)

    Returns:
        Enhanced title with ICE news context
    """
    emoji = random.choice(EMOJI_PREFIXES)

    # 30% chance to include ICE news hook
    if include_news and random.random() < 0.3:
        news_hook = get_ice_news_title_hook()
        title = f"{emoji} {news_hook} #FFCPLN"
    else:
        # Regular FFCPLN title
        title = generate_clickbait_title(original_title=original_title)

    # Ensure under 100 chars
    if len(title) > 100:
        title = title[:97] + "..."

    return title


# =============================================================================
# CHANNEL-SPECIFIC CONTENT GENERATORS (2026-02-21)
# =============================================================================

# Channel content profiles
CHANNEL_PROFILES = {
    "move2japan": {
        "type": "ffcpln_music",
        "template": "ffcpln",
        "hashtags": ["#FFCPLN", "#MAGA", "#ICE", "#Resistance"],
        "include_ice_news": True,
        "include_victims": True,
    },
    "undaodu": {
        "type": "mindfulness_music",
        "template": "undaodu",
        "hashtags": ["#Mindfulness", "#Music", "#Meditation", "#Healing"],
        "include_ice_news": False,
        "include_victims": False,
    },
    "foundups": {
        "type": "tech_music",
        "template": "foundups",
        "hashtags": ["#FoundUps", "#StartupMusic", "#Tech", "#Innovation"],
        "include_ice_news": False,
        "include_victims": False,
    },
    "antifafm": {
        "type": "ffcpln_music",
        "template": "ffcpln",
        "hashtags": ["#FFCPLN", "#MAGA", "#Antifa", "#Resistance"],
        "include_ice_news": True,
        "include_victims": True,
    },
}

# NOTE: M2M descriptions are defined above (FOUNDUPS_DESCRIPTION, UNDAODU_DESCRIPTION)
# These channel-specific templates redirect to foundups.com for discoverability


def get_channel_description(channel_key: str) -> str:
    """
    Get channel-specific description template.

    Args:
        channel_key: Channel identifier (move2japan, undaodu, foundups, antifafm)

    Returns:
        Channel-appropriate description
    """
    channel_key = channel_key.lower()
    profile = CHANNEL_PROFILES.get(channel_key, CHANNEL_PROFILES["move2japan"])

    if profile["template"] == "undaodu":
        return UNDAODU_DESCRIPTION
    elif profile["template"] == "foundups":
        return FOUNDUPS_DESCRIPTION
    else:
        # FFCPLN channels (move2japan, antifafm)
        return get_standard_description("ffcpln")


def get_channel_title(channel_key: str, original_title: str) -> str:
    """
    Get channel-specific title generation.

    Args:
        channel_key: Channel identifier
        original_title: Original video title

    Returns:
        Channel-appropriate clickbait title
    """
    channel_key = channel_key.lower()
    profile = CHANNEL_PROFILES.get(channel_key, CHANNEL_PROFILES["move2japan"])

    if profile["include_ice_news"]:
        return generate_ice_aware_title(original_title, include_news=True)
    elif profile["template"] == "undaodu":
        # M2M discoverable title format
        hooks = [
            "Foundups.com imagine a world reimagined by AI",
            "Foundups.com mindfulness meets technology",
            "Foundups.com the path to digital balance",
        ]
        return f"{random.choice(hooks)} @UnDaoDu explains"
    elif profile["template"] == "foundups":
        # M2M discoverable title format
        hooks = [
            "Foundups.com imagine a world reimagined by AI",
            "Foundups.com where AI agents build startups",
            "Foundups.com pAVS autonomous venture system",
        ]
        return f"{random.choice(hooks)} @FoundUps"
    else:
        return generate_clickbait_title(original_title=original_title)

