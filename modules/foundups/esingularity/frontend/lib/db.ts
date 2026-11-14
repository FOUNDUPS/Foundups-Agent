import { env } from 'cloudflare:workers';
import { createInterestCreatedIndex, createInterestTable, createInterestAdmissionTable, createInterestAdmissionTimeIndex, createInterestAdmissionClientIndex, createInterestEmailIndex, insertInterestWithLimits, insertInterestAdmission, pruneInterestAdmission } from '@/db/schema';
import type { InterestInput } from '@/lib/interest';

type SiteEnv = { DB: D1Database };
export async function saveCommunityInterest(input: InterestInput, client: string): Promise<boolean> {
  const db = (env as unknown as SiteEnv).DB;
  await db.batch([createInterestTable, createInterestCreatedIndex, createInterestAdmissionTable, createInterestAdmissionTimeIndex, createInterestAdmissionClientIndex, createInterestEmailIndex].map(sql => db.prepare(sql)));
  const now = Date.now();
  const id = crypto.randomUUID();
  // Daily rotation avoids retaining a stable visitor identifier. This is
  // pseudonymization, not a claim that an IP digest is anonymous.
  const keys = await Promise.all([now, now - 86400000].map(async day => {
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(`${new Date(day).toISOString().slice(0, 10)}:${client}`));
    return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
  }));
  const [clientKey, previousClientKey] = keys;
  const epoch = Math.floor(now / 1000);
  const results = await db.batch([
    db.prepare(insertInterestWithLimits).bind(id, input.name, input.email, input.relationship, input.story, new Date(now).toISOString(), new Date(now - 86400000).toISOString(), epoch - 3600, clientKey, previousClientKey),
    db.prepare(insertInterestAdmission).bind(id, clientKey, epoch),
    db.prepare(pruneInterestAdmission).bind(epoch - 3600),
  ]);
  return results[0].meta.changes === 1;
}
