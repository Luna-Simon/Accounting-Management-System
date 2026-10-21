"""
Reusable UI widgets.
"""

import csv
import tkinter as tk
from tkinter import ttk

from . import theme


def col(title, width, anchor="w", stretch=False):
    return (title, width, anchor, stretch)


class Table(ttk.Frame):
    def __init__(self, parent, columns, height=12):
        super().__init__(parent)
        self.columns = columns
        self.data = []
        ids = [f"c{i}" for i in range(len(columns))]

        self.tree = ttk.Treeview(self, columns=ids, show="headings",
                                 selectmode="extended", height=height)
        for cid, (title, width, anchor, stretch) in zip(ids, columns):
            self.tree.heading(cid, text=title, anchor=anchor)
            self.tree.column(cid, width=width, anchor=anchor, stretch=stretch, minwidth=60)

        self.tree.tag_configure("even", background=theme.BG)
        self.tree.tag_configure("odd", background=theme.PANEL)
        self.tree.tag_configure("total", background=theme.PANEL)
        if theme.bold_font:
            self.tree.tag_configure("total", font=theme.bold_font)

        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview,
                                 style="Vertical.TScrollbar")
        self.hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview,
                                 style="Horizontal.TScrollbar")
        self.tree.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.tree.bind("<Control-c>", self.copy_sel)
        self.tree.bind("<Control-a>", self.sel_all)

    def clear(self):
        self.tree.delete(*self.tree.get_children())
        self.data = []

    def add(self, values, tags=(), iid=None):
        if not tags:
            tags = ("odd" if len(self.data) % 2 else "even",)
        self.tree.insert("", "end", iid=iid, values=values, tags=tags)
        self.data.append(values)

    def selected(self):
        chosen = self.tree.selection()
        return chosen[0] if chosen else None

    def copy_sel(self, event=None):
        items = self.tree.selection()
        if not items:
            return
        rows = []
        for item in items:
            rows.append("\t".join(str(v) for v in self.tree.item(item, "values")))
        self.clipboard_clear()
        self.clipboard_append("\n".join(rows))

    def sel_all(self, event=None):
        self.tree.selection_set(self.tree.get_children())

    def export_csv(self, path):
        with open(path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow([column[0] for column in self.columns])
            writer.writerows(self.data)


class Card(ttk.LabelFrame):
    def __init__(self, parent, title="", **kwargs):
        super().__init__(parent, text=title, style="Card.TLabelframe", padding=14, **kwargs)
        self.columnconfigure(0, weight=1)


class HelpLabel(tk.Label):
    def __init__(self, parent, text, bg=None, **kwargs):
        super().__init__(parent, text=text, bg=bg or theme.BG, fg=theme.TEXT_DIM,
                         font=("Segoe UI", 9), **kwargs)
        self.configure(anchor="w", justify="left")


class StatCard(tk.Frame):
    def __init__(self, parent, label, value="0", icon="", **kwargs):
        super().__init__(parent, bg=theme.PANEL, **kwargs)
        self.configure(padx=14, pady=14, highlightbackground=theme.LINE,
                       highlightthickness=1)

        top = tk.Frame(self, bg=theme.PANEL)
        top.pack(fill="x")
        if icon:
            tk.Label(top, text=icon, bg=theme.PANEL, fg=theme.TEXT,
                     font=("Segoe UI", 16)).pack(side="left")
        tk.Label(top, text=label, bg=theme.PANEL, fg=theme.TEXT_DIM,
                 font=("Segoe UI", 9)).pack(side="left", padx=(8 if icon else 0, 0))

        self.value_var = tk.StringVar(value=value)
        tk.Label(self, textvariable=self.value_var, bg=theme.PANEL, fg=theme.TEXT,
                 font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(8, 0))

    def set_value(self, value):
        self.value_var.set(value)
