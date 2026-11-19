# Modding and PJ Mod Studio

PJ Mod Studio is the first authoring-tool prototype for this fork.

## Current prototype

Run it from the repository root:

```sh
python3 scripts/mod_studio.py
```

It can create project folders, write a versioned `mod.json` manifest, validate metadata and package original mod-authored files into a ZIP. It deliberately rejects symlinks and obvious game-dump/key files.

## Important: authoring is not runtime support

A package exported by this prototype is **not loaded by nxrt**. The editor does not yet modify the running game. A real mod system requires runtime support and a verified mapping between mod data and game resources.

The current runtime is a native recompilation with a custom runtime/renderer. Its README describes the runtime as an execution environment; it does not document a general-purpose plugin API, script VM, cutscene API or asset override layer. Therefore we must not pretend that placing a ZIP in a folder will make gameplay changes happen.

## Roadmap

1. **Authoring foundation (prototype):** project folders, manifest validation and ZIP packaging.
2. **Launcher integration:** add a PJ Mod Studio entry to the existing Tk launcher.
3. **Read-only resource inventory:** document resource identifiers and formats supported by the runtime, without distributing proprietary game content.
4. **Safe asset override layer:** implement only after confirming the runtime's resource-loading path; add deterministic priority, validation, size limits and rollback.
5. **Cutscene format:** define an original, documented timeline format (actors, timing, dialogue, camera cues) and preview it with placeholder assets.
6. **Gameplay extensions:** only after identifying stable, testable game-logic extension points in the recompiled code. Do not load arbitrary native code from mods.
7. **Compatibility tests:** use synthetic fixtures and a user's own legally obtained game installation; never include game data, keys or proprietary assets in packages or CI.

## Mod manifest v1

```json
{
  "format_version": 1,
  "id": "example.cutscene",
  "name": "Example Cutscene",
  "version": "1.0.0",
  "author": "Mod author",
  "type": "cutscene",
  "description": "An original cutscene project."
}
```

Supported editor project types are `asset`, `cutscene` and `gameplay`. The latter two are project labels only until runtime support is implemented.

## Package safety

Only include files authored by the mod creator or assets they have permission to redistribute. Never package game dumps, console keys, firmware, save files or proprietary extracted game resources. The editor does not help obtain game files or keys.
