# Public/private boundary

This repository is public. Use explicit file and field allowlists, never a whole
workspace copy, transcript dump, mailbox export or source-history mirror.

## Admitted here

- Public website generator, layout, CSS, JavaScript and SEO metadata.
- Public documentary titles, role descriptions and programme links already on
  hornethunter.com.
- Public responder forms, personal LinkedIn URL, published offer prices and
  their status labels.
- Sanitized maintenance decisions, validation outcomes and pending work.
- Published image URLs and checksums; retain privacy-edited versions.

## Keep outside this repository

- Passwords, keys, session cookies, bearer tokens, authentication files, browser
  profiles, environment files and connector/tool output dumps.
- Email bodies, email addresses harvested from correspondence, private contacts,
  agreements, fees, unpublished credits discussions and removed-footage details.
- Form responses, customer records, phone numbers, interview or medical details.
- Google Docs/Forms editor URLs, private document IDs and response spreadsheets.
- The unpublished manual, full narration/transcripts, proprietary filming or
  wrangling methods, precise unpublished field locations and training IP.
- Original unblurred photographs and unpublished media.

The paid manual remains a separate private content product. Public Git retains
its product description and development status only. If material is later
approved for publication, admit that exact excerpt through a separate review.

## Review before each update

Inspect every added file and new string, including commit/PR text. Run repository
secret scanning plus a content review: automated secret detectors cannot decide
whether a production detail or technique is confidential. `.gitignore` is only a
convenience and does not stop forced additions. Do not publish a discovered
secret in an issue or log; use the private incident process and rotate it.
