# Gemini Model & Timeout Upgrade

**Date**: 2026-03-14
**Status**: Done

## What

Updated Gemini model defaults and aligned timeout behaviour with the Claude provider.

## Why

- `gemini-2.0-pro-exp` was retired by Google (404 NOT_FOUND)
- `gemini-2.0-flash` returns 403 for new API keys ("no longer available to new users")
- Gemini client used a single 300s client-level timeout shared across both attempts, meaning a slow Pro attempt could starve the Flash fallback

## Changes

### config.py
- `GEMINI_PRO_MODEL`: `gemini-2.0-pro-exp` → `gemini-2.5-pro`
- `GEMINI_FLASH_MODEL`: `gemini-2.0-flash` → `gemini-2.5-flash`

### narration/gemini_client.py
- Replaced single shared 300s client timeout with per-request timeouts
- Pro attempt: fresh `genai.Client` with `NARRATION_TIMEOUT_PRO` (90s)
- Flash fallback: fresh `genai.Client` with `NARRATION_TIMEOUT_FLASH` (90s)
- Fixed `http_options` format: `{'timeout': 300}` → `genai.types.HttpOptions(timeout=<ms>)` (required by google-genai SDK v1.64+)
- Added timeout logging to match Claude client's log format

## Timeout Summary (all providers)

| Provider | Primary | Fallback | Worst case |
|----------|---------|----------|------------|
| Claude   | 90s (Sonnet 4.6) | 90s (Haiku 4.5) | ~180s |
| Gemini   | 90s (2.5 Pro) | 90s (2.5 Flash) | ~180s |
