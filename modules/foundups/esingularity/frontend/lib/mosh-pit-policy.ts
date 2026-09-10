// Pure policy shared by the server gate and its tests. Never use email as a grant.
export const MOSH_PROJECT = 'esingularity_001';
export const MOSH_SITE = 'appgprj_6a917b21b1a4819181a61738ed5274a5';
export const MOSH_PATH = `/f/${MOSH_PROJECT}/mosh-pit`;
export const MOSH_LIMIT = 50;

export function utcExpiry(value: unknown): number {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z$/.test(value)) return NaN;
  const stamp = Date.parse(value);
  if (!Number.isFinite(stamp) || new Date(stamp).toISOString().replace('.000Z', 'Z') !== value.replace('.000Z', 'Z')) return NaN;
  return stamp;
}

export type Membership = { userId: string; version: string; expiresAt: number };
export type Access =
  | { status: 'allowed'; membership: Membership }
  | { status: 'signed_out' | 'not_approved' | 'unavailable' };

export function membershipFor(raw: unknown, userId: string | null, now = Date.now()): Access {
  if (!userId) return { status: 'signed_out' };
  if (typeof raw !== 'string' || raw.length > 256_000) return { status: 'unavailable' };
  try {
    const policy = JSON.parse(raw);
    if (policy?.version !== 1 || policy.site_id !== MOSH_SITE || policy.project_id !== MOSH_PROJECT ||
        typeof policy.revision !== 'string' || !/^[A-Za-z0-9_-]{1,100}$/.test(policy.revision) ||
        !Array.isArray(policy.members) || policy.members.length > 500) return { status: 'unavailable' };
    const seen = new Set<string>();
    for (const member of policy.members) {
      if (!member || typeof member.user_id !== 'string' || !member.user_id.trim() ||
          member.user_id.length > 200 || seen.has(member.user_id) ||
          !Number.isFinite(utcExpiry(member.expires_at))) return { status: 'unavailable' };
      seen.add(member.user_id);
    }
    const member = policy.members.find((m: { user_id: string }) => m.user_id === userId);
    if (!member || utcExpiry(member.expires_at) <= now) return { status: 'not_approved' };
    return { status: 'allowed', membership: { userId, version: policy.revision, expiresAt: utcExpiry(member.expires_at) } };
  } catch {
    return { status: 'unavailable' };
  }
}

export type Activity = { event_id: string; actor: string; summary: string; details: string[]; truth: string };
export type Entry = Activity & { replies: Activity[]; more_replies: boolean };
export type Projection = {
  schema_version: 'mosh_pit_projection.v1'; foundup_id: string; disclosure_class: 'stakeholder';
  snapshot_id: string; timezone: 'Asia/Tokyo';
  days: { date: string | null; entries: Entry[] }[]; has_more: boolean; read_only: true;
};

// Reconstruct the explicit stakeholder shape; never forward arbitrary upstream fields.
export function cleanProjection(value: unknown, snapshot: string): Projection {
  const p = value as Projection;
  const text = (v: unknown, max: number): string => {
    if (typeof v !== 'string' || !v.trim() || v.length > max || /[\u0000-\u0008\u000b-\u001f]/.test(v)) throw Error('invalid_projection');
    return v;
  };
  const seen = new Set<string>();
  const activity = (a: Activity, root: boolean): Activity => {
    if (!a || !Array.isArray(a.details) || a.details.length > 12 ||
        !(root ? ['OBSERVED', 'REPORTED_BY_012'] : ['OBSERVED', 'REPORTED_BY_012', 'INFERRED', 'PROPOSED']).includes(a.truth)) throw Error('invalid_projection');
    const id = text(a.event_id, 200);
    if (seen.has(id)) throw Error('invalid_projection');
    seen.add(id);
    if (seen.size > 500) throw Error('invalid_projection');
    return { event_id: id, actor: text(a.actor, 120), summary: text(a.summary, 240),
      details: a.details.map(d => text(d, 2000)), truth: a.truth };
  };
  if (!p || p.schema_version !== 'mosh_pit_projection.v1' || p.foundup_id !== MOSH_PROJECT ||
      p.disclosure_class !== 'stakeholder' || p.snapshot_id !== snapshot || p.timezone !== 'Asia/Tokyo' ||
      p.read_only !== true || typeof p.has_more !== 'boolean' || !Array.isArray(p.days) || p.days.length > MOSH_LIMIT) throw Error('invalid_projection');
  let count = 0;
  let previous = '9999-99-99';
  const days = p.days.map(day => {
    if (!day || !Array.isArray(day.entries) || day.entries.length === 0 ||
        (day.date !== null && (!/^\d{4}-\d{2}-\d{2}$/.test(day.date) ||
        !Number.isFinite(Date.parse(day.date)) || new Date(day.date).toISOString().slice(0, 10) !== day.date)) ||
        (day.date ?? '') >= previous) throw Error('invalid_projection');
    previous = day.date ?? '';
    const entries = day.entries.map(entry => {
      if (++count > MOSH_LIMIT || !Array.isArray(entry.replies) || entry.replies.length > 50 || typeof entry.more_replies !== 'boolean') throw Error('invalid_projection');
      return { ...activity(entry, true), replies: entry.replies.map(reply => activity(reply, false)), more_replies: entry.more_replies };
    });
    return { date: day.date, entries };
  });
  return { schema_version: p.schema_version, foundup_id: MOSH_PROJECT, disclosure_class: 'stakeholder',
    snapshot_id: snapshot, timezone: 'Asia/Tokyo', days, has_more: p.has_more, read_only: true };
}
