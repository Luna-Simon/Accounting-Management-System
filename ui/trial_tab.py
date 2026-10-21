"""
Trial Balance Tab — Unadjusted / Adjusted toggle.
Worksheet + Income Statement / Balance Sheet reports.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

import accounting
import money

from . import theme
from .widgets import Table, col, Card, HelpLabel


class TBTab(ttk.Frame):
    def __init__(self, parent, book, on_change=None):
        super().__init__(parent, padding=16)
        self.book = book
        self.on_change = on_change
        self.vw = tk.StringVar(value="unadjusted")

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 16))

        title_frame = ttk.Frame(header)
        title_frame.pack(fill="x")
        ttk.Label(title_frame, text="Trial Balance & Worksheet", style="Title.TLabel").pack(side="left")

        self.meta_fr = ttk.Frame(header)
        self.meta_fr.pack(fill="x", pady=(10, 0))
        self.biz_lbl = ttk.Label(self.meta_fr, text="Business Name", style="Subtitle.TLabel")
        self.biz_lbl.pack(side="left")
        self.dt_lbl = ttk.Label(self.meta_fr, text="", style="MutedCard.TLabel")
        self.dt_lbl.pack(side="left", padx=(24, 0))

        controls = ttk.Frame(header)
        controls.pack(side="right")
        ttk.Label(controls, text="View:", style="MutedCard.TLabel").pack(side="left", padx=(0, 8))
        ttk.Radiobutton(controls, text="Unadjusted", value="unadjusted", variable=self.vw,
                        command=self.reload).pack(side="left", padx=6)
        ttk.Radiobutton(controls, text="Adjusted", value="adjusted", variable=self.vw,
                        command=self.reload).pack(side="left", padx=6)
        ttk.Button(controls, text="Depreciation…", style="Ghost.TButton",
                   command=self.open_dep).pack(side="left", padx=(16, 0))
        ttk.Button(controls, text="Income Statement", style="Ghost.TButton",
                   command=self.show_pl).pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="Balance Sheet", style="Ghost.TButton",
                   command=self.show_bs).pack(side="left", padx=(8, 0))

        self.status = ttk.Label(self, text="", style="Muted.TLabel")
        self.status.pack(fill="x", pady=(0, 12))

        table_card = Card(self, title="Worksheet — Trial Balance → Adjustments → Adjusted Trial Balance")
        table_card.pack(fill="both", expand=True)

        self.table = Table(table_card, [
            col("Code", 90, "center"),
            col("Account", 300, stretch=True),
            col("Type", 110, "center"),
            col("TB Debit", 110, "e"),
            col("TB Credit", 110, "e"),
            col("Adj Debit", 110, "e"),
            col("Adj Credit", 110, "e"),
            col("Adj TB Debit", 120, "e"),
            col("Adj TB Credit", 120, "e"),
        ])
        self.table.pack(fill="both", expand=True)

        self.totals_fr = ttk.Frame(self)
        self.totals_fr.pack(fill="x", pady=(12, 0))
        self.total_lbls = {}
        total_cols = [
            ("TB Debit", "total_tb_dr"), ("TB Credit", "total_tb_cr"),
            ("Adj Debit", "total_adj_dr"), ("Adj Credit", "total_adj_cr"),
            ("Adj TB Debit", "total_adj_tb_dr"), ("Adj TB Credit", "total_adj_tb_cr"),
        ]
        for i, (label_text, var_name) in enumerate(total_cols):
            lbl = ttk.Label(self.totals_fr, text=f"{label_text}: 0.00", style="MutedCard.TLabel")
            lbl.pack(side="left", padx=(0, 20))
            self.total_lbls[var_name] = lbl

    def open_dep(self):
        win = tk.Toplevel(self)
        win.title("Depreciation Expense")
        win.geometry("520x360")
        win.transient(self)
        win.configure(bg=theme.BG)
        win.grab_set()

        ttk.Label(win, text="Depreciation Expense (Straight-Line)", style="CardTitle.TLabel").pack(pady=(16, 8))
        HelpLabel(win, text="(Cost − Residual Value) ÷ Useful Life = Annual Depreciation").pack(pady=(0, 14))

        form = ttk.Frame(win)
        form.pack(padx=24, pady=8, fill="x")

        flds = [
            ("Depreciation Expense Account Code:", "dep_code", ""),
            ("Accumulated Depreciation Account Code:", "acc_code", ""),
            ("Asset Cost:", "cost", "500000"),
            ("Residual / Salvage Value:", "residual", "50000"),
            ("Useful Life (years):", "life", "10"),
            ("Months to depreciate:", "months", "1"),
        ]
        vars_ = {}
        for i, (label_text, var_name, default) in enumerate(flds):
            ttk.Label(form, text=label_text, style="CardTitle.TLabel").grid(
                row=i, column=0, sticky="w", pady=5)
            var = tk.StringVar(value=default)
            vars_[var_name] = var
            ttk.Entry(form, textvariable=var, width=22).grid(
                row=i, column=1, sticky="e", pady=5, padx=(16, 0))

        result_var = tk.StringVar(value="")
        result_label = ttk.Label(win, textvariable=result_var, style="Success.TLabel")
        result_label.pack(pady=(12, 0))

        def calc(*_):
            try:
                cost = float(vars_["cost"].get().replace(",", ""))
                residual = float(vars_["residual"].get().replace(",", ""))
                life = float(vars_["life"].get())
                months = int(vars_["months"].get())
                amt_cents = accounting.calc_dep(cost, residual, life, months)
                amount = amt_cents / 100.0
                annual = accounting.calc_dep(cost, residual, life, 12) / 100.0
                result_var.set(
                    f"Annual: {money.fmt(int(annual * 100), False)}   |   "
                    f"This entry ({months} mo): {money.fmt(amt_cents, False)}"
                )
                win.amt_cents = amt_cents
            except ValueError as e:
                result_var.set(f"Error: {e}")
                win.amt_cents = 0

        for var in vars_.values():
            var.trace_add("write", calc)
        calc()

        btns = ttk.Frame(win)
        btns.pack(pady=18)

        def post_dep():
            amt_cents = getattr(win, "amt_cents", 0)
            if amt_cents <= 0:
                messagebox.showerror("Depreciation", "Compute a valid amount first.")
                return
            dep_code = vars_["dep_code"].get().strip()
            acc_code = vars_["acc_code"].get().strip()
            if not dep_code or not acc_code:
                messagebox.showerror("Depreciation", "Enter both account codes.")
                return
            if not self.book.get_acct(dep_code):
                self.book.add_acct({
                    "code": dep_code, "name": "Depreciation Expense",
                    "type": "Expense", "normal": "Debit",
                })
            if not self.book.get_acct(acc_code):
                self.book.add_acct({
                    "code": acc_code, "name": "Accumulated Depreciation",
                    "type": "Asset", "normal": "Credit",
                })
            entry = accounting.make_dep(dep_code, acc_code, amt_cents,
                                        f"Depreciation expense ({vars_['months'].get()} month(s))")
            entry["date"] = date.today().isoformat()
            self.book.post("adjts", entry)
            self.reload()
            self.on_change()
            win.destroy()

        ttk.Button(btns, text="Post as Adjustment", style="Accent.TButton",
                   command=post_dep).pack(side="left", padx=8)
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="left", padx=8)

    def rpt_win(self, title, lines, total_label, total_value):
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("560x420")
        win.transient(self)
        win.configure(bg=theme.BG)
        win.grab_set()

        ttk.Label(win, text=title, style="Title.TLabel").pack(pady=(16, 8))
        business = self.book.info.get("business", "")
        if business:
            ttk.Label(win, text=business, style="Subtitle.TLabel").pack(pady=(0, 4))

        table_card = Card(win, title=title)
        table_card.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        table = Table(table_card, [
            col("Account", 340, stretch=True),
            col("Amount", 140, "e"),
        ], height=14)
        table.pack(fill="both", expand=True)
        for name, amount in lines:
            table.add((name, money.fmt(amount)))
        table.add((total_label, money.fmt(total_value, False)), ("total",))

        ttk.Button(win, text="Close", command=win.destroy).pack(pady=(0, 16))

    def show_pl(self):
        data = accounting.pl(self.book)
        lines = []
        for name, amount in data["revenue"]:
            lines.append((name, amount))
        lines.append(("Total Revenue", data["revenue_total"]))
        lines.append(("", 0))
        for name, amount in data["cost"]:
            lines.append((name, -amount))
        lines.append(("Total Cost of Sales", -data["cost_total"]))
        lines.append(("Gross Profit", data["gross"]))
        lines.append(("", 0))
        for name, amount in data["expenses"]:
            lines.append((name, -amount))
        lines.append(("Total Expenses", -data["expense_total"]))
        lines.append(("Net Income", data["net"]))
        self.rpt_win("Income Statement", lines, "Net Income", data["net"])

    def show_bs(self):
        data = accounting.bs(self.book)
        lines = []
        lines.append(("Assets", 0))
        for name, amount in data["assets"]:
            lines.append((f"   {name}", amount))
        lines.append(("Total Assets", data["asset_total"]))
        lines.append(("", 0))
        lines.append(("Liabilities", 0))
        for name, amount in data["liabilities"]:
            lines.append((f"   {name}", amount))
        lines.append(("Total Liabilities", data["liability_total"]))
        lines.append(("", 0))
        lines.append(("Equity", 0))
        for name, amount in data["equity"]:
            lines.append((f"   {name}", amount))
        lines.append(("Net Income (current period)", data["net_income"]))
        lines.append(("Total Equity", data["equity_total"]))
        lines.append(("", 0))
        lines.append(("Total Liabilities & Equity", data["total_liabilities_equity"]))
        self.rpt_win("Balance Sheet", lines,
                     "Total Liabilities & Equity", data["total_liabilities_equity"])

    def reload(self):
        business = self.book.info.get("business", "")
        period = self.book.info.get("period", "")
        self.biz_lbl.configure(text=business if business else "Business Name")
        self.dt_lbl.configure(text=period if period else date.today().strftime("%B %d, %Y"))

        adjusted = self.vw.get() == "adjusted"
        rows = accounting.ws_detail(self.book)
        self.table.clear()

        total_tb_dr = total_tb_cr = 0
        total_adj_dr = total_adj_cr = 0
        total_adj_tb_dr = total_adj_tb_cr = 0

        for row in rows:
            account = row["account"]
            code = account["code"]
            name = account["name"]
            atype = account["type"]

            tb_dr, tb_cr = row["tb_dr"], row["tb_cr"]
            adj_dr, adj_cr = row["adj_dr"], row["adj_cr"]
            adj_tb_dr, adj_tb_cr = row["adj_tb_dr"], row["adj_tb_cr"]

            if tb_dr == 0 and tb_cr == 0 and adj_dr == 0 and adj_cr == 0:
                continue

            tags = ()
            if tb_dr > 0:
                tags += ("debit",)
            elif tb_cr > 0:
                tags += ("credit",)
            if adj_dr > 0 or adj_cr > 0:
                tags += ("adj",)

            self.table.add((
                code, name, atype,
                money.fmt(tb_dr), money.fmt(tb_cr),
                money.fmt(adj_dr), money.fmt(adj_cr),
                money.fmt(adj_tb_dr), money.fmt(adj_tb_cr),
            ), tags)

            total_tb_dr += tb_dr
            total_tb_cr += tb_cr
            total_adj_dr += adj_dr
            total_adj_cr += adj_cr
            total_adj_tb_dr += adj_tb_dr
            total_adj_tb_cr += adj_tb_cr

        self.table.add(("", "Totals", "", money.fmt(total_tb_dr, False), money.fmt(total_tb_cr, False),
                        money.fmt(total_adj_dr, False), money.fmt(total_adj_cr, False),
                        money.fmt(total_adj_tb_dr, False), money.fmt(total_adj_tb_cr, False)),
                       ("total",))

        self.total_lbls["total_tb_dr"].configure(text=f"TB Debit: {money.fmt(total_tb_dr, False)}")
        self.total_lbls["total_tb_cr"].configure(text=f"TB Credit: {money.fmt(total_tb_cr, False)}")
        self.total_lbls["total_adj_dr"].configure(text=f"Adj Debit: {money.fmt(total_adj_dr, False)}")
        self.total_lbls["total_adj_cr"].configure(text=f"Adj Credit: {money.fmt(total_adj_cr, False)}")
        self.total_lbls["total_adj_tb_dr"].configure(text=f"Adj TB Debit: {money.fmt(total_adj_tb_dr, False)}")
        self.total_lbls["total_adj_tb_cr"].configure(text=f"Adj TB Credit: {money.fmt(total_adj_tb_cr, False)}")

        if total_tb_dr == total_tb_cr:
            tb_status = "✓ Unadjusted trial balance is in balance"
        else:
            diff = money.fmt(abs(total_tb_dr - total_tb_cr), False)
            tb_status = f"✗ Unadjusted out of balance by {diff}"

        if total_adj_tb_dr == total_adj_tb_cr:
            adj_status = "✓ Adjusted trial balance is in balance"
        else:
            diff = money.fmt(abs(total_adj_tb_dr - total_adj_tb_cr), False)
            adj_status = f"✗ Adjusted out of balance by {diff}"

        combined = f"{tb_status}    |    {adj_status}"
        if adjusted:
            combined = f"Adjusted view: {adj_status}    |    {tb_status}"
        self.status.configure(text=combined)
