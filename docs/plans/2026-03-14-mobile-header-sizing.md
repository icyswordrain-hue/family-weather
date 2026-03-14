# Mobile Header Sizing Tweaks

**Date**: 2026-03-14
**Status**: Done

## What

Increase the compact mobile header height by 1.1× and bump the "updated M/DD HH:MM"
timestamp text from 0.62rem to 0.75rem for better readability.

## Changes

| File | Change |
|------|--------|
| `web/static/style.css` | `.compact-header` padding: `12px 16px` → `13.2px 16px` (1.1× vertical) |
| `web/static/style.css` | `#mobile-last-updated` font-size: `0.62rem` → `0.75rem` |
