"""Regression contract for the quiet Red Dog conversation entry.

The account shell owns context, admission presentation and availability only.
The separate conversation client owns consent, transport and session state.
"""

from pathlib import Path


MEMBER_ROOT = Path(__file__).resolve().parents[1]
CONCIERGE_JS = MEMBER_ROOT / "js" / "account-concierge.js"
CONCIERGE_CSS = MEMBER_ROOT / "css" / "account-concierge.css"


def _js() -> str:
    return CONCIERGE_JS.read_text(encoding="utf-8")


def test_normal_mode_sheet_has_conversation_entry():
    content = _js()
    assert "{ id: 'conversation'" in content
    assert "case 'conversation':" in content
    assert "data-reddog-conversation-entry" in content


def test_entry_uses_actual_route_and_admission_context():
    content = _js()
    assert "window.mallVideoProjection.hostScope(window.location)" in content
    assert "document.body.getAttribute('data-foundup-id')" in content
    assert "new URLSearchParams(window.location.search).get('foundup')" not in content
    assert "/^[a-z0-9][a-z0-9_-]{0,79}$/" in content
    assert "productDiscovery && !discoveryAdmitted" in content
    assert "memberPresentationAdmitted ? 'member' : 'unknown'" in content
    assert "bindingRevision: conversationBindingRevision" in content


def test_guest_context_is_public_and_adapter_remains_available_to_guest():
    content = _js()
    assert "Public context only" in content
    assert "'getConversationContext', 'hasConversationEndpoint', 'registerConversationAdapter', 'openConversation'" in content
    assert "if (productDiscovery && !discoveryAdmitted) return;" in content
    assert content.index("injectConversationSurface();", content.index("openPlane = function")) < content.index(
        "if (productDiscovery && !discoveryAdmitted) return;", content.index("openPlane = function")
    )


def test_unregistered_or_unready_client_fails_closed():
    content = _js()
    assert "Conversation is not available on this page." in content
    assert "result.available !== true" in content
    assert "openButton.disabled = !availability.available" in content
    assert "if (!apiRoot) return Promise.resolve(null)" in content
    assert "conversationAdapter && getConversationAvailability(context).available" in content


def test_adapter_contract_passes_bounded_context_only():
    content = _js()
    assert "surface: publicScope ? 'public-video'" in content
    assert "foundupId: access === 'public' ? foundupId : null" in content
    assert "selectionState: selectionState" in content
    assert "bindingRevision: conversationBindingRevision" in content
    assert "conversationAdapter.open(context)" in content
    assert "clerkUser" not in content[content.index("function getConversationContext"):content.index("function getConversationAvailability")]


def test_conversation_entry_does_not_claim_listening_or_processing():
    content = _js()
    block = content[content.index("// ---- quiet conversation entry ----"):content.index("// ---- local swipe-up")]
    assert "startListening" not in block
    assert "setAnchorState" not in block
    assert "aria-live" not in block
    assert "thinking" not in block.lower()
    assert "fetch(" not in block


def test_existing_voice_action_remains_separate():
    content = _js()
    assert "case 'listen':" in content
    assert "if (!searchDictation || typeof searchDictation.start !== 'function') return false" in content
    assert "searchDictation.start(false)" in content
    assert "else startListening()" not in content


def test_endpoint_loader_is_host_admitted_and_same_origin():
    content = _js()
    assert 'meta[name="reddog-public-api-root"]' in content
    assert "url.origin !== window.location.origin" in content
    assert "path !== '/api/reddog/public'" in content
    assert "import('/js/reddog-public-client.js')" in content
    assert "if (!apiRoot) return" in content


def test_quiet_surface_has_scoped_styles():
    content = CONCIERGE_CSS.read_text(encoding="utf-8")
    assert ".reddog-conversation-entry" in content
    assert ".reddog-conversation-context" in content
    assert ".reddog-conversation-availability" in content
    assert ".reddog-conversation-open:disabled" in content
    assert ".reddog-guest-dialog" in content
    assert ".reddog-guest-dialog::backdrop" in content
    assert "calc(100vw - 1.5rem)" in content
