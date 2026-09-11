import { sql } from 'drizzle-orm';
import { check, index, integer, primaryKey, sqliteTable, text, uniqueIndex } from 'drizzle-orm/sqlite-core';

export const redDogWebBudget = sqliteTable('reddog_web_budget_v2', {
  bucket: text('bucket').notNull(),
  day: integer('day').notNull(),
  used: integer('used').notNull(),
  maximum: integer('maximum').notNull(),
  updated: integer('updated').notNull(),
}, (table) => [
  primaryKey({ columns: [table.bucket, table.day] }),
  check('reddog_web_budget_v2_bounds', sql`${table.used} >= 0 AND ${table.maximum} > 0 AND ${table.used} <= ${table.maximum}`),
]);

export const redDogWebSession = sqliteTable('reddog_web_session_v2', {
  tokenHash: text('token_hash').primaryKey(),
  encounter: text('encounter').notNull(),
  surface: text('surface').notNull(),
  origin: text('origin').notNull(),
  subject: text('subject').notNull(),
  actorClaim: text('actor_claim').notNull(),
  created: integer('created').notNull(),
  lastSeen: integer('last_seen').notNull(),
  revision: integer('revision').notNull(),
  nonce: text('nonce').notNull(),
  busy: text('busy'),
  busyUntil: integer('busy_until'),
  closing: integer('closing').notNull().default(0),
}, (table) => [
  uniqueIndex('idx_reddog_web_session_v2_encounter').on(table.encounter),
  index('idx_reddog_web_session_v2_expiry').on(table.created, table.lastSeen),
  index('idx_reddog_web_session_v2_busy_until').on(table.busyUntil),
  check('reddog_web_session_v2_token', sql`length(${table.tokenHash}) = 64`),
  check('reddog_web_session_v2_revision', sql`${table.revision} >= 0 AND ${table.revision} <= 10`),
  check('reddog_web_session_v2_clock', sql`${table.created} >= 0 AND ${table.lastSeen} >= ${table.created}`),
  check('reddog_web_session_v2_closing', sql`${table.closing} IN (0, 1)`),
  check('reddog_web_session_v2_busy_pair', sql`(${table.busy} IS NULL AND ${table.busyUntil} IS NULL) OR (${table.busy} IS NOT NULL AND ${table.busyUntil} IS NOT NULL)`),
]);

export const redDogWebLick = sqliteTable('reddog_web_lick_v1', {
  tokenHash: text('token_hash').primaryKey().references(() => redDogWebSession.tokenHash, { onDelete: 'cascade' }),
  profileId: text('profile_id').notNull(),
  displayName: text('display_name'),
  challengeHash: text('challenge_hash').notNull(),
  challengeComplete: integer('challenge_complete').notNull().default(0),
  consentVersion: text('consent_version').notNull(),
}, (table) => [
  uniqueIndex('idx_reddog_web_lick_v1_profile').on(table.profileId),
  check('reddog_web_lick_v1_challenge', sql`(${table.challengeComplete} = 0 AND length(${table.challengeHash}) = 64) OR (${table.challengeComplete} = 1 AND ${table.challengeHash} = '')`),
  check('reddog_web_lick_v1_display', sql`${table.displayName} IS NULL OR length(${table.displayName}) <= 80`),
]);

export const redDogWebClock = sqliteTable('reddog_web_clock_v2', {
  id: integer('id').primaryKey(),
  lastSeen: integer('last_seen').notNull(),
}, (table) => [
  check('reddog_web_clock_v2_bounds', sql`${table.id} = 1 AND ${table.lastSeen} >= 0`),
]);

export const createInterestTable = `
  CREATE TABLE IF NOT EXISTS community_interest (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    relationship TEXT NOT NULL,
    story TEXT,
    consent INTEGER NOT NULL CHECK (consent = 1),
    created_at TEXT NOT NULL
  )
`;

export const createInterestCreatedIndex = `
  CREATE INDEX IF NOT EXISTS idx_community_interest_created_at
  ON community_interest(created_at)
`;
