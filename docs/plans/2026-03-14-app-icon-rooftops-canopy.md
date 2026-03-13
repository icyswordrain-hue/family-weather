# App Icon: Rooftops + Canopy Arc (B1)

**Date:** 2026-03-14
**Status:** Done
**Replaces:** `2026-03-14-icon-transparent-and-maskable.md` (leaf+drop icon, superseded)

## Context

The original leaf+drop icon was replaced after design exploration using Nano Banana Pro
(Gemini 3 Pro Image). Ten candidate icons were generated across two rounds, exploring
concepts including canopy arches, tree views, raindrop worlds, pavilions, tree silhouettes,
and wind spirals.

**Selected: B1 — Neighborhood Rooftops + Canopy Arc**
- Cream/sand rooftop silhouette skyline with a sage-green protective arc overhead
- Directly communicates both "neighborhood" (厝邊, the Taiwanese word in the app name)
  and "canopy" (shelter, protection, weather awareness)
- Reads clearly at all sizes from 512px down to 32px favicon

## Icon Variants

| File | Purpose | Description |
|------|---------|-------------|
| `icon-512-any.webp` | `any` — browser, desktop, Windows taskbar | Transparent background; rooftops + arc float on OS chrome |
| `icon-192-any.webp` | `any` 192px | Resized from 512 transparent |
| `icon-512-maskable.webp` | `maskable` — Android/iOS home screen | Full-bleed dark navy (#1a2235), artwork within safe zone |
| `icon-192-maskable.webp` | `maskable` 192px | Resized from 512 maskable |
| `favicon-32.png` | Browser tab | Resized from 512 transparent |

## Generation Method

1. **B1 source** generated via Nano Banana Pro text-to-image at 2K resolution
2. **Transparent `any`** generated via Nano Banana Pro image-to-image edit (bg removal)
3. **Maskable** = B1 source directly (already full-bleed dark navy, no rounded corners)
4. **192px + favicon** resized from 512px sources using Pillow (LANCZOS)

## Files Changed

| File | Change |
|------|--------|
| `web/static/icon-512-any.webp` | Replaced — rooftops transparent bg |
| `web/static/icon-192-any.webp` | Replaced — 192px |
| `web/static/icon-512-maskable.webp` | Replaced — rooftops full-bleed dark |
| `web/static/icon-192-maskable.webp` | Replaced — 192px |
| `web/static/favicon-32.png` | Replaced — from rooftops transparent |
| `web/templates/dashboard.html` | Cache-busted icon `?v` params |

## Manifest (unchanged from previous commit)

```json
"icons": [
  { "src": "/static/icon-192-any.webp",      "sizes": "192x192", "purpose": "any" },
  { "src": "/static/icon-512-any.webp",      "sizes": "512x512", "purpose": "any" },
  { "src": "/static/icon-192-maskable.webp", "sizes": "192x192", "purpose": "maskable" },
  { "src": "/static/icon-512-maskable.webp", "sizes": "512x512", "purpose": "maskable" }
]
```
