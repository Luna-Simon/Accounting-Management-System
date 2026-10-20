import csv
from tkinter import ttk

from . import theme


def col(title, width, anchor="w", stretch=False):
    return (title, width, anchor, stretch)


class Table(ttk.Frame):
    """Excel/Sheets-style data table with clean dark theme."""
    
    def __init__(self, parent, columns, height=12):
        super().__init__(parent)
        self.columns = columns
        self.data = []
        ids = [f"c{i}" for i in range(len(columns))]
        
        # Treeview with minimal styling
        self.tree = ttk.Treeview(self, columns=ids, show="headings", selectmode="extended", height=height)
        for cid, (title, width, anchor, stretch) in zip(ids, columns):
            self.tree.heading(cid, text=title, anchor=anchor)
            self.tree.column(cid, width=width, anchor=anchor, stretch=stretch, minwidth=50)
        
        # Row tags for alternating colors
        self.tree.tag_configure("even", background=theme.BG)
        self.tree.tag_configure("odd", background=theme.PANEL)
        self.tree.tag_configure("total", background=theme.PANEL)
        self.tree.tag_configure("credit", foreground=theme.SUCCESS)
        self.tree.tag_configure("debit", foreground=theme.TEXT)
        # Apply bold font if theme is initialized
        if theme.bold_font:
            self.tree.tag_configure("total", font=theme.bold_font)
        
        # Scrollbars
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview, style="Vertical.TScrollbar")
        self.hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview, style="Horizontal.TScrollbar")
        self.tree.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        
        # Bindings for Excel-like behavior
        self.tree.bind("<Control-c>", self.copy_selection)
        self.tree.bind("<Control-a>", self.select_all)

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

    def copy_selection(self, event=None):
        """Copy selected rows as tab-separated values."""
        items = self.tree.selection()
        if not items:
            return
        rows = []
        for item in items:
            rows.append("\t".join(str(v) for v in self.tree.item(item, "values")))
        self.clipboard_clear()
        self.clipboard_append("\n".join(rows))

    def select_all(self, event=None):
        self.tree.selection_set(self.tree.get_children())

    def export_csv(self, path):
        with open(path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow([column[0] for column in self.columns])
            writer.writerows(self.data)


class Card(ttk.LabelFrame):
    """Apple-style card container."""
    
    def __init__(self, parent, title="", **kwargs):
        super().__init__(parent, text=title, style="Card.TLabelframe", padding=16, **kwargs)
        self.columnconfigure(0, weight=1)


class StatCard(ttk.Frame):
    """Dashboard stat card with icon, value, and label."""
    
    def __init__(self, parent, label, value="0", icon="", **kwargs):
        super().__init__(parent, style="Card.TFrame", **kwargs)
        self.configure(padding=20)
        
        # Icon/label row
        top = ttk.Frame(self)
        top.pack(fill="x")
        if icon:
            ttk.Label(top, text=icon, font=("Segoe UI", 20)).pack(side="left")
        ttk.Label(top, text=label, style="Muted.TLabel").pack(side="left", padx=(8 if icon else 0, 0))
        
        # Value
        self.value_var = tk.StringVar(value=value)
        ttk.Label(self, textvariable=self.value_var, style="CardValue.TLabel").pack(anchor="w", pady=(8, 0))
        
    def set_value(self, value):
        self.value_var.set(value)


import tkinter as tk