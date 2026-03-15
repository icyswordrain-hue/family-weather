# Client-Side Language Switching

## Goal
Eliminate API round-trips when the user toggles language. Both EN and ZH data (including pre-built slices) are returned in a single `/api/broadcast` response, enabling instant client-side switching.

## Problem
After the v2 dual-language broadcast change, `/api/broadcast` flattened only the requested language into the response. `applyLanguage()` swapped UI labels but never fetched the other language's narration, audio, or slices — the content stayed in the old language.

## Solution

### Server: Return both languages with pre-built slices
`/api/broadcast` (and Modal's `broadcast()`) now builds slices for every stored language and attaches them to `langs[l]["slices"]` before responding. The full `langs` dict (with slices) is included via `**cached`, alongside the flattened fields for the requested language.

### Frontend: Switch locally in `applyLanguage()`
When the user toggles language, `applyLanguage()` extracts the new language's data from `broadcastData.langs[lang]` — narration text, paragraphs, metadata, audio URLs, summaries, and slices — then re-renders. Zero network requests.

## Files Changed
- `app.py` `/api/broadcast` — build slices for all languages before returning
- `backend/modal_app.py` `broadcast()` — same
- `web/static/app.js` `applyLanguage()` — extract lang-specific data from `broadcastData.langs`
