# Icon Dark/Light Mode Robustness

**Date:** 2026-03-14
**Status:** Done

## Problem

After settling on terracotta as the brand icon color, the question was whether the icon should adapt to OS dark/light mode — and whether platform detection was even possible.

## Research: What's Actually Supported (2026)

| Surface | Adaptive icon support |
|---|---|
| Android home screen (maskable) | ❌ Static only — Android 12 Material You monochrome is native apps only |
| iOS home screen (web clip) | ❌ iOS 18 dark icon variants are native apps only, not PWAs |
| Windows 11 taskbar PWA | ❌ No OS-level switching for PWA icons |
| Browser tab favicon (SVG) | ✅ SVG `@media (prefers-color-scheme)` works in Chrome + Firefox |
| Browser chrome / address bar | ✅ `<meta name="theme-color" media="...">` in Chrome 93+ / Safari 15+ |
| Web App Manifest `media` on icons | ❌ Still an open W3C proposal (w3c/manifest#955), no browser ships it |

Platform-level dark/light PWA icon switching is not possible. This is a platform limitation, not a design failure.

## Why Terracotta Is Already Robust

`#B5522A` (terracotta) with an opaque squircle background works in both OS modes without any switching:

- **Dark taskbar/launcher**: warm terracotta pops against dark navy/grey — high contrast
- **Light taskbar/launcher**: terracotta is a mid-dark warm hue — clearly visible on white
- **Opaque background**: eliminates the "transparency trap" where a transparent icon blends into the OS background

No changes to the existing WebP icon files were needed.

## Solution: Two Targeted Improvements

### 1. SVG Favicon (browser tabs)

New file `web/static/favicon.svg` — a vector reconstruction of the squircle + rooftop peak + canopy arc artwork. The SVG embeds `@media (prefers-color-scheme)`:

- **Light mode**: terracotta `#B5522A` squircle
- **Dark mode**: slightly lighter terracotta `#C96438` (more visible against dark browser chrome)

Chrome and Firefox use the SVG; Safari ignores SVG favicons and falls back to the PNG automatically.

### 2. Adaptive `theme-color` (browser chrome / address bar)

Replaced the single static `theme-color` with a media-query pair:

```html
<meta name="theme-color" content="#1a2235" media="(prefers-color-scheme: dark)" />
<meta name="theme-color" content="#f5ede4" media="(prefers-color-scheme: light)" />
```

`#f5ede4` is the warm cream from the earthy design system. Chrome 93+ (Android address bar, standalone PWA chrome) and Safari 15+ (iOS status bar tint) will respond to this.

`manifest.json` `theme_color` stays `#1a2235` — it's used as the PWA install splash background, which is dark-first.

## Files Changed

| File | Change |
|---|---|
| `web/static/favicon.svg` | New — adaptive SVG favicon with embedded `@media` CSS |
| `web/templates/dashboard.html` | SVG favicon `<link>` added; single `theme-color` split into dark/light pair |
| `web/static/icon-192.webp` | Deleted — no longer referenced (superseded by `icon-192-any.webp`) |
| `web/static/icon-512.webp` | Deleted — no longer referenced (superseded by `icon-512-any.webp`) |

## Verification

1. Chrome DevTools → Rendering → Emulate `prefers-color-scheme` → tab favicon updates dark/light
2. Firefox → same favicon test
3. Safari → falls back to `favicon-32.png` (expected)
4. Chrome Android standalone PWA → address bar flips cream ↔ dark navy
5. iOS Safari standalone → status bar tint responds
6. Windows 11 taskbar / Android home screen → stays terracotta regardless of OS theme (expected, platform limitation)
