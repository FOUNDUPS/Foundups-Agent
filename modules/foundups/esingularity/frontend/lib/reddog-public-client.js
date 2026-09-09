/** Shared public-only transport. Bearers and conversation state never enter storage. */
export class PublicChatError extends Error {
  constructor(code, status = 0) {
    super(code);
    this.code = code;
    this.status = status;
  }
}

export class RedDogPublicClient {
  constructor(surface, apiRoot = 'https://esingularity.ai/api/reddog/public') {
    if (!['foundups', 'esingularity'].includes(surface)) throw new Error('Unknown surface');
    this.base = `${apiRoot}/${surface}`;
    this.session = null;
    this.busy = false;
    this.needsStatus = false;
    this.generation = 0;
  }

  async request(operation, body, token = '') {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 22000);
    try {
      const response = await fetch(`${this.base}/${operation}`, {
        method: 'POST', credentials: 'omit', cache: 'no-store', redirect: 'error',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify(body), signal: controller.signal,
      });
      if (!response.ok) throw new PublicChatError(response.status === 410 ? 'expired' : response.status === 429 ? 'limited' : 'unavailable', response.status);
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
    if (!Number.isInteger(data.revision) || typeof data.nonce !== 'string' || !Number.isInteger(data.remaining_turns)) {
      throw new PublicChatError('unavailable');
    }
    if (data.revision < this.session.revision) throw new PublicChatError('stale');
    Object.assign(this.session, {
      revision: data.revision, nonce: data.nonce, remaining_turns: data.remaining_turns,
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
      const data = await this.request('encounter', { consent: true, consent_version: 'reddog.public-guest.v1', actor_claim: 'unspecified' });
      if (generation !== this.generation) throw new PublicChatError('ended');
      const token = data.token || data.session_token;
      if (typeof token !== 'string' || !token) throw new PublicChatError('unavailable');
      this.session = { token, revision: -1, nonce: '', remaining_turns: 0, expires_at: 0, idle_expires_at: 0 };
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
      if (generation === this.generation && error instanceof PublicChatError && [401, 403, 410].includes(error.status)) this.session = null;
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

  async send(message) {
    if (this.busy || this.needsStatus) throw new PublicChatError('busy');
    if (!this.session) throw new PublicChatError('expired');
    if (!message.trim() || message.length > 2000) throw new PublicChatError('input');
    if (this.session.remaining_turns <= 0) throw new PublicChatError('limited');
    this.busy = true;
    const generation = this.generation;
    try {
      const data = await this.request('turn', { nonce: this.session.nonce, revision: this.session.revision, message }, this.session.token);
      this.update(data, generation);
      if (typeof data.reply !== 'string') throw new PublicChatError('unavailable');
      return data;
    } catch (error) {
      if (generation !== this.generation) throw new PublicChatError('ended');
      if (error instanceof PublicChatError && [401, 403, 410].includes(error.status)) {
        this.session = null;
        throw new PublicChatError('expired', error.status);
      }
      // The turn may already have run. Recover accounting once; never replay it.
      try { await this.recover(generation); } catch { /* Explicit check or restart required. */ }
      throw new PublicChatError(this.session ? 'uncertain' : 'expired');
    } finally {
      if (generation === this.generation) this.busy = false;
    }
  }

  async end() {
    const token = this.session?.token;
    const generation = ++this.generation; // Late replies cannot repopulate or display a withdrawn session.
    this.session = null;
    this.needsStatus = false;
    this.busy = true;
    try { if (token) await this.request('withdraw', {}, token); }
    finally { if (generation === this.generation) this.busy = false; }
  }
}

export function safeSources(sources) {
  if (!Array.isArray(sources)) return [];
  return sources.slice(0, 5).filter((source) => {
    if (!source || typeof source.title !== 'string' || typeof source.url !== 'string') return false;
    try { return new URL(source.url).protocol === 'https:'; } catch { return false; }
  });
}

const englishErrors = {
  expired: 'This session ended. Start a new chat when you are ready.',
  limited: 'The chat limit has been reached. Please return later or read the project links.',
  uncertain: 'The reply was not received. Your question was not resent. Check the session if needed, then send a new question.',
  connection: 'Could not connect. Please try again when you are ready.',
  unavailable: 'Chat is temporarily unavailable. You can still read the project links.',
  busy: 'Please wait for the current question, or check the session.',
  input: 'Please enter a question of up to 2,000 characters.',
  ended: 'Chat ended.',
};

/** Mount into existing Foundups/Mall controls; no authentication or access changes. */
export function mountPublicChat(host, surface = 'foundups') {
  const client = new RedDogPublicClient(surface);
  const get = (name) => host.querySelector(`[data-reddog-${name}]`);
  const form = get('form');
  const input = get('input');
  const send = get('send');
  const start = get('start');
  const end = get('end');
  const check = get('check');
  const consent = get('consent');
  const status = get('status');
  const messages = get('messages');
  if (![form, input, send, start, end, check, consent, status, messages].every(Boolean)) return;

  function render() {
    const active = !!client.session;
    consent.hidden = active;
    start.disabled = client.busy;
    end.hidden = !active;
    check.hidden = !active || !client.needsStatus;
    check.disabled = client.busy;
    input.disabled = !active || client.busy || client.needsStatus || client.session.remaining_turns <= 0;
    send.disabled = input.disabled;
    form.setAttribute('aria-busy', String(client.busy));
  }
  function note(text) { status.textContent = text; }
  function add(text, kind, sources) {
    const element = document.createElement('div');
    element.className = `chat-msg ${kind}`;
    element.textContent = text;
    for (const source of safeSources(sources)) {
      const link = document.createElement('a');
      link.href = source.url; link.textContent = source.title;
      link.target = '_blank'; link.rel = 'noopener noreferrer';
      element.append(document.createElement('br'), link);
    }
    messages.appendChild(element);
    messages.scrollTop = messages.scrollHeight;
  }
  function errorMessage(error) { return englishErrors[error.code] || englishErrors.unavailable; }
  function ready() { note(`${client.session.remaining_turns} questions remaining. Session ends after 2 minutes of inactivity or 10 minutes total.`); }

  start.addEventListener('click', async () => {
    const pending = client.start(); render(); note('Connecting…');
    try { await pending; messages.replaceChildren(); ready(); render(); input.focus(); }
    catch (error) { note(errorMessage(error)); }
    finally { render(); }
  });
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message || input.disabled) return;
    add(message, 'user'); input.value = '';
    const pending = client.send(message); render(); note('Red Dog is thinking…');
    try { const data = await pending; add(data.reply, 'bot', data.sources); ready(); }
    catch (error) { if (error.code !== 'ended') note(errorMessage(error)); }
    finally { render(); if (!input.disabled && host.getClientRects().length) input.focus(); }
  });
  check.addEventListener('click', async () => {
    const pending = client.check(); render();
    try { await pending; if (client.needsStatus) note('The previous question is still processing. Check again shortly.'); else ready(); }
    catch (error) { note(errorMessage(error)); }
    finally { render(); }
  });
  end.addEventListener('click', async () => {
    const pending = client.end(); messages.replaceChildren(); render(); note('Chat ended. Messages cleared from this page.');
    try { await pending; }
    catch { note('Messages cleared from this page. The server could not confirm the end; the session will expire automatically.'); }
    finally { render(); start.focus(); }
  });
  render();
  return client;
}
