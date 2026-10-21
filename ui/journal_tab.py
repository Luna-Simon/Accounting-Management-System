"""
Journal Tab — Business Transactions and Adjustments.
"""

import tkinter as tk
import threading
from datetime import date, datetime
from tkinter import filedialog, messagebox, ttk

import money

from accounting import DEFAULT_NORMAL
from . import theme
from .widgets import Table, col, Card, HelpLabel

_IGNORE_KEYS = {"Up", "Down", "Left", "Right", "Home", "End", "Tab", "Return",
                "Escape", "Shift_L", "Shift_R", "Control_L", "Control_R",
                "Alt_L", "Alt_R", "Caps_Lock"}


class TxnTab(ttk.Frame):
    def __init__(self, parent, book, jnl_kind, on_change):
        super().__init__(parent, padding=16)
        self.book = book
        self.kind = jnl_kind
        self.on_change = on_change
        self.noun = "Adjustment" if jnl_kind == "adjts" else "Entry"
        self.noun_plural = "Adjustments" if jnl_kind == "adjts" else "Transactions"
        self.edit_id = None
        self.lns = []
        self.opts = []
        self.lkp = {}
        self.lbls = {}
        self._imp_thread = None

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 16))
        tab_title = "Business Transaction" if jnl_kind == "txns" else "Adjustment Entry"
        ttk.Label(header, text=tab_title, style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Import from Excel", style="Ghost.TButton",
                   command=self.imp_xl).pack(side="right")

        top = Card(self, title="Entry Details")
        top.pack(fill="x", pady=(0, 16))
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Date (YYYY-MM-DD)", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4))
        self.dt_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(top, textvariable=self.dt_var, width=16).grid(
            row=1, column=0, sticky="w", pady=(0, 14))
        HelpLabel(top, text="Example: 2024-12-31", bg=theme.PANEL).grid(
            row=2, column=0, sticky="w", pady=(0, 14))

        ttk.Label(top, text="Description", style="CardTitle.TLabel").grid(
            row=0, column=1, sticky="w", padx=(24, 0), pady=(0, 4))
        self.desc_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.desc_var, width=52).grid(
            row=1, column=1, sticky="ew", padx=(24, 0), pady=(0, 14))
        example = ("Owner invested cash" if jnl_kind == "txns"
                   else "Supplies used during the period")
        HelpLabel(top, text=f"What happened? Example: {example}", bg=theme.PANEL).grid(
            row=2, column=1, sticky="w", padx=(24, 0), pady=(0, 14))

        lines_card = Card(self, title="Entry Lines (Debit / Credit)")
        lines_card.pack(fill="x", pady=(0, 16))
        lines_card.columnconfigure(0, weight=1)

        self.grid_frame = ttk.Frame(lines_card, style="Card.TFrame")
        self.grid_frame.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(0, 8))
        self.grid_frame.columnconfigure(0, weight=1)
        self._hdrs(self.grid_frame)

        HelpLabel(lines_card, text=(
            "Type to search the Account box (code or name), then put the amount in Debit OR Credit. "
            "Normal Side: Assets & Expenses increase with Debit; Liabilities, Equity & Revenue increase with Credit."
        ), bg=theme.PANEL, wraplength=560).grid(row=2, column=0, columnspan=4, sticky="w", pady=(4, 0))

        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 16))

        left_group = ttk.Frame(bar)
        left_group.pack(side="left")
        ttk.Button(left_group, text="+ Add Line", command=self.add_ln).pack(side="left", padx=(0, 8))
        ttk.Button(left_group, text="Refresh Accounts", command=self.ref_lkp).pack(side="left", padx=(0, 8))

        right_group = ttk.Frame(bar)
        right_group.pack(side="right")
        self.totals = tk.Label(right_group, text="Debit 0.00    Credit 0.00",
                               bg=theme.BG, fg=theme.TEXT_DIM, font=("Segoe UI", 9))
        self.totals.pack(side="right", padx=(16, 0))
        ttk.Button(right_group, text="Clear Form", style="Ghost.TButton", command=self.clr_frm).pack(side="right", padx=(0, 8))
        self.post_btn = ttk.Button(right_group, text=f"Post {self.noun}", style="Accent.TButton", command=self.pst)
        self.post_btn.pack(side="right")

        self.bind("<Escape>", lambda event: self.clr_frm())
        self.bind("<Control-Return>", lambda event: self.pst())
        self.bind("<F5>", lambda event: self.ref_lkp())
        self.bind("<Double-1>", lambda event: self.nxt_ln())

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(0, 16))
        ttk.Button(actions, text="Edit Selected", command=self.edt).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Delete Selected", style="Danger.TButton", command=self.dl).pack(side="left")

        table_card = Card(self, title=f"All {self.noun_plural}")
        table_card.pack(fill="both", expand=True)

        self.table = Table(table_card, [
            col("No.", 60, "center"),
            col("Date", 120, "center"),
            col("Account", 400, stretch=True),
            col("Debit", 140, "e"),
            col("Credit", 140, "e"),
            col("Description", 340, stretch=True),
        ], height=8)
        self.table.pack(fill="both", expand=True)
        self.table.tree.bind("<Double-1>", lambda event: self.edt())
        self.set_lns(2)

    def bld_lkp(self):
        self.opts = []
        self.lkp = {}
        self.lbls = {}
        for account in self.book.accts:
            label = f"{account['code']} — {account['name']} ({account['type']})"
            self.opts.append(label)
            self.lbls[account["code"]] = label
            for key in (label, account["code"], account["name"]):
                self.lkp[key] = account["code"]

    def ref_lkp(self):
        self.bld_lkp()
        for line in self.lns:
            cb = line["widgets"][0]
            cb.configure(values=self.opts)
            cur = line["vars"][0].get()
            if cur not in self.opts:
                line["vars"][0].set("")
        self.upd_tots()

    def reload(self):
        self.bld_lkp()
        for line in self.lns:
            line["widgets"][0].configure(values=self.opts)
        self.table.clear()
        total_dr = total_cr = 0
        entries = sorted(getattr(self.book, self.kind), key=lambda e: (e["date"], e["id"]))
        for index, entry in enumerate(entries):
            tag = "odd" if index % 2 else "even"
            for position, line in enumerate(entry["lines"]):
                name = self.book.acct_name(line["account"])
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
                total_dr += line["debit"]
                total_cr += line["credit"]
        self.table.add(("", "", "Total", money.fmt(total_dr, False), money.fmt(total_cr, False), ""),
                       ("total",), iid="total")

    def _hdrs(self, frame):
        for column, text in enumerate(("Account", "Debit (Dr)", "Credit (Cr)", "Normal Side")):
            ttk.Label(frame, text=text, style="CardTitle.TLabel").grid(
                row=0, column=column, sticky="w",
                padx=(0 if column == 0 else 16, 0), pady=(0, 8))

    def add_ln(self, account="", debit="", credit="", row=None):
        if row is None:
            row = len(self.lns) + 1
        variables = [tk.StringVar(value=account), tk.StringVar(value=debit), tk.StringVar(value=credit)]
        cb = ttk.Combobox(self.grid_frame, textvariable=variables[0], values=self.opts, width=44)
        cb.grid(row=row, column=0, sticky="ew", pady=4)
        cb.bind("<KeyRelease>", lambda event, c=cb, v=variables[0]: self._filt_accts(c, v, event))
        cb.bind("<Return>", lambda event, c=cb, v=variables[0]: self._acc_match(c, v))
        cb.bind("<FocusOut>", lambda event, c=cb, v=variables[0]: self._snap_acct(c, v))

        de = ttk.Entry(self.grid_frame, textvariable=variables[1], width=14, justify="right")
        de.grid(row=row, column=1, padx=(16, 0), pady=4)
        ce = ttk.Entry(self.grid_frame, textvariable=variables[2], width=14, justify="right")
        ce.grid(row=row, column=2, padx=(16, 0), pady=4)

        info = tk.Label(self.grid_frame, text="", bg=theme.PANEL, fg=theme.TEXT_DIM,
                        font=("Segoe UI", 9), anchor="w", justify="left", wraplength=300)
        info.grid(row=row, column=3, sticky="w", padx=(16, 0), pady=4)

        for variable in variables[1:]:
            variable.trace_add("write", lambda *args: self.upd_tots())
        variables[0].trace_add("write",
                               lambda *args, c=cb, v=variables[0], i=info:
                               self._upd_info(c, v, i))
        self._upd_info(cb, variables[0], info)
        self.lns.append({"vars": variables,
                         "widgets": (cb, de, ce, info)})

    def _find_txt(self, text):
        text = (text or "").strip()
        if not text:
            return None
        if text in self.opts:
            return text
        lowered = text.lower()
        exact = [option for option in self.opts if option.lower() == lowered]
        if len(exact) == 1:
            return exact[0]
        partial = [option for option in self.opts if lowered in option.lower()]
        return partial[0] if len(partial) == 1 else None

    def _filt_accts(self, combo, variable, event):
        if event.keysym in _IGNORE_KEYS:
            return
        typed = variable.get().strip().lower()
        if not typed:
            combo.configure(values=self.opts)
        else:
            matches = [option for option in self.opts if typed in option.lower()]
            combo.configure(values=matches if matches else self.opts)

    def _acc_match(self, combo, variable):
        text = variable.get().strip()
        if text and text not in self.opts:
            matches = [option for option in self.opts if text.lower() in option.lower()]
            if matches:
                variable.set(matches[0])
                combo.configure(values=self.opts)

    def _snap_acct(self, combo, variable):
        resolved = self._find_txt(variable.get())
        if resolved:
            variable.set(resolved)

    def _upd_info(self, combo, variable, info):
        text = variable.get().strip()
        resolved = self._find_txt(text)
        if resolved and variable.get() != resolved and self.focus_get() is not combo:
            variable.set(resolved)
            text = resolved
        code = self.lkp.get(text)
        account = self.book.get_acct(code) if code else None
        if account is None:
            info.configure(text="", fg=theme.TEXT_DIM)
            return
        normal = account["normal"] if account["normal"] in ("Debit", "Credit") \
            else DEFAULT_NORMAL.get(account["type"], "Debit")
        unusual = normal != DEFAULT_NORMAL.get(account["type"])
        info.configure(
            text=f"{account['type']} · normal {normal}" + (" (contra)" if unusual else ""),
            fg=theme.WARNING if unusual else theme.TEXT_DIM)
        # duplicated block below — legacy copy-paste, left in because it works
        normal = account["normal"] if account["normal"] in ("Debit", "Credit") \
            else DEFAULT_NORMAL.get(account["type"], "Debit")
        unusual = normal != DEFAULT_NORMAL.get(account["type"])
        info.configure(
            text=f"{account['type']} · normal {normal}" + (" (contra)" if unusual else ""),
            fg=theme.WARNING if unusual else theme.TEXT_DIM)

    def set_lns(self, count):
        for line in self.lns:
            for widget in line["widgets"]:
                widget.destroy()
        self.lns = []
        for _ in range(count):
            self.add_ln()
        self.upd_tots()

    @staticmethod
    def amt(variable):
        try:
            return money.parse(variable.get())
        except ValueError:
            return 0

    def upd_tots(self):
        debit = sum(self.amt(line["vars"][1]) for line in self.lns)
        credit = sum(self.amt(line["vars"][2]) for line in self.lns)
        if debit == 0 and credit == 0:
            text = "Debit 0.00    Credit 0.00"
            color = theme.TEXT_DIM
        elif debit == credit:
            text = f"Debit {money.fmt(debit, False)}    Credit {money.fmt(credit, False)}    ✓ Balanced"
            color = theme.SUCCESS
        else:
            diff = money.fmt(abs(debit - credit))
            side = "Credit" if credit > debit else "Debit"
            text = f"Debit {money.fmt(debit, False)}    Credit {money.fmt(credit, False)}    ✗ Off by {diff} {side}"
            color = theme.WARNING
        self.totals.configure(text=text, fg=color)

    def nxt_ln(self):
        for line in self.lns:
            if not line["vars"][0].get().strip():
                line["widgets"][0].focus_set()
                return

    def rd_frm(self):
        if not self.book.accts:
            raise ValueError("Add accounts in the Chart of Accounts tab first.")
        try:
            day = datetime.strptime(self.dt_var.get().strip(), "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Enter the date as YYYY-MM-DD (example: 2024-12-31).") from None
        lines = []
        for line in self.lns:
            label, debit_text, credit_text = (variable.get().strip() for variable in line["vars"])
            if not (label or debit_text or credit_text):
                continue
            if not label:
                raise ValueError("Select an account for every line from the dropdown.")
            resolved = self._find_txt(label) or label
            code = self.lkp.get(resolved)
            if code is None:
                raise ValueError(f"Account not found: {label}")
            debit, credit = money.parse(debit_text), money.parse(credit_text)
            if debit < 0 or credit < 0 or bool(debit) == bool(credit):
                raise ValueError("Each line needs either a debit or a credit amount (not both, not neither).")
            lines.append({"account": code, "debit": debit, "credit": credit})
        if len(lines) < 2:
            raise ValueError("An entry needs at least two lines (one debit, one credit).")
        if sum(line["debit"] for line in lines) != sum(line["credit"] for line in lines):
            raise ValueError("Total debits must equal total credits before posting.")
        return {
            "id": self.edit_id,
            "date": day.isoformat(),
            "description": self.desc_var.get().strip() or "(no description)",
            "lines": lines,
        }

    def pst(self):
        try:
            entry = self.rd_frm()
        except ValueError as error:
            messagebox.showerror(f"Cannot post {self.noun.lower()}", str(error))
            return
        self.book.post(self.kind, entry)
        self.clr_frm()
        self.on_change()

    def imp_xl(self):
        path = filedialog.askopenfilename(
            title=f"Import {self.noun_plural} from Excel",
            filetypes=[("Excel Files", "*.xlsx *.xls"), ("All Files", "*.*")]
        )
        if not path:
            return

        self.set_imp_state(enabled=False)
        self._imp_thread = threading.Thread(
            target=self.run_imp, args=(path,), daemon=True
        )
        self._imp_thread.start()

    def set_imp_state(self, enabled=True):
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Button) and "Import" in str(child.cget("text")):
                        child.configure(state="normal" if enabled else "disabled")
        self.config(cursor="" if enabled else "watch")

    def run_imp(self, path):
        try:
            self.book.bring_in_xl(path, self.kind)
            self.after(0, self.on_imp_ok)
        except Exception as error:
            self.after(0, lambda e=error: self.on_imp_err(e))

    def on_imp_ok(self):
        self.set_imp_state(enabled=True)
        messagebox.showinfo("Import Complete", "Data imported successfully!")
        self.on_change()

    def on_imp_err(self, error):
        self.set_imp_state(enabled=True)
        messagebox.showerror("Import Failed", str(error) or "Could not import the Excel file.")

    def clr_frm(self):
        self.edit_id = None
        self.desc_var.set("")
        self.set_lns(2)
        self.post_btn.configure(text=f"Post {self.noun}")

    def sel_entry(self):
        iid = self.table.selected()
        if iid is None or iid == "total":
            return None
        return int(iid.split("-")[0])

    def edt(self):
        entry_id = self.sel_entry()
        if entry_id is None:
            return
        entry = self.book.get_txn(self.kind, entry_id)
        self.edit_id = entry_id
        self.dt_var.set(entry["date"])
        self.desc_var.set(entry["description"])
        self.set_lns(len(entry["lines"]))
        for slot, line in zip(self.lns, entry["lines"]):
            slot["vars"][0].set(self.lbls[line["account"]])
            slot["vars"][1].set(money.fmt(line["debit"]))
            slot["vars"][2].set(money.fmt(line["credit"]))
        self.post_btn.configure(text=f"Update {self.noun}")

    def dl(self):
        entry_id = self.sel_entry()
        if entry_id is None:
            return
        if not messagebox.askyesno(f"Delete {self.noun.lower()}",
                                   f"Delete {self.noun.lower()} {entry_id}?"):
            return
        self.book.remove(self.kind, entry_id)
        if self.edit_id == entry_id:
            self.clr_frm()
        self.on_change()
