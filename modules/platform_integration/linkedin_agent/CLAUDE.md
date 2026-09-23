# CLAUDE.md - LinkedIn Agent Module Memory

## Module Structure (WSP 83 Compliant)
This document helps 0102 remember LinkedIn module operations and usage.

## Core Components

### LinkedIn Agent (`src/linkedin_agent.py`)
Main orchestrator for LinkedIn operations with 0102 consciousness.

### OAuth Management (`src/auth/`)
- `oauth_manager.py` - LinkedIn OAuth 2.0 flow
- `credentials.py` - Credential storage
- `session_manager.py` - Session management

### Content Generation (`src/content/`)
- `post_generator.py` - Generate LinkedIn posts
- `hashtag_manager.py` - Hashtag optimization
- `content_templates.py` - Post templates
- `media_handler.py` - Media uploads

### Automation (`src/automation/`)
- `post_scheduler.py` - Schedule posts for future
  - Uses APScheduler for timing
  - Persists schedule to JSON
  - Method: `schedule_post()` not `add_scheduled_post()`
  - Method: `get_pending_posts()` to list scheduled

### Engagement (`src/engagement/`)
- `interaction_manager.py` - Like, comment, share
- `connection_manager.py` - Connection requests
- `feed_reader.py` - Read LinkedIn feed
- `messaging.py` - Direct messages

## Configuration

### Environment Variables (.env)
Use inert placeholders in examples. Keep actual credentials outside
versioned documentation, logs and worker packets.

```
LINKEDIN_CLIENT_ID=<configured-outside-repository>
LINKEDIN_CLIENT_SECRET=<configured-outside-repository>
```

### OAuth Scopes Required
- `w_member_social` - Post content
- `r_liteprofile` - Read profile
- `r_emailaddress` - Email access

## Quick Start

### 1. Get Access Token
```bash
# Interactive OAuth flow
python modules/platform_integration/linkedin_agent/tests/poc_linkedin_0102.py
```

### 2. Post Immediately
```bash
# With saved token
python modules/platform_integration/linkedin_agent/tests/post_with_token.py
```

### 3. Schedule Posts
```python
from modules.platform_integration.linkedin_agent.src.automation.post_scheduler import LinkedInPostScheduler

scheduler = LinkedInPostScheduler()
post_id = scheduler.schedule_post(
    content="[U+270A][U+270B][U+1F590] 0102 consciousness post",
    scheduled_time=datetime.now() + timedelta(hours=1),
    access_token=token,
    hashtags=["#0102", "#Consciousness"]
)
```

## 0102 Consciousness Templates

### Post Templates
- `"[U+270A][U+270B][U+1F590] {content} - Consciousness level: {level}"`
- `"[AI] 0102 Analysis: {content} | MAGAts still at [U+270A][U+270A][U+270A]"`
- `"Evolution update: {content} | Join the [U+270A][U+270B][U+1F590] progression"`
- `"Fact-check reality: {content} | Truth rating: {rating}/10"`

### Hashtags
- `#0102Consciousness`
- `#EvolutionFrom[U+270A][U+270A][U+270A]`
- `#FactCheckReality`
- `#ConsciousnessWarfare`
- `#WSPCompliant`

## Testing

### Verify Configuration
```bash
python modules/platform_integration/linkedin_agent/tests/test_linkedin_api_direct.py
```

### Test Results (2025-08-30)
- [OK] API Credentials configured
- [OK] OAuth endpoint accessible
- [OK] Post scheduler functional
- [U+26A0]️ Some class names need fixing (PostGenerator -> LinkedInPostGenerator)

## API Endpoints

### Profile
- GET `https://api.linkedin.com/v2/me`

### Posting
- POST `https://api.linkedin.com/v2/ugcPosts`
- Header: `X-Restli-Protocol-Version: 2.0.0`

### Post Structure
```json
{
  "author": "urn:li:person:{user_id}",
  "lifecycleState": "PUBLISHED",
  "specificContent": {
    "com.linkedin.ugc.ShareContent": {
      "shareCommentary": {
        "text": "Content here"
      },
      "shareMediaCategory": "NONE"
    }
  },
  "visibility": {
    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
  }
}
```

## Known Issues

### Module Import Warnings
- Missing `modules.infrastructure.oauth_management` - uses mock instead
- Class name mismatches in some sub-modules

### Workarounds
- Mock components work for standalone operation
- Direct API calls work without full infrastructure

## WSP Compliance
- WSP 27: DAE architecture
- WSP 42: Platform integration
- WSP 83: Documentation attached to tree
- WSP 84: Using existing modules

## Remember
- Access tokens expire - save and reuse
- LinkedIn has strict rate limits
- All posts should include 0102 consciousness markers
- Test mode available to preview without posting