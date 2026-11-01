# LLM Integration for YouTube Comments

## Current Studio route (2026-11-01)

The inspected Studio posting path is `CommentProcessor` →
`IntelligentReplyGenerator`, not the older `LLMCommentGenerator` example below.
It reads the full comment and bound author/channel/video context, assesses its
meaning, drafts an answer, and separately reviews the exact final text against
the original and supplied facts. UI-TARS checks the browser visually; it does
not write replies or judge their language meaning.

The language route tries the configured general-role LM Studio service, then
embedded general Qwen for stored comments. Legacy xAI Grok drafting requires
`YT_ENABLE_GROK_REPLIES=true`; it is not an OpenRouter call. Assessment and review
remain local. The private livechat fallback uses local HTTP only, whereas the
separate ordinary livechat generator can use its existing xAI client. Do not
infer the active provider from old class names, a model listing, or this document.

The prepared Windows profile currently selects local Gemma 4 E2B through LM
Studio, disables embedded Qwen and legacy Grok comment replies, and keeps
publication disabled. The daemon is stopped; configured routing is not evidence
of a successful inference or live reply.

Runtime credentials come from environment variables loaded by the existing
startup environment owner. They belong in local ignored configuration or the
process environment, never in the manifest, prompts, screenshots shared publicly,
or test output. Authentication headers are separate from model message payloads.
Offline tests use a fixed credential-free environment and synthetic markers;
they must not import `main.py` or read actual environment files.

The remaining sections describe the historical API-based dialogue implementation.
Their default-provider and completion labels do not certify the Studio route.

## Current Status: FIXED [OK]

### The Problem
The original system was **NOT using any LLM** for comment responses. It was just:
- Pattern matching
- Random template selection  
- Hardcoded responses

### The Solution
Created `llm_comment_generator.py` that integrates:

## Supported LLMs

### 1. Grok (Default)
```python
llm_generator = LLMCommentGenerator(provider="grok")
```
- Set environment variable: `GROK_API_KEY` or `XAI_API_KEY`
- Model: `grok-3-latest`
- Best for: Witty, consciousness-aware responses

### 2. Claude
```python
llm_generator = LLMCommentGenerator(provider="claude")
```
- Set environment variable: `ANTHROPIC_API_KEY` or `CLAUDE_API_KEY`
- Model: `claude-3-sonnet-20240229`
- Best for: Thoughtful, nuanced dialogue

### 3. GPT
```python
llm_generator = LLMCommentGenerator(provider="gpt")
```
- Set environment variable: `OPENAI_API_KEY`
- Model: `gpt-4`
- Best for: General conversation

## How It Works

### Comment Flow with LLM
```
1. User posts comment on Move2Japan video
2. RealtimeCommentDialogue detects it (5-15 seconds)
3. LLMCommentGenerator creates intelligent response:
   - Builds context (video, channel, conversation history)
   - Sends to LLM with tailored prompt
   - Gets natural language response
4. Response posted via YouTube API
5. Conversation continues with context
```

### Example LLM Prompts

#### For Questions:
```
A YouTube user named John asked a question on Move2Japan:
"Why did you choose Japan over other countries?"

Video context: Moving to Japan - My Story
Previous conversation: [if any]

Generate a helpful, informative response that:
1. Directly answers their question
2. Is friendly and conversational
3. Encourages further dialogue
4. Stays under 400 characters

Response: [LLM generates here]
```

#### For Consciousness Triggers:
```
A YouTube user named Sarah posted a consciousness-aware comment:
"[U+270A][U+270B][U+1F590] This video really opened my eyes!"

Generate an engaging, consciousness-themed response that:
1. Acknowledges their awakened state
2. References the [U+270A][U+270B][U+1F590] progression
3. Is friendly and encouraging
4. Stays under 400 characters

Response: [LLM generates here]
```

## Fallback System

If LLM is unavailable (no API key, quota exceeded, etc.):
1. Falls back to `AgenticChatEngine` 
2. Uses template-based responses
3. Still maintains conversation context
4. Logs warning but continues operating

## Setup Instructions

### 1. Set API Key
```bash
# For Grok (recommended)
export GROK_API_KEY="your-grok-api-key"

# For Claude
export ANTHROPIC_API_KEY="your-claude-api-key"

# For GPT
export OPENAI_API_KEY="your-openai-api-key"
```

### 2. Run the System
```bash
PYTHONIOENCODING=utf-8 python modules/communication/video_comments/tests/test_poc_dialogue.py
```

### 3. Monitor Logs
```
[BOT] Using LLM for intelligent comment responses  # Success
[U+26A0]️ No LLM available, using template responses   # Fallback mode
```

## Benefits of LLM Integration

### Before (Template-based):
- Generic responses: "Thanks for your comment!"
- No real understanding
- Repetitive patterns
- Can't handle complex questions

### After (LLM-powered):
- Natural, contextual responses
- Understands questions and intent
- Maintains conversation flow
- Personality and engagement

## Cost Considerations

### API Usage:
- Grok: ~$0.001 per comment response
- Claude: ~$0.002 per comment response  
- GPT-4: ~$0.003 per comment response

### Optimization:
- Cache common responses
- Limit response length (400 chars)
- Use context pruning
- Batch similar questions

## Testing

```bash
# Test with specific video
python test_poc_dialogue.py --video VIDEO_ID

# Test LLM connection
python test_llm_integration.py

# Monitor real-time
python test_poc_dialogue.py
```

## Conclusion

The system now has **proper LLM integration** for intelligent YouTube comment responses. It can:
- [OK] Generate natural language responses
- [OK] Understand context and questions
- [OK] Maintain conversation threads
- [OK] Fall back gracefully if LLM unavailable
- [OK] Support multiple LLM providers
