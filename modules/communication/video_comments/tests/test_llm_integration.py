"""Legacy public generation API now delegates to the shared reviewed owner.

Retires direct-provider/forced-template expectations. No service constructors,
credentials, network, browser or public effects belong in this selection.
"""
import inspect
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from modules.communication.video_comments.src.llm_comment_generator import LLMCommentGenerator


class TestLLMIntegration(unittest.TestCase):
    def setUp(self):
        self.calls, self.reviews = [], []
        self.text = 'The film details are at HornetHunter.com.'
        self.approval = {'approved': True}
        self.context = {'receiving_channel_id': 'creator', 'author_channel_id': 'viewer',
                        'video_id': 'film', 'video_title': 'Hornet film'}
        self.receipt = SimpleNamespace(text=self.text, source='openrouter', theme=None,
                                      context={'assessment': {'meaning': 'Asks where to watch'}})
        def generate(**kwargs):
            self.calls.append(kwargs)
            return self.receipt
        def review(data, text):
            self.reviews.append((data, text))
            return self.approval
        owner = SimpleNamespace(generate_reply_with_source=generate, inspect_reply=review)
        self.patch = patch.dict(sys.modules, {
            'modules.communication.video_comments.src.intelligent_reply_generator':
                SimpleNamespace(get_reply_generator=lambda: owner)})
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.generator = LLMCommentGenerator()

    def reply(self, **changes):
        return self.generator.generate_comment_response('Where is the film?', 'Aki', {**self.context, **changes})

    def test_provider_preference_cannot_construct_a_client(self):
        for provider in ('grok', 'xai', 'claude', 'gpt', None):
            generator = LLMCommentGenerator(provider=provider)
            self.assertEqual(generator.provider, 'ai_gateway')
            self.assertFalse(hasattr(generator, 'llm_connector'))
        self.assertEqual(self.calls, [])

    def test_complete_identity_delegates_to_semantic_owner(self):
        self.assertEqual(self.reply(), self.text)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0]['semantic_context']['text'], 'Where is the film?')

    def test_original_author_identity_is_preserved(self):
        self.reply()
        self.assertEqual((self.calls[0]['author_name'], self.calls[0]['author_channel_id']), ('Aki', 'viewer'))
        self.assertEqual(self.reviews[0][0]['channel_id'], 'viewer')

    def test_receiving_channel_is_not_the_author(self):
        self.reply()
        self.assertEqual(self.calls[0]['target_channel_id'], 'creator')
        self.assertEqual(self.reviews[0][0]['_target_channel_id'], 'creator')

    def test_exact_video_context_is_preserved(self):
        self.reply()
        self.assertEqual(self.calls[0]['semantic_context']['video_id'], 'film')
        self.assertEqual(self.calls[0]['video_title'], 'Hornet film')

    def test_missing_receiving_channel_blocks_before_generation(self):
        self.assertIsNone(self.reply(receiving_channel_id=None))
        self.assertEqual(self.calls, [])

    def test_missing_author_channel_blocks_before_generation(self):
        self.assertIsNone(self.reply(author_channel_id=''))
        self.assertEqual(self.calls, [])

    def test_missing_video_identity_blocks_before_generation(self):
        self.assertIsNone(self.reply(video_id=None))
        self.assertEqual(self.calls, [])

    def test_malformed_context_is_not_coerced(self):
        for context in (None, [], 'context'):
            self.assertIsNone(self.generator.generate_comment_response('Question', 'Aki', context))
        self.assertIsNone(self.reply(author_channel_id=123))
        self.assertEqual(self.calls, [])

    def test_empty_generation_never_uses_a_template(self):
        self.receipt.text = None
        self.assertIsNone(self.reply())
        self.assertEqual(self.reviews, [])

    def test_final_review_is_mandatory(self):
        self.approval = {'approved': False}
        self.assertIsNone(self.reply())
        self.assertEqual(len(self.reviews), 1)

    def test_review_approval_requires_exact_boolean(self):
        self.approval = {'approved': 1}
        self.assertIsNone(self.reply())

    def test_final_text_is_not_truncated_or_appended(self):
        self.receipt.text = 'Exact reviewed response. ' * 20
        self.assertEqual(self.reply(), self.receipt.text)
        self.assertEqual(self.reviews[0][1], self.receipt.text)

    def test_review_receives_theme_and_generation_context(self):
        self.receipt.theme = {'message': 'Private theme', 'source_command_id': 'command-1'}
        self.reply()
        self.assertEqual(self.reviews[0][0]['_reply_theme'], self.receipt.theme)
        self.assertEqual(self.reviews[0][0]['_generation_context'], self.receipt.context)

    def test_dialogue_without_original_context_returns_no_draft(self):
        self.assertIsNone(self.generator.generate_dialogue_response(SimpleNamespace(context={}), 'Question', 'Aki'))
        self.assertEqual(self.calls, [])

    def test_public_method_signatures_and_dialogue_delegate(self):
        self.assertEqual(list(inspect.signature(self.generator.generate_comment_response).parameters),
                         ['comment_text', 'author', 'context'])
        self.assertEqual(list(inspect.signature(self.generator.generate_dialogue_response).parameters),
                         ['thread', 'text', 'author'])
        thread = SimpleNamespace(context=self.context)
        self.assertEqual(self.generator.generate_dialogue_response(thread, 'Where is the film?', 'Aki'), self.text)
