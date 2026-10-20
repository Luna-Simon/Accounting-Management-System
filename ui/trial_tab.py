"""
Trial Balance Tab - Modern toggle between unadjusted/adjusted.
"""

import tkinter as tk
from tkinter import ttk

import accounting
import money

from .widgets import Table, col, Card


class TrialTab(ttk.Frame):
    def __init__(self, parent, book):
        super().__init__(parent, padding=16)
        self.book = book
        self.view = tk.StringVar(value="unadjusted")

        # Header
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 16))
        ttk.Label(header, text="Trial Balance", style="Title.TLabel").pack(side="left")
        
        # View toggle
        toggle = ttk.Frame(header)
        toggle.pack(side="right")
        ttk.Radiobutton(toggle, text="Unadjusted", value="unadjusted", variable=self.view,
                        command=self.refresh).pack(side="left", padx=8)
        ttk.Radiobutton(toggle, text="Adjusted", value="adjusted", variable=self.view,
                        command=self.refresh).pack(side="left", padx=8)

        # Status
        self.status = ttk.Label(self, style="Muted.TLabel")
        self.status.pack(fill="x", pady=(0, 8))

        # Table
        table_card = Card(self, title="")
        table_card.pack(fill="both", expand=True)

        self.table = Table(table_card, [
            col("Code", 90, "center"),
            col("Account", 450, stretch=True),
            col("Debit", 160, "e"),
            col("Credit", 160, "e"),
        ])
        self.table.pack(fill="both", expand=True)

    def refresh(self):
        rows = accounting.trial_balance(self.book, self.view.get() == "adjusted")
        self.table.clear()
        for account, debit, credit in rows:
            tags = ("debit",) if debit > 0 else ("credit",) if credit > 0 else ()
            self.table.add((account["code"], account["name"], money.fmt(debit), money.fmt(credit)), tags)
        total_debit = sum(row[1] for row in rows)
        total_credit = sum(row[2] for row in rows)
        self.table.add(("", "Total", money.fmt(total_debit, False), money.fmt(total_credit, False)), ("total",))
        
        if total_debit == total_credit:
            self.status.configure(text="✓ Debits equal credits", style="Success.TLabel")
        else:
            difference = money.fmt(abs(total_debit - total_credit), False)
            self.status.configure(text=f"✗ Out of balance by {difference}", style="Error.TLabel")