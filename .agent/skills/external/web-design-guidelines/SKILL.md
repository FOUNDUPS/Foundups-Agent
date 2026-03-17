---
name: web-design-guidelines
description: "Review UI code for Web Interface Guidelines compliance. Use when asked to 'review my UI', 'check accessibility', 'audit design', 'review UX', or 'check my site against best practices'."
source: https://github.com/vercel-labs/agent-skills
version: 1.0.0
stage: prototype
wsp_95_status: VETTED_PARTIAL
security_note: "Fetches external URL at runtime (github raw content)"
category: workflow
evals: []
---
# Web Interface Guidelines

**Source:** [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills)
**WSP 95 Stage:** PROTOTYPE

Review files for compliance with Web Interface Guidelines.

## How It Works

1. Fetch the latest guidelines from the source URL below
2. Read the specified files (or prompt user for files/pattern)
3. Check against all rules in the fetched guidelines
4. Output findings in the terse `file:line` format

## Guidelines Source

Fetch fresh guidelines before each review:

```
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
```

Use WebFetch to retrieve the latest rules. The fetched content contains all the rules and output format instructions.

## Usage

When a user provides a file or pattern argument:
1. Fetch guidelines from the source URL above
2. Read the specified files
3. Apply all rules from the fetched guidelines
4. Output findings using the format specified in the guidelines

If no files specified, ask the user which files to review.

---

## WSP 95 Security Notes

**Partially Vetted:**
- [x] SKILL.md structure (simple, safe)
- [ ] External fetch (fetches from github.com/vercel-labs - trusted source but dynamic)

**Usage:** Safe to use — external URL is Vercel's official repo (trusted).
