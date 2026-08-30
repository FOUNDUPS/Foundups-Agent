import { env } from 'cloudflare:workers';
import { createInterestCreatedIndex, createInterestTable } from '@/db/schema';

type SiteEnv = { DB: D1Database };

function database() {
  return (env as unknown as SiteEnv).DB;
}

export async function saveCommunityInterest(input: {
  name: string;
  email: string;
  relationship: string;
  story: string | null;
}) {
  const db = database();
  await db.batch([
    db.prepare(createInterestTable),
    db.prepare(createInterestCreatedIndex),
  ]);

  const id = crypto.randomUUID();
  const createdAt = new Date().toISOString();
  await db.prepare(`
    INSERT INTO community_interest
      (id, name, email, relationship, story, consent, created_at)
    VALUES (?, ?, ?, ?, ?, 1, ?)
  `).bind(id, input.name, input.email, input.relationship, input.story, createdAt).run();

  return { id, createdAt };
}
