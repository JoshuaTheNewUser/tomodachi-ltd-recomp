#!/usr/bin/env python3
"""Rank scene/cutscene candidates using existing private function-index data."""
import argparse, json, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = {
    "scene_lifecycle": ("scene", "sequence", "scenario", "cutscene", "movie", "demo", "transition", "eventflow"),
    "dialogue": ("dialog", "message", "talk", "conversation", "subtitle"),
    "actor_animation": ("actor", "character", "motion", "animation", "anim"),
    "camera": ("camera", "cinema", "lookat"),
}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", default="main")
    parser.add_argument("--top", type=int, default=60)
    args = parser.parse_args()
    target = os.environ.get("SWITCHPILER_TARGET", "tomodachi")
    runtime = ROOT / "local/runtime.json"
    if runtime.exists() and "SWITCHPILER_TARGET" not in os.environ:
        try:
            target = json.loads(runtime.read_text()).get("target", target)
        except (OSError, json.JSONDecodeError):
            pass
    base = ROOT / "local/analysis" / target
    source = base / "index" / (args.module + ".jsonl")
    if not source.is_file():
        raise SystemExit("Missing private function index: " + str(source) +
                         ". Build it first; see docs/CUTSCENE-RESEARCH.md.")
    overrides = {}
    for filename in ("classes.jsonl", "data-readers.jsonl", "manual.jsonl"):
        path = base / "names" / filename
        if path.exists():
            for line in path.read_text(errors="replace").splitlines():
                try:
                    item = json.loads(line)
                    overrides[item.get("offset", "").lower()] = item.get("name")
                except json.JSONDecodeError:
                    continue
    results = []
    for line in source.read_text(errors="replace").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        offset = str(item.get("offset", "")).lower()
        name = overrides.get(offset) or item.get("name") or ("sub_" + offset.removeprefix("0x"))
        haystack = (name + " " + " ".join(map(str, item.get("strings", [])))).lower()
        matches = {}
        for category, terms in RULES.items():
            found = [term for term in terms if term in haystack]
            if found:
                matches[category] = found
        if not matches:
            continue
        scores = {category: len(terms) * 3 for category, terms in matches.items()}
        results.append({
            "offset": item.get("offset"), "name": name, "size": item.get("size"),
            "callers": item.get("callers", 0), "callees_count": len(item.get("callees", [])),
            "data_refs": item.get("data_refs", 0), "matches": matches, "scores": scores,
            "confidence": "unverified_candidate",
            "warning": "Keyword match only; inspect call relationships and verify scene entry and exit."
        })
    results.sort(key=lambda r: (r["scores"].get("scene_lifecycle", 0),
                                r["callers"]), reverse=True)
    data_paths = []
    table = base / "data/files.tsv"
    if table.exists():
        for line in table.read_text(errors="replace").splitlines()[1:]:
            fields = line.split("\t")
            if len(fields) >= 2 and any(k in (fields[0] + "/" + fields[1]).lower()
                                        for k in RULES["scene_lifecycle"]):
                data_paths.append({"container": fields[0], "member": fields[1]})
    report = {
        "schema_version": 1, "kind": "PrivateCutsceneResearchReport",
        "target": target, "module": args.module,
        "warning": "No controller is confirmed. Results are heuristic candidates only.",
        "scene_lifecycle_candidates": [r for r in results if "scene_lifecycle" in r["matches"]][:args.top],
        "other_candidates": [r for r in results if "scene_lifecycle" not in r["matches"]][:args.top],
        "matching_data_paths": data_paths[:200]
    }
    output = base / "cutscene-research" / (args.module + "-candidates.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print("Scene lifecycle candidates:", len(report["scene_lifecycle_candidates"]))
    print("Other candidates:", len(report["other_candidates"]))
    print("Matching data paths:", len(data_paths))
    print("Private report:", output)
    for result in report["scene_lifecycle_candidates"][:15]:
        print(result["offset"], result["name"], "callers=" + str(result["callers"]))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
