"""Legacy fact-check adapter now queues shared reviewed language work."""
from types import SimpleNamespace
from modules.communication.livechat.src.llm_integration import GrokIntegration, ModelReplyRequest


def test_factcheck_with_fallacy():
    calls = []
    generator = SimpleNamespace(channel_id='creator', stream_title='Film discussion',
                                generate_reply=lambda *args, **kwargs: calls.append(True))
    history = {'display-name': [{'username': 'Aki', 'author_id': 'viewer',
                                'message': 'I did not say all borders should be open.'}]}
    request = GrokIntegration(generator, history).fact_check('Aki', 'MOD', '')
    assert isinstance(request, ModelReplyRequest) and calls == []
    assert request.user_id == 'viewer' and request.role == 'USER'
    assert 'I did not say all borders should be open.' in request.message
    assert 'Do not invent a truthfulness score' in request.message
    assert request.receiving_channel_id == 'creator' and request.stream_title == 'Film discussion'
