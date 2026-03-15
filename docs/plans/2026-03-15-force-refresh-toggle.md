# Feature: Force Refresh Toggle in Settings

## Context

The pipeline has a narration-skip guard (step 3c in `_pipeline_steps`) that reuses the previous
narration when weather conditions are unchanged. There was no UI way to bypass this short of
switching providers. The guard is correct for regular hourly refreshes but blocks on-demand
regeneration when the user explicitly wants fresh narration.

## Changes

### `web/templates/dashboard.html`
New "Narration" segmented-control card inserted between Language and the action buttons,
matching the existing Provider/Language design pattern:

```
[ Auto ] [ Force ]
```

### `web/static/app.js`
- Translation keys added: `narration_label` / `narration_auto` / `narration_force` (EN + zh-TW)
- `triggerRefresh()` reads the toggle and includes `force: true/false` in the POST body
- `initRefreshButton()` gains a `change` listener on the narration-mode radios: when Force is
  selected the refresh button label becomes "Force 重新整理" and gains the `.force-mode` CSS class
- After `type: result` is received in the stream handler the toggle auto-resets to Auto and fires
  `change` to revert the button label and CSS

### `web/static/style.css`
`.ps-btn.force-mode` — darker amber (`#c47d10`) background/border to make force mode visible
at a glance without being alarming.

### `app.py`
- `/api/refresh`: reads `force = bool(body.get("force", False))`; forwarded to the Modal proxy
  body and to `_pipeline_steps()`
- `_pipeline_steps()` signature gains `force: bool = False`
- Step 3c guard restructured: `if force:` logs "Force refresh — regenerating narration" and
  falls through to generation; the existing conditions/provider-change check moves to `elif`

## Verification

```
pytest tests/   # 245 passed — mocked pipeline tests unaffected
```

Manual:
1. `RUN_MODE=LOCAL python app.py` → Settings → Narration = Force → Refresh
2. Stream log shows "Force refresh — regenerating narration" (not "Conditions unchanged")
3. Toggle auto-resets to Auto after refresh completes; button reverts to normal colour
