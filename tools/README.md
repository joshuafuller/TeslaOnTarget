# tools/

Developer utilities. Not part of the runtime image (excluded via `.dockerignore`).

## Maintained

Used for debugging Tesla API responses captured with `DEBUG_MODE=True` (see [../docs/CONFIGURATION.md](../docs/CONFIGURATION.md)):

- **`replay_captures.py`** — quick view of the extracted data from saved captures.
- **`analyze_full_captures.py`** — full analysis across captures (all fields, what changes between samples).
- **`analyze_tesla_api.py`** — inspect the shape of a Tesla API response.

## `exploration/`

One-off scripts used to discover/understand Tesla API fields (navigation, FSD, etc.). Kept for reference; not maintained and not wired into anything.
