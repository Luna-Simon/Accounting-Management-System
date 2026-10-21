"""
Dashboard Tab — key metrics.
"""

import tkinter as tk
from tkinter import ttk

import money

from accounting import pl as income_stmt
from . import theme
from .widgets import Table, col, Card, StatCard, HelpLabel


class DashTab(ttk.Frame):
    def __init__(self, parent, book, on_change):
        super().__init__(parent, padding=24)
        self.book = book
        self.on_change = on_change

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 24))
        ttk.Label(header, text="Accounting Management System", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Setup Business Information", style="Accent.TButton",
                   command=self.biz_info).pack(side="right")
        ttk.Label(header, text="Overview of your financial data", style="Subtitle.TLabel").pack(anchor="w")

        stats_frame = ttk.Frame(self)
        stats_frame.pack(fill="x", pady=(0, 24))
        for i in range(4):
            stats_frame.columnconfigure(i, weight=1)

        stats = [
            ("Accounts", "accounts", "📊"),
            ("Transactions", "entries", "💰"),
            ("Adjustments", "adjustments", "📝"),
            ("Net Income", "net_income", "💵"),
        ]
        self.stat_cards = {}
        for i, (label, key, icon) in enumerate(stats):
            card = StatCard(stats_frame, label=label, value="0", icon=icon)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
            stats_frame.columnconfigure(i, weight=1)
            self.stat_cards[key] = card

        recent_frame = Card(self, title="Recent Activity")
        recent_frame.pack(fill="both", expand=True)

        self.recent_table = Table(recent_frame, [
            col("Date", 130, "center"),
            col("Type", 120, "center"),
            col("Description", 500, stretch=True),
            col("Amount", 160, "e"),
        ], height=8)
        self.recent_table.pack(fill="both", expand=True)

    def biz_info(self):
        win = tk.Toplevel(self)
        win.title("Business Information")
        win.geometry("420x240")
        win.transient(self)
        win.configure(bg=theme.BG)
        win.grab_set()

        ttk.Label(win, text="Business Information", style="Title.TLabel").pack(pady=(16, 8))

        form = ttk.Frame(win)
        form.pack(padx=24, pady=8, fill="x")

        ttk.Label(form, text="Business name:").grid(row=0, column=0, sticky="w", pady=6)
        biz_var = tk.StringVar(value=self.book.info.get("business", ""))
        ttk.Entry(form, textvariable=biz_var, width=34).grid(row=0, column=1, sticky="w", padx=(12, 0), pady=6)

        ttk.Label(form, text="Reporting period:").grid(row=1, column=0, sticky="w", pady=6)
        period_var = tk.StringVar(value=self.book.info.get("period", ""))
        ttk.Entry(form, textvariable=period_var, width=34).grid(row=1, column=1, sticky="w", padx=(12, 0), pady=6)
        period_hint = ttk.Label(form, text='Example: "January 2024" or "2024-01-01 to 2024-01-31"',
                                style="Muted.TLabel")
        period_hint.grid(row=2, column=1, sticky="w", padx=(12, 0), pady=(0, 10))

        def save():
            self.book.info["business"] = biz_var.get().strip()
            self.book.info["period"] = period_var.get().strip()
            self.book.commit()
            self.reload()
            win.destroy()

        btns = ttk.Frame(win)
        btns.pack(pady=18)
        ttk.Button(btns, text="Save", style="Accent.TButton", command=save).pack(side="left", padx=8)
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="left", padx=8)

    def reload(self):
        self.stat_cards["accounts"].set_value(str(len(self.book.accts)))
        self.stat_cards["entries"].set_value(str(len(self.book.txns)))
        self.stat_cards["adjustments"].set_value(str(len(self.book.adjts)))

        try:
            net = income_stmt(self.book)["net"]
            self.stat_cards["net_income"].set_value(money.fmt(net, False))
        except Exception:
            self.stat_cards["net_income"].set_value("$0.00")

        self.recent_table.clear()
        all_entries = []
        for entry in self.book.txns:
            desc = entry["description"].strip()
            if desc:
                desc = desc[0].upper() + desc[1:] if len(desc) > 1 else desc.upper()
            total = sum(l["debit"] for l in entry["lines"])
            all_entries.append(("Transaction", entry["date"], desc, total))
        for entry in self.book.adjts:
            desc = entry["description"].strip()
            if desc:
                desc = desc[0].upper() + desc[1:] if len(desc) > 1 else desc.upper()
            total = sum(l["debit"] for l in entry["lines"])
            all_entries.append(("Adjustment", entry["date"], desc, total))

        all_entries.sort(key=lambda x: x[1], reverse=True)
        for entry in all_entries[:10]:
            self.recent_table.add((
                entry[1], entry[0], entry[2], money.fmt(entry[3]),
            ))
