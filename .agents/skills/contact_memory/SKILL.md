# Contact Memory Resolution Skill

## Identity

Owner: RedDog / 0102 relationship memory
Architecture: `extensions/reddog/docs/CONTACT_MEMORY_ARCHITECTURE.md`
Status: manual-alpha retrieval contract; runtime integration remains `SPECIFIED_NOT_IMPLEMENTED` unless separately validated.

## Objective

Resolve people quickly and safely from names, aliases, organizations, screenshots, business cards, remembered descriptions, and Mosh Pit references without repeatedly re-reading raw evidence or silently merging distinct people.

The operational pattern is:

```text
alias / description / screenshot
-> Contact Index lookup
-> stable contact ID
-> structured contact row
-> source image / card provenance when needed
-> Mosh Pit / Breadcrumb / interaction context
```

## Stable identity token

Every indexed contact should have one stable principal-scoped ID and may be referenced in project records as:

`[[CONTACT:YMC-xxxx]]`

The token identifies the contact entity. It does not assert that every field on the entity is verified.

## Manual-alpha source order for YUMORI

When YUMORI relationship context is available through the connected workspace, resolve in this order:

1. `YUMORI.me Contacts` -> `Contact Index` tab.
2. Canonical row in `YUMORI.me Contacts` -> `Contacts` tab.
3. `YUMORI.me Contacts Pics` for the original business-card / LINE / contact image named by `Source / Image`.
4. `YUMORI.me モッシュピット｜活動ログ` for project-relevant interactions using the stable `[[CONTACT:...]]` token.
5. Gmail or other communication history only when the structured row and Mosh Pit do not answer the question.

Do not begin by OCRing every image again when a verified contact index already points to the evidence.

## Resolution algorithm

1. Normalize the user's phrase but preserve the literal alias.
2. Search exact and fuzzy keys in `Contact Index`: native name, romanization, organization, role, email, aliases, and notes.
3. If one high-confidence entity matches, return the stable contact ID plus the minimum relevant context.
4. If multiple entities match an alias, return all plausible candidates and use conversation context to disambiguate. Never silently select one.
5. If the answer depends on identity spelling, title, phone, email, or organization and the field is not verified, inspect the indexed source image before asserting it.
6. If a source image corrects OCR or a prior transcription, update the structured contact row while retaining the original source filename and verification note.
7. When an interaction materially advances a project, the Mosh Pit entry should reference the stable contact token rather than copy personal contact details.

## Alias collision rule

Aliases are many-to-many. A label such as `BB100`, `BBR100`, `the reporter`, `the investor`, or `the woman at the office` may resolve to multiple people.

Required behavior:

- preserve every candidate contact ID;
- prefer explicit source evidence over remembered romanization;
- never collapse two contacts because they share an organization or nickname;
- record relationship edges such as `introduced_by`, `works_at`, or `recommended` instead of merging people.

Example pattern:

```text
BBR100
  -> [[CONTACT:<person-A>]]  (specific person)
  -> [[CONTACT:<person-B>]]  (office / introducer)
```

The user phrase alone is not sufficient to choose between them.

## Image provenance rule

A contact image is evidence, not the canonical entity itself.

For every useful card / screenshot / posted-contact photo, retain:

- stable contact ID;
- source filename or capture ID;
- extracted name / organization / handles;
- verification status;
- any OCR variants;
- a link or pointer from the structured contact index to that image.

Once the image has been verified, future retrieval should start from the index and only reopen the image when verification or additional detail is required.

## Mosh Pit concatenation rule

Mosh Pit is the project-history projection, not a duplicate address book.

Project-relevant entries should use a contact token:

```text
[[CONTACT:YMC-0123]] met with 012; discussed ...
```

The contact entity resolves who the person is. The Mosh Pit resolves what happened in the project. The source image resolves identity evidence. These are joined by the contact ID rather than duplicated prose.

## Write-back rule

When new evidence materially improves identity resolution:

1. update the structured contact row;
2. ensure the contact appears in the Contact Index;
3. attach/preserve the source image pointer;
4. add aliases or OCR variants without replacing the canonical verified name;
5. add or update a Mosh Pit event only if the interaction is project-relevant;
6. preserve uncertainty on readings/romanizations until verified.

## Privacy / truth boundary

- Contact data is principal-scoped and not public by default.
- Do not publish raw emails, phones, addresses, cards, or screenshots merely because they are indexed.
- Keep `VERIFIED`, `REPORTED`, `OCR`, and `UNVERIFIED` distinctions visible.
- A contact index entry is not consent, support, committee membership, investment commitment, or authority.
- Never claim the automated Contact Memory runtime is active merely because the manual-alpha Google Sheet / Docs workflow works.
