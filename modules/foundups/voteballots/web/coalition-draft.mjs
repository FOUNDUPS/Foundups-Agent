// Local draft validation only. This module creates no accounts or network requests.
const ROLES = new Set(['creator', 'official', 'community']);
const SINGLE_LINE_CONTROLS = /[\u0000-\u001f\u007f-\u009f\u061c\u200e\u200f\u2028-\u202e\u2066-\u2069\ufeff]/u;
const NOTE_CONTROLS = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069\ufeff]/u;
const X_RESERVED = new Set(['home', 'explore', 'notifications', 'messages', 'search', 'i', 'settings', 'compose', 'login', 'signup', 'intent', 'tos', 'privacy', 'share', 'help', 'about', 'download', 'who_to_follow']);
const TWITCH_RESERVED = new Set(['directory', 'downloads', 'settings', 'login', 'signup', 'p', 'collections', 'videos', 'turbo', 'jobs', 'support', 'search', 'drops', 'subscriptions', 'prime', 'wallet']);

function isInstitutionURL(url) {
  const labels = url.hostname.split('.');
  return labels.length >= 2 && labels.at(-1) === 'gov' && labels.every((label) => /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/u.test(label));
}

function isCreatorURL(url) {
  const path = url.pathname.replace(/\/$/u, '');
  if (url.hostname === 'youtube.com' || url.hostname === 'www.youtube.com') {
    return /^\/@[A-Za-z0-9._-]{3,30}$/u.test(path) || /^\/channel\/UC[A-Za-z0-9_-]{22}$/u.test(path);
  }
  if (url.hostname === 'twitch.tv' || url.hostname === 'www.twitch.tv') {
    return /^\/[A-Za-z0-9_]{4,25}$/u.test(path) && !TWITCH_RESERVED.has(path.slice(1).toLowerCase());
  }
  if (url.hostname === 'x.com' || url.hostname === 'www.x.com') {
    return /^\/[A-Za-z0-9_]{1,15}$/u.test(path) && !X_RESERVED.has(path.slice(1).toLowerCase());
  }
  return false;
}

function validProfile(value, role) {
  // Require a direct HTTPS URL before parsing; no empty userinfo or query delimiters.
  if (/\s|\\/u.test(value)) return false;
  const direct = /^https:\/\/([a-z0-9.-]+)(?::443)?(\/[^?#]*)?$/i.exec(value);
  if (!direct) return false;
  let url;
  try { url = new URL(value); } catch { return false; }
  if (url.protocol !== 'https:' || url.username || url.password || url.port || url.search || url.hash) return false;
  if (url.hostname !== direct[1].toLowerCase() || url.pathname !== (direct[2] || '/')) return false;
  let decodedPath;
  try { decodedPath = decodeURIComponent(url.pathname); } catch { return false; }
  if (SINGLE_LINE_CONTROLS.test(decodedPath) || /[\\?#]/u.test(decodedPath)) return false;
  if (role === 'official') return isInstitutionURL(url);
  if (role === 'creator') return isCreatorURL(url);
  return isCreatorURL(url) || isInstitutionURL(url);
}

function validTimestamp(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/u.test(value)) return false;
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return false;
  const canonical = date.toISOString();
  return canonical === value || canonical.replace('.000Z', 'Z') === value;
}

export function createCoalitionDraft(input, createdAtISO) {
  const errors = {};
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    return { ok: false, errors: { form: 'Enter the draft fields before preparing an application.' } };
  }
  const displayName = typeof input.displayName === 'string' ? input.displayName.trim() : '';
  const participationRole = input.participationRole;
  const profileUrl = typeof input.profileUrl === 'string' ? input.profileUrl.trim() : '';
  const contribution = typeof input.contribution === 'string' ? input.contribution.trim() : '';

  if (typeof input.displayName !== 'string' || !displayName || displayName.length > 100 || SINGLE_LINE_CONTROLS.test(input.displayName)) {
    errors.displayName = 'Enter a display name of 1–100 characters, without line breaks or control characters.';
  }
  if (!ROLES.has(participationRole)) errors.participationRole = 'Choose creator, public official or community.';
  if (input.profileUrl !== undefined && typeof input.profileUrl !== 'string') {
    errors.profileUrl = 'Enter a public HTTPS profile URL as text, or leave it blank for community participation.';
  } else if (SINGLE_LINE_CONTROLS.test(input.profileUrl || '') || profileUrl.length > 2048) {
    errors.profileUrl = 'Use a profile URL of at most 2,048 characters without control characters.';
  } else if (!profileUrl && (participationRole === 'creator' || participationRole === 'official')) {
    errors.profileUrl = 'Add a public profile URL for this pathway. It remains unverified.';
  } else if (profileUrl && !validProfile(profileUrl, participationRole)) {
    errors.profileUrl = participationRole === 'official'
      ? 'Use an HTTPS institutional .gov page without a query, fragment, sign-in details or custom port.'
      : 'Use an HTTPS YouTube channel, Twitch channel or X profile without a query, fragment, sign-in details or custom port. Community drafts may also use an institutional .gov page.';
  }
  if ((input.contribution !== undefined && typeof input.contribution !== 'string') || contribution.length > 1000 || NOTE_CONTROLS.test(input.contribution || '')) {
    errors.contribution = 'Keep the contribution note within 1,000 characters. Line breaks and tabs are allowed; other control characters are not.';
  }
  if (input.acknowledged !== true) errors.acknowledged = 'Acknowledge that this is a local draft and no application will be sent.';
  if (!validTimestamp(createdAtISO)) errors.createdAt = 'The draft date is invalid. Check the device clock and try again.';
  if (Object.keys(errors).length) return { ok: false, errors };

  return {
    ok: true,
    draft: {
      schemaVersion: 1,
      status: 'DRAFT_NOT_SUBMITTED',
      verification: 'UNVERIFIED',
      createdAt: createdAtISO,
      displayName,
      participationRole,
      profileUrl,
      contribution,
      acknowledged: true
    }
  };
}
