# Lifestyle Card Tagline — Always-Visible Action Summary

**Date:** 2026-03-14

## Problem

Collapsed lifestyle cards showed only the title + chevron + insight bars. The insight bars contain metric readings (temperature, AQI, rain probability) but no clear **action** — users had to expand every card to know what to do. Eight cards × a tap each is too much friction for a daily glance.

## Solution

Add a dedicated `*_tagline` field to each card: ≤8 words, imperative voice, always visible in both collapsed and expanded states. The tagline sits between the title row and the prose text, immediately below the card header.

```
Collapsed:  [icon]  Title                    ▾
                    Light jacket, no umbrella today.   ← tagline (always visible)
                    [insight bar: 🌡 Feels 18° · ☂ No rain gear]

Expanded:   [icon]  Title                    ▴
                    Light jacket, no umbrella today.   ← tagline stays
                    Full LLM prose explaining the reasoning...
                    [insight bar: 🌡 Feels 18° · ☂ No rain gear]
```

## Changes

### `narration/llm_prompt_builder.py`

Added 7 tagline keys to the `---CARDS---` JSON block in both `V7_SYSTEM_PROMPT` (English) and `V7_SYSTEM_PROMPT_ZH` (Traditional Chinese):

| Key | Instruction |
|---|---|
| `wardrobe_tagline` | ≤8 words; cover what to wear AND rain gear in one phrase |
| `commute_tagline` | ≤8 words; key commute condition |
| `meals_tagline` | ≤8 words; food suggestion matching weather mood |
| `hvac_tagline` | ≤8 words; climate action |
| `garden_tagline` | ≤8 words; garden task |
| `outdoor_tagline` | ≤8 words; activity + best time |
| `air_quality_tagline` | ≤8 words; air status |

No `rain_gear_tagline` — wardrobe and rain gear share one frontend card; `wardrobe_tagline` covers both.

Taglines are generated in the user's active language (`lang` param in `build_system_prompt()`), so no separate translation keys are needed.

### `web/routes.py` — `_slice_lifestyle()`

Added reads for all 7 tagline fields from the `summaries` dict, then included `"tagline"` in each card's return dict entry. Fallback is `""` (empty string) for graceful degradation when the template narrator is used or the LLM omits the field.

### `web/static/app.js`

**`add()` helper** (inside `renderLifestyleView()`):
- Signature: `add(icon, title, tagline, text, extraNodes = [])` — `tagline` is the new 3rd parameter
- Renders `<div class="ls-tagline">` conditionally between the title row and `.ls-text`; skipped entirely when tagline is falsy

All 7 call sites updated with `data.<card>.tagline || ''` as the 3rd argument.

### `web/static/style.css`

```css
.ls-tagline {
  font-size: 0.88rem;
  color: var(--text);
  font-weight: 500;
  margin-bottom: 0.35rem;
  line-height: 1.35;
}

html[lang="zh-TW"] .ls-tagline {
  font-size: 1.05rem;
}
```

No changes to collapse/expand CSS — `.ls-tagline` is always rendered, not hidden by the `.ls-card:not(.expanded) .ls-text` rule.

## Architecture Notes

- **Graceful degradation**: Template narrator returns no tagline fields → all taglines are `""` → no `.ls-tagline` divs rendered → cards silently revert to pre-tagline behaviour. No crash.
- **i18n**: Taglines come from the LLM in the correct language; no TRANSLATIONS object changes needed.
- **Alert cards unaffected**: built via a separate code path (`ls-alert-card`), no `add()` call.
- **Insight bars unchanged**: already always-visible; tagline adds an action layer above the metric layer.

---

## Update: Tagline/Details Swap Layout (2026-03-14)

### Problem

The tagline and full details text competed visually — similar sizing made the card feel dense when expanded. Users scanning collapsed cards wanted a bolder at-a-glance summary; users reading expanded details needed quieter secondary text.

### Solution

**Swap layout** — collapsed cards show a prominent tagline; expanding hides the tagline and reveals downsized detail text.

```
Collapsed:  [icon]  Title                         ▾
                    Bold tagline (1.05rem, 600)       ← visible

Expanded:   [icon]  Title                         ▴
                    Smaller details (0.75rem)          ← tagline hidden
                    [insight bars]
```

### CSS Changes (`web/static/style.css`)

| Rule | Before | After |
|---|---|---|
| `.ls-tagline` font-size | 0.88rem | 1.05rem |
| `.ls-tagline` font-weight | 500 | 600 |
| `.ls-tagline` margin-bottom | 0.35rem | removed |
| `.ls-card.expanded .ls-tagline` | — | `display: none` (new) |
| `.ls-text` font-size | 0.82rem | 0.75rem |
| `zh-TW .ls-tagline` font-size | 1.05rem | 1.2rem |
| `zh-TW .ls-text` font-size | 1.05rem | 0.95rem |

No JS changes — pure CSS swap via existing `.expanded` class toggle.
