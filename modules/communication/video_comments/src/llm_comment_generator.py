"""Legacy comment-generation API delegating to the existing reviewed owner.

Provider arguments are retired. Missing original identity/context produces no
draft. This adapter grants no nested-reply or publication authority.
"""
import logging

logger = logging.getLogger(__name__)


class LLMCommentGenerator:
    def __init__(self, provider=None):
        self.provider = 'ai_gateway'

    def generate_comment_response(self, comment_text, author, context):
        if not isinstance(context, dict):
            return None
        receiving = context.get('receiving_channel_id')
        author_channel = context.get('author_channel_id')
        if any(not isinstance(value, str) or not value.strip() for value in (
                receiving, author_channel, context.get('video_id'), comment_text, author)):
            return None
        from modules.communication.video_comments.src.intelligent_reply_generator import get_reply_generator
        generator = get_reply_generator()
        data = {'text': comment_text, 'author_name': author, 'channel_id': author_channel,
                'receiving_channel_id': receiving, 'video_id': context['video_id'],
                'video_title': context.get('video_title')}
        result = generator.generate_reply_with_source(
            comment_text=comment_text, author_name=author, author_channel_id=author_channel,
            target_channel_id=receiving, video_title=data['video_title'], semantic_context=data)
        if not result.text:
            return None
        review = generator.inspect_reply({**data, '_target_channel_id': receiving,
            '_generation_context': result.context, '_reply_theme': result.theme}, result.text)
        return result.text if review.get('approved') is True else None

    def generate_dialogue_response(self, thread, text, author):
        return self.generate_comment_response(text, author, getattr(thread, 'context', {}) or {})
