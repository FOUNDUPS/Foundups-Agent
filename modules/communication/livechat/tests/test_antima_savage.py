"""Political names do not grant unreviewed provider replies or forced slogans."""
from types import SimpleNamespace
from modules.communication.livechat.src.llm_integration import GrokIntegration, ModelReplyRequest


def test_savage_responses():
    calls = []
    generator = SimpleNamespace(channel_id='creator', stream_title='Film discussion',
                                generate_reply=lambda *args, **kwargs: calls.append(True))
    for username in ('AntiMa_Patriot', 'MAGA_Truth', 'TrumpWon2020'):
        history = {username: [{'username': username, 'author_id': 'viewer',
                              'message': 'Was that a quotation or your own view?'}]}
        request = GrokIntegration(generator, history).targeted_response(username, 'OWNER', '')
        assert isinstance(request, ModelReplyRequest) and calls == []
        assert request.username == username and request.role == 'USER'
        assert 'civil response to the actual meaning' in request.message
        assert '#AntiMa' not in request.message
    assert GrokIntegration(generator, {}).fact_check('MAGA_Truth', 'MOD', '') is None
