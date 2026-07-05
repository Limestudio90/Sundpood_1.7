# Changelog

## 2.0.1
- Fixed exported Windows build startup path resolution
- Removed hard failure on legacy encrypted runtime update checks when `key.py` is absent
- Improved mixer initialization fallback for renamed or API-specific output devices
- Fixed microphone passthrough routing for SSL 2+ and VB-Cable style device combinations
- Prefer stable host APIs and compatible mono/stereo stream settings when opening duplex streams

## 2.0
- Added Virtual Audio Cable support as the main routing target
- Added microphone passthrough mixed into the same virtual output
- Refreshed the main UI, preferences, hotkeys window, and overlay
- Added sound library refresh and folder import
- Improved audio device matching and startup stability
