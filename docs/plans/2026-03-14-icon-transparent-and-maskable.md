# Icon Refinement: Transparent + Maskable Variants

**Date:** 2026-03-14
**Status:** Done

## Problem

The original `icon-512.webp` had a self-drawn dark rounded-rect background baked into the image. This caused two issues:

1. **Windows desktop / browser** — the rounded-rect-inside-a-square looked like a floating badge, not a native OS icon. Windows 11 and browser chrome handle their own visual framing; an icon with a hard-drawn background doesn't blend.
2. **Android home screen** — the PWA manifest was pointing `purpose: "maskable"` at the same rounded-rect icon. Android applies its own shape mask on top, causing double-cropping; the artwork ended up small and over-padded.
3. **iOS home screen** — Apple touch icon should be full-bleed so iOS applies its own squircle clip cleanly. The self-rounded icon stacked awkwardly with iOS's own clipping.

## Solution: Two Icon Variants

### Variant A — Transparent (`any`)
- Background fully removed; leaf + droplet float on alpha-transparent canvas.
- Used everywhere OS/browser applies its own framing (browser tab, Windows taskbar, desktop shortcut).
- Files: `icon-512-any.webp`, `icon-192-any.webp`, `favicon-32.png`

### Variant B — Maskable (`maskable`)
- Full-bleed solid `#1a2235` dark background, no rounded corners.
- Artwork centered within the safe zone (center ~80% of canvas).
- Android and iOS apply their own shape (squircle, circle, etc.) into the solid fill.
- Files: `icon-512-maskable.webp`, `icon-192-maskable.webp`
- Also used as `apple-touch-icon`.

## Generation

Icons were generated using **Nano Banana Pro** (Gemini 3 Pro Image) via image-to-image editing of the original `icon-512.webp` at 2K resolution. 192px variants and `favicon-32.png` were resized from the 512px sources using Pillow (LANCZOS).

## Files Changed

| File | Change |
|------|--------|
| `web/static/icon-512-any.webp` | New — transparent background |
| `web/static/icon-192-any.webp` | New — 192px transparent |
| `web/static/icon-512-maskable.webp` | New — full-bleed dark background |
| `web/static/icon-192-maskable.webp` | New — 192px full-bleed |
| `web/static/favicon-32.png` | Replaced — transparent background |
| `web/static/manifest.json` | Split `any`/`maskable` to separate files; added 192px maskable entry |
| `web/templates/dashboard.html` | Favicon → `icon-512-any.webp`, apple-touch-icon → `icon-512-maskable.webp` |

## Manifest Structure After

```json
"icons": [
  { "src": "/static/icon-192-any.webp",      "sizes": "192x192", "purpose": "any" },
  { "src": "/static/icon-512-any.webp",      "sizes": "512x512", "purpose": "any" },
  { "src": "/static/icon-192-maskable.webp", "sizes": "192x192", "purpose": "maskable" },
  { "src": "/static/icon-512-maskable.webp", "sizes": "512x512", "purpose": "maskable" }
]
```

## Original Icon

`icon-512.webp` / `icon-192.webp` are retained in `web/static/` but no longer referenced.
