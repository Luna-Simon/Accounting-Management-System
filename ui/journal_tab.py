"""
Journal Tab - Modern entry form with Excel-like table.
"""

import tkinter as tk
import threading
from datetime import date, datetime
from tkinter import filedialog, messagebox, ttk

import money

from .widgets import Table, col, Card


class JournalTab(ttk.Frame):
    def __init__(self, parent, book, kind, on_change):
        super().__init__(parent, padding=16)
        self.book = book
        self.kind = kind
        self.on_change = on_change
        self.noun = "Adjustment" if kind == "adjustments" else "Entry"
        self.editing = None
        self.lines = []
        self.options = []
        self.lookup = {}
        self.labels = {}
        self._import_thread = None

        # Header
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 16))
        ttk.Label(header, text=f"{self.noun} Entry", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text=f"Record a new {self.noun.lower()} or import from Excel", style="Subtitle.TLabel").pack(side="left", padx=(12, 0))

        # Date and Description
        top = Card(self, title="")
        top.pack(fill="x", pady=(0, 16))
        top.columnconfigure(1, weight=1)
        ttk.Label(top, text="Date (YYYY-MM-DD)").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Label(top, text="Description").grid(row=0, column=1, sticky="w", padx=(12, 0), pady=6)
        self.date_var = tk.StringVar(value=date.today().isoformat())
        self.description_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.date_var, width=15).grid(row=1, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(top, textvariable=self.description_var).grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(0, 6))

        # Entry lines grid
        lines_card = Card(self, title="Entry Lines")
        lines_card.pack(fill="x", pady=(0, 16))
        lines_card.columnconfigure(0, weight=1)
        
        for column, text in enumerate(("Account", "Debit", "Credit")):
            ttk.Label(lines_card, text=text).grid(row=0, column=column, sticky="w", padx=(0 if column == 0 else 8, 0), pady=6)

        self.grid_frame = ttk.Frame(lines_card)
        self.grid_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=6)
        self.grid_frame.columnconfigure(0, weight=1)

        # Button bar
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 16))
        ttk.Button(bar, text="Add Line", command=self.add_line).pack(side="left")
        ttk.Button(bar, text="Import from Excel", style="Ghost.TButton", command=self.import_from_excel).pack(side="left", padx=(8, 0))
        self.post_button = ttk.Button(bar, text=f"Post {self.noun}", style="Accent.TButton", command=self.post)
        self.post_button.pack(side="right")
        ttk.Button(bar, text="Clear", style="Ghost.TButton", command=self.clear_form).pack(side="right", padx=8)
        self.totals = ttk.Label(bar, style="Muted.TLabel")
        self.totals.pack(side="right", padx=16)

        # Action buttons
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(0, 16))
        ttk.Button(actions, text="Edit Selected", command=self.edit).pack(side="left")
        ttk.Button(actions, text="Delete Selected", style="Danger.TButton", command=self.delete).pack(side="left", padx=8)

        # Entries table
        table_card = Card(self, title=f"{self.noun}s")
        table_card.pack(fill="both", expand=True)

        self.table = Table(table_card, [
            col("No.", 50, "center"),
            col("Date", 110, "center"),
            col("Account", 350, stretch=True),
            col("Debit", 140, "e"),
            col("Credit", 140, "e"),
            col("Description", 300, stretch=True),
        ], height=8)
        self.table.pack(fill="both", expand=True)
        self.table.tree.bind("<Double-1>", lambda event: self.edit())
        self.set_lines(2)

    def build_lookup(self):
        self.options = []
        self.lookup = {}
        self.labels = {}
        for account in self.book.accounts:
            label = f"{account['code']} — {account['name']}"
            self.options.append(label)
            self.labels[account["code"]] = label
            for key in (label, account["code"], account["name"]):
                self.lookup[key] = account["code"]

    def refresh(self):
        self.build_lookup()
        for line in self.lines:
            line["widgets"][0].configure(values=self.options)
        self.table.clear()
        total_debit = total_credit = 0
        entries = sorted(getattr(self.book, self.kind), key=lambda e: (e["date"], e["id"]))
        for index, entry in enumerate(entries):
            tag = "odd" if index % 2 else "even"
            for position, line in enumerate(entry["lines"]):
                name = self.book.name_of(line["account"])
                if line["credit"]:
                    name = "    " + name
                first = position == 0
                self.table.add((
                    str(entry["id"]) if first else "",
                    entry["date"] if first else "",
                    name,
                    money.fmt(line["debit"]),
                    money.fmt(line["credit"]),
                    entry["description"] if first else "",
                ), (tag,), iid=f"{entry['id']}-{position}")
                total_debit += line["debit"]
                total_credit += line["credit"]
        self.table.add(("", "", "Total", money.fmt(total_debit, False), money.fmt(total_credit, False), ""),
                       ("total",), iid="total")

    def add_line(self, account="", debit="", credit=""):
        row = len(self.lines) + 1
        variables = [tk.StringVar(value=account), tk.StringVar(value=debit), tk.StringVar(value=credit)]
        combo = ttk.Combobox(self.grid_frame, textvariable=variables[0], values=self.options, width=52)
        debit_entry = ttk.Entry(self.grid_frame, textvariable=variables[1], width=16, justify="right")
        credit_entry = ttk.Entry(self.grid_frame, textvariable=variables[2], width=16, justify="right")
        combo.grid(row=row, column=0, sticky="ew", pady=3)
        debit_entry.grid(row=row, column=1, padx=(8, 0), pady=3)
        credit_entry.grid(row=row, column=2, padx=(8, 0), pady=3)
        for variable in variables[1:]:
            variable.trace_add("write", lambda *args: self.update_totals())
        self.lines.append({"vars": variables, "widgets": (combo, debit_entry, credit_entry)})

    def set_lines(self, count):
        for line in self.lines:
            for widget in line["widgets"]:
                widget.destroy()
        self.lines = []
        for _ in range(count):
            self.add_line()
        self.update_totals()

    @staticmethod
    def amount(variable):
        try:
            return money.parse(variable.get())
        except ValueError:
            return 0

    def update_totals(self):
        debit = sum(self.amount(line["vars"][1]) for line in self.lines)
        credit = sum(self.amount(line["vars"][2]) for line in self.lines)
        text = f"Debit {money.fmt(debit, False)}    Credit {money.fmt(credit, False)}"
        if debit != credit:
            text += f"    Difference {money.fmt(abs(debit - credit), False)}"
        self.totals.configure(text=text)

    def read_form(self):
        if not self.book.accounts:
            raise ValueError("Add accounts in the Chart of Accounts tab first.")
        try:
            day = datetime.strptime(self.date_var.get().strip(), "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Enter the date as YYYY-MM-DD.") from None
        lines = []
        for line in self.lines:
            label, debit_text, credit_text = (variable.get().strip() for variable in line["vars"])
            if not (label or debit_text or credit_text):
                continue
            if not label:
                raise ValueError("Select an account for every line.")
            code = self.lookup.get(label)
            if code is None:
                raise ValueError(f"Account not found: {label}")
            debit, credit = money.parse(debit_text), money.parse(credit_text)
            if debit < 0 or credit < 0 or bool(debit) == bool(credit):
                raise ValueError("Each line needs either a debit or a credit amount.")
            lines.append({"account": code, "debit": debit, "credit": credit})
        if len(lines) < 2:
            raise ValueError("An entry needs at least two lines.")
        if sum(line["debit"] for line in lines) != sum(line["credit"] for line in lines):
            raise ValueError("Total debits must equal total credits.")
        return {
            "id": self.editing,
            "date": day.isoformat(),
            "description": self.description_var.get().strip(),
            "lines": lines,
        }

    def post(self):
        try:
            entry = self.read_form()
        except ValueError as error:
            messagebox.showerror(f"Cannot post {self.noun.lower()}", str(error))
            return
        self.book.save_entry(self.kind, entry)
        self.clear_form()
        self.on_change()

    def import_from_excel(self):
        """Launch Excel import in a background thread."""
        path = filedialog.askopenfilename(
            title=f"Import {self.noun}s from Excel",
            filetypes=[("Excel Files", "*.xlsx *.xls"), ("All Files", "*.*")]
        )
        if not path:
            return
        
        self._set_import_state(enabled=False)
        
        self._import_thread = threading.Thread(
            target=self._run_import,
            args=(path,),
            daemon=True
        )
        self._import_thread.start()

    def _set_import_state(self, enabled=True):
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Button) and "Import" in str(child.cget("text")):
                        child.configure(state="normal" if enabled else "disabled")
        self.config(cursor="" if enabled else "watch")

    def _run_import(self, path):
        try:
            self.book.import_from_excel(path, self.kind)
            self.after(0, self._on_import_success)
        except Exception as error:
            self.after(0, lambda e=error: self._on_import_error(e))

    def _on_import_success(self):
        self._set_import_state(enabled=True)
        messagebox.showinfo("Success", "Data imported successfully!")
        self.on_change()

    def _on_import_error(self, error):
        self._set_import_state(enabled=True)
        messagebox.showwarning("Import Failed", str(error) or "Could not import the Excel file.")

    def clear_form(self):
        self.editing = None
        self.description_var.set("")
        self.set_lines(2)
        self.post_button.configure(text=f"Post {self.noun}")

    def selected_entry(self):
        iid = self.table.selected()
        if iid is None or iid == "total":
            return None
        return int(iid.split("-")[0])

    def edit(self):
        entry_id = self.selected_entry()
        if entry_id is None:
            return
        entry = self.book.entry(self.kind, entry_id)
        self.editing = entry_id
        self.date_var.set(entry["date"])
        self.description_var.set(entry["description"])
        self.set_lines(len(entry["lines"]))
        for slot, line in zip(self.lines, entry["lines"]):
            slot["vars"][0].set(self.labels[line["account"]])
            slot["vars"][1].set(money.fmt(line["debit"]))
            slot["vars"][2].set(money.fmt(line["credit"]))
        self.post_button.configure(text=f"Update {self.noun}")

    def delete(self):
        entry_id = self.selected_entry()
        if entry_id is None:
            return
        if not messagebox.askyesno(f"Delete {self.noun.lower()}", f"Delete {self.noun.lower()} {entry_id}?"):
            return
        self.book.delete_entry(self.kind, entry_id)
        if self.editing == entry_id:
            self.clear_form()
        self.on_change()