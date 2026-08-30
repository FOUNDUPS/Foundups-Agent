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
