"""
Chart of Accounts Tab.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from accounting import DEFAULT_NORMAL, TYPES

from . import theme
from .widgets import Table, col, Card, HelpLabel


class COATab(ttk.Frame):
    def __init__(self, parent, book, on_change):
        super().__init__(parent, padding=16)
        self.book = book
        self.on_change = on_change
        self.current = None

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 16))
        ttk.Label(header, text="Chart of Accounts", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Import from Excel", style="Ghost.TButton",
                   command=self.imp_xl).pack(side="right")

        form_card = Card(self, title="Add / Edit Account")
        form_card.pack(fill="x", pady=(0, 16))
        form_card.columnconfigure(1, weight=1)

        # Account Code
        ttk.Label(form_card, text="Account Code", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4))
        self.cd_var = tk.StringVar()
        self.cd_entry = ttk.Entry(form_card, textvariable=self.cd_var, width=16)
        self.cd_entry.grid(row=1, column=0, sticky="w", pady=(0, 14))
        HelpLabel(form_card, text="No spaces. Examples: 101, 102, 501", bg=theme.PANEL).grid(
            row=2, column=0, sticky="w", pady=(0, 14))

        # Account Name
        ttk.Label(form_card, text="Account Name", style="CardTitle.TLabel").grid(
            row=0, column=1, sticky="w", padx=(24, 0), pady=(0, 4))
        self.nm_var = tk.StringVar()
        ttk.Entry(form_card, textvariable=self.nm_var, width=44).grid(
            row=1, column=1, sticky="ew", padx=(24, 0), pady=(0, 14))
        HelpLabel(form_card, text="Examples: Cash, Accounts Receivable, Depreciation Expense", bg=theme.PANEL).grid(
            row=2, column=1, sticky="w", padx=(24, 0), pady=(0, 14))

        # Account Type — dropdown
        ttk.Label(form_card, text="Account Type", style="CardTitle.TLabel").grid(
            row=3, column=0, sticky="w", pady=(0, 4))
        self.tp_var = tk.StringVar(value=TYPES[0])
        self.tp_cb = ttk.Combobox(form_card, textvariable=self.tp_var, values=TYPES,
                                  state="readonly", width=20)
        self.tp_cb.grid(row=4, column=0, sticky="w", pady=(0, 14))

        # Normal Balance — dropdown
        ttk.Label(form_card, text="Normal Balance", style="CardTitle.TLabel").grid(
            row=3, column=1, sticky="w", padx=(24, 0), pady=(0, 4))
        self.nr_var = tk.StringVar(value=DEFAULT_NORMAL[TYPES[0]])
        self.nr_cb = ttk.Combobox(form_card, textvariable=self.nr_var,
                                  values=["Debit", "Credit"], state="readonly", width=14)
        self.nr_cb.grid(row=4, column=1, sticky="w", padx=(24, 0), pady=(0, 14))

        self.tp_hint = HelpLabel(form_card, text="", bg=theme.PANEL)
        self.tp_hint.grid(row=5, column=0, sticky="w", pady=(4, 0))
        self.nr_hint = HelpLabel(form_card, text="Filled in automatically from Account Type.", bg=theme.PANEL)
        self.nr_hint.grid(row=5, column=1, sticky="w", padx=(24, 0), pady=(4, 0))

        self.nr_warn = tk.Label(form_card, text="", bg=theme.PANEL, fg=theme.WARNING,
                                font=("Segoe UI", 9), anchor="w", justify="left")
        self.nr_warn.grid(row=6, column=0, columnspan=2, sticky="w", pady=(0, 8))

        def tp_changed(*args):
            t = self.tp_var.get()
            if t in DEFAULT_NORMAL:
                self.nr_var.set(DEFAULT_NORMAL[t])
            self._tp_hint(t)
            self._nr_warn()
        self.tp_var.trace_add("write", tp_changed)
        self.nr_var.trace_add("write", lambda *args: self._nr_warn())
        self._tp_hint(TYPES[0])
        self._nr_warn()

        btn_frame = ttk.Frame(form_card)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=(10, 0), sticky="w")
        ttk.Button(btn_frame, text="Add Account", style="Accent.TButton", command=self.add_acct).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="Update Selected", command=self.upd_acct).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="Delete Selected", style="Danger.TButton", command=self.del_acct).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="Clear Form", style="Ghost.TButton", command=self.clr).pack(side="left")

        table_card = Card(self, title="All Accounts")
        table_card.pack(fill="both", expand=True)

        self.table = Table(table_card, [
            col("Code", 100, "center"),
            col("Account Name", 420, stretch=True),
            col("Type", 140, "center"),
            col("Normal Balance", 140, "center"),
        ])
        self.table.pack(fill="both", expand=True)
        self.table.tree.bind("<<TreeviewSelect>>", self.sel_acct)

    def _tp_hint(self, atype):
        hints = {
            "Asset": "Resources owned — Normal: Debit",
            "Liability": "Debts owed — Normal: Credit",
            "Equity": "Owner's stake — Normal: Credit",
            "Revenue": "Income earned — Normal: Credit",
            "Cost of Sales": "Cost of goods sold — Normal: Debit",
            "Expense": "Operating costs — Normal: Debit",
        }
        self.tp_hint.configure(text=(
            f"{hints.get(atype, '')}   |   "
            f"Choose: Asset, Liability, Equity, Revenue, Cost of Sales, Expense"
        ))

    def _nr_warn(self):
        atype = self.tp_var.get()
        normal = self.nr_var.get()
        if not atype or not normal:
            self.nr_warn.configure(text="")
            return
        expected = DEFAULT_NORMAL.get(atype)
        if expected is not None and normal != expected:
            self.nr_warn.configure(text=(
                f"⚠ Unusual for {atype} (usually {expected}). "
                f"Keep this only for contra accounts, like Accumulated Depreciation "
                f"(Asset/Credit) or Sales Returns (Revenue/Debit)."))
        else:
            self.nr_warn.configure(text="")

    def imp_xl(self):
        from tkinter import filedialog
        import pandas as pd

        path = filedialog.askopenfilename(
            title="Import Chart of Accounts from Excel",
            filetypes=[("Excel Files", "*.xlsx *.xls"), ("CSV Files", "*.csv")]
        )
        if not path:
            return
        try:
            df = pd.read_excel(path) if path.endswith(('.xlsx', '.xls')) else pd.read_csv(path)
            df.columns = df.columns.str.strip().str.lower()

            req = ['code', 'name', 'type', 'normal']
            missing = [c for c in req if c not in df.columns]
            if missing:
                raise ValueError(f"Missing columns: {', '.join(missing)}")

            imported = 0
            skipped = 0
            for _, row in df.iterrows():
                code = str(row['code']).strip()
                if not code:
                    continue
                if self.book.get_acct(code):
                    skipped += 1
                    continue
                self.book.add_acct({
                    "code": code,
                    "name": str(row['name']).strip(),
                    "type": str(row['type']).strip(),
                    "normal": str(row['normal']).strip(),
                })
                imported += 1

            messagebox.showinfo("Import Complete",
                                f"Imported: {imported}\nSkipped (already exist): {skipped}")
            self.on_change()
        except Exception as e:
            messagebox.showerror("Import Failed", str(e))

    def reload(self):
        self.table.clear()
        for account in self.book.accts:
            self.table.add((account["code"], account["name"], account["type"], account["normal"]),
                           iid=account["code"])

    def rd_frm(self):
        code = self.cd_var.get().strip()
        name = self.nm_var.get().strip()
        if not code or not name:
            raise ValueError("Enter both account code and name.")
        if " " in code:
            raise ValueError("Account codes cannot contain spaces.")
        return {"code": code, "name": name, "type": self.tp_var.get(), "normal": self.nr_var.get()}

    def sbm(self, action):
        try:
            action(self.rd_frm())
        except ValueError as error:
            messagebox.showerror("Chart of Accounts", str(error))
            return
        self.clr()
        self.on_change()

    def add_acct(self):
        self.sbm(self.book.add_acct)

    def upd_acct(self):
        if self.current is None:
            messagebox.showerror("Chart of Accounts", "Select an account from the table first.")
            return
        self.sbm(lambda account: self.book.chg_acct(self.current, account))

    def del_acct(self):
        if self.current is None:
            return
        try:
            self.book.rm_acct(self.current)
        except ValueError as error:
            messagebox.showerror("Chart of Accounts", str(error))
            return
        self.clr()
        self.on_change()

    def clr(self):
        self.current = None
        self.cd_var.set("")
        self.nm_var.set("")
        self.tp_var.set(TYPES[0])
        self.nr_var.set(DEFAULT_NORMAL[TYPES[0]])
        self._tp_hint(TYPES[0])
        self.table.tree.selection_set(())

    def sel_acct(self, event):
        code = self.table.selected()
        account = self.book.get_acct(code) if code else None
        if account is None:
            return
        self.current = code
        self.cd_var.set(account["code"])
        self.nm_var.set(account["name"])
        self.tp_var.set(account["type"])
        self.nr_var.set(account["normal"])
        self._tp_hint(account["type"])

    # Dead helper — no one calls this but it's here anyway.
    def _unused_helper(self):
        return "placeholder"
