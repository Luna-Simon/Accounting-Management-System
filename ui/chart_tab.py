"""
Chart of Accounts Tab - Modern spreadsheet-style account management.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from accounting import DEFAULT_NORMAL, TYPES

from .widgets import Table, col, Card


class ChartTab(ttk.Frame):
    def __init__(self, parent, book, on_change):
        super().__init__(parent, padding=16)
        self.book = book
        self.on_change = on_change
        self.current = None

        # Header
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 16))
        ttk.Label(header, text="Chart of Accounts", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Import from Excel", style="Ghost.TButton",
                   command=self.import_excel).pack(side="right")

        # Form card
        form_card = Card(self, title="Add / Edit Account")
        form_card.pack(fill="x", pady=(0, 16))
        form_card.columnconfigure(1, weight=1)

        fields = [
            ("Code", "code_var", 10),
            ("Name", "name_var", 40),
        ]
        for row, (label, var_name, width) in enumerate(fields):
            ttk.Label(form_card, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=6)
            var = tk.StringVar()
            setattr(self, var_name, var)
            ttk.Entry(form_card, textvariable=var, width=width).grid(row=row, column=1, sticky="ew", pady=6)

        # Type and Normal
        ttk.Label(form_card, text="Type").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=6)
        self.type_var = tk.StringVar(value=TYPES[0])
        type_combo = ttk.Combobox(form_card, textvariable=self.type_var, values=TYPES, state="readonly", width=18)
        type_combo.grid(row=2, column=1, sticky="w", pady=6)

        ttk.Label(form_card, text="Normal Balance").grid(row=3, column=0, sticky="w", padx=(0, 12), pady=6)
        self.normal_var = tk.StringVar(value=DEFAULT_NORMAL[TYPES[0]])
        normal_combo = ttk.Combobox(form_card, textvariable=self.normal_var, values=["Debit", "Credit"],
                     state="readonly", width=12).grid(row=3, column=1, sticky="w", pady=6)

        # Auto-update Normal when Type changes (using trace for reliability)
        def on_type_change(*args):
            t = self.type_var.get()
            if t in DEFAULT_NORMAL:
                self.normal_var.set(DEFAULT_NORMAL[t])
        self.type_var.trace_add("write", on_type_change)

        # Action buttons
        btn_frame = ttk.Frame(form_card)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(btn_frame, text="Add", style="Accent.TButton", command=self.add).pack(side="left")
        ttk.Button(btn_frame, text="Update", command=self.update).pack(side="left", padx=8)
        ttk.Button(btn_frame, text="Delete", style="Danger.TButton", command=self.delete).pack(side="left")
        ttk.Button(btn_frame, text="Clear", style="Ghost.TButton", command=self.clear).pack(side="left", padx=8)

        # Accounts table
        table_card = Card(self, title="Accounts")
        table_card.pack(fill="both", expand=True)

        self.table = Table(table_card, [
            col("Code", 90, "center"),
            col("Account Name", 400, stretch=True),
            col("Type", 150, "center"),
            col("Normal", 120, "center"),
        ])
        self.table.pack(fill="both", expand=True)
        self.table.tree.bind("<<TreeviewSelect>>", self.on_select)

    def import_excel(self):
        from tkinter import filedialog
        import pandas as pd
        
        path = filedialog.askopenfilename(
            title="Import Chart of Accounts",
            filetypes=[("Excel Files", "*.xlsx *.xls"), ("CSV Files", "*.csv")]
        )
        if not path:
            return
        try:
            df = pd.read_excel(path) if path.endswith(('.xlsx', '.xls')) else pd.read_csv(path)
            df.columns = df.columns.str.strip().str.lower()
            
            required = ['code', 'name', 'type', 'normal']
            missing = [c for c in required if c not in df.columns]
            if missing:
                raise ValueError(f"Missing columns: {', '.join(missing)}")
            
            imported = 0
            skipped = 0
            for _, row in df.iterrows():
                code = str(row['code']).strip()
                if not code:
                    continue
                if self.book.find(code):
                    skipped += 1
                    continue
                self.book.add_account({
                    "code": code,
                    "name": str(row['name']).strip(),
                    "type": str(row['type']).strip(),
                    "normal": str(row['normal']).strip(),
                })
                imported += 1
            
            messagebox.showinfo("Import Complete", f"Imported: {imported}, Skipped (existing): {skipped}")
            self.on_change()
        except Exception as e:
            messagebox.showerror("Import Failed", str(e))

    def refresh(self):
        self.table.clear()
        for account in self.book.accounts:
            self.table.add((account["code"], account["name"], account["type"], account["normal"]),
                           iid=account["code"])

    def read_form(self):
        code = self.code_var.get().strip()
        name = self.name_var.get().strip()
        if not code or not name:
            raise ValueError("Enter an account code and name.")
        if " " in code:
            raise ValueError("Account codes cannot contain spaces.")
        return {"code": code, "name": name, "type": self.type_var.get(), "normal": self.normal_var.get()}

    def submit(self, action):
        try:
            action(self.read_form())
        except ValueError as error:
            messagebox.showerror("Chart of Accounts", str(error))
            return
        self.clear()
        self.on_change()

    def add(self):
        self.submit(self.book.add_account)

    def update(self):
        if self.current is None:
            messagebox.showerror("Chart of Accounts", "Select an account to update.")
            return
        self.submit(lambda account: self.book.update_account(self.current, account))

    def delete(self):
        if self.current is None:
            return
        try:
            self.book.delete_account(self.current)
        except ValueError as error:
            messagebox.showerror("Chart of Accounts", str(error))
            return
        self.clear()
        self.on_change()

    def clear(self):
        self.current = None
        self.code_var.set("")
        self.name_var.set("")
        self.type_var.set(TYPES[0])
        self.normal_var.set(DEFAULT_NORMAL[TYPES[0]])
        self.table.tree.selection_set(())

    def on_select(self, event):
        code = self.table.selected()
        account = self.book.find(code) if code else None
        if account is None:
            return
        self.current = code
        self.code_var.set(account["code"])
        self.name_var.set(account["name"])
        self.type_var.set(account["type"])
        self.normal_var.set(account["normal"])