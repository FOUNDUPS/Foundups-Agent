# Contact Memory Resolution Skill

## Identity

Owner: RedDog / 0102 relationship memory
Architecture: `extensions/reddog/docs/CONTACT_MEMORY_ARCHITECTURE.md`
Status: manual-alpha retrieval contract; runtime integration remains `SPECIFIED_NOT_IMPLEMENTED` unless separately validated.

## Objective

Resolve people quickly and safely from names, aliases, organizations, screenshots, business cards, remembered descriptions, and relationship context without repeatedly re-reading raw evidence or silently merging distinct people.

The operational pattern is:

```text
alias / description / screenshot
-> Contact Index lookup
-> stable contact ID
-> structured contact row
-> source image / card provenance when needed
-> project Breadcrumb / Mosh Pit context only as activity history
```

## Stable identity token

Every indexed contact should have one stable principal-scoped ID such as `YMC-xxxx` inside Contact Memory / Contact Index.

The stable ID belongs to the contact system. **Do not write contact IDs or contact tokens into Mosh Pit.**

## Manual-alpha source order for YUMORI

When YUMORI relationship context is available through the connected workspace, resolve in this order:

1. `YUMORI.me Contacts` -> `Contact Index` tab.
2. Canonical row in `YUMORI.me Contacts` -> `Contacts` tab.
3. `YUMORI.me Contacts Pics` for the original business-card / LINE / contact image named by `Source / Image`.
4. `YUMORI.me モッシュピット｜活動ログ` only for what happened in the operation: meetings, decisions, sends, replies, outcomes, open loops, and other breadcrumbs.
5. Gmail or other communication history only when the structured contact row and project breadcrumbs do not answer the question.

Do not begin by OCRing every image again when a verified contact index already points to the evidence.

## Resolution algorithm

1. Normalize the user's phrase but preserve the literal alias.
2. Search exact and fuzzy keys in `Contact Index`: native name, romanization, organization, role, email, aliases, and notes.
3. If one high-confidence entity matches, return the stable contact ID plus the minimum relevant context.
4. If multiple entities match an alias, return all plausible candidates and use conversation context to disambiguate. Never silently select one.
5. If the answer depends on identity spelling, title, phone, email, or organization and the field is not verified, inspect the indexed source image before asserting it.
6. If a source image corrects OCR or a prior transcription, update the structured contact row while retaining the original source filename and verification note.
7. If an interaction materially advances the project, add only the activity breadcrumb to Mosh Pit. Keep identity/contact resolution in Contact Memory.

## Alias collision rule

Aliases are many-to-many. A label such as `BB100`, `BBR100`, `the reporter`, `the investor`, or `the woman at the office` may resolve to multiple people.

Required behavior:

- preserve every candidate contact ID in Contact Index;
- prefer explicit source evidence over remembered romanization;
- never collapse two contacts because they share an organization or nickname;
- record relationship edges such as `introduced_by`, `works_at`, or `recommended` in Contact Memory rather than merging people.

The user's phrase alone is not sufficient to choose between multiple candidates.

## Image provenance rule

A contact image is evidence, not the canonical entity itself.

For every useful card / screenshot / posted-contact photo, retain in Contact Memory / Contact Index:

- stable contact ID;
- source filename or capture ID;
- extracted name / organization / handles;
- verification status;
- any OCR variants;
- a pointer from the structured contact index to that image.

Once the image has been verified, future retrieval should start from the index and only reopen the image when verification or additional detail is required.

## Mosh Pit boundary — breadcrumb only

**Mosh Pit contains no contact information. Period.**

Mosh Pit is a reverse-chronological breadcrumb trail for 012 / 0102 project activity. It may record that a meeting happened, a message was sent, a reply arrived, a decision was made, a document changed, an outcome occurred, or an open loop remains.

Do not place any of the following in Mosh Pit:

- email addresses;
- phone numbers;
- physical addresses;
- business-card data;
- source-image filenames used for identity resolution;
- alias lists;
- Contact Index rows;
- stable contact IDs or `[[CONTACT:...]]` tokens;
- copied contact profiles.

A person's name or role may appear only when it is necessary to understand the historical breadcrumb itself. It must never function as a substitute contact record.

Contact Memory answers **who the person is and how to reach/resolve them**. Mosh Pit answers **what happened**.

## Write-back rule

When new evidence materially improves identity resolution:

1. update the structured contact row;
2. ensure the contact appears in the Contact Index;
3. attach/preserve the source image pointer in the contact system;
4. add aliases or OCR variants without replacing the canonical verified name;
5. add a Mosh Pit breadcrumb only if a project-relevant event occurred, and keep it free of contact information;
6. preserve uncertainty on readings/romanizations until verified.

## Privacy / truth boundary

- Contact data is principal-scoped and not public by default.
- Do not publish raw emails, phones, addresses, cards, screenshots, IDs, or aliases merely because they are indexed.
- Keep `VERIFIED`, `REPORTED`, `OCR`, and `UNVERIFIED` distinctions visible.
- A contact index entry is not consent, support, committee membership, investment commitment, or authority.
- Never claim the automated Contact Memory runtime is active merely because the manual-alpha Google Sheet / Docs workflow works.
