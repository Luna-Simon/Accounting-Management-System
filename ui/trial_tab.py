"""
Trial Balance Tab - Clean format matching accounting standards.
Shows Unadjusted/Adjusted toggle with proper formatting.
"""

import tkinter as tk
from tkinter import ttk
from datetime import date

import accounting
import money

from .widgets import Table, col, Card


class TrialTab(ttk.Frame):
    def __init__(self, parent, book, on_change=None):
        super().__init__(parent, padding=16)
        self.book = book
        self.on_change = on_change
        self.view = tk.StringVar(value="unadjusted")

        # Header with title and period
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 8))
        
        title_frame = ttk.Frame(header)
        title_frame.pack(fill="x")
        ttk.Label(title_frame, text="Trial Balance", style="Title.TLabel").pack(side="left")
        
        # Business name and date (from meta)
        self.meta_frame = ttk.Frame(header)
        self.meta_frame.pack(fill="x", pady=(4, 0))
        self.business_label = ttk.Label(self.meta_frame, text="", style="Subtitle.TLabel")
        self.business_label.pack(side="left")
        self.date_label = ttk.Label(self.meta_frame, text="", style="Muted.TLabel")
        self.date_label.pack(side="left", padx=(16, 0))
        
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

        # Column headers label
        col_header = ttk.Frame(self)
        col_header.pack(fill="x", pady=(0, 4))
        ttk.Label(col_header, text="Account Titles", style="Muted.TLabel").pack(side="left", padx=(0, 200))
        ttk.Label(col_header, text="Debit", style="Muted.TLabel").pack(side="right", padx=(0, 40))
        ttk.Label(col_header, text="Credit", style="Muted.TLabel").pack(side="right")

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
        # Update meta info
        business = self.book.meta.get("business", "")
        period = self.book.meta.get("period", "")
        if business:
            self.business_label.configure(text=business)
        else:
            self.business_label.configure(text="Business Name")
        if period:
            self.date_label.configure(text=period)
        else:
            self.date_label.configure(text=date.today().strftime("%B %d, %Y"))
        
        # Get trial balance data
        adjusted = self.view.get() == "adjusted"
        rows = accounting.trial_balance(self.book, adjusted)
        self.table.clear()
        
        # Add rows - only show accounts with balances
        for account, debit, credit in rows:
            if debit == 0 and credit == 0:
                continue
            tags = ("debit",) if debit > 0 else ("credit",) if credit > 0 else ()
            # Show account name without code prefix in the name column
            self.table.add((account["code"], account["name"], money.fmt(debit), money.fmt(credit)), tags)
        
        total_debit = sum(row[1] for row in rows)
        total_credit = sum(row[2] for row in rows)
        self.table.add(("", "Total", money.fmt(total_debit, False), money.fmt(total_credit, False)), ("total",))
        
        if total_debit == total_credit:
            status_text = "✓ Debits equal credits" + (" (Adjusted)" if adjusted else " (Unadjusted)")
            self.status.configure(text=status_text, style="Success.TLabel")
        else:
            difference = money.fmt(abs(total_debit - total_credit), False)
            self.status.configure(text=f"✗ Out of balance by {difference}", style="Error.TLabel")