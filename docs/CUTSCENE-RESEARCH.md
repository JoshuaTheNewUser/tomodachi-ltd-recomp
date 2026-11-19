# PJ Cutscene Research v0.1

This milestone creates a repeatable way to investigate the scene lifecycle before attempting runtime hooks.

## Current status

The repository contains research utilities for indexing function calls, strings, data files, class/vtable relationships and data readers. Game-derived inputs and outputs are private and must not be committed.

No scene-controller function has been confirmed. The public GitHub checkout does not contain the local game-derived indexes needed to identify one. The helper ranks candidates only; a keyword match is not proof.

## What was added

- scripts/cutscene-research.py reads an existing private function index.
- It ranks possible scene-lifecycle, dialogue, actor-animation and camera functions.
- It optionally lists matching paths from the private data-file index.
- It writes its report under local/analysis/<target>/cutscene-research/.

## Run

From the repository root, after your local research setup has produced local/analysis/<target>/index/main.jsonl:

    python3 scripts/cutscene-research.py --module main

To inspect another module:

    python3 scripts/cutscene-research.py --module sdk

The report is private and labels every result as an unverified candidate. It does not extract game data, patch executable code, or implement playback.

## How we verify a candidate

1. Inspect its function record and callers/callees in the existing index.
2. Check whether its references point to scene/sequence data rather than unrelated interface text.
3. Observe whether it runs at both scene entry and exit, not merely during a scene.
4. Repeat with multiple scenes and ordinary gameplay as a negative comparison.
5. Record module build ID, function address, evidence, alternative explanations and confidence locally.

A true lifecycle hook needs evidence of a stable start/stop boundary. A function name containing "scene" is not enough.

## Next milestone

v0.2 — verified scene boundary: document at least one candidate with repeatable evidence for scene entry and exit. Only then should we design a runtime adapter.

## Privacy and scope

Keep game dumps, keys, generated C, decompiled pseudo-C, game strings, extracted assets and reports containing game-derived information out of Git. This helper only reads existing local analysis indexes and writes a private report.
