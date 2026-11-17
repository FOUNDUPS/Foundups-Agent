"""YouTube consumer of the shared Gateway and verified model-routing owners.

The configured local general role is the existing incumbent. Dynamic replacement
requires the existing signed production binding, reverified at each call. Catalog
discovery and Nemotron shadow proposals never grant production authority here.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
import logging
import os
from pathlib import Path
import time

logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[4]
STAGES = frozenset({'assess', 'write', 'review'})
SURFACES = frozenset({'comments', 'livechat'})
VERIFIER_FIELDS = (
    'CATALOG_SNAPSHOT_PATH', 'BENCHMARK_EVIDENCE_RECEIPTS_PATH',
    'PROMOTION_EVIDENCE_RECEIPTS_PATH', 'PRODUCTION_EVIDENCE_BUNDLE_PATH',
    'RUNTIME_BINDING_POLICY_PATH', 'EVIDENCE_TRUSTED_KEYS_PATH',
)


@dataclass(frozen=True)
class YouTubeModelResult:
    response: str = field(default='', repr=False)
    provider: str = 'none'
    model: str = ''
    success: bool = False
    route_id: str | None = None
    reason: str | None = None


def _cancelled(event):
    return event is not None and event.is_set()


def _general_language_model(model):
    from modules.infrastructure.shared_utilities.local_model_selection import is_general_language_model
    return is_general_language_model(model)


def _binding_environment(stage, surface):
    """Only explicit path configuration crosses into the existing verifier."""
    prefix = f'YT_MODEL_{surface.upper()}_{stage.upper()}'
    binding = os.getenv(prefix + '_BINDING_PATH') or os.getenv('YT_MODEL_RUNTIME_BINDING_RECEIPT_PATH', '')
    selection = os.getenv(prefix + '_SELECTION_PATH') or os.getenv('YT_MODEL_SELECTION_RECEIPT_PATH', '')
    env = {
        'REDDOG_RESIDENT_MODEL_RUNTIME_BINDING_ROOT': os.getenv('YT_MODEL_ROUTING_ROOT', ''),
        'REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_RECEIPT_PATH': binding,
        'REDDOG_MODEL_SELECTION_RECEIPT_PATH': selection,
        'REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS': 'lm_studio_local,openrouter',
    }
    for suffix in VERIFIER_FIELDS:
        env['REDDOG_MODEL_' + suffix] = os.getenv('YT_MODEL_' + suffix, '')
    configured = any(value for key, value in env.items() if key != 'REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS')
    return env, configured


def _resolve_binding(env, surface):
    from modules.communication.moltbot_bridge.src.reddog_model_runtime_binding_query import query_model_runtime_binding
    receipt = query_model_runtime_binding(
        repo_root=REPO_ROOT, environ=env, expected_surface='youtube_' + surface)
    if (receipt.accepted is not True or receipt.task_family != 'youtube_reply'
            or len(receipt.role_bindings) != 1
            or receipt.role_bindings[0].get('role') != 'principal'
            or receipt.panel_models):
        raise ValueError('youtube_model_binding_unavailable')
    endpoint = receipt.role_bindings[0]
    provider, model = endpoint['provider'], endpoint['model_id']
    if provider not in {'lm_studio_local', 'openrouter'} or not _general_language_model(model):
        raise ValueError('youtube_model_route_disallowed')
    if not receipt.topology_valid_until or time.time() >= receipt.topology_valid_until:
        raise ValueError('youtube_model_binding_expired')
    return provider, model, receipt.binding_receipt_id, receipt.topology_valid_until


def _incumbent_model():
    from modules.infrastructure.shared_utilities.local_model_selection import resolve_model_selection
    selection = resolve_model_selection('general')
    if not selection.exists or not _general_language_model(selection.path.name):
        raise ValueError('youtube_general_role_unavailable')
    role_name = selection.path.name.lower().replace('_', '-').replace('.gguf', '').split('-q')[0]
    model = os.getenv('LM_STUDIO_MODEL') or role_name
    selected = model.lower().replace('_', '-')
    if not _general_language_model(model) or not (selected == role_name or selected.endswith('/' + role_name)):
        raise ValueError('youtube_general_role_mismatch')
    # The native inventory key can differ from the OpenAI-compatible display ID.
    # Reuse the existing operator-selected General key; never apply it to signed routes.
    native_key = os.getenv('LM_STUDIO_NATIVE_MODEL_KEY')
    if native_key:
        if not _general_language_model(native_key):
            raise ValueError('youtube_native_general_role_mismatch')
        return native_key
    return model


def _guard_payload(payload):
    """Reuse the existing approval-only Fusion guard; never silently rewrite."""
    from .model_autoresearch_canonical_prompt_guard import build_canonical_local_autoresearch_prompt_guard
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    approval = build_canonical_local_autoresearch_prompt_guard()(
        prompt=text, task_id='youtube_reply', source_prompt_digest='')
    if approval.passed is not True or approval.prompt != text:
        raise ValueError('youtube_model_prompt_blocked')


def _require_current(deadline, cancel_event):
    if _cancelled(cancel_event) or (deadline is not None and time.time() >= deadline):
        raise ValueError('youtube_model_route_no_longer_current')


def _local_call(model, payload, deadline=None, cancel_event=None):
    from modules.infrastructure.shared_utilities.local_llm_backends import LMStudioBackend
    backend = LMStudioBackend(
        model_id=model, base_url=os.getenv('LM_STUDIO_BASE_URL', 'http://127.0.0.1:1234/v1'),
        request_timeout=3, api_token=os.getenv('LM_API_TOKEN') or None,
        max_retries=0, pre_dispatch_check=lambda: _require_current(deadline, cancel_event))
    if not backend.initialize():
        raise ValueError('youtube_local_model_not_resident')
    _require_current(deadline, cancel_event)
    controls = {'response_format': payload['response_format']} if 'response_format' in payload else {}
    response = backend.create_chat_completion(
        messages=payload['messages'], max_tokens=payload['max_tokens'],
        temperature=payload['temperature'], enable_thinking=False, reasoning_effort='none', **controls)
    return response['choices'][0]['message']['content']


def _openrouter_call(gateway, model, payload, deadline=None, cancel_event=None):
    from .ai_gateway import _post_openai_request
    config = gateway.providers.get('openrouter')
    if config is None or not config.api_key:
        raise ValueError('youtube_openrouter_unavailable')
    # Exact approved model only; no router alias, paid fallback, or provider data collection.
    if model.startswith('openrouter/') or model == 'moonshotai/kimi-k3':
        raise ValueError('youtube_unpinned_router_alias')
    wire = {**payload, 'model': model, 'provider': {
        'data_collection': 'deny', 'allow_fallbacks': False,
        'max_price': {'prompt': 0, 'completion': 0},
    }}
    _guard_payload(wire)
    _require_current(deadline, cancel_event)
    response = _post_openai_request(
        replace(config, timeout=3),
        {'Authorization': 'Bearer ' + config.api_key, 'Content-Type': 'application/json'}, wire)
    result = response.json()
    if result.get('model') != model:
        raise ValueError('youtube_model_response_route_mismatch')
    return result['choices'][0]['message']['content']


def call_youtube_task(gateway, *, system_prompt, prompt, stage, surface='comments',
                      max_tokens=400, response_format=None, cancel_event=None):
    """One admitted call, no provider fallback and no publishing authority."""
    if (not isinstance(stage, str) or not isinstance(surface, str)
            or stage not in STAGES or surface not in SURFACES or type(max_tokens) is not int
            or not 1 <= max_tokens <= 2048 or not isinstance(system_prompt, str)
            or not isinstance(prompt, str)):
        return YouTubeModelResult(reason='invalid_task')
    if _cancelled(cancel_event):
        return YouTubeModelResult(reason='cancelled')
    payload = {'messages': [{'role': 'system', 'content': system_prompt},
                            {'role': 'user', 'content': prompt}],
               'max_tokens': max_tokens, 'temperature': 0.4 if stage == 'write' else 0}
    if response_format is not None:
        payload['response_format'] = response_format
    try:
        if len(json.dumps(payload, ensure_ascii=False).encode('utf-8')) > 65_536:
            return YouTubeModelResult(reason='prompt_too_large')
        env, configured = _binding_environment(stage, surface)
        if configured:
            provider, model, route_id, deadline = _resolve_binding(env, surface)
        else:
            provider, model, route_id = 'lm_studio_local', _incumbent_model(), 'configured_general_incumbent'
            deadline = None
        if _cancelled(cancel_event):
            return YouTubeModelResult(reason='cancelled')
        # The same guard protects local output from secrets carried in input.
        _guard_payload(payload)
        _require_current(deadline, cancel_event)
        text = (_local_call(model, payload, deadline, cancel_event) if provider == 'lm_studio_local'
                else _openrouter_call(gateway, model, payload, deadline, cancel_event))
        _require_current(deadline, cancel_event)
        if _cancelled(cancel_event):
            return YouTubeModelResult(reason='cancelled')
        if not isinstance(text, str) or not text.strip():
            return YouTubeModelResult(provider=provider, model=model, route_id=route_id, reason='empty_response')
        try:
            _guard_payload({'model_output': text})
        except ValueError:
            return YouTubeModelResult(reason='invalid_reply_text')
        logger.info('[YOUTUBE-MODEL] surface=%s stage=%s provider=%s', surface, stage, provider)
        return YouTubeModelResult(text.strip(), provider, model, True, route_id)
    except Exception as exc:
        # No upstream body, prompt, key, selected endpoint URL, or raw exception.
        logger.warning('[YOUTUBE-MODEL] Call unavailable: %s', type(exc).__name__)
        return YouTubeModelResult(reason='route_unavailable')
