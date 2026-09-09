import { sql } from 'drizzle-orm';
import { sqliteTable, text, integer, primaryKey, check } from 'drizzle-orm/sqlite-core';

// New, public-only accounting tables. Existing interest DDL below is retained.
export const redDogBudget = sqliteTable('reddog_web_budget_v1', {
  bucket: text('bucket').notNull(), day: integer('day').notNull(),
  used: integer('used').notNull(), maximum: integer('maximum').notNull(),
}, t => [primaryKey({columns:[t.bucket,t.day]}), check('reddog_budget_bounds',sql`${t.used} >= 0 AND ${t.used} <= ${t.maximum}`)]);
export const redDogSession = sqliteTable('reddog_web_session_v1', {
  tokenHash:text('token_hash').primaryKey(), surface:text('surface').notNull(), origin:text('origin').notNull(),
  subject:text('subject').notNull(), created:integer('created').notNull(), lastSeen:integer('last_seen').notNull(),
  revision:integer('revision').notNull(), nonce:text('nonce').notNull(), busy:text('busy'),
  closed:integer('closed').notNull().default(0),
}, t => [check('reddog_revision_bounds',sql`${t.revision} >= 0 AND ${t.revision} <= 10`)]);
export const redDogClock = sqliteTable('reddog_web_clock_v1', {
  id:integer('id').primaryKey(), lastSeen:integer('last_seen').notNull(),
}, t => [check('reddog_clock_bounds',sql`${t.id} = 1 AND ${t.lastSeen} >= 0`)]);

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
