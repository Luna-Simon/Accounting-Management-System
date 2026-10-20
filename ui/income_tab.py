"""
Income Statement Tab - Modern financial statement view.
"""

import tkinter as tk
from tkinter import ttk

import accounting
import money

from .widgets import Table, col, Card


class IncomeTab(ttk.Frame):
    def __init__(self, parent, book):
        super().__init__(parent, padding=16)
        self.book = book
        self.business = tk.StringVar()
        self.period = tk.StringVar()

        # Header with business/period fields
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 16))
        ttk.Label(header, text="Income Statement", style="Title.TLabel").pack(side="left")
        
        meta_frame = ttk.Frame(header)
        meta_frame.pack(side="right")
        ttk.Label(meta_frame, text="Business:").pack(side="left")
        business = ttk.Entry(meta_frame, textvariable=self.business, width=25)
        business.pack(side="left", padx=(6, 16))
        ttk.Label(meta_frame, text="Period:").pack(side="left")
        period = ttk.Entry(meta_frame, textvariable=self.period, width=30)
        period.pack(side="left", padx=6)
        for entry in (business, period):
            entry.bind("<KeyRelease>", self.save_meta)

        # Statement card
        stmt_card = Card(self, title="")
        stmt_card.pack(fill="both", expand=True)

        self.table = Table(stmt_card, [col("Account", 500, stretch=True), col("Amount", 160, "e"), col("Total", 160, "e")])
        self.table.pack(fill="both", expand=True)

    def save_meta(self, event):
        self.book.meta["business"] = self.business.get()
        self.book.meta["period"] = self.period.get()
        self.book.save()
        self.refresh()

    def refresh(self):
        for variable, key in ((self.business, "business"), (self.period, "period")):
            if variable.get() != self.book.meta[key]:
                variable.set(self.book.meta[key])
        report = accounting.income_statement(self.book)
        table = self.table
        table.clear()

        def row(label, amount="", total="", tags=()):
            table.add((label, amount, total), tags)

        if self.business.get().strip():
            row(self.business.get().strip(), tags=("bold",))
        row("Income Statement", tags=("bold",))
        if self.period.get().strip():
            row(self.period.get().strip())
        row("")

        row("Revenues", tags=("bold",))
        for name, amount in report["revenue"]:
            row("    " + name, money.fmt(amount))
        row("Net Sales" if report["cost"] else "Total Revenues",
            total=money.fmt(report["revenue_total"], False), tags=("bold",))

        if report["cost"]:
            row("Cost of Sales", tags=("bold",))
            for name, amount in report["cost"]:
                row("    " + name, money.fmt(amount))
            row("Total Cost of Sales", total=money.fmt(report["cost_total"], False), tags=("bold",))
            row("Gross Profit", total=money.fmt(report["gross"], False), tags=("bold",))

        row("Expenses", tags=("bold",))
        for name, amount in report["expenses"]:
            row("    " + name, money.fmt(amount))
        row("Total Expenses", total=money.fmt(report["expense_total"], False), tags=("bold",))

        net = report["net"]
        row("Net Income" if net >= 0 else "Net Loss", total=money.fmt(net, False), tags=("total",))