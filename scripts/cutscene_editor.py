#!/usr/bin/env python3
"""PJ Cutscene Editor — timeline authoring prototype.

Creates original, data-only cutscene descriptions. This editor does not load or
modify proprietary game assets and does not yet execute scenes inside the game.
"""
from __future__ import annotations

import json
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

SCHEMA_VERSION = 1
KINDS = ("dialogue", "wait", "camera_cue", "actor_animation")
ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$")


def validate_scene(scene: dict) -> None:
    if not isinstance(scene, dict) or scene.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Expected a PJ cutscene document with schema_version 1.")
    for key in ("id", "title"):
        if not isinstance(scene.get(key), str) or not scene[key].strip():
            raise ValueError(f"'{key}' must be a non-empty string.")
    if not ID_RE.fullmatch(scene["id"]):
        raise ValueError("Cutscene ID contains unsupported characters.")
    events = scene.get("events")
    if not isinstance(events, list):
        raise ValueError("'events' must be a list.")
    seen = set()
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError(f"Event {index + 1} must be an object.")
        eid, kind = event.get("id"), event.get("type")
        if not isinstance(eid, str) or not ID_RE.fullmatch(eid) or eid in seen:
            raise ValueError(f"Event {index + 1} has an invalid or duplicate ID.")
        seen.add(eid)
        if kind not in KINDS:
            raise ValueError(f"Event {eid}: unsupported type.")
        start, duration = event.get("start"), event.get("duration")
        if not isinstance(start, (int, float)) or isinstance(start, bool) or start < 0:
            raise ValueError(f"Event {eid}: start must be a non-negative number.")
        if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration < 0:
            raise ValueError(f"Event {eid}: duration must be a non-negative number.")
        required = {
            "dialogue": ("speaker", "text"),
            "wait": (),
            "camera_cue": ("camera",),
            "actor_animation": ("actor", "animation"),
        }[kind]
        for field in required:
            if not isinstance(event.get(field), str) or not event[field].strip():
                raise ValueError(f"Event {eid}: '{field}' must be a non-empty string.")
    scene["events"].sort(key=lambda e: (e["start"], e["id"]))


class EventDialog(tk.Toplevel):
    def __init__(self, parent, event=None):
        super().__init__(parent)
        self.title("Cutscene event")
        self.resizable(False, False)
        self.result = None
        self.transient(parent)
        self.grab_set()
        event = event or {}
        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)
        self.vars = {}
        fields = (("id", "Event ID"), ("type", "Type"), ("start", "Start time (seconds)"),
                  ("duration", "Duration (seconds)"), ("speaker", "Speaker (dialogue)"),
                  ("text", "Dialogue text"), ("camera", "Camera cue ID"),
                  ("actor", "Actor ID"), ("animation", "Animation ID"))
        for row, (key, label) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=4)
            if key == "type":
                var = tk.StringVar(value=event.get(key, "dialogue"))
                widget = ttk.Combobox(frame, textvariable=var, state="readonly", values=KINDS, width=34)
            else:
                var = tk.StringVar(value=str(event.get(key, "0" if key in ("start", "duration") else "")))
                widget = ttk.Entry(frame, textvariable=var, width=37)
            widget.grid(row=row, column=1, sticky="ew", pady=4)
            self.vars[key] = var
        ttk.Button(frame, text="Save event", command=self.submit).grid(
            row=len(fields), column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self.bind("<Return>", lambda _e: self.submit())

    def submit(self):
        data = {key: var.get().strip() for key, var in self.vars.items()}
        try:
            data["start"] = float(data["start"])
            data["duration"] = float(data["duration"])
        except ValueError:
            messagebox.showerror("Invalid time", "Start and duration must be numbers.", parent=self)
            return
        kind = data["type"]
        allowed = {
            "dialogue": ("id", "type", "start", "duration", "speaker", "text"),
            "wait": ("id", "type", "start", "duration"),
            "camera_cue": ("id", "type", "start", "duration", "camera"),
            "actor_animation": ("id", "type", "start", "duration", "actor", "animation"),
        }[kind]
        self.result = {key: data[key] for key in allowed}
        try:
            validate_scene({"schema_version": 1, "id": "test", "title": "test", "events": [self.result]})
        except ValueError as exc:
            messagebox.showerror("Invalid event", str(exc), parent=self)
            self.result = None
            return
        self.destroy()


class CutsceneEditor(tk.Tk):
    def __init__(self, project: Path):
        super().__init__()
        self.project = project.resolve()
        self.folder = self.project / "cutscenes"
        self.folder.mkdir(parents=True, exist_ok=True)
        self.title("PJ Cutscene Editor — " + self.project.name)
        self.geometry("1000x680")
        self.minsize(780, 520)
        self.configure(bg="#14251c")
        self.scene = {"schema_version": SCHEMA_VERSION, "id": "new_cutscene",
                      "title": "New Cutscene", "events": []}
        self._style()
        self._build()
        self.refresh()

    def _style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", rowheight=28, font=("DejaVu Sans", 10))
        style.configure("TButton", padding=7)
        style.configure("TLabel", background="#14251c", foreground="#eff8f0")
        style.configure("Title.TLabel", font=("DejaVu Sans", 18, "bold"), foreground="#a5e6b6")

    def _build(self):
        top = ttk.Frame(self, padding=16)
        top.pack(fill="x")
        ttk.Label(top, text="CUTSCENE EDITOR", style="Title.TLabel").pack(anchor="w")
        ttk.Label(top, text="Data-driven timeline • original placeholder IDs • experimental schema").pack(anchor="w")
        meta = ttk.Frame(self, padding=(16, 4))
        meta.pack(fill="x")
        ttk.Label(meta, text="Cutscene ID").pack(side="left")
        self.id_var = tk.StringVar(value=self.scene["id"])
        ttk.Entry(meta, textvariable=self.id_var, width=22).pack(side="left", padx=(6, 16))
        ttk.Label(meta, text="Title").pack(side="left")
        self.title_var = tk.StringVar(value=self.scene["title"])
        ttk.Entry(meta, textvariable=self.title_var, width=34).pack(side="left", padx=6)
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        self.events = ttk.Treeview(body, columns=("time", "duration", "type", "summary"),
                                   show="headings", selectmode="browse")
        for col, label, width in (("time", "Start (s)", 90), ("duration", "Duration", 90),
                                  ("type", "Event", 150), ("summary", "Details", 460)):
            self.events.heading(col, text=label)
            self.events.column(col, width=width, anchor="w")
        self.events.pack(fill="both", expand=True)
        row = ttk.Frame(body)
        row.pack(fill="x", pady=(10, 0))
        ttk.Button(row, text="＋ Add event", command=self.add_event).pack(side="left")
        ttk.Button(row, text="Edit selected", command=self.edit_event).pack(side="left", padx=6)
        ttk.Button(row, text="Remove", command=self.remove_event).pack(side="left")
        ttk.Button(row, text="Preview timeline", command=self.preview).pack(side="right")
        bottom = ttk.Frame(self, padding=(16, 0, 16, 16))
        bottom.pack(fill="x")
        ttk.Button(bottom, text="Open cutscene…", command=self.open_scene).pack(side="left")
        ttk.Button(bottom, text="Save cutscene", command=self.save_scene).pack(side="left", padx=6)
        ttk.Button(bottom, text="Validate", command=self.validate).pack(side="left")
        ttk.Label(bottom, text="Preview is a timeline summary, not in-game playback.").pack(side="right")

    def refresh(self):
        self.events.delete(*self.events.get_children())
        for event in sorted(self.scene["events"], key=lambda e: (e["start"], e["id"])):
            if event["type"] == "dialogue":
                summary = f'{event["speaker"]}: {event["text"]}'
            elif event["type"] == "camera_cue":
                summary = f'Camera cue: {event["camera"]}'
            elif event["type"] == "actor_animation":
                summary = f'{event["actor"]} → {event["animation"]}'
            else:
                summary = "Wait / timing marker"
            self.events.insert("", "end", iid=event["id"],
                               values=(f'{event["start"]:.2f}', f'{event["duration"]:.2f}',
                                       event["type"], summary))

    def _selected_index(self):
        selected = self.events.selection()
        if not selected:
            return None
        return next((i for i, event in enumerate(self.scene["events"]) if event["id"] == selected[0]), None)

    def add_event(self):
        dialog = EventDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            if any(e["id"] == dialog.result["id"] for e in self.scene["events"]):
                messagebox.showerror("Duplicate ID", "Choose a unique event ID.", parent=self)
                return
            self.scene["events"].append(dialog.result)
            self.refresh()

    def edit_event(self):
        index = self._selected_index()
        if index is None:
            return
        dialog = EventDialog(self, self.scene["events"][index])
        self.wait_window(dialog)
        if dialog.result:
            if any(i != index and e["id"] == dialog.result["id"] for i, e in enumerate(self.scene["events"])):
                messagebox.showerror("Duplicate ID", "Choose a unique event ID.", parent=self)
                return
            self.scene["events"][index] = dialog.result
            self.refresh()

    def remove_event(self):
        index = self._selected_index()
        if index is not None:
            del self.scene["events"][index]
            self.refresh()

    def _sync_meta(self):
        self.scene["id"] = self.id_var.get().strip()
        self.scene["title"] = self.title_var.get().strip()

    def validate(self):
        self._sync_meta()
        try:
            validate_scene(self.scene)
            messagebox.showinfo("Valid cutscene", "The cutscene document is structurally valid.\n"
                                "It is not yet executable by the game runtime.", parent=self)
        except ValueError as exc:
            messagebox.showerror("Validation failed", str(exc), parent=self)

    def preview(self):
        self._sync_meta()
        try:
            validate_scene(self.scene)
        except ValueError as exc:
            messagebox.showerror("Cannot preview", str(exc), parent=self)
            return
        lines = [f'{self.scene["title"]} — timeline preview', ""]
        for e in sorted(self.scene["events"], key=lambda x: (x["start"], x["id"])):
            lines.append(f'{e["start"]:7.2f}s  [{e["type"]}]  ' + (
                f'{e["speaker"]}: {e["text"]}' if e["type"] == "dialogue" else
                f'camera={e["camera"]}' if e["type"] == "camera_cue" else
                f'{e["actor"]} animation={e["animation"]}' if e["type"] == "actor_animation" else
                f'wait {e["duration"]:.2f}s'))
        messagebox.showinfo("Timeline preview", "\n".join(lines) if len(lines) > 2 else "No events yet.", parent=self)

    def save_scene(self):
        self._sync_meta()
        try:
            validate_scene(self.scene)
        except ValueError as exc:
            messagebox.showerror("Cannot save", str(exc), parent=self)
            return
        path = self.folder / f'{self.scene["id"]}.json'
        path.write_text(json.dumps(self.scene, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        messagebox.showinfo("Saved", f"Saved cutscene project:\n{path}", parent=self)

    def open_scene(self):
        path = filedialog.askopenfilename(parent=self, initialdir=self.folder,
                    filetypes=[("PJ cutscene", "*.json"), ("JSON", "*.json")])
        if not path:
            return
        try:
            loaded = json.loads(Path(path).read_text(encoding="utf-8"))
            validate_scene(loaded)
            self.scene = loaded
            self.id_var.set(loaded["id"])
            self.title_var.set(loaded["title"])
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Cannot open cutscene", str(exc), parent=self)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/cutscene_editor.py <mod-project-folder>", file=sys.stderr)
        raise SystemExit(2)
    CutsceneEditor(Path(sys.argv[1])).mainloop()
