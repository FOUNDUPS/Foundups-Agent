# Storytime touch/mouse/PWA audit — 2026-10-26 JST

## Module and scope

Storytime is a small activity under existing EDUIT, using Kids Episodes production
and the Shorts-owned review/viewer. It is not a new FoundUp or a replacement Mall.
Play FoundUps Mall remains the shared identity/catalog/navigation owner. This
private Sites POC reuses the existing Mall gesture engine but is not mounted in
its live catalog. Existing `eduit`/`kids_episodes`/`us_story_time` IDs remain stable.

Recovered the later published parent positioning and four game locale variants
from the exact Sites source revision `b683722ee081025639f636830a106fd1d9880661`;
GitHub PR2224 merged the earlier viewer milestone. Recovery keeps the later
creative work reviewable rather than reverting to its older merged version.

## Input and layout contract

- Scene targets are native buttons: touch tap, mouse click and keyboard activation.
- Whiteboard uses Pointer Events with pointer capture and cancellation for mouse,
  finger and pen. Coordinates are normalized against the actual displayed frame.
- Mall gesture owner supplies pinch and Ctrl+wheel; explicit expand/exit controls
  and Escape provide fallback. Native mobile fullscreen is not assumed.
- Width/aspect-ratio, dynamic viewport, safe-area insets and wrapping controls
  adapt to phones/tablets/desktop. No model sniffing, forced orientation or zoom ban.
- Language controls use local SVG GB/JP/PT/ES flag assets. Only flags are visible;
  names remain in accessible labels/tooltips, selected state via aria-pressed.
- Locale selection pauses gameplay; changing a language cannot consume rescue time.

## PWA implementation and limits

A scoped manifest declares standalone display, app identity, start URL, theme and
192/512 icons. The service worker caches an explicit public episode UI allowlist
with network-first updates. No OAuth/account/API/feedback requests are cached.
Video range requests remain network-only; offline video is not promised.
Browser installation criteria and iPhone home-screen behavior need real-device
acceptance. Private Sites sign-in remains required for initial online access.
Do not claim complete offline playback or bypass the shared Mall service worker.
On Mall mounting, the Mall owns registration; omit this standalone worker there.

## Retrieval and truth labels

Governed Holo lexical query returned ok=true, freshness=UNKNOWN, index gap=true.
Read exact EDUIT interface, roadmap, deployment, architecture, current scene and
editor sources. WSP00 detector dependencies unavailable; torch-free gate fallback
reported compliant. No detector-backed witness, native WRE or RSI activation claimed.

## Publishing

Reuse hardened publisher/OAuth where configured; restored checkout has no credential
directory. The existing authorized Studio session is the fallback for the explicitly
requested upload. Verify Us Story Time channel ID, duplicate content, original
media provenance, made-for-kids setting and unlisted first upload. Record actual
returned video identity separately; never call a prepared upload a published one.


## Observed upload receipt — 2026-10-26 JST

Studio observed Us Story Time, channel `UCfo9NxwyjAQvaVn3cEjXT4g`, through
the existing FoundUps account switcher. Latest source revision sound-languages-9
MP4 SHA256 `3f173b450bd7ac4780a69de3a1a704e1e5510af7ba753498f35038a25c5ea34a`
matched its provenance. FFprobe reports H264/AAC, 1920x1080,15.000 seconds.
Studio rounds its displayed duration to0:16; don't reinterpret that as a changed
source render. Upload completed with video ID `9JlKe5R_ckM`, visibility Unlisted,
made-for-kids selected and AI-use disclosure selected. Studio checks reported
no copyright or Community Guidelines issues; HD processing was still pending
at the first saved-content observation. URL: https://youtu.be/9JlKe5R_ckM

No public release, notifications, DNS change or deletion of older drafts occurred.
A grouped metadata call was rejected by automatic review; separate disclosure
and visibility controls succeeded. Existing category was left unchanged.

Independent review passed9 focused checks and found two hardening gaps, repaired:
active pointer IDs isolate simultaneous fingers; persisted feedback validates
time, SVG size and normalized stroke coordinates before reopening. Browser
confirmed SVG flags visible without labels in a narrow viewport. Physical phone
installation and auditory perception remain unverified.
