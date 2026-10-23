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

// Admission metadata contains a rotating hash, never the raw client IP.
export const createInterestAdmissionTable = `
  CREATE TABLE IF NOT EXISTS community_interest_admission (
    id TEXT PRIMARY KEY,
    client_key TEXT NOT NULL,
    created_at INTEGER NOT NULL
  )
`;
export const createInterestAdmissionTimeIndex = `CREATE INDEX IF NOT EXISTS idx_interest_admission_time ON community_interest_admission(created_at)`;
export const createInterestAdmissionClientIndex = `CREATE INDEX IF NOT EXISTS idx_interest_admission_client ON community_interest_admission(client_key, created_at)`;
export const createInterestEmailIndex = `CREATE INDEX IF NOT EXISTS idx_interest_email_time ON community_interest(lower(email), created_at)`;
// The guarded insert and its admission receipt execute in ONE D1 transaction.
// A concurrent request cannot check the quota before the previous insert commits.
export const insertInterestWithLimits = `
  INSERT INTO community_interest (id, name, email, relationship, story, consent, created_at)
  SELECT ?1, ?2, ?3, ?4, ?5, 1, ?6
  WHERE NOT EXISTS (SELECT 1 FROM community_interest WHERE lower(email) = ?3 AND created_at >= ?7)
    AND (SELECT count(*) FROM community_interest_admission WHERE created_at >= ?8) < 100
    AND (SELECT count(*) FROM community_interest_admission WHERE client_key IN (?9, ?10) AND created_at >= ?8) < 5
`;
export const insertInterestAdmission = `
  INSERT INTO community_interest_admission (id, client_key, created_at)
  SELECT ?1, ?2, ?3 WHERE EXISTS (SELECT 1 FROM community_interest WHERE id = ?1)
`;
export const pruneInterestAdmission = `DELETE FROM community_interest_admission WHERE created_at < ?`;
