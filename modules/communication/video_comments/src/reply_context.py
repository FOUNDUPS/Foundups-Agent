"""Pure reply prompt/personality assembly; no model, provider, or memory effects."""

import logging

logger = logging.getLogger(__name__)


CHANNEL_PERSONALITIES = {
    'UC-LSSlOZwpGIRIYihaz8zCw': {  # Move2Japan
        'name': 'Move2Japan',
        'style': 'Political commentary, MAGA mockery',
        'themes': ['democracy', 'justice', 'anti-fascism', 'MAGA trolling'],
        'tone': 'sharp, witty, confrontational',
        'maga_response': 'aggressive',  # Full MAGA mockery
        'regular_response': 'political_banter'
    },
    'UCfHM9Fw9HD-NwiS0seD_oIA': {  # UnDaoDu
        'name': 'UnDaoDu',
        'style': 'AI consciousness, 0102 entanglement',
        'themes': ['AI', 'Bell-State', 'AGI', '0102→0201', 'quantum neural networks'],
        'tone': 'sharp, witty, scientific',
        'maga_response': 'soft_redirect',  # Gentle dismissal
        'regular_response': 'consciousness_banter'
    },
    'UCSNTUXjAgpd4sgWYP0xoJgw': {  # FoundUps
        'name': 'FoundUps',
        'style': 'pAVS ecosystem, AI-human collaboration, decentralized ventures',
        'themes': ['pAVS', 'AI agents', 'startup', 'UPS tokens', 'CABR engine', 'decentralization'],
        'tone': 'visionary, encouraging, practical, educational',
        'maga_response': 'soft_redirect',  # Off-topic redirect
        'regular_response': 'startup_banter',
        # Litepaper context for intelligent replies (2026-02-25)
        'context_docs': ['litepaper'],
        'key_concepts': {
            'pAVS': 'Peer-to-Peer Autonomous Venture System - where AI agents and humans build ventures together',
            'UPS': 'Universal Participation Stake - backed 1:1 by Bitcoin (Hotel California: BTC enters, never exits)',
            'CABR': 'Compute-Adjusted Benefit Ratio - the V3 validation engine for fair work distribution',
            'F_i': 'FoundUp tokens - each venture has its own token backed by UPS',
            'Du': 'Dedicated User stakers - committed participants who stake long-term',
        },
        'promo_url': 'foundups.com/litepaper',
    },
    'UCVSmg5aOhP4tnQ9KFUg97qA': {  # antifaFM (formerly RavingANTIFA)
        'name': 'antifaFM',
        'style': 'Political music, anti-fascist resistance, FFCPLN playlist',
        'themes': ['FFCPLN', 'anti-fascism', 'resistance', 'music', 'ICE accountability'],
        'tone': 'sharp, witty, confrontational, musical',
        'maga_response': 'aggressive',  # Full mockery
        'regular_response': 'political_music_banter',
        'promo_url': 'antifafm.com',
    },
}


def select_channel_personality(target_channel_id, theme):
    channel_personality = CHANNEL_PERSONALITIES.get(target_channel_id)
    if channel_personality:
        logger.info(f"[REPLY-GEN] Using {channel_personality['name']} personality: {channel_personality['style']}")
        # Override theme based on channel
        if theme == "default":
            theme = channel_personality['themes'][0]
    else:
        logger.debug(f"[REPLY-GEN] Unknown channel {target_channel_id} - using default personality")
        channel_personality = {
            'name': 'Default',
            'style': 'Generic engagement',
            'maga_response': 'aggressive',
            'regular_response': 'political_banter'
        }
    return channel_personality, theme


def _base_prompt(comment_text, author_name, custom_prompt, tier):
    if author_name and author_name.lower() != "unknown":
        comment_prompt = f'Comment from @{author_name}: "{comment_text}"'
    else:
        comment_prompt = f'Comment: "{comment_text}"'

    # Custom guidance augments the real comment; it must never replace it.
    if custom_prompt:
        user_prompt = f"{comment_prompt}\n\nRESPONSE GUIDANCE:\n{custom_prompt}"
        logger.info("[ANTI-REGURGITATION] Using custom semantic variation prompt")
    elif tier == 0:
        # TIER 0 (MAGA_TROLL): Mockery with #FFCPLN hashtag
        user_prompt = f'''{comment_prompt}

Generate a sarcastic, mocking reply that dismisses this troll comment. Style: witty mockery, not hostile.
- Reference: "besties for 15 years think he didnt know it" (if relevant to trust/betrayal themes)
- MUST include #FFCPLN hashtag somewhere naturally
- Keep it short (1-2 sentences)
- Be dismissive but clever
- Do NOT start with @mentions

Examples of tone:
- "Ok buddy, sure 👍 #FFCPLN"
- "15 years of friendship and you think he didn't see it coming? #FFCPLN"
- "That's... certainly a take. #FFCPLN"'''
        logger.info("[TIER-0] Using MAGA mockery prompt with #FFCPLN")
    elif tier == 2:
        # TIER 2 (MODERATOR): Context first; status affects tone, not subject matter.
        user_prompt = f'''{comment_prompt}

Generate a warm, concise reply for a trusted community member.
- Address the actual point they made before acknowledging their support.
- Do not invent moderation activity, history, or contributions.
- Do not force #FFCPLN, a playlist, or a promotion unless their comment or the video context makes it relevant.
- Keep it short (1-2 sentences).
- Do NOT start with @mentions.'''
        logger.info("[TIER-2] Using context-first trusted-community prompt")
    else:
        # TIER 1 (REGULAR): Standard contextual reply
        user_prompt = f'{comment_prompt}\n\nGenerate a friendly, short reply (1-2 sentences). Do NOT start with @mentions:'
    return user_prompt


def _analysis_prompt(analysis):
    # Build alignment guidance (CRITICAL for proper engagement)
    alignment_guidance = ""
    if analysis.aligns_with_video is True:
        alignment_guidance = f"""

🤝 VIDEO ALIGNMENT: AGREES
The commenter AGREES with the video's stance ({analysis.alignment_reason}).
RESPONSE STRATEGY: VALIDATE their point. Acknowledge you're on the same side.
- YES: "100% - calling it what it is", "Exactly right", "Spot on observation"
- NO: Do NOT dismiss, correct, or redirect them. They're an ally."""
    elif analysis.aligns_with_video is False:
        alignment_guidance = f"""

🚫 VIDEO ALIGNMENT: DISAGREES
The commenter DISAGREES with the video's stance ({analysis.alignment_reason}).
RESPONSE STRATEGY: Challenge respectfully or redirect.
- Options: Fact-check, gentle push-back, or redirect to video content"""

    return f"""

COMMENT ANALYSIS (use this to craft a relevant response):
- Topic: {analysis.topic}
- Sentiment: {analysis.sentiment}
- Type: {analysis.comment_type}
- Key Point: {analysis.key_point}
- Engagement Hook: {analysis.engagement_hook or 'respond to their main point'}{alignment_guidance}

IMPORTANT: Your reply MUST address their {analysis.comment_type} about "{analysis.key_point[:30]}". Do NOT use generic phrases like "thanks for watching" or "holding it down" - respond to what they ACTUALLY said.

OUTPUT FORMAT: Reply with ONLY the reply text. Do NOT include:
- Explanations (e.g., "This reply addresses...")
- Notes (e.g., "Note: This comment...")
- Reasoning (e.g., "This is relevant because...")
- Multiple options or alternatives
Just output the actual reply text, nothing else."""


def build_grounded_prompt(comment_text, author_name, custom_prompt, tier, video_title,
                          context, voice_context, analysis):
    """Assemble existing guidance without replacing the comment or inventing memory."""
    user_prompt = _base_prompt(comment_text, author_name, custom_prompt, tier)
    if video_title:
        user_prompt += (
            "\n\nVIDEO CONTEXT (ground the reply in this exact video):"
            f'\n- Title: "{video_title}"'
        )

    if context:
        user_prompt += f"\n\nCOMMENTER CONTEXT (personalize carefully):\n{context}"

    if voice_context:
        user_prompt += f"\n\n012's VERIFIED MEMORY (use ONLY this for personal claims):\n{voice_context}"
    if analysis:
        user_prompt += _analysis_prompt(analysis)
    # CRITICAL FIX (2026-02-21): OUTPUT FORMAT must ALWAYS be added, not just when content_analysis exists
    # This prevents LLM from outputting explanations like "Note: This comment..." in replies
    if "OUTPUT FORMAT:" not in user_prompt:
        user_prompt += """

OUTPUT FORMAT: Reply with ONLY the reply text. Do NOT include:
- Explanations (e.g., "This reply addresses...")
- Notes (e.g., "Note: This comment...")
- Reasoning (e.g., "This is relevant because...")
- Multiple options or alternatives
- Brackets or parentheses with commentary
Just output the actual reply text, nothing else."""
        logger.info("[LLM-CHAIN] 📝 OUTPUT FORMAT instructions added to prompt")
    return user_prompt
