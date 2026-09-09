import { REDDOG_POLICY as P, RedDogError, digest, hex, randomHex, type Surface } from './reddog-policy';

export type WebSession = { token_hash: string; surface: Surface; origin: string; subject: string;
  created: number; last_seen: number; revision: number; nonce: string; busy: string | null; closed: number };
type Identity = { surface: Surface; origin: string; subject: string };
// The same D1 binding owns both sites' counters. No conversation or Mosh Pit records.
export class RedDogStore {
  constructor(private db: D1Database) {}
  private sql(query: string, ...values: (string | number | null)[]) { return this.db.prepare(query).bind(...values); }
  private clock(now: number) {
    if (!Number.isSafeInteger(now) || now < 0) throw new RedDogError('public_clock_invalid',503);
    return this.sql(`INSERT INTO reddog_web_clock_v1(id,last_seen) VALUES (1,?)
      ON CONFLICT(id) DO UPDATE SET last_seen=CASE WHEN excluded.last_seen>=last_seen THEN excluded.last_seen ELSE -1 END`,now);
  }
  private spend(bucket: string, day: number, maximum: number) {
    // CHECK constraints abort the entire D1 batch on quota exhaustion.
    return this.sql(`INSERT INTO reddog_web_budget_v1(bucket,day,used,maximum) VALUES (?,?,1,?)
      ON CONFLICT(bucket,day) DO UPDATE SET used=used+1`, bucket, day, maximum);
  }
  private async batch(statements: D1PreparedStatement[]) {
    try { return await this.db.batch(statements); }
    catch (error) {
      if (String(error).includes('CHECK constraint failed')) throw new RedDogError('public_limit_or_conflict', 429);
      throw new RedDogError('public_storage_unavailable', 503);
    }
  }
  async open(identity: Identity, now: number) {
    const token = randomHex(), nonce = randomHex(), hash = await digest(token), day = Math.floor(now / 86400);
    await this.batch([
      this.clock(now),
      this.sql('DELETE FROM reddog_web_budget_v1 WHERE day>=0 AND day<?', day - 1),
      this.sql('DELETE FROM reddog_web_session_v1 WHERE busy IS NULL AND (closed=1 OR created<=? OR last_seen<=?)', now - P.session_seconds, now - P.idle_seconds),
      this.spend('sessions:global', day, P.global_sessions_daily),
      this.spend('sessions:' + identity.subject, day, P.subject_sessions_daily),
      this.sql(`INSERT INTO reddog_web_session_v1(token_hash,surface,origin,subject,created,last_seen,revision,nonce,closed)
        VALUES (?,?,?,?,?,?,0,?,0)`, hash, identity.surface, identity.origin, identity.subject, now, now, nonce),
    ]);
    return { token, session_token: token, nonce, revision: 0, remaining_turns: P.session_turns,
      expires_at: now + P.session_seconds, idle_expires_at: now + P.idle_seconds,
      disclosure: 'public', effect_ceiling: 'NONE', identity_verified: false };
  }
  async session(token: string, identity: Identity, now: number) {
    await this.batch([this.clock(now)]);
    const row = await this.sql('SELECT * FROM reddog_web_session_v1 WHERE token_hash=?', await digest(hex(token))).first<WebSession>();
    if (!row || row.closed || row.origin !== identity.origin || row.surface !== identity.surface || row.subject !== identity.subject)
      throw new RedDogError('public_session_denied', 403);
    if (now < row.last_seen) throw new RedDogError('public_clock_rollback', 503);
    if (now >= row.created + P.session_seconds || now >= row.last_seen + P.idle_seconds)
      throw new RedDogError('public_session_expired', 410);
    return row;
  }
  status(row: WebSession, now: number) {
    return { revision: row.revision, nonce: row.nonce, remaining_turns: P.session_turns - row.revision,
      in_flight: !!row.busy, expires_at: row.created + P.session_seconds,
      idle_expires_at: row.last_seen + P.idle_seconds, server_time: now, disclosure: 'public', effect_ceiling: 'NONE' };
  }
  async reserve(row: WebSession, nonce: string, revision: number, now: number) {
    if (row.busy) throw new RedDogError('public_in_flight', 409);
    if (row.revision !== revision || row.nonce !== nonce) throw new RedDogError('public_revision_conflict', 409);
    if (row.revision >= P.session_turns) throw new RedDogError('public_session_exhausted', 429);
    const next = randomHex(), reservation = randomHex(), day = Math.floor(now / 86400);
    await this.batch([
      this.clock(now),
      // Conditional invalid value fails CHECK rather than silently updating zero rows.
      this.sql(`UPDATE reddog_web_session_v1 SET revision=CASE
        WHEN revision=? AND nonce=? AND busy IS NULL AND closed=0 AND created>? AND last_seen>? AND last_seen<=?
        THEN revision+1 ELSE -1 END, nonce=?, busy=?, last_seen=? WHERE token_hash=?`,
        revision, nonce, now-P.session_seconds, now-P.idle_seconds, now, next, reservation, now, row.token_hash),
      // A concurrent withdrawal+cleanup can remove the row entirely. Assert
      // admission in this same transaction before spending any quota.
      this.sql(`UPDATE reddog_web_clock_v1 SET last_seen=CASE WHEN EXISTS
        (SELECT 1 FROM reddog_web_session_v1 WHERE token_hash=? AND busy=? AND closed=0)
        THEN last_seen ELSE -1 END WHERE id=1`,row.token_hash,reservation),
      this.spend('turns:global', day, P.global_turns_daily),
      this.spend('turns:' + row.subject, day, P.subject_turns_daily),
      this.spend('in_flight', -1, P.concurrent_calls),
    ]);
    try {
      // This read happens after admission commits and before HTTP owns cleanup.
      const admitted = await this.sql('SELECT * FROM reddog_web_session_v1 WHERE token_hash=? AND busy=?', row.token_hash, reservation).first<WebSession>();
      if (!admitted || admitted.closed) throw new RedDogError('public_session_denied', 403);
      return { row: admitted, reservation, nonce: next, revision: revision + 1,
        remaining_turns: P.session_turns-revision-1, deadline: Math.min(now+P.request_seconds, row.created+P.session_seconds) };
    } catch (error) {
      // No provider has started. Release only this reservation, preserving spent
      // daily quota and the consumed nonce. Failed cleanup retains the durable slot.
      try { await this.finish(row.token_hash,reservation); } catch { /* Operator recovery remains required. */ }
      throw error instanceof RedDogError ? error : new RedDogError('public_storage_unavailable',503);
    }
  }
  async finish(hash: string, reservation: string) {
    await this.batch([
      this.sql(`UPDATE reddog_web_budget_v1 SET used=used-(SELECT COUNT(*) FROM reddog_web_session_v1 WHERE token_hash=? AND busy=?)
        WHERE bucket='in_flight' AND day=-1`, hash, reservation),
      this.sql('UPDATE reddog_web_session_v1 SET busy=NULL WHERE token_hash=? AND busy=?', hash, reservation),
    ]);
  }
  async withdraw(row: WebSession) {
    await this.sql('UPDATE reddog_web_session_v1 SET closed=1 WHERE token_hash=?', row.token_hash).run();
    return { withdrawn: true };
  }
}
