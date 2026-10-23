"""Reference-conditioned storyboard images using the existing gateway config.

No environment loading, credential store, runtime registration or automatic
retry. The admitted story owner supplies ProviderConfig and authorization.
Images remain unreviewed; compose with a separately admitted video generator.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler

MODEL = "black-forest-labs/flux.2-klein-4b"
BASE_URL = "https://openrouter.ai/api/v1"
MAX_IMAGE = 8 * 1024 * 1024
MAX_RESPONSE = 12 * 1024 * 1024


def _text(value, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("Invalid storyboard text")
    return value


def _mime(data):
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    raise ValueError("Storyboard requires PNG, JPEG or WebP bytes")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _post(url, key, payload):
    """One bounded request. Never include upstream errors or credentials in errors."""
    request = Request(url, data=json.dumps(payload).encode(), method="POST",
                      headers={"Authorization": "Bearer " + key,
                               "Content-Type": "application/json"})
    try:
        with build_opener(_NoRedirect).open(request, timeout=180) as response:
            raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise ValueError("Response exceeds bound")
        return json.loads(raw)
    except Exception:
        raise RuntimeError("OpenRouter request failed; reconcile before retry") from None


class OpenRouterStoryboard:
    """One image per call; config is gateway.providers['openrouter'].

    references: nonempty sequence of {path, sha256, rights_evidence} for approved
    local raster references. Rasterize repository SVGs before binding. Model and
    references are host configuration, never taken from model-authored stories.
    authorize receives stage 'storyboard_image' and a content-free request record.
    The host owns durable effect admission/cost limits; this callback is required.
    """
    def __init__(self, provider_config, *, references, authorize, model=MODEL, transport=None):
        if provider_config.name != "openrouter" or provider_config.base_url.rstrip("/") != BASE_URL:
            raise ValueError("Use the existing OpenRouter gateway configuration")
        if not isinstance(provider_config.api_key, str) or not provider_config.api_key.strip():
            raise ValueError("OpenRouter gateway credential is not configured")
        if not callable(authorize) or not isinstance(references, (list, tuple)) or not 1 <= len(references) <= 4:
            raise ValueError("Authorization and one to four reference images required")
        self.model = _text(model, 150)
        self._key = provider_config.api_key
        self._references = tuple(dict(ref) for ref in references)
        self._authorize = authorize
        self._transport = transport or _post

    def __call__(self, shot, context):
        shot_id = _text(shot.get("shot_id"), 120)
        if not re.fullmatch(r"[A-Za-z0-9_-]+", shot_id):
            raise ValueError("Invalid shot ID")
        prompt = _text(shot.get("prompt"), 16000)
        root = Path(context["output_dir"]).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("Existing output directory required")
        # An exclusive intent file survives uncertain effects and refuses replay.
        intent = root / (shot_id + ".storyboard.json")
        if intent.exists() or intent.is_symlink():
            raise FileExistsError("Storyboard already attempted; reconcile before retry")
        refs, hashes = [], []
        for ref in self._references:
            path = Path(ref["path"])
            if path.is_symlink() or not path.is_file():
                raise ValueError("Regular reference image required")
            with path.open("rb") as stream:
                data = stream.read(MAX_IMAGE + 1)
            digest = hashlib.sha256(data).hexdigest()
            if not data or len(data) > MAX_IMAGE or digest != ref.get("sha256"):
                raise ValueError("Reference size or hash mismatch")
            _text(ref.get("rights_evidence"), 4000)
            mime, _ = _mime(data)
            refs.append({"type": "image_url", "image_url": {
                "url": f"data:{mime};base64," + base64.b64encode(data).decode()}})
            hashes.append(digest)
        payload = {"model": self.model, "n": 1, "aspect_ratio": "16:9",
                   "prompt": "Create ONE storyboard frame, not a collage. Preserve the reference "
                             "character geometry and flat palette. No text. Scene:\n" + prompt,
                   "input_references": refs, "provider": {"allow_fallbacks": False}}
        record = {"provider": "openrouter", "model": self.model, "shot_id": shot_id,
                  "reference_sha256": hashes, "status": "attempted_unresolved",
                  "request_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()}
        if self._authorize("storyboard_image", dict(record)) is not True:
            raise PermissionError("Storyboard generation was not admitted")
        with intent.open("x", encoding="utf-8") as stream:
            json.dump(record, stream, indent=2)
        try:
            result = self._transport(BASE_URL + "/images", self._key, payload)
        except Exception:
            raise RuntimeError("OpenRouter request failed; reconcile before retry") from None
        items = result.get("data") if isinstance(result, dict) else None
        if not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict):
            raise ValueError("Expected exactly one generated image")
        encoded = items[0].get("b64_json")
        if not isinstance(encoded, str) or len(encoded) > (MAX_IMAGE + 2) // 3 * 4:
            raise ValueError("Missing or oversized image")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError):
            raise ValueError("Invalid image encoding") from None
        if not data or len(data) > MAX_IMAGE:
            raise ValueError("Invalid image size")
        mime, extension = _mime(data)
        if items[0].get("media_type", mime) != mime:
            raise ValueError("Image format mismatch")
        path = root / (shot_id + ".storyboard" + extension)
        with path.open("xb") as stream:
            stream.write(data)
        result = {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(),
                "status": "generated_unreviewed", "provider": "openrouter", "model": self.model,
                "reference_sha256": hashes, "intent_path": str(intent),
                "rights_evidence": "Generated via OpenRouter; reference provenance supplied. "
                                   "Output rights and visual continuity still require review.",
                "reference_rights_evidence": [ref["rights_evidence"] for ref in self._references]}
        with (root / (shot_id + ".storyboard.result.json")).open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
        return result


class StoryboardVideoShot:
    """Compose into story_pipeline.run_story(generate_shot=...).

    review_frame(frame, shot, context) must explicitly return True before video
    generation. generate_video receives a copy of shot with start_frame evidence;
    it must consume those bytes and return the existing {path, rights_evidence}
    video contract. No still-image video substitute or provider fallback occurs.
    """
    def __init__(self, storyboard, *, review_frame, generate_video):
        if not all(callable(fn) for fn in (storyboard, review_frame, generate_video)):
            raise ValueError("Storyboard, review and video callbacks required")
        self.storyboard, self.review_frame, self.generate_video = storyboard, review_frame, generate_video

    def __call__(self, shot, context):
        frame = self.storyboard(shot, context)
        digest = frame["sha256"]
        if self.review_frame(dict(frame), dict(shot), dict(context)) is not True:
            raise ValueError("Storyboard frame review did not pass")
        if hashlib.sha256(Path(frame["path"]).read_bytes()).hexdigest() != digest:
            raise ValueError("Reviewed storyboard changed")
        return self.generate_video(dict(shot, start_frame=dict(frame)), dict(context))
