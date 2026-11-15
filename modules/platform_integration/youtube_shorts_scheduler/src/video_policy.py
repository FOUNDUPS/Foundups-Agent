"""Ephemeral consumer guards for the existing private 012 directive queue.

This module stores no policies and grants no publication authority. Queue reads
stay fresh at each effect; original/staged edit values live only with the DOM.
"""
from dataclasses import dataclass, field
import hashlib
import json
import re
from urllib.parse import urlsplit


class VideoPolicyBlocked(RuntimeError):
    """The next write cannot be qualified; no retry of a started write."""


class PreSaveAuditBlocked(VideoPolicyBlocked):
    """Incomplete draft: retain the page for diagnosis, without Save or Escape."""


def metadata_audit_issues(title, description):
    """Conservative completeness checks, not a content classifier or quality score."""
    issues = []
    title = title.strip() if isinstance(title, str) else ""
    title_subject = re.sub(r"(?:^|\s)#[^\s]+", "", title).strip()
    description = description.strip() if isinstance(description, str) else ""
    months = (r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
              r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?")
    dated = (re.fullmatch(r"[\d\s./:,年月日_-]+", title_subject) or
             re.fullmatch(rf"(?:\d{{1,2}}\s+)?(?:{months})(?:[\s,.-]+\d{{1,4}})*", title_subject, re.I))
    generic = re.fullmatch(r"(?:highlight[s]? overview|untitled|no title|video|short[s]?)(?:[\s#_-]*\d+)?", title_subject, re.I)
    if not title_subject or dated or generic:
        issues.append("title_missing_or_placeholder")
    elif len(title) > 100:
        issues.append("title_too_long")
    # An index trailer alone is provenance, not a human-facing description.
    body = description.split("M2M_CONTEXT", 1)[0].strip()
    if not body or re.fullmatch(r"(?:n/a|tbd|description|none)", body, re.I):
        issues.append("description_missing")
    elif len(description) > 5000:
        issues.append("description_too_long")
    elif re.match(r"(?:here(?:'s| is)|below is)\s+(?:a\s+)?(?:copy.ready|bilingual|youtube description)", body, re.I):
        issues.append("description_contains_drafting_preamble")
    return issues


def audience_target(channel_id):
    """Resolve only the exact configured channel; unknown/kids channels never default to No."""
    from .channel_config import configured_audience
    try:
        target = configured_audience(channel_id)
    except ValueError:
        raise PreSaveAuditBlocked("audience_policy_invalid_or_conflicting") from None
    if type(target) is not bool:
        raise PreSaveAuditBlocked("audience_policy_unconfigured")
    return target


def audit_schedule(session, snapshot):
    """Recheck the same current draft and audience at the actual scheduling Save."""
    from datetime import datetime, timezone
    import pytz
    from .schedule_inventory import _date_value, _time_value
    session.check(snapshot)
    issues = metadata_audit_issues(snapshot.get("title"), snapshot.get("description"))
    if issues:
        raise PreSaveAuditBlocked("presave_audit:" + ",".join(issues))
    target = audience_target(session.channel_id)
    if (snapshot.get("audience_ready") is not True or
            snapshot.get("made_for_kids") is not target or session.audience is not target):
        raise PreSaveAuditBlocked("presave_audit:audience_unverified_or_changed")
    schedule = session.requested_schedule or {}
    try:
        date = _date_value(schedule.get("date", ""))
        time = _time_value(schedule.get("time", ""))
        zone = pytz.timezone(schedule["timezone"])
        if not date or not time or schedule.get("visibility") != "scheduled":
            raise ValueError("invalid slot")
        local = zone.localize(datetime.strptime(f"{date} {time}", "%b %d, %Y %I:%M %p"), is_dst=None)
        # Refuse ambiguous/nonexistent DST wall times rather than guess an offset.
        if local <= datetime.now(timezone.utc):
            raise ValueError("unsafe slot")
    except (KeyError, ValueError, TypeError, AttributeError, pytz.InvalidTimeError):
        raise PreSaveAuditBlocked("presave_audit:schedule_invalid_or_timezone_unknown") from None
    schedule["made_for_kids"] = target  # Included in the existing durable claim digest.


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
    audience: bool | None = None

    @classmethod
    def capture(cls, snapshot, channel_id=None, video_id=None):
        native, current = detail_identity(snapshot, channel_id, video_id)
        values = {name: snapshot[name] for name in ("title", "description")}
        return cls(native, current, values, dict(values), dict(values),
                   audience=snapshot.get("made_for_kids"))

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
const audience = ['VIDEO_MADE_FOR_KIDS_MFK', 'VIDEO_MADE_FOR_KIDS_NOT_MFK'].map(name =>
 Array.from(document.querySelectorAll('tp-yt-paper-radio-button[name="' + name + '"]')).filter(el => el.isConnected && el.getClientRects().length));
const selected = el => el.checked === true || el.getAttribute('aria-checked') === 'true';
const audienceReady = audience.every(group => group.length === 1 && !group[0].disabled &&
 !group[0].hasAttribute('disabled') && group[0].getAttribute('aria-disabled') !== 'true');
const audienceKnown = audienceReady && selected(audience[0][0]) !== selected(audience[1][0]);
return {channel_id: ids.length === 1 ? ids[0] : null, url: window.location.href,
 save_disabled: saveDisabled, prompt_open: promptOpen,
 made_for_kids: audienceKnown ? selected(audience[0][0]) : null,
 audience_ready: audienceReady,
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
    scheduling_policy(channel_id, current, getattr(owner.dom, "_policy_cycle_attempts", 0))
    require_public_gate()
    read_policy(channel_id, current, surface="metadata")
    schedule = getattr(owner, "_policy_requested_schedule", None)
    if not isinstance(schedule, dict):
        raise VideoPolicyBlocked("inline_intent_unknown")
    # The list popup exposes neither the full description nor Audience. A row,
    # cached audit or title alone cannot qualify a complete, fresh detail draft.
    raise PreSaveAuditBlocked("presave_audit:detail_editor_required")
