"""
Comment Content Analyzer - Gemma-based Content Extraction for Contextual Replies

2025-12-30: Occam's Razor solution for contextual replies
Instead of template fallbacks, extract MEANING from comments BEFORE generation.

WSP References:
- WSP 77 (Agent Coordination): Gemma fast analysis
- WSP 96 (WRE Skills): Content extraction layer
- WSP 84 (Code Reuse): Follows gemma_validator.py pattern

Architecture:
1. Classification (existing) - WHO is this? (0✊/1✋/2🖐️)
2. Content Analysis (NEW) - WHAT are they saying?
3. Generation (existing) - Reply WITH context

Flow:
    Comment: "Obviously he was just saying what she wanted to hear, because the clip ended after that.."
                        ↓
    Content Analysis:
        topic: "video_content"
        sentiment: "skeptical"
        comment_type: "observation"
        key_point: "questioning authenticity of statement in clip"
        is_question: False
        engagement_hook: "clip timing"
                        ↓
    Contextual Reply: "Good eye on the clip timing! What do you think his real intention was? 🤔"
"""

import logging
import re
from typing import Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from modules.infrastructure.shared_utilities.local_model_selection import resolve_triage_model_path

logger = logging.getLogger(__name__)


@dataclass
class VideoContext:
    """
    Video-level context extracted from title/description.

    FIX (2025-12-30): Agent needs video context to understand commenter alignment.
    Without this, agent may dismiss comments that AGREE with video stance.

    Example:
        Video: "GOP on Gaza - 'I think we should kill them all.' Sickening."
        → stance: "anti_genocide"
        → topic: "Gaza, GOP, genocide"
        → critical_of: ["GOP", "genocide advocates"]
    """
    title: str  # Original video title
    stance: str  # pro/anti/neutral on main topic
    topic: str  # Main topic(s) covered
    critical_of: list  # Who/what the video criticizes
    supportive_of: list  # Who/what the video supports
    confidence: float


@dataclass
class ContentAnalysis:
    """
    Structured content analysis result.

    Used by reply generator to craft contextual responses.
    """
    topic: str  # What the comment is about (video_content, politics, personal, question, etc.)
    sentiment: str  # positive, negative, neutral, skeptical, supportive
    comment_type: str  # question, observation, opinion, statement, reaction
    key_point: str  # Main point/claim in the comment
    is_question: bool  # Does it ask something?
    engagement_hook: Optional[str]  # What to respond to (e.g., "clip timing", "his statement")
    confidence: float  # How confident is this analysis (0.0-1.0)
    # NEW (2025-12-30): Video alignment
    aligns_with_video: Optional[bool] = None  # True=agrees, False=disagrees, None=unknown
    alignment_reason: Optional[str] = None  # Why we think they align/disagree

    def to_prompt_context(self) -> str:
        """Convert analysis to prompt context for LLM generation."""
        alignment_str = ""
        if self.aligns_with_video is not None:
            if self.aligns_with_video:
                alignment_str = f"\n- VIDEO ALIGNMENT: AGREES with video stance ({self.alignment_reason})"
            else:
                alignment_str = f"\n- VIDEO ALIGNMENT: DISAGREES with video stance ({self.alignment_reason})"

        return f"""Comment Analysis:
- Topic: {self.topic}
- Sentiment: {self.sentiment}
- Type: {self.comment_type}
- Key Point: {self.key_point}
- Is Question: {self.is_question}
- Engagement Hook: {self.engagement_hook or 'general'}{alignment_str}"""


class CommentContentAnalyzer:
    """
    Gemma-based content analyzer for contextual reply generation.

    Extracts MEANING from comments so replies can address actual content
    instead of using generic templates.

    Speed Target: <100ms (Gemma 270M via llama_cpp)
    """

    # Topic keywords for rule-based fallback
    TOPIC_PATTERNS = {
        'video_content': ['clip', 'video', 'watch', 'see', 'show', 'scene', 'moment', 'part'],
        'politics': ['trump', 'biden', 'maga', 'democrat', 'republican', 'vote', 'election'],
        'personal': ['you', 'your', 'my', 'i think', 'i feel', 'i believe'],
        'question': ['?', 'what', 'how', 'why', 'when', 'where', 'who', 'can you'],
        'appreciation': ['thank', 'thanks', 'appreciate', 'love', 'great', 'amazing'],
    }

    # Sentiment indicators
    SENTIMENT_PATTERNS = {
        'positive': ['love', 'great', 'amazing', 'perfect', 'exactly', 'agree', 'yes', 'true'],
        'negative': ['hate', 'terrible', 'awful', 'wrong', 'bad', 'no', 'never', 'stupid'],
        'skeptical': ['obviously', 'clearly', 'doubt', 'question', 'wonder', 'seems', 'probably'],
        'supportive': ['support', 'with you', 'stand', 'fight', 'together', 'community'],
    }

    def __init__(self, model_path: Optional[Path] = None, use_gemma: bool = True):
        """
        Initialize content analyzer.

        Args:
            model_path: Path to Gemma GGUF model
            use_gemma: Whether to use Gemma LLM (False = rule-based only)
        """
        if model_path is None:
            model_path = resolve_triage_model_path()

        self.model_path = model_path
        self.use_gemma = use_gemma
        self.gemma_llm = None  # Lazy loaded

        logger.info(f"[CONTENT-ANALYZER] Initialized (use_gemma={use_gemma})")

    def _initialize_gemma(self) -> bool:
        """Initialize Gemma model (lazy loading)."""
        if self.gemma_llm is not None:
            return True

        if not self.use_gemma:
            return False

        try:
            from llama_cpp import Llama
            import os

            if not self.model_path.exists():
                logger.warning(f"[CONTENT-ANALYZER] Gemma model not found: {self.model_path}")
                return False

            logger.info(f"[CONTENT-ANALYZER] Loading Gemma from {self.model_path}")

            # Suppress llama.cpp noise
            old_stdout, old_stderr = os.dup(1), os.dup(2)
            devnull = os.open(os.devnull, os.O_WRONLY)

            try:
                os.dup2(devnull, 1)
                os.dup2(devnull, 2)

                self.gemma_llm = Llama(
                    model_path=str(self.model_path),
                    n_ctx=512,
                    n_threads=2,
                    n_gpu_layers=0,
                    verbose=False
                )
            finally:
                os.dup2(old_stdout, 1)
                os.dup2(old_stderr, 2)
                os.close(devnull)

            logger.info("[CONTENT-ANALYZER] Gemma loaded successfully")
            return True

        except Exception as e:
            logger.warning(f"[CONTENT-ANALYZER] Gemma init failed: {e}")
            return False

    def analyze(self, comment_text: str, author_name: str = "") -> ContentAnalysis:
        """
        Analyze comment content for contextual reply generation.

        Args:
            comment_text: The comment to analyze
            author_name: Comment author (optional context)

        Returns:
            ContentAnalysis with extracted meaning
        """
        if not comment_text or not comment_text.strip():
            return self._default_analysis()

        comment_lower = comment_text.lower().strip()

        # Try Gemma analysis first (if available)
        if self.use_gemma and self._initialize_gemma():
            try:
                return self._gemma_analyze(comment_text, author_name)
            except Exception as e:
                logger.warning(f"[CONTENT-ANALYZER] Gemma analysis failed, using rules: {e}")

        # Fallback to rule-based analysis
        return self._rule_based_analyze(comment_text, comment_lower)

    def _gemma_analyze(self, comment_text: str, author_name: str) -> ContentAnalysis:
        """
        Use Gemma for content analysis.

        Extracts: topic, sentiment, type, key point, engagement hook
        """
        prompt = f"""Analyze this YouTube comment briefly:

Comment: "{comment_text}"

Answer these in ONE WORD each:
1. Topic (video_content/politics/personal/question/appreciation/other):
2. Sentiment (positive/negative/neutral/skeptical/supportive):
3. Type (question/observation/opinion/statement/reaction):
4. Key point in 5 words or less:
5. What to respond to:

Answers:"""

        try:
            response = self.gemma_llm(
                prompt,
                max_tokens=100,
                temperature=0.3,
                stop=["\n\n", "Comment:"]
            )

            text = response['choices'][0]['text'].strip()
            logger.debug(f"[CONTENT-ANALYZER] Gemma response: {text}")

            # Parse Gemma output
            return self._parse_gemma_response(text, comment_text)

        except Exception as e:
            logger.warning(f"[CONTENT-ANALYZER] Gemma inference failed: {e}")
            return self._rule_based_analyze(comment_text, comment_text.lower())

    def _parse_gemma_response(self, gemma_text: str, comment_text: str) -> ContentAnalysis:
        """Parse Gemma's structured response."""
        lines = gemma_text.strip().split('\n')

        topic = "other"
        sentiment = "neutral"
        comment_type = "statement"
        key_point = ""
        engagement_hook = None

        for line in lines:
            line_lower = line.lower()
            if '1.' in line or 'topic' in line_lower:
                for t in ['video_content', 'politics', 'personal', 'question', 'appreciation']:
                    if t in line_lower:
                        topic = t
                        break
            elif '2.' in line or 'sentiment' in line_lower:
                for s in ['positive', 'negative', 'skeptical', 'supportive']:
                    if s in line_lower:
                        sentiment = s
                        break
            elif '3.' in line or 'type' in line_lower:
                for ct in ['question', 'observation', 'opinion', 'reaction']:
                    if ct in line_lower:
                        comment_type = ct
                        break
            elif '4.' in line or 'key' in line_lower:
                # Extract key point after colon
                if ':' in line:
                    key_point = line.split(':', 1)[1].strip()[:50]
            elif '5.' in line or 'respond' in line_lower:
                if ':' in line:
                    engagement_hook = line.split(':', 1)[1].strip()[:30]

        # Fallback key point extraction
        if not key_point:
            key_point = comment_text[:50].strip()

        is_question = '?' in comment_text

        return ContentAnalysis(
            topic=topic,
            sentiment=sentiment,
            comment_type=comment_type,
            key_point=key_point,
            is_question=is_question,
            engagement_hook=engagement_hook,
            confidence=0.7  # Gemma analysis
        )

    def _rule_based_analyze(self, comment_text: str, comment_lower: str) -> ContentAnalysis:
        """
        Fast rule-based content analysis.

        Uses pattern matching for topic/sentiment detection.
        """
        # Detect topic
        topic = "other"
        for topic_name, keywords in self.TOPIC_PATTERNS.items():
            if any(kw in comment_lower for kw in keywords):
                topic = topic_name
                break

        # Detect sentiment
        sentiment = "neutral"
        for sent_name, keywords in self.SENTIMENT_PATTERNS.items():
            if any(kw in comment_lower for kw in keywords):
                sentiment = sent_name
                break

        # Detect comment type
        is_question = '?' in comment_text
        if is_question:
            comment_type = "question"
        elif any(word in comment_lower for word in ['think', 'believe', 'feel', 'seems']):
            comment_type = "opinion"
        elif any(word in comment_lower for word in ['obviously', 'clearly', 'notice', 'see']):
            comment_type = "observation"
        else:
            comment_type = "statement"

        # Extract key point (first sentence or clause)
        key_point = comment_text.split('.')[0].strip()[:50]
        if not key_point:
            key_point = comment_text[:50].strip()

        # Find engagement hook (what to respond to)
        engagement_hook = None
        hook_patterns = [
            (r'because (.+?)(?:\.|$)', 'reason'),
            (r'that (.+?)(?:\.|$)', 'reference'),
            (r'(?:he|she|they) (.+?)(?:\.|$)', 'subject action'),  # Fixed: group he|she|they together
        ]
        for pattern, hook_type in hook_patterns:
            match = re.search(pattern, comment_lower)
            if match and match.group(1):  # Added None check
                engagement_hook = match.group(1)[:30]
                break

        logger.info(f"[CONTENT-ANALYZER] Rule-based: topic={topic}, sentiment={sentiment}, type={comment_type}")

        return ContentAnalysis(
            topic=topic,
            sentiment=sentiment,
            comment_type=comment_type,
            key_point=key_point,
            is_question=is_question,
            engagement_hook=engagement_hook,
            confidence=0.5  # Rule-based (lower confidence)
        )

    def analyze_video_context(self, video_title: str, video_description: str = "") -> VideoContext:
        """
        Extract video stance/topic from title and description.

        FIX (2025-12-30): Agent needs to understand video context to properly
        engage with commenters who AGREE vs DISAGREE with the video.

        Args:
            video_title: YouTube video title
            video_description: Optional video description

        Returns:
            VideoContext with stance, topic, and entities
        """
        if not video_title:
            return VideoContext(
                title="",
                stance="neutral",
                topic="unknown",
                critical_of=[],
                supportive_of=[],
                confidence=0.0
            )

        title_lower = video_title.lower()

        # Critical stance indicators (calling out bad actors)
        CRITICAL_INDICATORS = {
            'sickening': 'critical',
            'disgusting': 'critical',
            'horrifying': 'critical',
            'shameful': 'critical',
            'evil': 'critical',
            'criminal': 'critical',
            'genocide': 'anti_genocide',
            'kill them all': 'anti_genocide',
            'exterminate': 'anti_genocide',
            'fascist': 'anti_fascist',
            'nazi': 'anti_nazi',
            'racist': 'anti_racist',
            'maga': 'anti_maga',
            'trump': 'critical_of_trump',
        }

        # Extract stance
        stance = "neutral"
        critical_of = []
        supportive_of = []

        for indicator, detected_stance in CRITICAL_INDICATORS.items():
            if indicator in title_lower:
                stance = detected_stance
                break

        # Entity extraction (who is being discussed/criticized)
        ENTITIES = {
            'gop': 'GOP',
            'republican': 'Republicans',
            'democrat': 'Democrats',
            'trump': 'Trump',
            'biden': 'Biden',
            'netanyahu': 'Netanyahu',
            'israel': 'Israel',
            'palestine': 'Palestinians',
            'gaza': 'Gaza',
            'hamas': 'Hamas',
            'maga': 'MAGA',
        }

        for keyword, entity in ENTITIES.items():
            if keyword in title_lower:
                # If title is critical, these are being criticized
                if stance.startswith('anti_') or stance == 'critical':
                    critical_of.append(entity)
                else:
                    # Could be supportive or neutral mention
                    pass

        # Topic extraction
        # YTR1: Default to "general" not "politics" - reduces false MAGA_TROLL classification bias
        topic = "general"
        if 'gaza' in title_lower or 'palestine' in title_lower:
            topic = "Gaza/Palestine"
        elif 'israel' in title_lower:
            topic = "Israel"
        elif 'election' in title_lower or 'vote' in title_lower:
            topic = "elections"
        elif any(kw in title_lower for kw in ('trump', 'biden', 'democrat', 'republican', 'congress', 'senate')):
            topic = "politics"

        logger.info(f"[VIDEO-CONTEXT] Title: '{video_title[:50]}...'")
        logger.info(f"[VIDEO-CONTEXT]   Stance: {stance}, Topic: {topic}")
        logger.info(f"[VIDEO-CONTEXT]   Critical of: {critical_of}")

        return VideoContext(
            title=video_title,
            stance=stance,
            topic=topic,
            critical_of=critical_of,
            supportive_of=supportive_of,
            confidence=0.7 if stance != "neutral" else 0.3
        )

    def determine_alignment(
        self,
        video_context: VideoContext,
        content_analysis: ContentAnalysis,
        comment_text: str
    ) -> tuple:
        """
        Determine if commenter aligns with or opposes video stance.

        FIX (2025-12-30): This is CRITICAL for proper engagement.
        - Commenter who AGREES with video → Supportive reply, acknowledge their point
        - Commenter who DISAGREES → May need different engagement strategy

        Example:
            Video: "GOP on Gaza - 'I think we should kill them all.' Sickening."
            Comment: "He is as critical as Netanyahu and his criminal gangsters"
            Analysis:
              - Video criticizes genocide/GOP
              - Comment criticizes Netanyahu
              - Both are critical of those enabling violence
              → ALIGNMENT: AGREES

        Returns:
            (aligns: bool, reason: str)
        """
        if not video_context or not video_context.title:
            return (None, "no video context")

        comment_lower = comment_text.lower()

        # Check if commenter is criticizing same entities as video
        commenter_critical_of = []

        # Entity detection in comment
        CRITICAL_ENTITIES = {
            'netanyahu': 'Netanyahu',
            'criminal': 'criminality',
            'gangster': 'criminality',
            'genocide': 'genocide',
            'kill': 'violence',
            'murder': 'violence',
            'war crime': 'war crimes',
            'gop': 'GOP',
            'republican': 'Republicans',
            'trump': 'Trump',
            'maga': 'MAGA',
        }

        for keyword, entity in CRITICAL_ENTITIES.items():
            if keyword in comment_lower:
                commenter_critical_of.append(entity)

        # Check alignment
        # If video is anti-genocide and commenter criticizes genocide enablers → AGREES
        if video_context.stance in ('anti_genocide', 'critical'):
            # Commenter criticizes Netanyahu/war crimes/violence → AGREES with anti-genocide stance
            if any(e in commenter_critical_of for e in ['Netanyahu', 'criminality', 'genocide', 'war crimes', 'violence']):
                reason = f"both critical of {', '.join(commenter_critical_of)}"
                logger.info(f"[ALIGNMENT] ✅ AGREES: {reason}")
                return (True, reason)

            # Commenter defends those being criticized → DISAGREES
            # FIX (2025-12-30): Expanded patterns to catch dismissive sarcasm trolling
            # Example: "If you keep throwing out ridiculous statements" → dismisses genocide reporting
            DEFENSE_PATTERNS = [
                # Direct defense
                'nothing wrong', 'not that bad', 'innocent',
                # Dismissing as false
                'fake news', 'lies', 'propaganda', 'misinformation',
                # Dismissing as exaggerated
                'ridiculous', 'exaggerate', 'overreact', 'hysterical', 'drama',
                'blown out of proportion', 'making things up', 'nonsense',
                # Sarcasm used to dismiss (common troll tactic)
                'sarcastic response', 'deserve sarcasm', 'throwing out',
                # Deflection
                'both sides', 'what about', 'whatabout',
            ]
            if any(p in comment_lower for p in DEFENSE_PATTERNS):
                # Find which pattern matched for logging
                matched = next((p for p in DEFENSE_PATTERNS if p in comment_lower), "unknown")
                reason = f"defends those video criticizes (pattern: '{matched}')"
                logger.info(f"[ALIGNMENT] ❌ DISAGREES: {reason}")
                return (False, reason)

        # If video criticizes GOP/MAGA
        if 'GOP' in video_context.critical_of or 'MAGA' in video_context.critical_of:
            if any(e in commenter_critical_of for e in ['GOP', 'Republicans', 'MAGA', 'Trump']):
                reason = "both critical of GOP/MAGA"
                logger.info(f"[ALIGNMENT] ✅ AGREES: {reason}")
                return (True, reason)

        # Can't determine alignment
        logger.info(f"[ALIGNMENT] ❓ UNKNOWN: insufficient signals")
        return (None, "insufficient signals")

    def analyze_with_video_context(
        self,
        comment_text: str,
        author_name: str = "",
        video_title: str = "",
        video_description: str = ""
    ) -> ContentAnalysis:
        """
        Full analysis including video context alignment.

        This is the main entry point for contextual analysis.

        Args:
            comment_text: The comment to analyze
            author_name: Comment author
            video_title: Video title for context
            video_description: Video description for context

        Returns:
            ContentAnalysis with alignment information
        """
        # Step 1: Analyze comment content
        analysis = self.analyze(comment_text, author_name)

        # Step 2: If video context provided, determine alignment
        if video_title:
            video_context = self.analyze_video_context(video_title, video_description)
            aligns, reason = self.determine_alignment(video_context, analysis, comment_text)
            analysis.aligns_with_video = aligns
            analysis.alignment_reason = reason

            if aligns is True:
                logger.info(f"[CONTENT-ANALYZER] 🤝 Commenter AGREES with video: {reason}")
            elif aligns is False:
                logger.info(f"[CONTENT-ANALYZER] 🚫 Commenter DISAGREES with video: {reason}")

        return analysis

    def _default_analysis(self) -> ContentAnalysis:
        """Return default analysis for empty/invalid comments."""
        return ContentAnalysis(
            topic="other",
            sentiment="neutral",
            comment_type="statement",
            key_point="",
            is_question=False,
            engagement_hook=None,
            confidence=0.0
        )


# Singleton instance
_analyzer_instance = None


def get_content_analyzer() -> CommentContentAnalyzer:
    """Get singleton content analyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = CommentContentAnalyzer()
    return _analyzer_instance
