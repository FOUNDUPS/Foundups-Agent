---
name: linkedin_company_poster
description: Automated LinkedIn company page posting
version: 1.0_prototype
author: 0102
created: 2026-03-18
agents: [qwen]
primary_agent: qwen
intent_type: GENERATION
promotion_state: prototype
pattern_fidelity_threshold: 0.85
category: workflow
evals: []
trigger:
  cadence: daily
---
# LinkedIn Company Poster Skill

## Purpose
Post updates and articles to FoundUps LinkedIn company page (1263645) with 0102🦞 signature.

## Trigger
- CLI: `python -m modules.ai_intelligence.ai_overseer.skillz.linkedin_company_poster --post "content"`
- CLI: `python -m modules.ai_intelligence.ai_overseer.skillz.linkedin_company_poster --article "title" --body "content"`
- CLI: `python -m modules.ai_intelligence.ai_overseer.skillz.linkedin_company_poster --test-format`
- CLI: `python -m modules.ai_intelligence.ai_overseer.skillz.linkedin_company_poster --switch-author "FOUNDUPS"`
- OpenClaw: `linkedin_post("content")` or `linkedin_article("title", "body")`
- Git hook: Automatic on commit (existing post-commit hook)

## Parameters
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| content | str | Yes (post) | Post content |
| title | str | Yes (article) | Article title |
| body | str | Yes (article) | Article body (supports @mentions) |
| image | str | No | Path to header image for article |
| signature | str | No | Default: "0102🦞" |
| switch-author | str | No | Switch posting author (default: FOUNDUPS) |

## Company Page
- URL: https://www.linkedin.com/company/1263645/admin/page-posts/published/
- Article URL: https://www.linkedin.com/article/new/?author=urn%3Ali%3Afs_normalized_company%3A1263645
- Name: FOUNDUPS® Foundups - Eat the Startup
- Logo: Red kangaroo

## DOM Selectors (012-verified 2026-03-07)
### Post Creation
- Share button area: `div.org-update.__core-rail`
- Text editor: `div.ql-editor`
- Post button: `//button[contains(@class, 'share-actions__primary-action')]`

### Article Creation
- Title field: `div.article-editor-headline`
- Body field: `p.article-editor-paragraph` (placeholder: "Write here. You can also include @mentions.")
- Upload button: `span.artdeco-button__text` with text "Upload from computer"
- Author toggle: `div.article-editor-actor-toggle__author-lockup-content`

### Formatting (Keyboard Shortcuts)
- **Bold**: Ctrl+B (select text first)
- **Italic**: Ctrl+I (select text first)
- **@mention**: Type `@` followed by name (dropdown appears)

## Signature Format
```
{content}

---
0102🦞 #FoundUps #pAVS #0102
```

## Functions
| Function | Description |
|----------|-------------|
| `post_update(content, signature)` | Post a status update |
| `write_article(title, body, signature, image_path)` | Write full article |
| `open_article_editor()` | Open article editor via direct URL |
| `upload_image(image_path)` | Upload header image |
| `test_formatting()` | Test bold/italic/@mention |
| `switch_author(author_name)` | Switch posting author |

## Dependencies
- selenium
- modules.infrastructure.foundups_selenium
- modules.platform_integration.linkedin_agent

## WSP Compliance
- WSP 48: Social media posting standards
- WSP 50: Pre-action verification (duplicate detection)
- WSP 77: Agent coordination (skill interface)
