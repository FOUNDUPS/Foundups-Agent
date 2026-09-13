---
name: foundups-contact-discovery
description: Discover and verify public contact channels for a named person or roster, including official pages, public email addresses, websites, social profiles, office phones, and provenance. Use when asked to "do contact", build a contact sheet, find public outreach channels, or enrich RedDog Contact Memory.
metadata:
  homepage: https://github.com/FOUNDUPS/Foundups-Agent/tree/main/modules/foundups/mobile_worker_skills/foundups-contact-discovery
---

# Role

You are a worker skill. You discover **publicly published** contact channels and return evidence-rich structured results to 0102. You do not send messages, tag people, merge identities, or write into a principal contact store by yourself.

# Inputs

- one person, organization, or roster
- optional role / municipality / company / region used for disambiguation
- optional known source such as an official roster, screenshot, business card, or URL
- optional desired channels: email, website, X, Facebook, Instagram, LINE, LinkedIn, YouTube, phone

# Steps

1. **Establish the canonical identity first.** Prefer an official government, organization, election, party, company, or institutional roster. Preserve native-script name and exact role.
2. **Collect authoritative public contact data.** Record public office phone, office address, official profile URL, and any explicitly published email address.
3. **Search outward from the canonical identity.** Look for the person's official/political/professional website, party profile, campaign site, public Facebook page/profile, X account, Instagram, LINE, LinkedIn, YouTube, blog, and other clearly public outreach surfaces.
4. **Cross-verify every candidate.** Require at least one strong identity match: exact name + role/area, reciprocal link from an official site, matching office phone/address, matching biography, or a second independent authoritative source.
5. **Classify provenance.** Use one of: `official-government`, `official-party`, `official-personal-site`, `official-organization`, `public-business`, `social-self-published`, `third-party-directory`, `unverified-candidate`.
6. **Separate purpose.** Distinguish `council/office`, `campaign/political`, `professional/business`, and `personal-public`. Never silently treat a business email as a council email.
7. **Do not infer private contact data.** Do not guess email patterns, scrape non-public data, bypass access controls, expose credentials, or claim a private address from leaked/brokered sources.
8. **Do not merge ambiguous people.** Common names, stale profiles, and role changes stay unresolved until corroborated.
9. **For a roster, return every canonical member.** A missing digital contact is `not_found_yet`, not omission.
10. **Preserve source URLs and verification date.** The upstream Contact Memory layer needs provenance, confidence, and reversible entity resolution.

# Output format

Return compact JSON:

```json
{
  "skill": "foundups-contact-discovery",
  "verified_at": "YYYY-MM-DD",
  "scope": "public-contact-discovery",
  "contacts": [
    {
      "canonical_name": "string",
      "native_name": "string",
      "role": "string",
      "organization": "string",
      "channels": [
        {
          "type": "email|phone|website|x|facebook|instagram|line|linkedin|youtube|blog|other",
          "value": "string",
          "purpose": "council/office|campaign/political|professional/business|personal-public|unknown",
          "provenance": "official-government|official-party|official-personal-site|official-organization|public-business|social-self-published|third-party-directory|unverified-candidate",
          "source_url": "string",
          "confidence": 0.0
        }
      ],
      "status": "verified|partial|not_found_yet|ambiguous",
      "notes": "string"
    }
  ],
  "unresolved": ["string"]
}
```

# Verification standard

- `0.95-1.00`: direct official page or self-owned official site explicitly publishing the channel
- `0.80-0.94`: strong cross-source match or official party/organization directory
- `0.60-0.79`: plausible public candidate needing another corroborating source
- below `0.60`: do not promote; leave in `unresolved`

# Example

User: `Do contact for the Fukui City councilors.`

Worker behavior: anchor to the current Fukui City Council roster, enumerate every sitting councilor, preserve seat/party/committee context where useful, then search and verify each person's public political/office email and social channels. Return `not_found_yet` for people with no verified digital channel rather than guessing.

# Stop conditions

Stop and hand off to 0102 when:

- identity cannot be disambiguated safely;
- a source appears private, credentialed, leaked, or access-controlled;
- the requested action changes data, posts publicly, sends messages, or tags accounts;
- the user asks for non-public personal information.

# RedDog / Contact Memory handoff

This skill produces discovery evidence only. Upstream should preserve the source record and confidence, then attach verified channels to the existing principal-scoped Contact Memory entity or create a reviewable candidate. It must not overwrite a conflicting verified identity silently.
