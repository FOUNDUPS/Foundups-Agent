/**
 * Guest-only client for the canonical Python RedDog public-admission API.
 *
 * Importing and constructing this module performs no request. A deployment must
 * explicitly supply the same-origin `/api/reddog/public` root. Session material
 * is held in memory only and no account, Mall, or private context is transmitted.
 */
export class PublicChatError extends Error {
  constructor(code, status = 0) {
    super(code);
    this.code = code;
    this.status = status;
  }
}
const API_PATH = '/api/reddog/public';
const SURFACES = new Set(['foundups', 'esingularity', 'autopost']);
export function resolvePublicApiRoot(configuredRoot, pageOrigin) {
  if (typeof configuredRoot !== 'string' || !configuredRoot.trim()) return '';
  if (typeof pageOrigin !== 'string' || !pageOrigin) return '';
  try {
    const expectedOrigin = new URL(pageOrigin).origin;
    const root = new URL(configuredRoot.trim(), expectedOrigin);
    if (root.origin !== expectedOrigin || root.username || root.password
        || root.search || root.hash || root.pathname.replace(/\/$/, '') !== API_PATH) {
      return '';
    }
    return expectedOrigin + API_PATH;
  } catch {
    return '';
  }
}
export function encounterPayload() {
  return {
    consent: true,
    consent_version: 'reddog.public-guest.v1',
    actor_claim: 'unspecified',
  };
}
export function normalizePublicFoundupId(value) {
  return typeof value === 'string' && /^[a-z0-9][a-z0-9_-]{0,79}$/.test(value) ? value : '';
}
export function turnPayload(session, message, foundupId = '') {
  const payload = {
    nonce: session.nonce,
    revision: session.revision,
    message: message.trim(),
  };
  const publicFoundupId = normalizePublicFoundupId(foundupId);
  if (foundupId !== '' && !publicFoundupId) throw new PublicChatError('input');
  if (publicFoundupId) payload.foundup_id = publicFoundupId;
  return payload;
}
export class RedDogPublicClient {
  constructor(surface, configuredRoot, options = {}) {
    if (!SURFACES.has(surface)) throw new Error('Unknown public surface');
    const origin = options.origin || globalThis.location?.origin || '';
    const root = resolvePublicApiRoot(configuredRoot, origin);
    if (!root) throw new PublicChatError('unavailable');
    this.base = `${root}/${surface}`;
    this.fetchImpl = options.fetchImpl || globalThis.fetch;
    if (typeof this.fetchImpl !== 'function') throw new PublicChatError('unavailable');
    this.session = null;
    this.busy = false;
    this.needsStatus = false;
    this.generation = 0;
  }
  async request(operation, body, token = '') {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 22000);
    try {
      const response = await this.fetchImpl(`${this.base}/${operation}`, {
        method: 'POST',
        credentials: 'omit',
        cache: 'no-store',
        redirect: 'error',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      if (!response.ok) {
        const code = response.status === 410 ? 'expired'
          : response.status === 429 ? 'limited' : 'unavailable';
        throw new PublicChatError(code, response.status);
      }
      return await response.json();
    } catch (error) {
      if (error instanceof PublicChatError) throw error;
      throw new PublicChatError('connection');
    } finally {
      clearTimeout(timer);
    }
  }
  update(data, generation) {
    if (generation !== this.generation || !this.session) throw new PublicChatError('ended');
    if (!Number.isInteger(data.revision) || typeof data.nonce !== 'string'
        || !Number.isInteger(data.remaining_turns)) throw new PublicChatError('unavailable');
    if (data.revision < this.session.revision) throw new PublicChatError('stale');
    Object.assign(this.session, {
      revision: data.revision,
      nonce: data.nonce,
      remaining_turns: data.remaining_turns,
      expires_at: data.expires_at ?? this.session.expires_at,
      idle_expires_at: data.idle_expires_at ?? this.session.idle_expires_at,
    });
    this.needsStatus = data.in_flight === true;
  }
  async start() {
    if (this.busy || this.session) throw new PublicChatError('busy');
    this.busy = true;
    const generation = ++this.generation;
    try {
      const data = await this.request('encounter', encounterPayload());
      if (generation !== this.generation) throw new PublicChatError('ended');
      if (typeof data.token !== 'string' || !data.token) throw new PublicChatError('unavailable');
      this.session = {
        token: data.token, revision: -1, nonce: '', remaining_turns: 0,
        expires_at: 0, idle_expires_at: 0,
      };
      this.update(data, generation);
      return data;
    } catch (error) {
      if (generation === this.generation) this.session = null;
      throw error;
    } finally {
      if (generation === this.generation) this.busy = false;
    }
  }

  async recover(generation) {
    if (!this.session) throw new PublicChatError('expired');
    this.needsStatus = true;
    try {
      const data = await this.request('status', {}, this.session.token);
      this.update(data, generation);
      return data;
    } catch (error) {
      if (generation === this.generation && error instanceof PublicChatError
          && [401, 403, 410].includes(error.status)) this.session = null;
      throw error;
    }
  }

  async check() {
    if (this.busy) throw new PublicChatError('busy');
    this.busy = true;
    const generation = this.generation;
    try { return await this.recover(generation); }
    finally { if (generation === this.generation) this.busy = false; }
  }

  async send(message, foundupId = '') {
    if (this.busy || this.needsStatus) throw new PublicChatError('busy');
    if (!this.session) throw new PublicChatError('expired');
    if (typeof message !== 'string' || !message.trim() || message.length > 2000) {
      throw new PublicChatError('input');
    }
    if (this.session.remaining_turns <= 0) throw new PublicChatError('limited');
    const body = turnPayload(this.session, message, foundupId);
    this.busy = true;
    const generation = this.generation;
    try {
      const data = await this.request('turn', body, this.session.token);
      if (data.disclosure !== 'public' || data.effect_ceiling !== 'NONE'
          || typeof data.reply !== 'string' || !data.reply.trim() || [...data.reply].length > 4000) {
        throw new PublicChatError('unavailable');
      }
      this.update(data, generation);
      return data;
    } catch (error) {
      if (generation !== this.generation) throw new PublicChatError('ended');
      if (error instanceof PublicChatError && [401, 403, 410].includes(error.status)) {
        this.session = null;
        throw new PublicChatError('expired', error.status);
      }
      // A turn may have run. Recover accounting once; never replay the message.
      try { await this.recover(generation); } catch { /* Explicit next action only. */ }
      throw new PublicChatError(this.session ? 'uncertain' : 'expired');
    } finally {
      if (generation === this.generation) this.busy = false;
    }
  }

  async end() {
    const token = this.session?.token;
    const generation = ++this.generation;
    this.session = null;
    this.needsStatus = false;
    this.busy = true;
    try { if (token) await this.request('withdraw', {}, token); }
    finally { if (generation === this.generation) this.busy = false; }
  }

  clearLocal() {
    this.generation += 1;
    this.session = null;
    this.needsStatus = false;
    this.busy = false;
  }
}

const ERROR_TEXT = {
  expired: 'This guest session ended. Start a new one when you are ready.',
  limited: 'The guest conversation limit has been reached.',
  uncertain: 'The reply was not received. Your question was not resent. Check the session before continuing.',
  connection: 'Could not connect. No question will be resent automatically.',
  unavailable: 'Guest conversation is unavailable on this deployment.',
  busy: 'Please wait for the current request or check its status.',
  input: 'Enter a question of up to 2,000 characters.',
  ended: 'Guest conversation ended.',
};

function element(doc, tag, className, text = '') {
  const node = doc.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
}

function buildDialog(doc) {
  const shell = element(doc, 'dialog', 'reddog-guest-dialog');
  shell.setAttribute('aria-label', 'Red Dog guest conversation');
  const title = element(doc, 'h2', 'reddog-guest-title', 'Public guest conversation');
  const disclosure = element(doc, 'p', 'reddog-guest-disclosure',
    'Text only. Public catalog context only. No account, private memory, tools, or work authority.');
  const account = element(doc, 'a', 'reddog-guest-account', 'Sign in or check account access');
  account.href = 'https://foundups.com/member/?account=1';
  account.textContent += ' (separate from this guest session)';
  const consentLabel = element(doc, 'label', 'reddog-guest-consent');
  const consent = doc.createElement('input');
  consent.type = 'checkbox';
  consent.setAttribute('data-reddog-guest-consent', '');
  consentLabel.append(consent, doc.createTextNode(' I consent to send my text to the public Red Dog service for this guest session.'));
  const status = element(doc, 'p', 'reddog-guest-status', 'Consent is required before any request.');
  status.setAttribute('aria-live', 'polite');
  const messages = element(doc, 'div', 'reddog-guest-messages');
  messages.setAttribute('aria-live', 'polite');
  const form = element(doc, 'form', 'reddog-guest-form');
  form.hidden = true;
  const input = doc.createElement('textarea');
  input.maxLength = 2000;
  input.rows = 3;
  input.placeholder = 'Ask about public FoundUps information';
  input.setAttribute('aria-label', 'Public guest question');
  const send = element(doc, 'button', 'reddog-guest-send', 'Send');
  send.type = 'submit';
  form.append(input, send);
  const controls = element(doc, 'div', 'reddog-guest-controls');
  const start = element(doc, 'button', 'reddog-guest-start', 'Start guest session');
  const check = element(doc, 'button', 'reddog-guest-check', 'Check request');
  const end = element(doc, 'button', 'reddog-guest-end', 'End session');
  const close = element(doc, 'button', 'reddog-guest-close', 'Close');
  for (const button of [start, check, end, close]) button.type = 'button';
  check.hidden = true; end.hidden = true;
  controls.append(start, check, end, close);
  shell.append(title, disclosure, account, consentLabel, status, messages, form, controls);
  doc.body.appendChild(shell);
  return { shell, consent, status, messages, form, input, send, start, check, end, close };
}

/** Adapter for `window.redDog.registerConversationAdapter(...)`. */
export function createMemberConversationAdapter(options = {}) {
  const doc = options.document || globalThis.document;
  const origin = options.origin || doc?.location?.origin || '';
  const configuredRoot = options.apiRoot ?? doc?.querySelector(
    'meta[name="reddog-public-api-root"]'
  )?.content ?? '';
  const root = resolvePublicApiRoot(configuredRoot, origin);
  let client = null;
  let view = null;
  let bindingKey = '';
  let boundFoundupId = '';
  let returnFocus = null;

  function bindContext(context) {
    const candidate = context && typeof context === 'object' ? context : {};
    const revision = Number.isSafeInteger(candidate.bindingRevision)
      ? String(candidate.bindingRevision) : 'unbound';
    const foundupId = normalizePublicFoundupId(candidate.foundupId);
    const nextKey = `${revision}:${foundupId || 'generic'}`;
    if (bindingKey && bindingKey !== nextKey) {
      client?.clearLocal();
      if (view) {
        closeDialog();
        view.messages.replaceChildren();
        view.input.value = '';
        view.consent.checked = false;
        view.form.hidden = true;
        view.status.textContent = 'Context changed. Start a new guest session after reviewing consent.';
      }
    }
    bindingKey = nextKey;
    boundFoundupId = foundupId;
  }

  const availability = (context) => {
    bindContext(context);
    if (context?.access === 'unknown' || context?.selectionState === 'invalid'
        || (context?.foundupId != null && !normalizePublicFoundupId(context.foundupId))) {
      return { available: false, reason: 'Guest conversation is unavailable in this context.' };
    }
    return root
      ? { available: true }
      : { available: false, reason: 'Public guest conversation is not configured on this deployment.' };
  };

  function render() {
    if (!view || !client) return;
    const active = Boolean(client.session);
    view.start.disabled = !view.consent.checked || client.busy || active;
    view.consent.disabled = client.busy || active;
    view.form.hidden = !active;
    view.input.disabled = !active || client.busy || client.needsStatus
      || client.session.remaining_turns <= 0;
    view.send.disabled = view.input.disabled;
    view.check.hidden = !active || !client.needsStatus;
    view.end.hidden = !active;
  }

  function note(text) { view.status.textContent = text; }
  function add(text, kind) {
    const message = element(doc, 'p', `reddog-guest-message ${kind}`, text);
    view.messages.appendChild(message);
  }
  function ready() {
    note(`${client.session.remaining_turns} guest questions remaining. No account or private context is attached.`);
  }
  function showError(error) { note(ERROR_TEXT[error?.code] || ERROR_TEXT.unavailable); }

  function closeDialog() {
    if (!view) return;
    if (typeof view.shell.close === 'function' && view.shell.open) view.shell.close();
    else view.shell.removeAttribute('open');
    if (returnFocus && returnFocus.isConnected && typeof returnFocus.focus === 'function') {
      returnFocus.focus();
    }
    returnFocus = null;
  }

  function wire() {
    view.consent.addEventListener('change', render);
    view.close.addEventListener('click', closeDialog);
    view.shell.addEventListener('close', () => {
      if (returnFocus && returnFocus.isConnected && typeof returnFocus.focus === 'function') {
        returnFocus.focus();
      }
      returnFocus = null;
    });
    view.start.addEventListener('click', async () => {
      if (!view.consent.checked || client.busy || client.session) return;
      const pending = client.start(); render(); note('Opening a bounded public guest session…');
      try { await pending; ready(); view.input.focus(); }
      catch (error) { showError(error); }
      finally { render(); }
    });
    view.form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const text = view.input.value.trim();
      if (!text || view.input.disabled) return;
      add(text, 'user'); view.input.value = '';
      const pending = client.send(text, boundFoundupId);
      render(); note('Red Dog is preparing a public reply…');
      try { const data = await pending; add(data.reply, 'bot'); ready(); }
      catch (error) { if (error?.code !== 'ended') showError(error); }
      finally { render(); }
    });
    view.check.addEventListener('click', async () => {
      const pending = client.check(); render();
      try { await pending; client.needsStatus ? note('The request is still processing.') : ready(); }
      catch (error) { showError(error); }
      finally { render(); }
    });
    view.end.addEventListener('click', async () => {
      const pending = client.end();
      view.messages.replaceChildren();
      view.input.value = '';
      render(); note('Guest session ended; local session state was cleared.');
      try { await pending; }
      catch { note('Local state was cleared; the server session will expire automatically.'); }
      finally { view.consent.checked = false; render(); }
    });
  }

  return {
    syncContext: bindContext,
    getAvailability: availability,
    open(context) {
      if (!doc || !availability(context).available) return false;
      if (!client) client = new RedDogPublicClient('foundups', root, {
        origin, fetchImpl: options.fetchImpl,
      });
      if (!view) { view = buildDialog(doc); wire(); }
      const scope = boundFoundupId
        ? ` The public FoundUp ID “${boundFoundupId}” will accompany each question.`
        : ' No selected FoundUp ID will accompany questions.';
      view.shell.querySelector('.reddog-guest-disclosure').textContent =
        'Text only. Public catalog context only. No account, private memory, tools, or work authority.' + scope;
      returnFocus = doc.activeElement;
      if (typeof view.shell.showModal === 'function') view.shell.showModal();
      else view.shell.setAttribute('open', '');
      render();
      view.close.focus();
      return true;
    },
  };
}
