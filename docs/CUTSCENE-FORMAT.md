# PJ Cutscene Format v1 (experimental)

This document defines the first **authoring format** for PJ Mod Studio cutscene projects.

> Status: editor prototype only. The current game runtime does not interpret this format. A valid JSON file is not proof of in-game playback.

## Example

```json
{
  "schema_version": 1,
  "id": "sample_meetup",
  "title": "A Sample Meetup",
  "events": [
    {
      "id": "opening_wait",
      "type": "wait",
      "start": 0.0,
      "duration": 1.0
    },
    {
      "id": "first_line",
      "type": "dialogue",
      "start": 1.0,
      "duration": 3.0,
      "speaker": "actor_a",
      "text": "Hello there!"
    },
    {
      "id": "camera_wide",
      "type": "camera_cue",
      "start": 1.0,
      "duration": 2.0,
      "camera": "wide_placeholder"
    },
    {
      "id": "actor_wave",
      "type": "actor_animation",
      "start": 4.0,
      "duration": 1.5,
      "actor": "actor_a",
      "animation": "wave_placeholder"
    }
  ]
}
```

## Event types

| Type | Fields | Meaning |
|---|---|---|
| `wait` | `start`, `duration` | Timing marker / pause |
| `dialogue` | `speaker`, `text` | Original dialogue line |
| `camera_cue` | `camera` | Symbolic camera cue ID |
| `actor_animation` | `actor`, `animation` | Symbolic actor and animation IDs |

Every event has a unique `id`, a non-negative `start` time and a non-negative `duration`. Events may overlap; the runtime will eventually need explicit conflict rules.

## Why IDs are symbolic

The editor must not assume that arbitrary actor, camera or animation names exist in the game. A future runtime adapter must map approved symbolic IDs to supported game resources and behaviors. Unknown IDs should fail validation rather than silently doing something unexpected.

## Roadmap to real in-game playback

1. Inspect the recompiled game's scene, animation, camera and dialogue execution paths.
2. Identify stable, testable integration points and the data structures they require.
3. Implement a small runtime interpreter for a restricted set of event types.
4. Test with synthetic scenes and placeholder actors/cameras first.
5. Only then map supported IDs to resources available in the user's own game installation.
6. Add a compatibility/version declaration so mods cannot run against unknown runtime builds.

Do not package game dumps, firmware, console keys, saves, or proprietary extracted game assets. Mod packages should contain original mod-authored content or material the mod author has permission to redistribute.
