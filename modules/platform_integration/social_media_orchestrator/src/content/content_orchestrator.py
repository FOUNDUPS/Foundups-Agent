"""
Content Orchestrator - Cross-platform content formatting and optimization
WSP Compliance: WSP 3, WSP 49
"""

import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime


class ContentOrchestrator:
    """
    Content generation and cross-platform formatting service
    
    Handles content optimization for different social media platforms,
    including character limits, hashtag optimization, and format conversion.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Content Orchestrator
        
        Args:
            config: Configuration for content processing
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Platform-specific limits and rules
        self.platform_limits = {
            'twitter': {
                'max_length': 280,
                'max_hashtags': 2,  # Recommended for engagement
                'supports_markdown': False,
                'supports_mentions': True,
                'mention_prefix': '@',
                'hashtag_prefix': '#'
            },
            'linkedin': {
                'max_length': 3000,
                'max_hashtags': 5,
                'supports_markdown': True,
                'supports_mentions': True,
                'mention_prefix': '@',
                'hashtag_prefix': '#'
            }
        }

        
    def format_for_platform(self, content: str, platform: str, options: Dict[str, Any] = None) -> str:
        """
        Format content for a specific platform
        
        Args:
            content: Original content text
            platform: Target platform identifier
            options: Platform-specific formatting options
            
        Returns:
            str: Formatted content optimized for the platform
        """
        options = options or {}
        
        if platform not in self.platform_limits:
            self.logger.warning(f"Unknown platform: {platform}, using original content")
            return content
            
        platform_config = self.platform_limits[platform]
        formatted_content = content
        
        # Apply platform-specific formatting
        if platform == 'twitter':
            formatted_content = self._format_for_twitter(content, options, platform_config)
        elif platform == 'linkedin':
            formatted_content = self._format_for_linkedin(content, options, platform_config)
            
        # Apply general formatting
        formatted_content = self._apply_general_formatting(formatted_content, platform_config, options)
        
        # Final length check and truncation if needed
        formatted_content = self._ensure_length_limit(formatted_content, platform_config)
        
        self.logger.debug(f"Formatted content for {platform}: {len(formatted_content)} chars")
        return formatted_content
        
    def _format_for_twitter(self, content: str, options: Dict[str, Any], platform_config: Dict[str, Any]) -> str:
        """Format content specifically for Twitter/X"""
        formatted = content
        
        # Convert markdown links to plain text for Twitter
        if not platform_config['supports_markdown']:
            formatted = self._strip_markdown(formatted)
            
        # Optimize hashtags for Twitter (fewer is better)
        hashtags = options.get('hashtags', [])
        if hashtags:
            # Limit hashtags for Twitter
            limited_hashtags = hashtags[:platform_config['max_hashtags']]
            hashtag_text = ' ' + ' '.join(f"#{tag.strip('#')}" for tag in limited_hashtags)
            formatted += hashtag_text
            
        # Add mentions if provided
        mentions = options.get('mentions', [])
        if mentions:
            mention_text = ' ' + ' '.join(f"@{mention.strip('@')}" for mention in mentions[:2])  # Limit mentions
            formatted += mention_text
            
        return formatted
        
    def _format_for_linkedin(self, content: str, options: Dict[str, Any], platform_config: Dict[str, Any]) -> str:
        """Format content specifically for LinkedIn"""
        formatted = content
        
        # LinkedIn supports longer content and more professional formatting
        
        # Add hashtags (LinkedIn allows more)
        hashtags = options.get('hashtags', [])
        if hashtags:
            hashtag_text = '\n\n' + ' '.join(f"#{tag.strip('#')}" for tag in hashtags[:platform_config['max_hashtags']])
            formatted += hashtag_text
            
        # Add mentions
        mentions = options.get('mentions', [])
        if mentions:
            mention_text = '\n' + ' '.join(f"@{mention.strip('@')}" for mention in mentions)
            formatted += mention_text
            
        # Add professional sign-off if configured
        if options.get('add_signature', False):
            signature = options.get('signature', '\n\n#FoundUps #Development #Innovation')
            formatted += signature
            
        return formatted
        
    def _apply_general_formatting(self, content: str, platform_config: Dict[str, Any], options: Dict[str, Any]) -> str:
        """Apply general formatting rules"""
        formatted = content
        
        # Clean up extra whitespace
        formatted = re.sub(r'\n{3,}', '\n\n', formatted)  # Max 2 consecutive newlines
        formatted = re.sub(r' {2,}', ' ', formatted)  # Remove extra spaces
        formatted = formatted.strip()
        
        # Add timestamp if requested
        if options.get('add_timestamp', False):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            formatted += f"\n\nPosted: {timestamp}"
            
        return formatted
        
    def _strip_markdown(self, content: str) -> str:
        """Remove markdown formatting for platforms that don't support it"""
        # Remove markdown links [text](url) -> text (url)
        content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', content)
        
        # Remove bold/italic markers
        content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)  # **bold**
        content = re.sub(r'\*([^*]+)\*', r'\1', content)      # *italic*
        content = re.sub(r'__([^_]+)__', r'\1', content)      # __bold__
        content = re.sub(r'_([^_]+)_', r'\1', content)        # _italic_
        
        # Remove code formatting
        content = re.sub(r'`([^`]+)`', r'\1', content)        # `code`
        
        return content
        
    def _ensure_length_limit(self, content: str, platform_config: Dict[str, Any]) -> str:
        """Ensure content doesn't exceed platform length limits"""
        max_length = platform_config['max_length']
        
        if len(content) <= max_length:
            return content
            
        # Need to truncate - preserve hashtags and mentions at the end if possible
        hashtag_match = re.search(r'(\s#\w+(?:\s#\w+)*)\s*$', content)
        mention_match = re.search(r'(\s@\w+(?:\s@\w+)*)\s*$', content)
        
        suffix = ''
        if hashtag_match:
            suffix = hashtag_match.group(1)
            content = content[:hashtag_match.start()]
            
        if mention_match and mention_match.start() > (hashtag_match.start() if hashtag_match else 0):
            suffix = mention_match.group(1) + suffix
            content = content[:mention_match.start()]
            
        # Calculate available space
        available_length = max_length - len(suffix) - 3  # 3 for "..."
        
        if available_length > 0:
            truncated = content[:available_length].rsplit(' ', 1)[0]  # Break at word boundary
            return truncated + "..." + suffix
        else:
            # Suffix too long, just truncate everything
            return content[:max_length-3] + "..."
            
    def analyze_content(self, content: str) -> Dict[str, Any]:
        """
        Analyze content for optimization recommendations
        
        Args:
            content: Content to analyze
            
        Returns:
            Dict[str, Any]: Analysis results and recommendations
        """
        analysis = {
            'length': len(content),
            'word_count': len(content.split()),
            'hashtags': len(re.findall(r'#\w+', content)),
            'mentions': len(re.findall(r'@\w+', content)),
            'links': len(re.findall(r'https?://\S+', content)),
            'recommendations': []
        }
        
        # Platform-specific recommendations
        for platform, config in self.platform_limits.items():
            platform_analysis = {
                'platform': platform,
                'fits_limit': analysis['length'] <= config['max_length'],
                'recommended_hashtags': min(analysis['hashtags'], config['max_hashtags']),
                'would_truncate': analysis['length'] > config['max_length']
            }
            
            if platform_analysis['would_truncate']:
                excess = analysis['length'] - config['max_length']
                analysis['recommendations'].append(
                    f"Content is {excess} characters too long for {platform}"
                )
                
        return analysis
        
    def optimize_hashtags(self, hashtags: List[str], platform: str) -> List[str]:
        """
        Optimize hashtags for a specific platform
        
        Args:
            hashtags: List of hashtag strings
            platform: Target platform
            
        Returns:
            List[str]: Optimized hashtag list
        """
        if platform not in self.platform_limits:
            return hashtags
            
        max_hashtags = self.platform_limits[platform]['max_hashtags']
        
        # Clean hashtags (remove # if present, then re-add)
        cleaned = [tag.strip().lstrip('#') for tag in hashtags if tag.strip()]
        
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for tag in cleaned:
            tag_lower = tag.lower()
            if tag_lower not in seen:
                seen.add(tag_lower)
                unique.append(tag)
                
        # Limit to platform maximum
        optimized = unique[:max_hashtags]
        
        # Convert back to hashtag format
        return [f"#{tag}" for tag in optimized]
        
    def suggest_content_improvements(self, content: str, platform: str) -> List[str]:
        """
        Suggest improvements for content optimization
        
        Args:
            content: Content to improve
            platform: Target platform
            
        Returns:
            List[str]: List of improvement suggestions
        """
        suggestions = []
        analysis = self.analyze_content(content)
        
        if platform not in self.platform_limits:
            return ["Unknown platform - cannot provide specific suggestions"]
            
        config = self.platform_limits[platform]
        
        # Length suggestions
        if analysis['length'] > config['max_length']:
            suggestions.append(f"Content is too long for {platform}. Consider shortening by {analysis['length'] - config['max_length']} characters.")
        elif analysis['length'] < config['max_length'] * 0.3:
            suggestions.append(f"Content is quite short for {platform}. You could add more detail.")
            
        # Hashtag suggestions
        if analysis['hashtags'] == 0:
            suggestions.append(f"Consider adding hashtags to increase discoverability on {platform}.")
        elif analysis['hashtags'] > config['max_hashtags']:
            suggestions.append(f"Too many hashtags for {platform}. Recommended maximum: {config['max_hashtags']}")
            
        # Platform-specific suggestions
        if platform == 'twitter':
            if analysis['word_count'] > 40:
                suggestions.append("Twitter performs better with concise content. Consider shortening.")
                
        elif platform == 'linkedin':
            if analysis['word_count'] < 25:
                suggestions.append("LinkedIn content performs better with more detailed posts.")
            if not any(word.startswith('#') for word in content.split()):
                suggestions.append("LinkedIn posts benefit from relevant industry hashtags.")
                
        return suggestions


def prepare_campaign(brief: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare source-backed drafts/calendar; never schedule or publish."""
    from .campaign_planner import prepare_content_campaign

    return prepare_content_campaign(brief, ContentOrchestrator({}).platform_limits)
