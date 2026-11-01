"""Ephemeral consumer guards for the existing private 012 directive queue.

This module stores no policies and grants no publication authority. Queue reads
stay fresh at each effect; original/staged edit values live only with the DOM.
"""
from dataclasses import dataclass, field
import hashlib
import json
from urllib.parse import urlsplit


class VideoPolicyBlocked(RuntimeError):
    """The next write cannot be qualified; no retry of a started write."""


def require_public_gate():
    from modules.communication.livechat.src.automation_gates import gate_snapshot
    gates = gate_snapshot()
    if gates.get("stop_active") or gates.get("yt_automation") is not True:
        raise VideoPolicyBlocked("public_automation_gate_closed")


def read_policy(channel_id, video_id=None, *, surface):
    from modules.communication.livechat.src.operator_command_queue import get_video_policy
    if not isinstance(channel_id, str) or not channel_id:
        raise VideoPolicyBlocked("receiving_channel_unknown")
    try:
        policy = get_video_policy(channel_id, video_id, surface=surface)
    except Exception as exc:
        raise VideoPolicyBlocked("policy_unavailable") from exc
    if not isinstance(policy, dict) or policy.get("available") is not True or policy.get("blocked"):
        raise VideoPolicyBlocked("policy_unavailable_or_blocked")
    return policy


def observe(policy, *, surface, channel_id, video_id=None, outcome, detail=None):
    """No private title/context enters receipts; a click remains unknown."""
    from modules.communication.livechat.src.operator_command_queue import record_video_policy_observation
    ids = policy.get("matched_command_ids", [])
    if ids:
        record_video_policy_observation(ids, surface=surface, channel_id=channel_id,
                                       video_id=video_id, outcome=outcome, detail=detail or {})


def scheduling_policy(channel_id, video_id, attempts):
    policy = read_policy(channel_id, video_id, surface="scheduling")
    cap = policy.get("max_per_cycle")
    if policy.get("scheduling_enabled") is False or (cap is not None and attempts >= cap):
        observe(policy, surface="scheduling", channel_id=channel_id, video_id=video_id,
                outcome="blocked", detail={"reason": "paused_or_cycle_cap"})
        raise VideoPolicyBlocked("paused_or_cycle_cap")
    return policy


def detail_identity(snapshot, channel_id=None, video_id=None):
    if not isinstance(snapshot, dict):
        raise VideoPolicyBlocked("detail_identity_unknown")
    native = snapshot.get("channel_id")
    page = urlsplit(snapshot.get("url", ""))
    parts = page.path.split("/")
    current = parts[2] if len(parts) == 4 and parts[1] == "video" and parts[3] == "edit" else None
    if (page.scheme != "https" or page.netloc != "studio.youtube.com" or not current
            or not isinstance(native, str) or not native or page.query or page.fragment
            or (channel_id is not None and native != channel_id)
            or (video_id is not None and current != video_id)):
        raise VideoPolicyBlocked("detail_identity_mismatch")
    if not all(isinstance(snapshot.get(name), str) for name in ("title", "description")):
        raise VideoPolicyBlocked("detail_fields_unknown")
    return native, current


@dataclass
class EditSession:
    channel_id: str
    video_id: str
    original: dict
    staged: dict
    proposed: dict = field(default_factory=dict)
    allow_metadata: bool = True
    submitting: bool = False
    policies: dict = field(default_factory=dict)
    window_handle: str | None = None
    requested_schedule: dict | None = None
    draft_sha256: str | None = None

    @classmethod
    def capture(cls, snapshot, channel_id=None, video_id=None):
        native, current = detail_identity(snapshot, channel_id, video_id)
        values = {name: snapshot[name] for name in ("title", "description")}
        return cls(native, current, values, dict(values), dict(values))

    def check(self, snapshot):
        detail_identity(snapshot, self.channel_id, self.video_id)
        if self.submitting:
            raise VideoPolicyBlocked("submission_outcome_unknown")
        if any(snapshot[name] != self.staged[name] for name in self.staged):
            raise VideoPolicyBlocked("foreign_or_unverified_draft")

    def desired(self, snapshot, proposed=None):
        self.check(snapshot)
        policy = read_policy(self.channel_id, self.video_id, surface="metadata")
        if proposed is not None:
            self.proposed = dict(proposed)
        values = dict(self.proposed)
        for name in values:
            mode = policy.get(name + "_mode")
            if mode == "preserve":
                values[name] = self.original[name]
            elif mode == "replace":
                value = policy.get(name + "_text")
                if not isinstance(value, str):
                    raise VideoPolicyBlocked("replacement_missing")
                values[name] = value
        if not self.allow_metadata:
            values = dict(self.original)
        self.policies["metadata"] = policy
        observe(policy, surface="metadata", channel_id=self.channel_id,
                video_id=self.video_id, outcome="observed")
        return values

    def submitted(self):
        self.submitting = True
        for surface, policy in self.policies.items():
            observe(policy, surface=surface, channel_id=self.channel_id, video_id=self.video_id,
                    outcome="unknown", detail={"reason": "submission_started_readback_required"})


def save_digest(channel_id, video_id, fields, schedule=None):
    value = {"channel_id": channel_id, "video_id": video_id,
             "metadata": fields, "schedule": schedule}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def claim_save(session):
    from modules.communication.livechat.src.operator_command_queue import claim_video_policy_save
    session.draft_sha256 = save_digest(session.channel_id, session.video_id,
                                      session.staged, session.requested_schedule)
    metadata = session.policies["metadata"]
    scheduling = session.policies.get("scheduling", {})
    ids = sorted(set(metadata["matched_command_ids"] + scheduling.get("matched_command_ids", [])))
    result = claim_video_policy_save(session.channel_id, session.video_id, command_ids=ids,
        metadata_fingerprint=metadata["fingerprint"], scheduling_fingerprint=scheduling.get("fingerprint"),
        draft_sha256=session.draft_sha256)
    if not isinstance(result, dict) or result.get("claimed") is not True:
        raise VideoPolicyBlocked("save_already_claimed_or_unavailable")


def verify_metadata_save(session, snapshot):
    """Metadata facts alone must never settle an attempted schedule change."""
    from modules.communication.livechat.src.operator_command_queue import verify_video_policy_save
    detail_identity(snapshot, session.channel_id, session.video_id)
    fields = {key: snapshot[key] for key in session.staged}
    if fields != session.staged:
        return False
    if session.requested_schedule is not None:
        metadata = session.policies["metadata"]
        fresh = read_policy(session.channel_id, session.video_id, surface="metadata")
        if fresh["fingerprint"] != metadata["fingerprint"]:
            observe(metadata, surface="metadata", channel_id=session.channel_id,
                    video_id=session.video_id, outcome="unknown",
                    detail={"reason": "metadata_policy_changed_after_submission"})
            return False
        observe(metadata, surface="metadata", channel_id=session.channel_id,
                video_id=session.video_id, outcome="applied",
                detail={"persisted_readback": True, "policy_fingerprint": metadata["fingerprint"],
                        "readback_sha256": save_digest(session.channel_id, session.video_id, fields)})
        return False  # metadata fact only: the whole scheduling claim stays unknown
    result = verify_video_policy_save(session.channel_id, session.video_id,
        draft_sha256=session.draft_sha256,
        readback_sha256=save_digest(session.channel_id, session.video_id, fields),
        metadata_fingerprint=session.policies["metadata"]["fingerprint"])
    return isinstance(result, dict) and result.get("verified") is True


# Exact strings, without strip/logging, from the existing detail editor owners.
DETAIL_SNAPSHOT_SCRIPT = r"""
const nativeLocations = [
 window.ytcfg && typeof window.ytcfg.get === 'function' ? window.ytcfg.get('CHANNEL_ID') : null,
 window.yt && window.yt.config_ ? window.yt.config_.CHANNEL_ID : null
];
const ids = Array.from(new Set(nativeLocations.filter(x => typeof x === 'string' && x.length)));
function text(selector) {
 const el = document.querySelector(selector);
 return el ? (typeof el.innerText === 'string' ? el.innerText : el.textContent) : null;
}
const saveButtons = Array.from(document.querySelectorAll('ytcp-button#save-button, button#save-button')).filter(el => el.getClientRects().length);
const saveDisabled = saveButtons.length > 0 && saveButtons.every(el => el.disabled || el.hasAttribute('disabled') || el.getAttribute('aria-disabled') === 'true');
const promptOpen = Array.from(document.querySelectorAll('tp-yt-paper-dialog, [role="dialog"]')).some(el => el.getClientRects().length);
return {channel_id: ids.length === 1 ? ids[0] : null, url: window.location.href,
 save_disabled: saveDisabled, prompt_open: promptOpen,
 title: text('ytcp-social-suggestions-textbox#title-textarea #textbox'),
 description: text('ytcp-social-suggestions-textbox#description-textarea #textbox')};
"""

INLINE_SNAPSHOT_SCRIPT = DETAIL_SNAPSHOT_SCRIPT.split("function text(")[0] + r"""
const wanted = arguments[1];
const rows = arguments[0] ? [arguments[0]] : Array.from(document.querySelectorAll('ytcp-video-row')).filter(row =>
 Array.from(row.querySelectorAll('a[href*="/video/"]')).some(a => new URL(a.href, location.href).pathname === '/video/' + wanted + '/edit'));
const row = rows.length === 1 ? rows[0] : null;
const links = row && row.isConnected ? Array.from(row.querySelectorAll('a[href*="/video/"]')) : [];
const videos = Array.from(new Set(links.map(a => {
 const url = new URL(a.href, location.href);
 const match = url.pathname.match(/^\/video\/([A-Za-z0-9_-]{11})\/edit$/);
 return url.origin === 'https://studio.youtube.com' && match ? match[1] : null;
}).filter(Boolean)));
const popups = Array.from(document.querySelectorAll('ytcp-video-visibility-edit-popup')).filter(p => p.getClientRects().length);
const popup = popups.length === 1 ? popups[0] : null;
const rowElements = row ? [row, ...row.querySelectorAll('*')] : [];
const rowIds = new Set(rowElements.map(el => el.id).filter(Boolean));
const labelled = popup ? (popup.getAttribute('aria-labelledby') || '').split(/\s+/) : [];
const controls = popup && popup.id && rowElements.some(el => (el.getAttribute('aria-controls') || '').split(/\s+/).includes(popup.id));
const popupBound = !!popup && !!row && (row.contains(popup) || controls || labelled.some(id => rowIds.has(id)));
return {channel_id: ids.length === 1 ? ids[0] : null, url: window.location.href,
 video_id: videos.length === 1 ? videos[0] : null, popup_bound: popupBound};
"""


def inline_identity(driver, row=None, *, channel_id=None, video_id=None, require_popup=False):
    snapshot = driver.execute_script(INLINE_SNAPSHOT_SCRIPT, row, video_id)
    if not isinstance(snapshot, dict):
        raise VideoPolicyBlocked("inline_identity_unknown")
    native, current = snapshot.get("channel_id"), snapshot.get("video_id")
    page = urlsplit(snapshot.get("url", ""))
    if (not isinstance(native, str) or not native or not isinstance(current, str) or not current
            or page.scheme != "https" or page.netloc != "studio.youtube.com"
            or page.path not in (f"/channel/{native}/videos/short", f"/channel/{native}/videos/upload")
            or (channel_id is not None and native != channel_id)
            or (video_id is not None and current != video_id)
            or (require_popup and snapshot.get("popup_bound") is not True)):
        raise VideoPolicyBlocked("inline_identity_mismatch")
    return native, current


def submit_inline(owner, row, video_id, callback):
    if not isinstance(video_id, str) or not video_id:
        raise VideoPolicyBlocked("inline_target_unknown")
    channel_id, current = inline_identity(owner.driver, row,
        channel_id=getattr(owner, "_policy_channel_id", None), video_id=video_id, require_popup=True)
    policy = scheduling_policy(channel_id, current, getattr(owner.dom, "_policy_cycle_attempts", 0))
    require_public_gate()
    from modules.communication.livechat.src.operator_command_queue import claim_video_policy_save
    metadata = read_policy(channel_id, current, surface="metadata")
    schedule = getattr(owner, "_policy_requested_schedule", None)
    if not isinstance(schedule, dict):
        raise VideoPolicyBlocked("inline_intent_unknown")
    digest = save_digest(channel_id, current, {}, schedule)
    claim = claim_video_policy_save(channel_id, current,
        command_ids=sorted(set(metadata["matched_command_ids"] + policy["matched_command_ids"])),
        metadata_fingerprint=metadata["fingerprint"], scheduling_fingerprint=policy["fingerprint"],
        draft_sha256=digest)
    if not isinstance(claim, dict) or claim.get("claimed") is not True:
        raise VideoPolicyBlocked("inline_save_already_claimed_or_unavailable")
    submitted = getattr(owner, "_policy_submitted_videos", set())
    if (channel_id, current) in submitted:
        raise VideoPolicyBlocked("inline_submission_outcome_unknown")
    submitted.add((channel_id, current))
    owner._policy_submitted_videos = submitted
    owner._policy_submission_started = True
    owner.dom._policy_cycle_attempts = getattr(owner.dom, "_policy_cycle_attempts", 0) + 1
    observe(policy, surface="scheduling", channel_id=channel_id, video_id=current,
            outcome="unknown", detail={"reason": "submission_started_readback_required"})
    try:
        return callback()
    except Exception as exc:
        raise VideoPolicyBlocked("inline_submission_started_outcome_unknown") from exc
