#!/usr/bin/env python3
"""PJ Mod Studio — safe starter editor for Tomodachi LTD Recomp.

This first prototype creates and validates mod project packages. It does NOT yet
apply mods to the game: runtime asset mounting and gameplay/cutscene hooks must
be implemented and tested separately before any package can affect gameplay.
"""
from __future__ import annotations

import json
import re
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "mods" / "projects"
SCHEMA_VERSION = 1
MOD_TYPES = {
    "asset": "Asset replacement",
    "cutscene": "Cutscene (experimental format)",
    "gameplay": "Gameplay extension (future runtime support)",
}
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{1,47}$")


def read_manifest(folder: Path) -> dict:
    path = folder / "mod.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("mod.json must contain a JSON object.")
    required = ("id", "name", "version", "author", "type")
    missing = [key for key in required if not isinstance(data.get(key), str) or not data[key].strip()]
    if missing:
        raise ValueError("Missing required fields: " + ", ".join(missing))
    if not SAFE_ID.fullmatch(data["id"]):
        raise ValueError("Mod ID must be 2–48 lowercase letters, numbers, dots, underscores or hyphens.")
    if data["type"] not in MOD_TYPES:
        raise ValueError("Unknown mod type.")
    if data.get("format_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported format_version; this editor supports {SCHEMA_VERSION}.")
    return data


def safe_package_files(folder: Path):
    """Yield project files while rejecting symlinks and paths outside the project."""
    root = folder.resolve()
    for path in sorted(folder.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlinks are not allowed in mod packages: {path.name}")
        if path.is_file():
            resolved = path.resolve()
            if root not in resolved.parents:
                raise ValueError("A project file points outside the project folder.")
            if path.name.lower() in {"prod.keys"} or path.suffix.lower() in {".nsp", ".xci"}:
                raise ValueError("Game dumps and console keys must never be included in a mod package.")
            yield path


class ModStudio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PJ Mod Studio — Tomodachi LTD Recomp")
        self.geometry("900x620")
        self.minsize(720, 500)
        self.configure(bg="#14251c")
        self.project: Path | None = None
        self._style()
        self._build()
        self.refresh_projects()

    def _style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", rowheight=30, font=("DejaVu Sans", 10))
        style.configure("Treeview.Heading", font=("DejaVu Sans", 10, "bold"))
        style.configure("TButton", padding=8, font=("DejaVu Sans", 10))
        style.configure("TLabel", background="#14251c", foreground="#eff8f0")
        style.configure("Title.TLabel", font=("DejaVu Sans", 19, "bold"), foreground="#a5e6b6")
        style.configure("Muted.TLabel", foreground="#bfd0c2")
        style.configure("TEntry", padding=6)

    def _build(self):
        header = ttk.Frame(self, padding=(20, 18))
        header.pack(fill="x")
        ttk.Label(header, text="PJ MOD STUDIO", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Create • Validate • Package — runtime support is being developed",
                  style="Muted.TLabel").pack(anchor="w", pady=(4, 0))

        body = ttk.Frame(self, padding=(20, 4, 20, 18))
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body)
        left.pack(side="left", fill="y", padx=(0, 16))
        ttk.Label(left, text="MOD PROJECTS").pack(anchor="w", pady=(0, 8))
        self.tree = ttk.Treeview(left, columns=("kind",), show="tree headings", height=15)
        self.tree.heading("#0", text="Project")
        self.tree.heading("kind", text="Type")
        self.tree.column("#0", width=210)
        self.tree.column("kind", width=130)
        self.tree.pack(fill="y", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._select_project)
        ttk.Button(left, text="＋ New project", command=self.new_project).pack(fill="x", pady=(10, 4))
        ttk.Button(left, text="Open project folder", command=self.open_project).pack(fill="x")

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        ttk.Label(right, text="PROJECT DETAILS").pack(anchor="w", pady=(0, 8))
        self.details = tk.Text(right, height=16, wrap="word", bg="#20372a", fg="#eff8f0",
                               insertbackground="white", relief="flat", padx=12, pady=12,
                               font=("DejaVu Sans", 10))
        self.details.pack(fill="both", expand=True)
        self.details.insert("1.0", "Select a project to inspect it.\n\nCreate a project to start building a mod.")
        self.details.configure(state="disabled")
        actions = ttk.Frame(right)
        actions.pack(fill="x", pady=(12, 0))
        ttk.Button(actions, text="Validate", command=self.validate_project).pack(side="left")
        ttk.Button(actions, text="Export .zip", command=self.export_project).pack(side="left", padx=8)
        ttk.Button(actions, text="Refresh", command=self.refresh_projects).pack(side="right")

        footer = ttk.Label(self, text="Prototype: packages are not loaded by the game yet. Do not include game dumps, keys, or extracted proprietary assets.",
                           style="Muted.TLabel", padding=(20, 0, 20, 14), wraplength=850)
        footer.pack(fill="x")

    def refresh_projects(self):
        self.tree.delete(*self.tree.get_children())
        PROJECTS.mkdir(parents=True, exist_ok=True)
        for folder in sorted(p for p in PROJECTS.iterdir() if p.is_dir()):
            try:
                data = read_manifest(folder)
                kind = MOD_TYPES[data["type"]]
                label = data["name"]
            except Exception:
                kind, label = "Invalid project", folder.name
            self.tree.insert("", "end", iid=str(folder), text=label, values=(kind,))
        if self.project and self.project.exists():
            self._show_project()

    def _select_project(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        self.project = Path(selected[0])
        self._show_project()

    def _show_project(self):
        if not self.project:
            return
        try:
            data = read_manifest(self.project)
            text = (
                f"{data['name']}\n\nID: {data['id']}\nVersion: {data['version']}\n"
                f"Author: {data['author']}\nType: {MOD_TYPES[data['type']]}\n"
                f"Description: {data.get('description', '(none)')}\n\n"
                f"Folder: {self.project}\n\n"
                "This is an authoring project. Game-side support for this mod type "
                "must exist before the mod can change gameplay."
            )
        except Exception as exc:
            text = f"Project validation error:\n{exc}\n\nFolder: {self.project}"
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", text)
        self.details.configure(state="disabled")

    def new_project(self):
        dialog = NewProjectDialog(self)
        self.wait_window(dialog)
        if not dialog.result:
            return
        data = dialog.result
        folder = PROJECTS / data["id"]
        if folder.exists():
            messagebox.showerror("Already exists", "A project with that ID already exists.", parent=self)
            return
        folder.mkdir(parents=True)
        (folder / "assets").mkdir()
        (folder / "cutscenes").mkdir()
        manifest = {"format_version": SCHEMA_VERSION, **data}
        (folder / "mod.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (folder / "README.md").write_text(
            f"# {data['name']}\n\n{data.get('description', '')}\n\n"
            "This project contains original mod-authored files only.\n", encoding="utf-8")
        self.project = folder
        self.refresh_projects()
        self.tree.selection_set(str(folder))
        self._show_project()

    def validate_project(self):
        if not self.project:
            messagebox.showinfo("Select a project", "Choose a project first.", parent=self)
            return
        try:
            data = read_manifest(self.project)
            files = list(safe_package_files(self.project))
            messagebox.showinfo("Validation passed",
                                f"{data['name']} is valid.\n\n{len(files)} package files found.\n"
                                "This validates the package only; it does not test in-game compatibility.",
                                parent=self)
        except Exception as exc:
            messagebox.showerror("Validation failed", str(exc), parent=self)

    def export_project(self):
        if not self.project:
            messagebox.showinfo("Select a project", "Choose a project first.", parent=self)
            return
        try:
            read_manifest(self.project)
            files = list(safe_package_files(self.project))
        except Exception as exc:
            messagebox.showerror("Cannot export", str(exc), parent=self)
            return
        target = filedialog.asksaveasfilename(parent=self, title="Export mod package",
                    initialfile=f"{self.project.name}.zip", defaultextension=".zip",
                    filetypes=[("PJ Mod package", "*.zip")])
        if not target:
            return
        try:
            with ZipFile(target, "w", ZIP_DEFLATED) as archive:
                for path in files:
                    archive.write(path, path.relative_to(self.project).as_posix())
            messagebox.showinfo("Export complete", f"Created {target}\n\nThe game does not load this package yet.",
                                parent=self)
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc), parent=self)

    def open_project(self):
        if not self.project:
            messagebox.showinfo("Select a project", "Choose a project first.", parent=self)
            return
        import os
        import subprocess
        import sys
        if sys.platform == "win32":
            os.startfile(self.project)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(self.project)])
        else:
            subprocess.Popen(["xdg-open", str(self.project)])


class NewProjectDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("New mod project")
        self.resizable(False, False)
        self.result = None
        self.transient(parent)
        self.grab_set()
        frame = ttk.Frame(self, padding=18)
        frame.pack(fill="both", expand=True)
        self.fields = {}
        rows = (("name", "Project name"), ("id", "Mod ID"), ("author", "Author"),
                ("version", "Version"), ("description", "Description"))
        defaults = {"version": "1.0.0", "author": "PJ"}
        for row, (key, label) in enumerate(rows):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=6)
            entry = ttk.Entry(frame, width=38)
            entry.grid(row=row, column=1, sticky="ew", pady=6)
            entry.insert(0, defaults.get(key, ""))
            self.fields[key] = entry
        ttk.Label(frame, text="Mod type").grid(row=5, column=0, sticky="w", padx=(0, 12), pady=6)
        self.kind = tk.StringVar(value="asset")
        ttk.Combobox(frame, textvariable=self.kind, state="readonly",
                     values=list(MOD_TYPES), width=35).grid(row=5, column=1, sticky="ew", pady=6)
        ttk.Button(frame, text="Create project", command=self._submit).grid(row=6, column=0, columnspan=2,
                                                                           sticky="ew", pady=(14, 0))
        self.bind("<Return>", lambda _e: self._submit())

    def _submit(self):
        data = {key: widget.get().strip() for key, widget in self.fields.items()}
        data["type"] = self.kind.get()
        if not all(data[key] for key in ("name", "id", "author", "version")):
            messagebox.showerror("Missing information", "Name, ID, author and version are required.", parent=self)
            return
        if not SAFE_ID.fullmatch(data["id"]):
            messagebox.showerror("Invalid ID", "Use 2–48 lowercase letters, numbers, dots, underscores or hyphens.", parent=self)
            return
        self.result = data
        self.destroy()


if __name__ == "__main__":
    ModStudio().mainloop()
